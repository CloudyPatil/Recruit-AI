from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from matcher import match_with_explanation
from file_extractor import extract_text
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Resume Matcher API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "API Running"}

# ENDPOINT 1 - Single resume with explanation
@app.post("/match-single")
async def match_single(
    resume_file: UploadFile = File(...),
    job_description: str = Form(...)
):
    contents = await resume_file.read()
    resume_text = extract_text(contents, resume_file.filename)
    
    if not resume_text or len(resume_text) < 20:
        return {"error": "Could not extract text"}
    
    result = match_with_explanation(resume_text, job_description)
    result["filename"] = resume_file.filename
    return result

# ENDPOINT 2 - Bulk resumes with explanation
@app.post("/match-bulk")
async def match_bulk(
    job_description: str = Form(...),
    resume_files: List[UploadFile] = File(...)
):
    results = []
    
    for file in resume_files:
        contents = await file.read()
        resume_text = extract_text(contents, file.filename)
        
        if not resume_text or len(resume_text) < 20:
            results.append({
                "filename": file.filename,
                "error": "Could not extract text"
            })
            continue
        
        # Use SHAP explanation for bulk too
        match = match_with_explanation(resume_text, job_description)
        match["filename"] = file.filename
        results.append(match)
    
    valid = [r for r in results if 'final_score' in r]
    errors = [r for r in results if 'error' in r]
    valid.sort(key=lambda x: x['final_score'], reverse=True)
    
    for i, r in enumerate(valid):
        r['rank'] = i + 1
    
    return {
        "total": len(results),
        "ranked_candidates": valid,
        "errors": errors
    }

@app.post("/extract-text")
async def extract_text_api(resume_file: UploadFile = File(...)):
    from file_extractor import extract_resume_text
    import tempfile, os

    suffix = "." + resume_file.filename.split(".")[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await resume_file.read())
        tmp_path = tmp.name

    try:
        text = extract_resume_text(tmp_path)
    finally:
        os.unlink(tmp_path)

    return {"text": text}

@app.post("/parse-resume")
async def parse_resume(resume_file: UploadFile = File(...)):
    import os, json
    from groq import Groq
    
    contents = await resume_file.read()
    text = extract_text(contents, resume_file.filename)
    
    if not text or len(text) < 50:
        return {"error": "Could not extract resume"}
    
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    prompt = f"""Extract structured info from this resume.

Resume:
{text[:3500]}

Return ONLY valid JSON:
{{
  "summary": "2-line professional summary",
  "experience": [
    {{
      "role": "job title",
      "company": "company",
      "duration": "period",
      "description": "what they did, tech used"
    }}
  ],
  "projects": [
    {{
      "name": "project name",
      "tech": ["tech1","tech2"],
      "description": "what was built"
    }}
  ],
  "skills": ["skill1","skill2"],
  "education": [
    {{"degree":"...","institute":"...","year":"..."}}
  ]
}}"""

    try:
        res = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        return {"error": str(e), "raw_text": text[:1000]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)