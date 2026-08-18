"""
AsthmaDaily RAG - Preprocessing
================================
Text cleanup applied to every page BEFORE chunking. PDF-extracted text from
clinical guideline documents (GINA, WHO) has three recurring problems that
hurt retrieval quality if left alone:

1. Hyphenated words broken across a line wrap ("manage-\nment" -> "management")
2. Repeated boilerplate (running headers, footers, sidebar table-of-contents
   text, "COPYRIGHTED MATERIAL - DO NOT COPY OR DISTRIBUTE", bare page
   numbers) that shows up on almost every page and pollutes every chunk that
   happens to start or end near a page boundary.
3. Irregular whitespace / control characters from the PDF's internal layout
   (multiple spaces, stray newlines mid-sentence, non-breaking spaces).

All three are fixed here, per source document (GINA and WHO have different
boilerplate), before chunking ever sees the text.
"""
import re
import unicodedata
from collections import Counter

# A line is considered "boilerplate" if it is short and repeats across a large
# fraction of a document's pages (running headers/footers do exactly this;
# real body-text sentences essentially never repeat verbatim page after page).
BOILERPLATE_MAX_LEN = 90
BOILERPLATE_MIN_PAGE_FRACTION = 0.15


def _fix_hyphenation(text: str) -> str:
    """Join words that were split across a line-wrap with a hyphen, e.g.
    'bronchodila-\ntor' -> 'bronchodilator'. Only fires on lowercase-to-lowercase
    joins to avoid merging real end-of-sentence hyphens or acronyms."""
    return re.sub(r"([a-z])-\n([a-z])", r"\1\2", text)


def _normalize_unicode(text: str) -> str:
    """Normalize curly quotes/dashes and unicode composition artifacts."""
    text = unicodedata.normalize("NFKC", text)
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u00a0": " ", "\u2022": "- ",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def _collapse_whitespace(text: str) -> str:
    """Collapse runs of spaces/tabs, but keep paragraph breaks (\n\n) intact
    so the section-aware splitter can still use them as split points."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_page_text(text: str) -> str:
    """Per-page cleanup: hyphenation fix -> unicode normalization -> whitespace
    collapse. Boilerplate removal happens separately across the whole
    document (see remove_boilerplate_lines) because it needs cross-page
    frequency counts."""
    text = _fix_hyphenation(text)
    text = _normalize_unicode(text)
    text = _collapse_whitespace(text)
    return text


def _is_probably_boilerplate_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if len(stripped) <= BOILERPLATE_MAX_LEN:
        return True
    return False


def remove_boilerplate_lines(pages):
    """Detects lines that repeat across many pages of the SAME document
    (running headers, footers, sidebar nav text, bare page numbers,
    copyright notices) and strips them out. Operates per document_name so
    GINA's boilerplate doesn't get compared against WHO's.

    Mutates page.page_content in place and returns the same list for
    convenience.
    """
    by_doc = {}
    for page in pages:
        doc = page.metadata.get("document_name", "UNKNOWN")
        by_doc.setdefault(doc, []).append(page)

    for doc, doc_pages in by_doc.items():
        n_pages = len(doc_pages)
        line_counts = Counter()
        for page in doc_pages:
            candidate_lines = {
                ln.strip() for ln in page.page_content.split("\n")
                if _is_probably_boilerplate_line(ln)
            }
            line_counts.update(candidate_lines)

        min_occurrences = max(3, int(n_pages * BOILERPLATE_MIN_PAGE_FRACTION))
        boilerplate_lines = {
            ln for ln, count in line_counts.items()
            if ln and count >= min_occurrences
        }
        # Also drop bare page-number-only lines (e.g. "26", "- 26 -")
        page_number_pattern = re.compile(r"^-?\s*\d{1,4}\s*-?$")

        for page in doc_pages:
            kept = []
            for ln in page.page_content.split("\n"):
                s = ln.strip()
                if s in boilerplate_lines:
                    continue
                if page_number_pattern.match(s):
                    continue
                kept.append(ln)
            page.page_content = _collapse_whitespace("\n".join(kept))

    return pages


def preprocess_pages(pages):
    """Full preprocessing pipeline applied to a list of LangChain Documents
    (one per PDF page, already carrying document_name/source metadata from
    ingest.load_pdfs). Returns the same list, mutated in place."""
    for page in pages:
        page.page_content = clean_page_text(page.page_content)
    remove_boilerplate_lines(pages)
    return pages
