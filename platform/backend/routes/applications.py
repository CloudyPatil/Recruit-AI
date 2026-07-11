from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
import httpx, os, shutil, json
from database.mysql_db import execute_query
from middleware.auth_middleware import candidate_only, hr_only
from datetime import date

router = APIRouter(prefix="/applications", tags=["Applications"])
RESUME_FOLDER = "resumes"
os.makedirs(RESUME_FOLDER, exist_ok=True)

@router.post("/apply/{job_id}")
async def apply_job(
    job_id: int,
    resume: UploadFile = File(...),
    candidate=Depends(candidate_only)
):
    # Check already applied
    existing = execute_query(
        "SELECT app_id FROM applications WHERE candidate_id=%s AND job_id=%s",
        (candidate["id"], job_id), fetch=True
    )
    if existing:
        return {"message": "Already applied"}

    # Save resume
    resume_path = f"{RESUME_FOLDER}/{candidate['id']}_{job_id}_{resume.filename}"
    with open(resume_path, "wb") as f:
        shutil.copyfileobj(resume.file, f)

    # Get job description
    job = execute_query(
        "SELECT * FROM jobs WHERE job_id=%s", (job_id,), fetch=True
    )[0]

    # Call ML Model
    # Call ML Model
    async with httpx.AsyncClient(timeout=60) as client:
        with open(resume_path, "rb") as rf:
            ml_response = await client.post(
                "http://localhost:8000/match-single",
                files={"resume_file": (resume.filename, rf)},
                data={"job_description": job["description"]}
            )

    # Check response
    if ml_response.status_code != 200:
        print("ML Error:", ml_response.status_code, ml_response.text)
        raise HTTPException(500, "ML scoring failed")

    try:
        ml_data = ml_response.json()
    except:
        print("ML returned non-JSON:", ml_response.text[:200])
        raise HTTPException(500, "ML response invalid")
    
    # Check max applicants
    if job["max_applicants"] and job["max_applicants"] > 0:
        count = execute_query(
            "SELECT COUNT(*) as cnt FROM applications WHERE job_id=%s",
            (job_id,), fetch=True
        )[0]["cnt"]
        if count >= job["max_applicants"]:
            # Auto close job
            execute_query(
             "UPDATE jobs SET status='closed' WHERE job_id=%s", (job_id,)
            )
            raise HTTPException(400, "Maximum applicants reached. Job is now closed.")

    # Save application
    app_id = execute_query(
    """INSERT INTO applications
       (candidate_id, job_id, resume_path, status,
        ml_score, matched_skills, missing_skills, shap_explanation)
       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
    (candidate["id"], job_id, resume_path, "ml_scored",
     ml_data["final_score"],
     json.dumps(ml_data.get("matched_skills",[])),
     json.dumps(ml_data.get("missing_skills",[])),
     json.dumps(ml_data.get("explanation",{})))
)
    return {
        "app_id": app_id,
        "ml_score": ml_data["final_score"],
        "matched_skills": ml_data.get("matched_skills"),
        "missing_skills": ml_data.get("missing_skills")
    }

@router.get("/job/{job_id}/candidates")
async def get_ranked_candidates(job_id: int, hr=Depends(hr_only)):
    candidates = execute_query(
        """SELECT a.*, u.name, u.email 
           FROM applications a
           JOIN users u ON a.candidate_id = u.id
           WHERE a.job_id=%s
           ORDER BY a.ml_score DESC""",
        (job_id,), fetch=True
    )
    
    import httpx
    from services.email_service import send_report_ready_email

    for c in candidates:
        if c["status"] == "interview_sent" and c.get("interview_id"):
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    res = await client.post(
                        f"http://localhost:5001/api/report/generate/{c['interview_id']}"
                    )
                if res.status_code == 200:
                    report = res.json()
                    scores = report.get("scores", {})
                    final = scores.get("final", 0)
                    round1 = scores.get("round1", 0)
                    round3 = scores.get("round3", 0)
                    is_terminated = report.get("terminated", False)

                    # Mark complete if rounds done OR terminated
                    if round1 > 0 or round3 > 0 or is_terminated:
                        new_status = "interview_done"
                        execute_query(
                            """UPDATE applications 
                               SET status=%s,
                                   interview_status='completed',
                                   final_score=%s
                               WHERE app_id=%s""",
                            (new_status, final, c["app_id"])
                        )
                        c["status"] = new_status
                        c["final_score"] = final

                        # Email HR that report is ready (only once)
                        try:
                            hr_info = execute_query(
                                "SELECT name, email FROM users WHERE id=%s",
                                (hr["id"],), fetch=True
                            )[0]
                            send_report_ready_email(
                                hr_info["email"], hr_info["name"],
                                c["name"], "the role"
                            )
                        except:
                            pass
            except Exception as e:
                print("Sync fail:", e)
    
    return {"candidates": candidates}

# Add to routes/applications.py

# Update applications.py my-applications + ranked

@router.get("/my-applications")
async def my_applications(candidate=Depends(candidate_only)):
    apps = execute_query(
        """SELECT a.*, j.title 
           FROM applications a
           JOIN jobs j ON a.job_id=j.job_id
           WHERE a.candidate_id=%s
           ORDER BY a.created_at DESC""",
        (candidate["id"],), fetch=True
    )
    
    import httpx
    for app in apps:
        if app["status"] == "interview_sent" and app.get("interview_id"):
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    res = await client.post(
                        f"http://localhost:5001/api/report/generate/{app['interview_id']}"
                    )
                if res.status_code == 200:
                    report = res.json()
                    scores = report.get("scores", {})
                    final = scores.get("final", 0)
                    round1 = scores.get("round1", 0)
                    round3 = scores.get("round3", 0)
                    is_terminated = report.get("terminated", False)

                    # Mark complete if rounds done OR terminated
                    if round1 > 0 or round3 > 0 or is_terminated:
                        new_status = "interview_done"
                        execute_query(
                            """UPDATE applications 
                               SET status=%s,
                                   interview_status='completed',
                                   final_score=%s
                               WHERE app_id=%s""",
                            (new_status, final, app["app_id"])
                        )
                        app["status"] = new_status
                        app["final_score"] = final
            except:
                pass
    
    return {"applications": apps}

@router.get("/total-applicants")
def total_applicants(hr=Depends(hr_only)):
    result = execute_query(
        """SELECT COUNT(*) as total FROM applications a
           JOIN jobs j ON a.job_id=j.job_id
           WHERE j.hr_id=%s""",
        (hr["id"],), fetch=True
    )
    return {"total": result[0]["total"]}