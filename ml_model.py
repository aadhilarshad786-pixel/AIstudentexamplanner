from collections import Counter

JOB_CATALOG = [
    {"title": "Data Analyst", "company": "Insight Labs", "skills": {"python", "sql", "excel", "power bi"}, "salary": "₹3–6 LPA", "color": "cyan"},
    {"title": "Junior Data Scientist", "company": "Nova Analytics", "skills": {"python", "pandas", "numpy", "machine learning", "statistics"}, "salary": "₹5–9 LPA", "color": "violet"},
    {"title": "Business Analyst", "company": "Orbit Consulting", "skills": {"sql", "excel", "power bi", "statistics"}, "salary": "₹4–8 LPA", "color": "amber"},
    {"title": "ML Intern", "company": "ModelWorks", "skills": {"python", "numpy", "pandas", "machine learning"}, "salary": "₹2–5 LPA", "color": "pink"},
]

ROADMAP = ["Python", "SQL", "Excel", "Statistics", "Power BI", "Pandas", "Machine Learning"]


def normalize_skills(skills):
    return {skill.strip().lower() for skill in skills.split(",") if skill.strip()}


def analyze_skills(raw_skills):
    skills = normalize_skills(raw_skills)
    recommendations = []
    missing = Counter()
    for job in JOB_CATALOG:
        overlap = skills & job["skills"]
        score = round(min(98, 45 + (len(overlap) / len(job["skills"])) * 55))
        recommendations.append({**job, "score": score, "matched": sorted(overlap), "missing": sorted(job["skills"] - skills)})
        missing.update(job["skills"] - skills)
    recommendations.sort(key=lambda job: job["score"], reverse=True)
    roadmap = [{"name": name, "done": name.lower() in skills} for name in ROADMAP]
    top_match = recommendations[0]["score"] if recommendations else 0
    return {"skills": sorted(skills), "jobs": recommendations, "missing": [item[0].title() for item in missing.most_common()], "roadmap": roadmap, "top_match": top_match}


def analyze_study(subjects, metrics):
    marks = [float(item["mark"]) for item in subjects]
    average = round(sum(marks) / len(marks)) if marks else 0
    weak = [item for item in subjects if item["mark"] < 60]
    improving = [item for item in subjects if 60 <= item["mark"] < 75]
    strong = [item for item in subjects if item["mark"] >= 75]
    metric_score = ((metrics["attendance"] * .15 + metrics["assignment_score"] * .15 + metrics["test_score"] * .25 + metrics["consistency"] * .15 + min(metrics["study_hours"] * 10, 100) * .30) if metrics else 0)
    predicted = round(min(99, max(0, average * .55 + metric_score * .45))) if marks else 0
    return {"average": average, "predicted": predicted, "trend": "Improving" if predicted >= average else "Needs attention", "weak": weak, "improving": improving, "strong": strong, "total": len(subjects)}