from flask import Flask, render_template, request, redirect, url_for, make_response
import query as q
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

try:
    import openai
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

app = Flask(__name__)

# Feature flags / protection
DEBUG_SAMPLE_ENABLED = os.environ.get('DEBUG_SAMPLE_ENABLED', 'true').lower() in ('1', 'true', 'yes')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
PDF_ENABLED = os.environ.get('PDF_ENABLED', 'true').lower() in ('1', 'true', 'yes')

# Load vector DB if available
try:
    vectordb = q.load_index()
    load_error = None
except Exception as e:
    vectordb = None
    load_error = str(e)

# Diary storage
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DIARY_FILE = DATA_DIR / "diary.json"


def load_diary():
    if not DIARY_FILE.exists():
        return []
    try:
        return json.loads(DIARY_FILE.read_text(encoding='utf8'))
    except Exception:
        return []


def save_diary(entries):
    DIARY_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf8')


def compute_dashboard(entries, days=7):
    today = datetime.utcnow().date()
    cutoff = today - timedelta(days=days - 1)
    recent = [e for e in entries if datetime.fromisoformat(e['date']).date() >= cutoff]

    symptom_free = 0
    night_symptoms = 0
    activity_limited = 0
    exposures = {}

    for e in recent:
        if e.get('breathing') == 'Good' and e.get('symptoms') in ('None', 'None'):
            symptom_free += 1
        if e.get('night_symptoms') == 'Yes':
            night_symptoms += 1
        if e.get('activity') in ('Limited', 'Limited '):
            activity_limited += 1
        for ex in e.get('exposures', []):
            exposures[ex] = exposures.get(ex, 0) + 1

    sorted_exposures = sorted(exposures.items(), key=lambda x: x[1], reverse=True)

    # control status heuristic: fraction of symptom-free days
    total = max(1, len(recent))
    frac_free = symptom_free / total
    if frac_free >= 0.8:
        control_status = 'good'
    elif frac_free >= 0.5:
        control_status = 'ok'
    else:
        control_status = 'bad'

    return {
        'period_days': days,
        'total_days': len(recent),
        'symptom_free_days': symptom_free,
        'night_symptoms': night_symptoms,
        'activity_limited': activity_limited,
        'exposures': sorted_exposures,
        'control_status': control_status,
    }


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', load_error=load_error)


@app.route('/diary', methods=['GET', 'POST'])
def diary():
    entries = load_diary()
    message = None
    if request.method == 'POST':
        # collect form
        entry = {
            'date': request.form.get('date') or datetime.utcnow().isoformat(),
            'breathing': request.form.get('breathing'),
            'symptoms': request.form.get('symptoms'),
            'night_symptoms': request.form.get('night_symptoms'),
            'activity': request.form.get('activity'),
            'medication': request.form.get('medication'),
            'exposures': request.form.getlist('exposures'),
            'notes': request.form.get('notes', '').strip(),
        }
        entries.insert(0, entry)
        save_diary(entries)
        # redirect with a flag so the page can show a toast/message
        return redirect(url_for('diary', saved=1))

    # show last 14 entries
    saved = request.args.get('saved')
    return render_template('diary.html', entries=entries[:14], saved=saved)


@app.route('/dashboard')
def dashboard():
    entries = load_diary()
    week = compute_dashboard(entries, days=7)
    month = compute_dashboard(entries, days=30)

    # doctor summary using last 30 days
    doctor_summary = {
        'symptom_days_30': month['total_days'] - month['symptom_free_days'],
        'night_symptoms_30': month['night_symptoms'],
        'activity_limit_30': month['activity_limited'],
        'top_exposures_30': month['exposures'][:5],
    }

    return render_template('dashboard.html', week=week, month=month, doctor_summary=doctor_summary)


@app.route('/ask_form')
def ask_form():
    return render_template('rag.html', results=None, question=None, error=None, load_error=load_error)


@app.route('/ask', methods=['POST'])
def ask():
    question = request.form.get('question', '').strip()
    k = int(request.form.get('k', 3))
    source = request.form.get('source') or None
    age_group = request.form.get('age_group') or None
    topic = request.form.get('topic') or None
    use_source_aware = request.form.get('source_aware') == 'on'

    results = None
    error = None

    if not vectordb:
        error = f"Vector DB not loaded: {load_error}"
    elif not question:
        error = "Please provide a question."
    else:
        try:
            if use_source_aware and age_group == '0-19':
                results = q.source_aware_retrieve(vectordb, question, age_group=age_group, k=k)
            else:
                results = q.retrieve(vectordb, question, k=k, source=source, age_group=age_group, topic=topic)
        except Exception as e:
            error = str(e)

        # attempt LLM summary if available
        llm_out = None
        if not error:
            llm_out = None
            if os.environ.get('OPENAI_API_KEY') and OPENAI_AVAILABLE:
                llm_out = call_openai_summary(question, results)

        return render_template('rag.html', results=results, question=question, error=error, load_error=load_error, synthesized=None, llm_out=llm_out)


def synthesize_answer(results, max_chars=800):
    """Simple local synthesizer: concatenates top passages and adds citations.
    If results is a mapping (source-aware), synthesizes per-source."""
    def synth_from_list(items):
        parts = []
        citations = []
        for i, (doc, score) in enumerate(items):
            text = (doc.page_content or '').strip().replace('\n', ' ')
            snippet = text[:300]
            parts.append(snippet)
            citations.append(f"{doc.metadata.get('document_name')} p.{doc.metadata.get('page_number')}")
            if sum(len(p) for p in parts) > max_chars:
                break
        summary = ' '.join(parts)
        return summary, citations

    if not results:
        return None

    if isinstance(results, dict):
        out = {}
        for src, items in results.items():
            summary, citations = synth_from_list(items)
            out[src] = {'summary': summary, 'citations': citations}
        return out
    else:
        summary, citations = synth_from_list(results)
        return {'summary': summary, 'citations': citations}


def call_openai_summary(question, results, max_tokens=300):
    """Call OpenAI to generate an abstractive summary with citations.
    Expects OPENAI_API_KEY to be set in environment. Returns dict similar to synthesize_answer but with 'llm' key."""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key or not OPENAI_AVAILABLE:
        return None

    openai.api_key = api_key

    # Prepare passages
    passages = []
    if isinstance(results, dict):
        for src, items in results.items():
            for doc, score in items:
                text = (doc.page_content or '').replace('\n', ' ')
                citations = f"{doc.metadata.get('document_name')} p.{doc.metadata.get('page_number')}"
                passages.append(f"[{citations}] {text[:800]}")
    else:
        for doc, score in results:
            text = (doc.page_content or '').replace('\n', ' ')
            citations = f"{doc.metadata.get('document_name')} p.{doc.metadata.get('page_number')}"
            passages.append(f"[{citations}] {text[:800]}")

    prompt = (
        f"You are a clinical assistant. The user question is:\n{question}\n\nThe following extracted guideline passages are provided (each prefixed by citation):\n"
        + "\n\n".join(passages[:6])
        + (
            "\n\nTask: Write a concise, patient-facing answer in Arabic (3-5 short sentences). "
            "Then list the citations on a separate line prefixed 'Citations:'. "
            "Be conservative: only state conclusions that are directly supported by the provided passages. "
            "Avoid hallucination or adding outside knowledge. If the passages are insufficient, say you couldn't find a clear guideline answer and suggest the user consult their clinician."
        )
    )

    try:
        resp = openai.ChatCompletion.create(
            model=os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.0,
        )
        text = resp['choices'][0]['message']['content'].strip()
        # Basic safety: require the model to include a 'Citations:' line. If not present,
        # fall back to local synthesizer behavior (caller can handle None).
        if 'citations:' in text.lower() or 'citations :' in text.lower() or 'citation' in text.lower():
            return {'llm': text}
        else:
            # don't return potentially hallucinated LLM output without citations
            return None
    except Exception:
        return None


@app.route('/synthesize', methods=['POST'])
def synthesize():
    # reuse ask inputs but always synthesize
    question = request.form.get('question', '').strip()
    k = int(request.form.get('k', 3))
    source = request.form.get('source') or None
    age_group = request.form.get('age_group') or None
    topic = request.form.get('topic') or None
    use_source_aware = request.form.get('source_aware') == 'on'

    if not vectordb:
        return render_template('rag.html', results=None, question=question,
                               error=f"Vector DB not loaded: {load_error}", load_error=load_error)

    try:
        if use_source_aware and age_group == '0-19':
            results = q.source_aware_retrieve(vectordb, question, age_group=age_group, k=k)
        else:
            results = q.retrieve(vectordb, question, k=k, source=source, age_group=age_group, topic=topic)
    except Exception as e:
        return render_template('rag.html', results=None, question=question, error=str(e), load_error=load_error)

    synthesized = synthesize_answer(results)
    return render_template('rag.html', results=results, question=question, synthesized=synthesized, load_error=load_error)


@app.route('/export/doctor_summary')
def export_doctor_summary():
    entries = load_diary()
    month = compute_dashboard(entries, days=30)
    doctor_summary = {
        'symptom_days_30': month['total_days'] - month['symptom_free_days'],
        'night_symptoms_30': month['night_symptoms'],
        'activity_limit_30': month['activity_limited'],
        'top_exposures_30': month['exposures'][:10],
        'generated_at': datetime.utcnow().isoformat(),
    }
    return render_template('export_doctor_summary.html', summary=doctor_summary)


@app.route('/export/doctor_summary.pdf')
def export_doctor_summary_pdf():
    # Try to generate PDF via pdfkit if available
    html = export_doctor_summary().get_data(as_text=True)
    try:
        import pdfkit
        pdf = pdfkit.from_string(html, False)
        return (pdf, 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': 'attachment; filename="doctor_summary.pdf"'
        })
    except Exception as e:
        # Fall back to HTML with notice
        return html + f"\n<!-- PDF generation failed: {e} -->"


@app.route('/debug/sample')
def debug_sample():
    """Generate a sample LLM/summary and attempt to save a PDF to outputs/ for quick verification."""
    # sample question in Arabic to exercise Arabic prompt
    question = "ما هي التوصيات الأساسية لإدارة نوبة الربو لدى البالغين؟"

    results = None
    if vectordb:
        try:
            results = q.retrieve(vectordb, question, k=3)
        except Exception:
            results = None

    # protect endpoint by flag or admin password
    if not DEBUG_SAMPLE_ENABLED:
        return "Not Found", 404
    if ADMIN_PASSWORD:
        token = request.args.get('admin')
        if not token or token != ADMIN_PASSWORD:
            return "Unauthorized", 401

    # prefer OpenAI if available
    llm_out = None
    synthesized = None
    if os.environ.get('OPENAI_API_KEY') and OPENAI_AVAILABLE:
        llm_out = call_openai_summary(question, results)
    if not llm_out:
        synthesized = synthesize_answer(results)

    # prepare a small summary object to render
    summary_obj = {
        'generated_at': datetime.utcnow().isoformat(),
        'question': question,
        'llm': llm_out.get('llm') if llm_out else None,
        'synthesized': synthesized,
    }

    html = render_template('export_doctor_summary.html', summary=summary_obj)

    # Ensure outputs dir
    outdir = Path('outputs')
    outdir.mkdir(exist_ok=True)
    pdf_path = outdir / 'sample_doctor_summary.pdf'
    try:
        if not PDF_ENABLED:
            raise RuntimeError('PDF generation disabled via PDF_ENABLED=false')
        import pdfkit
        pdfkit.from_string(html, str(pdf_path))
        return f"Sample PDF generated: {pdf_path}\nAlso returned HTML preview below:\n" + html
    except Exception as e:
        return html + f"\n<!-- PDF generation failed: {e} -->"


if __name__ == '__main__':
    app.run(debug=True, port=5000)
