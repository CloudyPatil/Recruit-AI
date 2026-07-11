import json
from groq import Groq
import os
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import httpx
from database.mysql_db import execute_query
from middleware.auth_middleware import hr_only, candidate_only
from services.email_service import (
    send_interview_notification,
    send_selection_email,
    send_rejection_email,
    send_report_ready_email
)
from datetime import datetime, timedelta
from fastapi.responses import StreamingResponse
from services.pdf_service import generate_report_pdf

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

router = APIRouter(prefix="/interviews", tags=["Interviews"])

@router.post("/send/{app_id}")
async def send_interview(app_id: int, hr=Depends(hr_only)):
    import os, json
    from datetime import datetime, timedelta

    app = execute_query(
        """SELECT a.*, u.name, u.email, j.title
           FROM applications a
           JOIN users u ON a.candidate_id=u.id
           JOIN jobs j ON a.job_id=j.job_id
           WHERE a.app_id=%s""",
        (app_id,), fetch=True
    )[0]

    # Extract STRUCTURED resume data
    resume_data = {}
    resume_summary = ""

    if app.get("resume_path") and os.path.exists(app["resume_path"]):
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                with open(app["resume_path"], "rb") as rf:
                    parse_res = await client.post(
                        "http://localhost:8000/parse-resume",
                        files={"resume_file": (os.path.basename(app["resume_path"]), rf)}
                    )
                if parse_res.status_code == 200:
                    resume_data = parse_res.json()
                    resume_summary = resume_data.get("summary", "")
        except Exception as e:
            print("Resume parse failed:", e)

    # Experience level from matched skills
    skills_count = len(json.loads(app.get("matched_skills") or "[]"))
    if skills_count > 8:
        exp_level = "mid"
    elif skills_count > 4:
        exp_level = "junior"
    else:
        exp_level = "fresher"

    async with httpx.AsyncClient(timeout=30) as client:
        bot_response = await client.post(
            "http://localhost:5001/api/interview/create",
            json={
                "candidate_id": app["candidate_id"],
                "job_id": app["job_id"],
                "candidate_name": app["name"],
                "job_title": app["title"],
                "ml_score": app["ml_score"],
                "experience_level": exp_level,
                "resume_summary": resume_summary,
                "resume_data": resume_data
            }
        )
    bot_data = bot_response.json()

    expires_at = datetime.now() + timedelta(hours=24)

    execute_query(
        """UPDATE applications
           SET status='interview_sent',
               interview_id=%s,
               interview_url=%s,
               interview_expires=%s
           WHERE app_id=%s""",
        (bot_data["interview_id"],
         bot_data["link_token"],
         expires_at, app_id)
    )

    send_interview_notification(app["email"], app["name"], app["title"])
    return {"message": "Interview invitation sent"}

@router.get("/report/{app_id}")
async def get_report(app_id: int, hr=Depends(hr_only)):
    app = execute_query(
        "SELECT * FROM applications WHERE app_id=%s",
        (app_id,), fetch=True
    )[0]

    interview_id = app["interview_id"]

    async with httpx.AsyncClient(timeout=60) as client:
        # Try to GET existing report first
        report = await client.get(
            f"http://localhost:5001/api/report/get/{interview_id}"
        )

        # If not found, GENERATE it
        if report.status_code != 200 or not report.json():
            gen = await client.post(
                f"http://localhost:5001/api/report/generate/{interview_id}"
            )
            return gen.json()

    return report.json()

@router.get("/check/{app_id}")
def check_interview(app_id: int, candidate=Depends(candidate_only)):
    from datetime import datetime
    app = execute_query(
        "SELECT * FROM applications WHERE app_id=%s AND candidate_id=%s",
        (app_id, candidate["id"]), fetch=True
    )
    if not app:
        raise HTTPException(404, "Not found")

    app = app[0]

    # ALREADY COMPLETED - no retry
    if app["status"] == "interview_done" or app["interview_status"] == "completed":
        return {"valid": False, "message": "Interview already completed"}

    if app["interview_expires"] and datetime.now() > app["interview_expires"]:
        return {"valid": False, "message": "Interview expired"}

    if app["interview_attempts"] >= 3:
        return {"valid": False, "message": "Max attempts reached"}

    return {
        "valid": True,
        "attempts_left": 3 - app["interview_attempts"],
        "interview_url": app["interview_url"]
    }


@router.post("/mark-attempted/{app_id}")
def mark_attempted(app_id: int, candidate=Depends(candidate_only)):
    execute_query(
        """UPDATE applications
           SET interview_status='started',
               interview_attempts=interview_attempts+1,
               last_attempt_at=NOW()
           WHERE app_id=%s""",
        (app_id,)
    )
    return {"message": "Started"}


@router.post("/mark-completed/{app_id}")
def mark_completed(app_id: int):
    execute_query(
        """UPDATE applications
           SET interview_status='completed',
               status='interview_done'
           WHERE app_id=%s""",
        (app_id,)
    )
    return {"message": "Completed"}


@router.post("/mark-failed/{app_id}")
def mark_failed(app_id: int, candidate=Depends(candidate_only)):
    execute_query(
        """UPDATE applications
           SET interview_status='failed'
           WHERE app_id=%s""",
        (app_id,)
    )
    return {"message": "Marked failed"}


@router.post("/reset/{app_id}")
def reset_interview(app_id: int, hr=Depends(hr_only)):
    # HR can reset interview if candidate had genuine issue
    execute_query(
        """UPDATE applications
           SET interview_status='not_started',
               interview_attempts=0,
               interview_expires=%s
           WHERE app_id=%s""",
        (datetime.now() + timedelta(hours=24), app_id)
    )
    return {"message": "Interview reset"}

@router.post("/reject/{app_id}")
def reject_candidate(app_id: int, hr=Depends(hr_only)):
    # Get candidate + job info
    info = execute_query(
        """SELECT u.name, u.email, j.title, hr.company
           FROM applications a
           JOIN users u ON a.candidate_id=u.id
           JOIN jobs j ON a.job_id=j.job_id
           JOIN users hr ON j.hr_id=hr.id
           WHERE a.app_id=%s""",
        (app_id,), fetch=True
    )[0]

    execute_query(
        "UPDATE applications SET status='rejected' WHERE app_id=%s",
        (app_id,)
    )

    try:
        send_rejection_email(
            info["email"], info["name"],
            info["title"], info["company"] or "the company"
        )
    except Exception as e:
        print("Email failed:", e)

    return {"message": "Candidate rejected"}


@router.post("/select/{app_id}")
def select_candidate(app_id: int, hr=Depends(hr_only)):
    execute_query(
        "UPDATE applications SET status='selected' WHERE app_id=%s",
        (app_id,)
    )
    return {"message": "Candidate selected"}


# In interviews.py

@router.post("/sync-status/{app_id}")
async def sync_status(app_id: int):
    """Check bot for interview completion status"""
    app = execute_query(
        "SELECT * FROM applications WHERE app_id=%s",
        (app_id,), fetch=True
    )
    if not app:
        return {"updated": False}
    
    app = app[0]
    if not app.get("interview_id"):
        return {"updated": False}

    # Ask bot for current status
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(
                f"http://localhost:5001/api/report/get/{app['interview_id']}"
            )
        if res.status_code == 200:
            report = res.json()
            final_score = report.get("scores", {}).get("final", 0)
            
            execute_query(
                """UPDATE applications 
                   SET status='interview_done',
                       interview_status='completed',
                       final_score=%s
                   WHERE app_id=%s""",
                (final_score, app_id)
            )
            return {"updated": True, "score": final_score}
    except:
        pass
    
    return {"updated": False}


@router.get("/report/{app_id}/enhanced")
async def get_enhanced_report(app_id: int, hr=Depends(hr_only)):
    """Get detailed enhanced report with LLM analysis"""
    app = execute_query(
        """SELECT a.*, u.name as candidate_name, u.email, u.phone, 
                  u.location, u.github_data, j.title, j.skills_required,
                  j.experience_required, j.education_required,
                  hr.company
           FROM applications a
           JOIN users u ON a.candidate_id=u.id
           JOIN jobs j ON a.job_id=j.job_id
           JOIN users hr ON j.hr_id=hr.id
           WHERE a.app_id=%s""",
        (app_id,), fetch=True
    )[0]

    # Get bot report
    async with httpx.AsyncClient(timeout=60) as client:
        report_res = await client.get(
            f"http://localhost:5001/api/report/get/{app['interview_id']}"
        )
        if report_res.status_code != 200 or not report_res.json():
            gen = await client.post(
                f"http://localhost:5001/api/report/generate/{app['interview_id']}"
            )
            bot_report = gen.json()
        else:
            bot_report = report_res.json()

        # Parse data FIRST (before LLM call)
        matched_skills = parse_json(app.get("matched_skills"))
        missing_skills = parse_json(app.get("missing_skills"))
        required_skills = parse_json(app.get("skills_required"))
        github = parse_json(app.get("github_data"))
        scores = bot_report.get("scores", {})

        # Get conversation log from bot
        conversation = {}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                log_res = await client.get(
                    f"http://localhost:5001/api/interview/log/{app['interview_id']}"
                )
            if log_res.status_code == 200:
                conversation = log_res.json()
        except Exception as e:
            print("Log fetch failed:", e)        

        # Make analysis safer with fallbacks
        try:
          enhanced = generate_enhanced_analysis(
              bot_report, conversation, matched_skills, missing_skills, github
          )
        except Exception as e:
            print("Enhanced analysis failed:", e)
            enhanced = {
                "executive_summary": "Auto analysis unavailable",
                "verdict": "Maybe",
                "top_strength": "Review manually",
                "biggest_concern": "Auto analysis unavailable",
                "communication": {
                    "clarity": 7, "confidence": 7,
                    "structure": 7, "grammar": 7, "pace": "Normal"
                },
                "best_answer": {},
                "concerning_answer": {},
                "action_items": ["Review interview manually"]
            }

    # Parse data
    matched_skills = parse_json(app.get("matched_skills"))
    missing_skills = parse_json(app.get("missing_skills"))
    required_skills = parse_json(app.get("skills_required"))
    github = parse_json(app.get("github_data"))
    scores = bot_report.get("scores", {})

    # Generate enhanced analysis using LLM
    enhanced = generate_enhanced_analysis(
        bot_report, conversation, matched_skills, missing_skills, github
    )

    # Risk level
    flags = bot_report.get("anti_cheat", {}).get("total_flags", 0)
    final_score = scores.get("final", 0)
    risk = "LOW" if flags <= 1 else "MEDIUM" if flags <= 3 else "HIGH"

    # Skill verification
    skill_verification = verify_skills(matched_skills, missing_skills, github, conversation)

    # Make observations safe
    observations = bot_report.get("observations", {}) or {}

    return {
    "candidate": {
        "name": app["candidate_name"],
        "email": app["email"],
        "phone": app.get("phone"),
        "location": app.get("location"),
    },
    "job": {
        "title": app["title"],
        "company": app.get("company"),
        "experience_required": app.get("experience_required"),
        "education_required": app.get("education_required"),
    },
    "terminated": bot_report.get("terminated", False),
    "scores": scores,
    "executive_summary": enhanced.get("executive_summary", ""),
    "verdict": enhanced.get("verdict", ""),
    "top_strength": enhanced.get("top_strength", ""),
    "biggest_concern": enhanced.get("biggest_concern", ""),
    "skill_verification": skill_verification,
    "communication": enhanced.get("communication", {}),
    "best_answer": enhanced.get("best_answer", {}),
    "concerning_answer": enhanced.get("concerning_answer", {}),
    "action_items": enhanced.get("action_items", []),
    "integrity": {
        "status": bot_report.get("anti_cheat", {}).get("status", "CLEAN"),
        "total_flags": flags,
        "risk_level": risk,
        "flags": bot_report.get("anti_cheat", {}).get("flags", [])
    },
    "recommendation": bot_report.get("recommendation", "PENDING"),
    "ai_summary": bot_report.get("ai_summary", ""),
    "observations": bot_report.get("observations", {}),
    "truthfulness": {
        "score": observations.get("truthfulness_score", 0),
        "verified_claims": observations.get("verified_claims", "N/A"),
        "suspicious_claims": observations.get("suspicious_claims", "N/A")
     }
    }


def parse_json(val):
    if not val: return []
    if isinstance(val, (list, dict)): return val
    try: return json.loads(val)
    except: return []


def verify_skills(matched, missing, github, conversation):
    """Verify each skill - resume, github, interview mentions"""
    verification = []

    gh_languages = []
    if github and isinstance(github, dict):
        gh_languages = github.get("top_languages", [])

    # Get all candidate answers as text
    answers_text = ""
    if conversation and isinstance(conversation, dict):
        logs = conversation.get("conversation_log", [])
        for entry in logs:
            if entry.get("role") == "candidate":
                answers_text += " " + entry.get("text", "")
    answers_text = answers_text.lower()

    # Check each matched skill
    for skill in matched:
        skill_lower = skill.lower()
        in_github = skill_lower in [g.lower() for g in gh_languages]
        in_interview = skill_lower in answers_text

        if in_github and in_interview:
            status = "Strongly Verified"
            level = "strong"
        elif in_github or in_interview:
            status = "Verified"
            level = "good"
        else:
            status = "Mentioned in Resume"
            level = "weak"

        verification.append({
            "skill": skill,
            "status": status,
            "level": level,
            "in_github": in_github,
            "in_interview": in_interview
        })

    # Add missing
    for skill in missing:
        verification.append({
            "skill": skill,
            "status": "Not Found",
            "level": "missing",
            "in_github": False,
            "in_interview": False
        })

    return verification



def generate_enhanced_analysis(bot_report, conversation, matched, missing, github):
    scores = bot_report.get("scores", {})
    final = scores.get("final", 0)

    # Get conversation - need MORE context
    log_text = ""
    if conversation and isinstance(conversation, dict):
        logs = conversation.get("conversation_log", [])
        # Get LAST 30 messages, not 20
        for entry in logs[-30:]:
            role = entry.get("role", "")
            text = entry.get("text", "")[:300]
            log_text += f"{role.upper()}: {text}\n"

    if not log_text.strip():
        log_text = "No conversation recorded"

    prompt = f"""Analyze this interview. Extract REAL quotes from conversation.

Scores: ML={scores.get('ml_score',0)}, R1={scores.get('round1',0)}, R2={scores.get('round2',0)}, R3={scores.get('round3',0)}, Final={final}
Matched Skills: {', '.join(matched[:10])}
Missing Skills: {', '.join(missing[:5])}

Full Conversation:
{log_text[:3000]}

Find the BEST and WORST candidate answers from above conversation.
Use ACTUAL quotes from the transcript above.

Return ONLY valid JSON:
{{
  "executive_summary": "2-3 lines for HR decision",
  "verdict": "Strong Hire | Hire | Maybe | No Hire",
  "top_strength": "single biggest strength",
  "biggest_concern": "main concern",
  "communication": {{
    "clarity": 7, "confidence": 8, "structure": 6,
    "grammar": 9, "pace": "Normal"
  }},
  "best_answer": {{
    "question": "actual question from transcript",
    "answer_excerpt": "actual candidate answer",
    "why_good": "specific reason"
  }},
  "concerning_answer": {{
    "question": "actual question",
    "answer_excerpt": "actual answer",
    "why_concerning": "what was wrong"
  }},
  "action_items": [
    "Specific discussion point 1",
    "Specific discussion point 2",
    "Specific discussion point 3"
  ]
}}"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Better model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print("LLM analysis failed:", e)
        return {
            "executive_summary": f"Candidate scored {final}%",
            "verdict": "Maybe" if final >= 60 else "No Hire",
            "top_strength": "Review interview manually",
            "biggest_concern": "Auto-analysis unavailable",
            "communication": {"clarity":7,"confidence":7,"structure":7,"grammar":7,"pace":"Normal"},
            "best_answer": {},
            "concerning_answer": {},
            "action_items": ["Review interview recording manually"]
        }
    
@router.get("/report/{app_id}/pdf")
async def download_report_pdf(app_id: int, hr=Depends(hr_only)):
    """Generate and download PDF report"""
    # Get enhanced report data
    report = await get_enhanced_report(app_id, hr)
    
    # Generate PDF
    pdf_buffer = generate_report_pdf(report)
    
    candidate_name = report.get("candidate", {}).get("name", "candidate").replace(" ", "_")
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={candidate_name}_report.pdf"
        }
    )
