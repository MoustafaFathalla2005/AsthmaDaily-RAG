"""
AsthmaDaily - Translations
===========================
Single source of truth for every user-facing string in the app.

The old templates hard-coded Arabic in some places and English in others,
so a page never fully switched language - the language toggle just added
more mixing. This module fixes that: every string the UI shows lives here,
under both an 'en' and an 'ar' key, and templates only ever call `t('key')`
(injected as a Jinja global by webapp.py's context processor). Switching
`?lang=en` / `?lang=ar` now switches 100% of the page, not just some labels.

Keep keys grouped by page/section (comments below) so it's easy to find the
right spot when a new string needs to be added - add it to BOTH languages
at the same time so nothing is ever left half-translated again.
"""

TRANSLATIONS = {
    "en": {
        # --- Common / nav ---
        "brand": "AsthmaDaily",
        "nav_diary": "Daily Diary",
        "nav_dashboard": "Dashboard",
        "nav_ask": "Clinical Q&A",
        "nav_home": "Home",
        "toast_saved": "Entry saved",

        # --- Home ---
        "home_tagline": "Log how you're doing in under a minute — and get answers grounded in trusted clinical guidelines.",
        "home_cta_diary": "Log today",
        "home_cta_dashboard": "View dashboard",
        "home_cta_ask": "Ask the guidelines",
        "home_feature_diary_title": "Quick daily check-in",
        "home_feature_diary_body": "Track symptoms, night waking, activity limits and exposures in seconds.",
        "home_feature_dashboard_title": "See your patterns",
        "home_feature_dashboard_body": "A weekly control score and your most common exposure triggers, at a glance.",
        "home_feature_ask_title": "Ask with confidence",
        "home_feature_ask_body": "Every answer is grounded in GINA and WHO guidelines, with page-level citations.",

        # --- Diary ---
        "diary_title": "Daily Diary",
        "diary_subtitle": "Quick daily check-in. Takes about 30-60 seconds.",
        "diary_date": "Date",
        "diary_breathing": "Breathing",
        "diary_breathing_good": "Good",
        "diary_breathing_okay": "Okay",
        "diary_breathing_bad": "Bad",
        "diary_symptoms": "Symptoms",
        "diary_symptoms_none": "None",
        "diary_symptoms_mild": "Mild",
        "diary_symptoms_severe": "Severe",
        "diary_night": "Night symptoms",
        "diary_night_no": "No",
        "diary_night_yes": "Yes",
        "diary_activity": "Activity",
        "diary_activity_normal": "Normal",
        "diary_activity_limited": "Limited",
        "diary_medication": "Medication",
        "diary_med_prescribed": "As prescribed",
        "diary_med_missed": "Missed",
        "diary_exposures_label": "Possible exposures (choose all that apply)",
        "exposure_Dust": "Dust",
        "exposure_Smoke": "Smoke",
        "exposure_Pets": "Pets",
        "exposure_Exercise": "Exercise",
        "exposure_Cold air": "Cold air",
        "exposure_Strong smells": "Strong smells",
        "exposure_Air pollution": "Air pollution",
        "diary_notes": "Notes (optional)",
        "diary_save": "Save entry",
        "diary_recent": "Recent entries",
        "diary_no_entries": "No entries yet. Start by adding today's check-in.",
        "diary_exposures_prefix": "Exposures:",
        "choose": "Choose...",

        # --- Dashboard ---
        "dashboard_title": "Dashboard",
        "dashboard_subtitle": "Quick overview of your recent asthma control and potential patterns.",
        "dashboard_this_week": "This week",
        "dashboard_good": "Good",
        "dashboard_fair": "Fair",
        "dashboard_poor": "Poor",
        "dashboard_symptom_free_days": "Symptom-free days",
        "dashboard_night_symptoms": "Night symptoms",
        "dashboard_activity_limited": "Activity limitations",
        "dashboard_patterns_title": "Potential patterns (top exposures)",
        "dashboard_no_pattern": "No exposure pattern detected yet.",
        "dashboard_days_suffix": "days",
        "dashboard_doctor_summary_title": "Doctor summary (last 30 days)",
        "dashboard_symptom_days": "Symptom days",
        "dashboard_top_exposures": "Top reported exposures:",
        "dashboard_tip": "Tip: bring this summary to your next appointment.",
        "dashboard_export_pdf": "Download PDF for your doctor",

        # --- Clinical Q&A / RAG ---
        "rag_title": "Clinical Q&A",
        "rag_subtitle": "Ask a question and see retrieved guideline passages with source citations.",
        "rag_placeholder": "Ask simply, e.g. \"Why do my symptoms get worse after exercise?\"",
        "rag_examples": "Examples: \"exercise and asthma\" · \"smoke as trigger\"",
        "rag_search_btn": "Search guidelines",
        "rag_summarize_btn": "Summarize + Cite",
        "rag_advanced": "Advanced options",
        "rag_topk": "Results",
        "rag_source": "Source",
        "rag_source_any": "(any)",
        "rag_age_group": "Age group",
        "rag_age_any": "(any)",
        "rag_llm_title": "Summarized answer (AI)",
        "rag_summarized_title": "Summarized answer",
        "rag_citations": "Citations",
        "rag_no_results": "No results from",
        "rag_source_prefix": "Source:",

        # --- Doctor summary export ---
        "export_generated": "Generated:",
        "export_title": "Patient summary for clinician",
        "export_intro": "This summary shows asthma status and reported exposures over the last 30 days.",
        "export_key_points": "Key points",
        "export_symptom_days": "Symptom days (30d)",
        "export_night_symptoms": "Nights with symptoms",
        "export_activity_days": "Activity-limited days",
        "export_top_exposures": "Most frequent exposures",
        "export_no_exposures": "No exposures recorded.",
        "export_days_suffix": "days",
        "export_print_tip": "Print: use your browser's Print button, or download a PDF copy via /export/doctor_summary.pdf if available.",
    },
    "ar": {
        # --- Common / nav ---
        "brand": "AsthmaDaily",
        "nav_diary": "المذكرة اليومية",
        "nav_dashboard": "لوحة المتابعة",
        "nav_ask": "استشارة الدليل",
        "nav_home": "الرئيسية",
        "toast_saved": "تم حفظ الإدخال",

        # --- Home ---
        "home_tagline": "سجّل حالتك يومياً في أقل من دقيقة، واحصل على إجابات مبنية على إرشادات سريرية موثوقة.",
        "home_cta_diary": "سجّل اليوم",
        "home_cta_dashboard": "عرض لوحة المتابعة",
        "home_cta_ask": "اسأل الدليل",
        "home_feature_diary_title": "تسجيل يومي سريع",
        "home_feature_diary_body": "سجّل الأعراض والاستيقاظ الليلي وقيود النشاط والتعرضات في ثوانٍ.",
        "home_feature_dashboard_title": "شاهد أنماطك",
        "home_feature_dashboard_body": "درجة تحكم أسبوعية وأكثر مسببات التعرض شيوعًا، بنظرة سريعة.",
        "home_feature_ask_title": "اسأل بثقة",
        "home_feature_ask_body": "كل إجابة مبنية على إرشادات GINA وWHO، مع استشهادات بأرقام الصفحات.",

        # --- Diary ---
        "diary_title": "المذكرة اليومية",
        "diary_subtitle": "تسجيل يومي سريع. يستغرق من 30 إلى 60 ثانية تقريبًا.",
        "diary_date": "التاريخ",
        "diary_breathing": "التنفس",
        "diary_breathing_good": "جيد",
        "diary_breathing_okay": "متوسط",
        "diary_breathing_bad": "سيئ",
        "diary_symptoms": "الأعراض",
        "diary_symptoms_none": "لا يوجد",
        "diary_symptoms_mild": "خفيفة",
        "diary_symptoms_severe": "شديدة",
        "diary_night": "أعراض ليلية",
        "diary_night_no": "لا",
        "diary_night_yes": "نعم",
        "diary_activity": "النشاط",
        "diary_activity_normal": "طبيعي",
        "diary_activity_limited": "محدود",
        "diary_medication": "الدواء",
        "diary_med_prescribed": "حسب الوصفة",
        "diary_med_missed": "فائت",
        "diary_exposures_label": "التعرضات المحتملة (اختر كل ما ينطبق)",
        "exposure_Dust": "غبار",
        "exposure_Smoke": "دخان",
        "exposure_Pets": "حيوانات أليفة",
        "exposure_Exercise": "مجهود بدني",
        "exposure_Cold air": "هواء بارد",
        "exposure_Strong smells": "روائح قوية",
        "exposure_Air pollution": "تلوث الهواء",
        "diary_notes": "ملاحظات (اختياري)",
        "diary_save": "حفظ الإدخال",
        "diary_recent": "أحدث الإدخالات",
        "diary_no_entries": "لا توجد إدخالات بعد. ابدأ بإضافة تسجيل اليوم.",
        "diary_exposures_prefix": "التعرضات:",
        "choose": "اختر...",

        # --- Dashboard ---
        "dashboard_title": "لوحة المتابعة",
        "dashboard_subtitle": "نظرة سريعة على تحكمك في الربو مؤخرًا والأنماط المحتملة.",
        "dashboard_this_week": "هذا الأسبوع",
        "dashboard_good": "جيد",
        "dashboard_fair": "متوسط",
        "dashboard_poor": "غير متحكم",
        "dashboard_symptom_free_days": "أيام بلا أعراض",
        "dashboard_night_symptoms": "أعراض ليلية",
        "dashboard_activity_limited": "قيود النشاط",
        "dashboard_patterns_title": "الأنماط المحتملة (أكثر التعرضات)",
        "dashboard_no_pattern": "لم يُكتشف أي نمط تعرض بعد.",
        "dashboard_days_suffix": "أيام",
        "dashboard_doctor_summary_title": "ملخص للطبيب (آخر 30 يومًا)",
        "dashboard_symptom_days": "أيام الأعراض",
        "dashboard_top_exposures": "أكثر التعرضات المُبلَّغ عنها:",
        "dashboard_tip": "نصيحة: أحضر هذا الملخص في موعدك القادم.",
        "dashboard_export_pdf": "تحميل PDF لطبيبك",

        # --- Clinical Q&A / RAG ---
        "rag_title": "استشارة الدليل السريري",
        "rag_subtitle": "اطرح سؤالًا وشاهد المقاطع المسترجعة من الإرشادات مع مصادرها.",
        "rag_placeholder": "اسأل ببساطة، مثل: \"ليه أعراضي بتزيد بعد المجهود؟\"",
        "rag_examples": "أمثلة: \"المجهود والربو\" · \"الدخان كمسبب\"",
        "rag_search_btn": "ابحث في الإرشادات",
        "rag_summarize_btn": "لخّص مع المصادر",
        "rag_advanced": "خيارات متقدمة",
        "rag_topk": "عدد النتائج",
        "rag_source": "المصدر",
        "rag_source_any": "(أي مصدر)",
        "rag_age_group": "الفئة العمرية",
        "rag_age_any": "(أي فئة)",
        "rag_llm_title": "إجابة مُلخّصة (ذكاء اصطناعي)",
        "rag_summarized_title": "إجابة مُلخّصة",
        "rag_citations": "المصادر",
        "rag_no_results": "لا توجد نتائج من",
        "rag_source_prefix": "المصدر:",

        # --- Doctor summary export ---
        "export_generated": "تاريخ الإنشاء:",
        "export_title": "ملخص المريض للطبيب",
        "export_intro": "هذا الملخص يعرض حالة الربو والتعرضات المبلغ عنها خلال آخر 30 يومًا.",
        "export_key_points": "أهم النقاط",
        "export_symptom_days": "أيام الأعراض (30 يوم)",
        "export_night_symptoms": "ليالٍ بها أعراض",
        "export_activity_days": "أيام قيد النشاط",
        "export_top_exposures": "التعرضات الأكثر تكرارًا",
        "export_no_exposures": "لا توجد تعرضات مسجلة.",
        "export_days_suffix": "أيام",
        "export_print_tip": "طباعة: استخدم زر Print في المتصفح، أو حمّل نسخة PDF عبر /export/doctor_summary.pdf إن كان متاحًا.",
    },
}


def get_translator(lang: str):
    """Returns a t(key) function bound to the given language ('en' or 'ar'),
    falling back to English for any missing key and to the raw key itself
    if it's missing from both (so a typo shows up as text, not a crash)."""
    lang = lang if lang in TRANSLATIONS else "en"

    def t(key: str) -> str:
        return TRANSLATIONS[lang].get(key, TRANSLATIONS["en"].get(key, key))

    return t
