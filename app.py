from flask import Flask, request, jsonify, render_template
import re
from collections import Counter
import pdfplumber
import io

app = Flask(__name__)

STOPWORDS = {
    "a","an","the","and","or","but","in","on","at","to","for","of","with","by","from",
    "is","are","was","were","be","been","being","have","has","had","do","does","did",
    "will","would","could","should","may","might","can","this","that","these","those",
    "we","you","they","he","she","it","i","our","your","their","its","my","as","if",
    "not","no","so","up","out","about","into","than","then","when","where","who","which",
    "all","any","both","each","few","more","most","other","some","such","only","own",
    "same","too","very","just","also","well","new","good","high","strong","able",
    "through","during","including","within","between","experience","work","working","team",
    "role","position","job","candidate","required","preferred","must","ability","skills",
    "skill","knowledge","understanding","using","use","used","ensure","help","provide",
    "support","develop","manage","build","create","design","implement","drive","lead",
    "related","relevant","looking","seeking","join","opportunity","across","within"
}

TECH_PHRASES = [
    "machine learning", "deep learning", "natural language processing", "computer vision",
    "data science", "data analysis", "data engineering", "software engineering",
    "web development", "mobile development", "full stack", "front end", "back end",
    "product management", "project management", "agile", "scrum", "ci/cd",
    "cloud computing", "aws", "google cloud", "microsoft azure", "devops",
    "version control", "object oriented", "restful api", "sql database",
    "neural network", "large language model", "artificial intelligence",
    "power bi", "tableau", "microsoft office", "google workspace",
    "circuit design", "embedded systems", "signal processing", "mems",
    "arduino", "raspberry pi", "internet of things", "pcb design",
    "social media", "content creation", "digital marketing", "seo",
    "community management", "brand strategy", "campaign management",
]


def extract_text_from_pdf(file_bytes):
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def extract_keywords(text):
    text_lower = text.lower()
    found_phrases = []
    for phrase in TECH_PHRASES:
        if phrase in text_lower:
            found_phrases.append(phrase)
            text_lower = text_lower.replace(phrase, " ")
    words = re.findall(r'\b[a-z][a-z+#.\-]{1,}\b', text_lower)
    single_keywords = [w for w in words if w not in STOPWORDS and len(w) > 2]
    freq = Counter(single_keywords)
    top_singles = [w for w, _ in freq.most_common(40)]
    return list(dict.fromkeys(found_phrases + top_singles))


def analyze_resume(resume, jd):
    resume_lower = resume.lower()
    jd_keywords = extract_keywords(jd)

    matched, missing = [], []
    for kw in jd_keywords[:30]:
        (matched if kw in resume_lower else missing).append(kw)

    resume_keywords = extract_keywords(resume)
    bonus = [k for k in resume_keywords if k not in jd_keywords][:6]

    score = min(int(len(matched) / max(len(jd_keywords[:30]), 1) * 100), 100)

    suggestions = []
    rules = [
        (len(missing) > 5,
         f"Add these missing keywords naturally: {', '.join(missing[:4])}."),
        (not re.search(r'\d+%|\d+ percent|\d+x|\$\d+|\d+ (users|clients|projects|people|members)', resume_lower),
         "Add quantified achievements (e.g. 'increased engagement by 30%', 'led a team of 5')."),
        (len(resume_lower.split()) < 300,
         "Your resume seems short — expand project descriptions with more detail about your impact."),
        (not any(w in resume_lower for w in ['summary', 'objective', 'profile']),
         "Add a professional summary at the top tailored to this specific role."),
        (any(k in missing for k in ['communication', 'teamwork', 'collaboration', 'leadership']),
         "Highlight soft skills through specific examples in your experience section."),
        (len(matched) < 5,
         "Mirror the exact language in the job description — ATS software scans for specific terms."),
        (not any(w in resume_lower for w in ['github', 'portfolio', 'linkedin']),
         "Add links to your GitHub, portfolio, or LinkedIn."),
        (True,
         "Tailor your bullet points to reflect the responsibilities in this job description."),
    ]

    for condition, suggestion in rules:
        if len(suggestions) >= 5:
            break
        if condition:
            suggestions.append(suggestion)

    if score >= 70:
        verdict = f"Strong match! {len(matched)} of {len(jd_keywords[:30])} key terms present."
    elif score >= 45:
        verdict = "Partial match. A few tweaks could make this a strong application."
    else:
        verdict = "Weak match. Consider tailoring your resume significantly before applying."

    return {
        "score": score,
        "verdict": verdict,
        "matched": matched[:10],
        "missing": missing[:8],
        "bonus": bonus,
        "suggestions": suggestions
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if "resume" not in request.files:
        return jsonify({"error": "Please upload a resume PDF."}), 400

    resume_file = request.files["resume"]
    jd = request.form.get("jd", "").strip()

    if not jd:
        return jsonify({"error": "Please provide a job description."}), 400

    if not resume_file.filename.endswith(".pdf"):
        return jsonify({"error": "Resume must be a PDF file."}), 400

    try:
        resume_text = extract_text_from_pdf(resume_file.read())
    except Exception as e:
        return jsonify({"error": f"Could not read PDF: {str(e)}"}), 400

    if not resume_text:
        return jsonify({"error": "Could not extract text from PDF. Make sure it's not a scanned image."}), 400

    result = analyze_resume(resume_text, jd)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)
