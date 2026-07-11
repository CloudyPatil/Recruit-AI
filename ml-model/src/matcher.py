from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re
import numpy as np

model = SentenceTransformer('./models/sbert_model')

SKILLS = [
    # Programming
    "python","java","javascript","c++","c#","ruby","go","php","kotlin","swift",
    # Web
    "react","angular","vue","node.js","django","flask","html","css","fastapi",
    # ML/AI
    "machine learning","deep learning","nlp","tensorflow","pytorch","keras",
    "scikit-learn","computer vision","data science",
    # Cloud/DevOps
    "aws","azure","gcp","docker","kubernetes","jenkins","ci/cd","terraform",
    # Database
    "mysql","postgresql","mongodb","redis","sql","oracle","sqlite",
    # Finance
    "accounting","taxation","auditing","financial modeling","excel","tally",
    # Medical
    "surgery","nursing","patient care","diagnosis","pharmacology",
    # Design
    "figma","photoshop","illustrator","ui/ux","autocad","sketch",
    # Business
    "sales","marketing","management","hr","recruitment","business analysis"
]

def extract_skills(text):
    text_lower = text.lower()
    found = []
    for skill in SKILLS:
        if skill in text_lower:
            found.append(skill)
    return list(set(found))

def match_resume_to_job(resume_text, job_description):
    
    # SBERT similarity
    r_emb = model.encode([resume_text[:512]])
    j_emb = model.encode([job_description[:512]])
    semantic_score = cosine_similarity(r_emb, j_emb)[0][0]
    
    # Skill matching
    resume_skills = set(extract_skills(resume_text))
    job_skills = set(extract_skills(job_description))
    
    if len(job_skills) > 0:
        skill_score = len(resume_skills & job_skills) / len(job_skills)
    else:
        skill_score = 0.5
    
    # Final weighted score
    final = (semantic_score * 0.6) + (skill_score * 0.4)
    
    return {
        "final_score": round(float(final * 100), 1),
        "semantic_score": round(float(semantic_score * 100), 1),
        "skill_score": round(float(skill_score * 100), 1),
        "matched_skills": list(resume_skills & job_skills),
        "missing_skills": list(job_skills - resume_skills),
        "candidate_skills": list(resume_skills)
    }

def match_with_explanation(resume_text, job_description):
    result = match_resume_to_job(resume_text, job_description)
    
    # Component contributions
    semantic_contribution = result['semantic_score'] * 0.6
    skill_contribution = result['skill_score'] * 0.4
    
    # Per-skill impact
    skill_breakdown = []
    job_skills = set(extract_skills(job_description))
    
    for skill in job_skills:
        if skill in result['matched_skills']:
            skill_breakdown.append({
                "skill": skill,
                "status": "matched",
                "impact": round(40 / len(job_skills), 2)
            })
        else:
            skill_breakdown.append({
                "skill": skill,
                "status": "missing",
                "impact": -round(40 / len(job_skills), 2)
            })
    
    result['explanation'] = {
        "semantic_contribution": round(semantic_contribution, 2),
        "skill_contribution": round(skill_contribution, 2),
        "skill_breakdown": skill_breakdown,
        "summary": generate_summary(result)
    }
    
    return result

def generate_summary(result):
    score = result['final_score']
    if score >= 75:
        verdict = "Strong Match ✅"
    elif score >= 50:
        verdict = "Moderate Match ⚠️"
    else:
        verdict = "Weak Match ❌"
    
    return {
        "verdict": verdict,
        "matched_count": len(result['matched_skills']),
        "missing_count": len(result['missing_skills'])
    }

# TEST
if __name__ == "__main__":
    resume = """
    John Smith - Python Developer
    3 years experience in machine learning and tensorflow
    Worked with AWS, Docker, and MongoDB
    Built ML models using scikit-learn and pytorch
    """
    
    job = """
    Looking for Python ML Engineer
    Required: Python, TensorFlow, AWS, Docker
    Good to have: Kubernetes, MongoDB
    """
    
    result = match_resume_to_job(resume, job)
    
    print(f"Final Score: {result['final_score']}%")
    print(f"Semantic: {result['semantic_score']}%")
    print(f"Skills: {result['skill_score']}%")
    print(f"Matched: {result['matched_skills']}")
    print(f"Missing: {result['missing_skills']}")