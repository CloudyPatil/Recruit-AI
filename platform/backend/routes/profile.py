from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
import os, shutil, json, httpx
from database.mysql_db import execute_query
from middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/profile", tags=["Profile"])

UPLOAD_DIR = "uploads/profiles"
RESUME_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESUME_DIR, exist_ok=True)


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    profile_skills: Optional[List[str]] = []


@router.get("/me")
def get_profile(user=Depends(get_current_user)):
    data = execute_query(
        "SELECT * FROM users WHERE id=%s",
        (user["id"],), fetch=True
    )[0]
    data.pop("password", None)
    return data


@router.put("/update")
def update_profile(data: ProfileUpdate, user=Depends(get_current_user)):
    execute_query(
        """UPDATE users SET
           name=COALESCE(%s,name),
           phone=COALESCE(%s,phone),
           location=COALESCE(%s,location),
           bio=COALESCE(%s,bio),
           linkedin_url=COALESCE(%s,linkedin_url),
           github_url=COALESCE(%s,github_url),
           portfolio_url=COALESCE(%s,portfolio_url),
           profile_skills=%s
           WHERE id=%s""",
        (data.name, data.phone, data.location, data.bio,
         data.linkedin_url, data.github_url, data.portfolio_url,
         json.dumps(data.profile_skills or []), user["id"])
    )
    return {"message": "Profile updated"}


@router.post("/upload-photo")
async def upload_photo(
    photo: UploadFile = File(...),
    user=Depends(get_current_user)
):
    ext = photo.filename.split(".")[-1]
    path = f"{UPLOAD_DIR}/user_{user['id']}.{ext}"
    with open(path, "wb") as f:
        shutil.copyfileobj(photo.file, f)
    
    execute_query(
        "UPDATE users SET photo_url=%s WHERE id=%s",
        (path, user["id"])
    )
    return {"photo_url": path}


@router.post("/upload-resume")
async def upload_default_resume(
    resume: UploadFile = File(...),
    user=Depends(get_current_user)
):
    ext = resume.filename.split(".")[-1]
    path = f"{RESUME_DIR}/default_{user['id']}.{ext}"
    with open(path, "wb") as f:
        shutil.copyfileobj(resume.file, f)
    
    execute_query(
        "UPDATE users SET default_resume_path=%s WHERE id=%s",
        (path, user["id"])
    )
    return {"resume_path": path}


@router.post("/sync-github")
async def sync_github(user=Depends(get_current_user)):
    """Fetch GitHub data from public API"""
    profile = execute_query(
        "SELECT github_url FROM users WHERE id=%s",
        (user["id"],), fetch=True
    )[0]
    
    if not profile["github_url"]:
        return {"error": "No GitHub URL set"}

    # Extract username from URL
    username = profile["github_url"].rstrip("/").split("/")[-1]

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Get user info
            user_res = await client.get(
                f"https://api.github.com/users/{username}"
            )
            # Get repos
            repos_res = await client.get(
                f"https://api.github.com/users/{username}/repos?per_page=100"
            )

        if user_res.status_code != 200:
            return {"error": "GitHub user not found"}

        user_data = user_res.json()
        repos = repos_res.json() if repos_res.status_code == 200 else []

        # Process data
        languages = {}
        total_stars = 0
        top_repos = []

        for repo in repos:
            if repo.get("language"):
                lang = repo["language"].lower()
                languages[lang] = languages.get(lang, 0) + 1
            total_stars += repo.get("stargazers_count", 0)

        # Sort top repos by stars
        sorted_repos = sorted(repos, key=lambda x: x.get("stargazers_count", 0), reverse=True)
        top_repos = [
            {
                "name": r["name"],
                "stars": r["stargazers_count"],
                "language": r.get("language"),
                "url": r["html_url"],
                "description": r.get("description", "")
            }
            for r in sorted_repos[:5]
        ]

        github_data = {
            "username": username,
            "name": user_data.get("name"),
            "bio": user_data.get("bio"),
            "public_repos": user_data.get("public_repos", 0),
            "followers": user_data.get("followers", 0),
            "following": user_data.get("following", 0),
            "total_stars": total_stars,
            "languages": languages,
            "top_languages": sorted(languages.keys(), key=languages.get, reverse=True)[:5],
            "top_repos": top_repos,
            "avatar": user_data.get("avatar_url"),
            "profile_url": user_data.get("html_url")
        }

        execute_query(
            "UPDATE users SET github_data=%s WHERE id=%s",
            (json.dumps(github_data), user["id"])
        )

        return github_data

    except Exception as e:
        return {"error": str(e)}