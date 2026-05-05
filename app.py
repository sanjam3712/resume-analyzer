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
    "related","relevant","looking","seeking","join","opportunity","across","within",
    "responsible","responsibilities","qualifications","requirements","minimum","years"
}

HIGH_VALUE_PHRASES = [
    "python","java","javascript","typescript","c++","c#","golang","rust","swift","kotlin","ruby","php","scala","r",
    "react","angular","vue","django","flask","fastapi","spring","node.js","express","tensorflow","pytorch","keras","scikit-learn","pandas","numpy",
    "postgresql","mysql","mongodb","redis","elasticsearch","dynamodb","cassandra","sqlite","oracle","sql server",
    "aws","azure","google cloud","docker","kubernetes","terraform","ansible","jenkins","ci/cd","devops","git","github","gitlab",
    "machine learning","deep learning","data science","data analysis","nlp","computer vision","llm","neural network","statistics","tableau","power bi",
    "embedded systems","arduino","raspberry pi","mems","circuit design","pcb design","signal processing","fpga","microcontroller","iot","sensors",
    "full stack","restful api","graphql","web development","mobile development","ios","android","react native","flutter",
    "linux","unix","bash","matlab","comsol","autocad","figma","jira","confluence","postman","vs code",
    "agile","scrum","product management","project management","stakeholder management","cross-functional",
    "seo","digital marketing","social media","content creation","campaign management","google analytics","a/b testing","crm",
]

MEDIUM_VALUE_WORDS = [
    "api","database","backend","frontend","testing","deployment","automation","optimization",
    "architecture","scalable","performance","security","debugging","documentation",
    "research","analysis","strategy","communication","leadership","collaboration",
    "presentation","reporting","metrics","kpis","budgeting","forecasting",
]

SECTION_KEYWORDS = {
    "summary": ["summary","objective","profile","about","overview"],
    "experience": ["experience","work history","employment","career","internship","intern"],
    "education": ["education","degree","university","college","bachelor","master","phd","gpa","cgpa"],
    "skills": ["skills","technologies","tools","competencies","technical skills","languages"],
    "projects": ["projects","portfolio","built","developed","created","designed"],
}

SENIORITY_SENIOR = ["senior","lead","principal","staff","architect","manager","director","head of","vp","chief"]
SENIORITY_JUNIOR = ["junior","entry","fresher","graduate","intern","trainee","associate","assistant"]


def extract_text_from_pdf(file_bytes):
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def extract_keywords(text, top_n=40):
    text_lower = text.lower()
    found_phrases = []
    for phrase in HIGH_VALUE_PHRASES:
        if phrase in text_lower:
            found_phrases.append(phrase)
            text_lower = text_lower.replace(phrase, " ")
    words = re.findall(r'\b[a-z][a-z+#.\-]{1,}\b', text_lower)
    singles = [w for w in words if w not in STOPWORDS and len(w) > 2]
    freq = Counter(singles)
    top_singles = [w for w, _ in freq.most_common(top_n)]
    return list(dict.fromkeys(found_phrases + top_singles))


def detect_sections(resume_lower):
    found = {}
    for section, keywords in SECTION_KEYWORDS.items():
        found[section] = any(k in resume_lower for k in keywords)
    return found


def detect_seniority(text_lower):
    if any(w in text_lower for w in SENIORITY_SENIOR):
        return "senior"
    if any(w in text_lower for w in SENIORITY_JUNIOR):
        return "junior"
    return "mid"


def score_keywords(matched, missing, jd_keywords):
    total_weight = 0
    matched_weight = 0
    for kw in jd_keywords[:30]:
        weight = 3 if kw in HIGH_VALUE_PHRASES else (2 if kw in MEDIUM_VALUE_WORDS else 1)
        total_weight += weight
        if kw in matched:
            matched_weight += weight
    if total_weight == 0:
        return 0
    return min(int((matched_weight / total_weight) * 100), 100)


def analyze_resume(resume, jd):
    resume_lower = resume.lower()
    jd_lower = jd.lower()
    jd_keywords = extract_keywords(jd)

    matched, missing = [], []
    for kw in jd_keywords[:30]:
        (matched if kw in resume_lower else missing).append(kw)

    resume_keywords = extract_keywords(resume)
    bonus = [k for k in resume_keywords if k not in jd_keywords and k not in STOPWORDS][:6]

    score = score_keywords(matched, missing, jd_keywords)

    sections = detect_sections(resume_lower)
    missing_sections = [s for s, found in sections.items() if not found]

    jd_seniority = detect_seniority(jd_lower)
    resume_seniority = detect_seniority(resume_lower)
    seniority_mismatch = (jd_seniority == "senior" and resume_seniority == "junior")

    has_numbers = bool(re.search(
        r'\d+%|\d+ percent|\d+x|\$\d+|\d+ (users|clients|projects|people|members|students|teams)',
        resume_lower
    ))

    word_count = len(resume.split())
    ats_warning = word_count < 100

    suggestions = []

    if missing:
        top_missing = [k for k in missing if k in HIGH_VALUE_PHRASES][:3] or missing[:3]
        suggestions.append(f"Add these high-priority keywords to your resume: {', '.join(top_missing)}.")

    if not has_numbers:
        suggestions.append("Quantify your achievements — add numbers like 'reduced load time by 40%' or 'managed a team of 6'. This is the #1 thing that impresses recruiters.")

    if seniority_mismatch:
        suggestions.append("This role appears to be senior-level. Emphasize leadership, ownership, and impact rather than just listing tasks.")

    if missing_sections:
        section_names = ", ".join(missing_sections)
        suggestions.append(f"Your resume seems to be missing these sections: {section_names}. Make sure they're clearly labeled.")

    if score < 50:
        suggestions.append("Your keyword match is low. Try rewriting your bullet points to mirror the exact language used in the job description — many companies use ATS software that filters by keywords.")

    if ats_warning:
        suggestions.append("Warning: Your PDF may not be ATS-friendly. Make sure it's a text-based PDF (not a scanned image) and avoid tables or text boxes.")

    if len(suggestions) < 5:
        suggestions.append("Tailor your professional summary specifically to this role — mention the job title and 2-3 of the most important requirements.")

    suggestions = suggestions[:5]

    if score >= 70:
        verdict = f"Strong match! Your resume covers {len(matched)} of the key requirements. You're a competitive candidate for this role."
    elif score >= 45:
        verdict = f"Partial match. You meet some requirements but have gaps in {len(missing)} key areas. A few targeted tweaks could make this a strong application."
    else:
        verdict = f"Weak match. Your resume covers only {len(matched)} of {len(jd_keywords[:30])} key requirements. Consider significantly tailoring it for this role."

    return {
        "score": score,
        "verdict": verdict,
        "matched": matched[:10],
        "missing": missing[:8],
        "bonus": bonus,
        "suggestions": suggestions,
        "sections": sections,
        "missing_sections": missing_sections,
        "seniority_mismatch": seniority_mismatch,
        "ats_warning": ats_warning,
        "has_numbers": has_numbers,
        "word_count": word_count,
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
