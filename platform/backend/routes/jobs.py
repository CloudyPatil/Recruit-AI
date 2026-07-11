from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import json
from database.mysql_db import execute_query
from middleware.auth_middleware import hr_only, get_current_user

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class JobInput(BaseModel):
    title: str
    description: str
    skills_required: List[str]
    experience_required: str
    education_required: str
    deadline: Optional[str] = None
    max_applicants: Optional[int] = 0


@router.post("/create")
def create_job(data: JobInput, hr=Depends(hr_only)):
    job_id = execute_query(
        """INSERT INTO jobs
           (hr_id,title,description,skills_required,
            experience_required,education_required,
            deadline,max_applicants)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (hr["id"], data.title, data.description,
         json.dumps(data.skills_required),
         data.experience_required, data.education_required,
         data.deadline, data.max_applicants)
    )
    return {"job_id": job_id, "message": "Job created"}


@router.get("/all")
def get_all_jobs(
    user=Depends(get_current_user),
    search: Optional[str] = None,
    experience: Optional[str] = None,
    sort: Optional[str] = "recent"
):
    query = """
        SELECT j.*, u.company, u.name as hr_name
        FROM jobs j
        JOIN users u ON j.hr_id = u.id
        WHERE j.status='open'
    """
    params = []
    
    if search:
        query += " AND (j.title LIKE %s OR j.description LIKE %s OR j.skills_required LIKE %s)"
        s = f"%{search}%"
        params.extend([s, s, s])
    
    if experience:
        query += " AND j.experience_required = %s"
        params.append(experience)
    
    if sort == "recent":
        query += " ORDER BY j.created_at DESC"
    elif sort == "oldest":
        query += " ORDER BY j.created_at ASC"
    
    jobs = execute_query(query, tuple(params), fetch=True)
    return {"jobs": jobs}


@router.get("/detail/{job_id}")
def get_job_detail(job_id: int, user=Depends(get_current_user)):
    job = execute_query(
        """SELECT j.*, u.company, u.name as hr_name, u.email as hr_email
           FROM jobs j
           JOIN users u ON j.hr_id = u.id
           WHERE j.job_id=%s""",
        (job_id,), fetch=True
    )
    if not job:
        raise HTTPException(404, "Job not found")
    
    # Get applicant count
    count = execute_query(
        "SELECT COUNT(*) as cnt FROM applications WHERE job_id=%s",
        (job_id,), fetch=True
    )[0]["cnt"]
    
    job_data = job[0]
    job_data["applicant_count"] = count
    return job_data


@router.get("/my-jobs")
def get_my_jobs(hr=Depends(hr_only)):
    jobs = execute_query(
        """SELECT * FROM jobs 
           WHERE hr_id=%s AND status='open'
           ORDER BY created_at DESC""",
        (hr["id"],), fetch=True
    )
    return {"jobs": jobs}


@router.post("/save/{job_id}")
def save_job(job_id: int, user=Depends(get_current_user)):
    existing = execute_query(
        "SELECT id FROM saved_jobs WHERE user_id=%s AND job_id=%s",
        (user["id"], job_id), fetch=True
    )
    if existing:
        execute_query(
            "DELETE FROM saved_jobs WHERE user_id=%s AND job_id=%s",
            (user["id"], job_id)
        )
        return {"saved": False}
    
    execute_query(
        "INSERT INTO saved_jobs (user_id, job_id) VALUES (%s, %s)",
        (user["id"], job_id)
    )
    return {"saved": True}


@router.get("/saved")
def get_saved_jobs(user=Depends(get_current_user)):
    jobs = execute_query(
        """SELECT j.*, u.company FROM jobs j
           JOIN saved_jobs s ON j.job_id = s.job_id
           JOIN users u ON j.hr_id = u.id
           WHERE s.user_id=%s
           ORDER BY s.created_at DESC""",
        (user["id"],), fetch=True
    )
    saved_ids = [j["job_id"] for j in jobs]
    return {"jobs": jobs, "saved_ids": saved_ids}


@router.delete("/delete/{job_id}")
def delete_job(job_id: int, hr=Depends(hr_only)):
    job = execute_query(
        "SELECT * FROM jobs WHERE job_id=%s AND hr_id=%s",
        (job_id, hr["id"]), fetch=True
    )
    if not job:
        raise HTTPException(404, "Job not found")

    execute_query(
        """UPDATE applications 
           SET status='job_closed' 
           WHERE job_id=%s AND status NOT IN ('selected','rejected')""",
        (job_id,)
    )

    execute_query(
        "UPDATE jobs SET status='closed' WHERE job_id=%s",
        (job_id,)
    )

    return {"message": "Job deleted"}