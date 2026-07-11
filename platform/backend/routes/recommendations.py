from fastapi import APIRouter, Depends, HTTPException
import json, os
from groq import Groq
from database.mysql_db import execute_query
from middleware.auth_middleware import candidate_only

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

# Use bot's Groq key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)


@router.get("/skill-gap/{app_id}")
def get_skill_gap(app_id: int, candidate=Depends(candidate_only)):
    app = execute_query(
        """SELECT a.*, j.title, j.skills_required, j.description
           FROM applications a
           JOIN jobs j ON a.job_id=j.job_id
           WHERE a.app_id=%s AND a.candidate_id=%s""",
        (app_id, candidate["id"]), fetch=True
    )
    if not app:
        raise HTTPException(404, "Application not found")

    app = app[0]

    # Only allow for rejected candidates
    if app["status"] != "rejected":
        raise HTTPException(403, "Available only for rejected applications")

    matched = parse_json(app.get("matched_skills"))
    missing = parse_json(app.get("missing_skills"))
    required = parse_json(app.get("skills_required"))

    total = len(required) if required else len(matched) + len(missing)
    match_pct = round(len(matched) / total * 100, 1) if total > 0 else 0

    return {
        "job_title": app["title"],
        "match_percentage": match_pct,
        "matched_skills": matched,
        "missing_skills": missing,
        "total_required": total,
        "ml_score": app.get("ml_score", 0)
    }


@router.get("/learning-plan/{app_id}")
async def get_learning_plan(app_id: int, candidate=Depends(candidate_only)):
    app = execute_query(
        """SELECT a.*, j.title, j.description
           FROM applications a
           JOIN jobs j ON a.job_id=j.job_id
           WHERE a.app_id=%s AND a.candidate_id=%s""",
        (app_id, candidate["id"]), fetch=True
    )
    if not app:
        raise HTTPException(404, "Not found")

    app = app[0]
    
    if app["status"] != "rejected":
        raise HTTPException(403, "Available only for rejected applications")

    missing = parse_json(app.get("missing_skills"))
    
    # Get interview report
    report_data = ""
    if app.get("interview_id"):
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                res = await client.get(
                    f"http://localhost:5001/api/report/get/{app['interview_id']}"
                )
            if res.status_code == 200:
                report = res.json()
                scores = report.get("scores", {})
                obs = report.get("observations", {})
                report_data = f"""
Interview Scores:
- Communication: {scores.get('round1',0)}%
- Aptitude: {scores.get('round2',0)}%
- Technical: {scores.get('round3',0)}%

Weaknesses: {obs.get('weaknesses','N/A')}
Suspicious areas: {obs.get('suspicious_claims','N/A')}
"""
        except:
            pass

    if not missing and not report_data:
        return {"plan": [], "message": "No improvement areas found"}

    prompt = f"""You are a career counselor. Generate personalized learning plan.

Job Applied: {app['title']}
Missing Skills: {', '.join(missing) if missing else 'None'}

Interview Performance:
{report_data}

Generate plan that addresses BOTH missing skills AND weak interview areas.
Include soft skills if communication was weak.
Include practice if technical was weak.

For EACH topic, provide:
- Why it matters (1 line)
- 1 free course/YouTube channel name
- 1 practice project idea
- Estimated weeks (1-8)

Return ONLY valid JSON:
{{
  "plan": [
    {{
      "skill": "skill_name",
      "importance": "why",
      "course": "course name",
      "course_url": "https://youtube.com/results?search_query=skill",
      "project": "project idea",
      "weeks": 3
    }}
  ],
  "total_weeks": 12,
  "summary": "Personalized encouragement"
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print("Learning plan failed:", e)
        # Fallback
        return {
            "plan": [
                {
                    "skill": s,
                    "importance": f"{s} required for this role",
                    "course": f"Search '{s} tutorial'",
                    "course_url": f"https://youtube.com/results?search_query={s}+tutorial",
                    "project": f"Build project using {s}",
                    "weeks": 3
                } for s in (missing[:5] if missing else ["communication","technical"])
            ],
            "total_weeks": 15,
            "summary": "Focus on these areas to improve"
        }


@router.get("/my-gaps")
def get_all_gaps(candidate=Depends(candidate_only)):
    apps = execute_query(
        """SELECT a.missing_skills, a.matched_skills, j.title
           FROM applications a
           JOIN jobs j ON a.job_id=j.job_id
           WHERE a.candidate_id=%s AND a.status='rejected'""",
        (candidate["id"],), fetch=True
    )

    skill_frequency = {}
    for app in apps:
        missing = parse_json(app.get("missing_skills"))
        for skill in missing:
            skill_frequency[skill] = skill_frequency.get(skill, 0) + 1

    top_gaps = sorted(skill_frequency.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_applications": len(apps),
        "top_missing_skills": [
            {"skill": s, "appears_in": c} for s, c in top_gaps[:10]
        ]
    }


def parse_json(val):
    if not val: return []
    if isinstance(val, list): return val
    try: return json.loads(val)
    except: return []