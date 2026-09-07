import json
from groq import Groq
from config import Config

client = Groq(api_key=Config.GROQ_API_KEY)

def call_llm(system_prompt, user_prompt, max_tokens=300):
    response = client.chat.completions.create(
        model = "llama3-8b-8192",
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        max_tokens  = max_tokens,
        temperature = 0.7
    )
    return response.choices[0].message.content.strip()


def get_round1_questions(resume_summary="", job_title="", experience_level="fresher"):
    """
    Generate 5 personalized communication questions
    based on candidate's experience level
    """
    system = (
        f"Generate EXACTLY 5 COMMUNICATION & SOFT-SKILL questions. "
        f"Candidate level: {experience_level}. "
        f"Adjust difficulty accordingly:\n"
        f"- fresher: Simple intro, college experience, learning attitude\n"
        f"- junior: Team work, basic challenges, growth mindset\n"
        f"- mid: Conflict handling, project leadership, mentoring\n"
        f"- senior: Strategic thinking, stakeholder mgmt, leadership\n\n"
        f"NO technical questions. Focus on HOW they communicate. "
        f"Reply ONLY as JSON array: "
        f'["q1","q2","q3","q4","q5"]'
    )
    user = f"Job: {job_title}\nResume: {resume_summary}"
    
    try:
        result = call_llm(system, user, max_tokens=400)
        import json
        s = result.find("[")
        e = result.rfind("]") + 1
        questions = json.loads(result[s:e])
        return questions[:5] if len(questions) >= 5 else questions
    except:
        return _fallback_round1(experience_level)


def _fallback_round1(level):
    if level == "fresher":
        return [
            "Tell me about yourself and your college journey.",
            "What was your favorite project in college and why?",
            "How do you handle learning a new concept?",
            "Describe a time you worked in a team during studies.",
            "Why are you interested in this role?"
        ]
    elif level == "senior":
        return [
            "Walk me through your career and key achievements.",
            "Describe a complex stakeholder situation you managed.",
            "How do you mentor and develop your team?",
            "Tell me about a strategic decision you led.",
            "Where do you see your career heading next?"
        ]
    else:  # junior/mid
        return [
            "Tell me about yourself and your work experience.",
            "Describe a challenge you faced at work and how you solved it.",
            "How do you handle disagreements with teammates?",
            "Tell me about your most successful project.",
            "Why are you looking for a change?"
        ]


def evaluate_soft_skill_answer(question, answer):
    # Detect non-answers
    answer_lower = answer.lower().strip()
    non_answer_phrases = [
        "i don't know", "i dont know", "no idea", "not sure",
        "skip", "next", "pass", "no answer", "don't know",
        "no clue", "cant answer", "can't answer"
    ]
    
    # Empty or too short
    if len(answer.strip()) < 5 or len(answer.split()) < 3:
        return {
            "relevance": 0, "clarity": 0, "structure": 0,
            "correctness": 0, "score": 0,
            "feedback": "No meaningful answer provided"
        }
    
    # Explicit "don't know"
    if any(phrase in answer_lower for phrase in non_answer_phrases):
        return {
            "relevance": 0, "clarity": 0, "structure": 0,
            "correctness": 0, "score": 0,
            "feedback": "Candidate acknowledged inability to answer"
        }
    
    system = (
        "You are a STRICT interview evaluator. Grade harshly.\n\n"
        "SCORING RULES:\n"
        "- If answer is wrong/irrelevant: correctness = 0-2\n"
        "- If answer shows partial understanding: correctness = 3-5\n"
        "- If answer is mostly correct: correctness = 6-8\n"
        "- If answer is complete and accurate: correctness = 9-10\n\n"
        "DO NOT give sympathy marks. Wrong answer = LOW score.\n\n"
        "Reply ONLY in JSON: "
        '{"relevance":0-10,"clarity":0-10,"structure":0-10,'
        '"correctness":0-10,"score":0-10,"feedback":"short"}'
    )
    user = f"Q: {question}\nA: {answer}"
    result = call_llm(system, user, max_tokens=150)
    
    try:
        s = result.find("{")
        e = result.rfind("}") + 1
        parsed = json.loads(result[s:e])
        
        # Recalculate score with correctness weight
        correctness = parsed.get("correctness", 0)
        relevance = parsed.get("relevance", 0)
        clarity = parsed.get("clarity", 0)
        
        # Correctness is 70%, relevance 20%, clarity 10%
        final_score = (correctness * 0.7) + (relevance * 0.2) + (clarity * 0.1)
        parsed["score"] = round(final_score, 1)
        
        return parsed
    except:
        return {
            "relevance": 0, "clarity": 0, "structure": 0,
            "correctness": 0, "score": 0,
            "feedback": "Parse error"
        }


def generate_opening_question(resume_summary, job_title):
    system = ("You are an AI interviewer. Ask ONE opening "
              "question. Max 2 sentences. No intro text.")
    user = f"Job: {job_title}\nResume: {resume_summary}"
    return call_llm(system, user, max_tokens=80)


def generate_followup_question(conversation_history, job_title):
    recent = conversation_history[-4:]
    history = "\n".join(
        [f"{m['role'].upper()}: {m['text']}" for m in recent]
    )
    system = ("You are an AI interviewer. Ask ONE follow-up "
              "question. Max 2 sentences. No extra text.")
    user = f"Job: {job_title}\nConversation:\n{history}"
    return call_llm(system, user, max_tokens=80)


# ── Round 3: Generate technical question bank ────
def generate_round3_question_plan(resume_summary, job_title, resume_data=None):
    resume_data = resume_data or {}
    projects = resume_data.get("projects", [])
    experience = resume_data.get("experience", [])
    
    # Build context covering ALL projects + experience
    proj_text = ""
    for p in projects:
        proj_text += f"- {p.get('name','')}: {p.get('description','')[:150]} (Tech: {','.join(p.get('tech',[]))})\n"
    
    exp_text = ""
    for e in experience:
        exp_text += f"- {e.get('role','')} at {e.get('company','')}: {e.get('description','')[:150]}\n"

    system = (
        "You are an AI interviewer planning a technical interview.\n\n"
        "TECHNICAL (7 questions): Mix of OOPS, OS, DBMS, SQL, Networks.\n\n"
        "RESUME (6 questions): MUST cover EACH project and experience "
        "the candidate listed. Distribute questions across ALL projects, "
        "not just one. Ask specific technical questions like:\n"
        "- 'In [Project A], what was your role architecture?'\n"
        "- 'For [Project B], how did you handle [specific tech]?'\n"
        "- 'At [Company], what was your biggest contribution?'\n\n"
        "Reply ONLY as JSON: "
        '{"technical":["q1",...7],"resume":["q1",...6]}'
    )
    
    user = f"""Job: {job_title}

ALL Projects (cover each one):
{proj_text or 'None'}

ALL Experience (cover each one):
{exp_text or 'None'}"""

    try:
        result = call_llm(system, user, max_tokens=1300)
        s = result.find("{")
        e = result.rfind("}") + 1
        plan = json.loads(result[s:e])
        return {
            "technical": plan.get("technical", [])[:7],
            "resume": plan.get("resume", [])[:6]
        }
    except Exception as e:
        print(f"Plan error: {e}")
        return _fallback_plan(projects, experience)


def _fallback_plan(projects, experience):
    tech = [
        "Explain the four pillars of OOPS with examples.",
        "Difference between process and thread? When to use which?",
        "Explain database normalization and its forms.",
        "Write SQL to find second highest salary.",
        "Difference between TCP and UDP? When to use each?",
        "Explain deadlock and 4 conditions for it.",
        "What is indexing? Types of indexes?"
    ]
    
    resume_qs = []
    for p in projects[:3]:
        name = p.get("name", "your project")
        resume_qs.append(f"Tell me about {name}. What was the main challenge?")
        if p.get("tech"):
            resume_qs.append(f"Why did you choose {p['tech'][0]} for {name}?")
    
    for e in experience[:2]:
        role = e.get("role", "your role")
        company = e.get("company", "company")
        resume_qs.append(f"What was your main contribution as {role} at {company}?")
    
    while len(resume_qs) < 6:
        resume_qs.append("Walk me through your most impactful project.")
    
    return {"technical": tech, "resume": resume_qs[:6]}


# ── Get next question from plan ──────────────────
def get_next_round3_question(plan, asked_questions, conversation_history, job_title):
    """
    Strategy:
    - Q1-7: TECHNICAL questions (OOPS, OS, DBMS, SQL, Networks)
    - Q8-13: RESUME questions covering ALL projects + experience
    - Follow-ups injected when answers are vague
    """
    asked_count = len(asked_questions)
    
    tech_remaining = [q for q in plan.get("technical", []) 
                      if q not in asked_questions]
    resume_remaining = [q for q in plan.get("resume", []) 
                        if q not in asked_questions]
    
    # Phase 1: Technical (Q1-7)
    if asked_count < 7 and tech_remaining:
        return tech_remaining[0]
    
    # Phase 2: Resume (Q8-13)
    if asked_count >= 7:
        last_answer = ""
        for msg in reversed(conversation_history):
            if msg["role"] == "candidate":
                last_answer = msg["text"]
                break
        
        # Count follow-ups already asked in resume phase
        followup_count = sum(
            1 for q in asked_questions[7:]
            if q not in plan.get("resume", [])
        )
        
        if last_answer:
            words = last_answer.lower().split()
            word_count = len(words)
            
            vague_phrases = ["i used", "i worked", "i built", "i made",
                             "i created", "i developed", "it was"]
            has_vague = any(p in last_answer.lower() for p in vague_phrases)
            
            is_vague = word_count < 20 or (has_vague and word_count < 40)
            
            # Max 2 follow-ups per resume question to keep coverage
            if is_vague and followup_count < 2:
                return _generate_truthfulness_followup(last_answer, job_title)
        
        # ALWAYS pick next resume question to ensure coverage
        if resume_remaining:
            return resume_remaining[0]
    
    if tech_remaining:
        return tech_remaining[0]
    if resume_remaining:
        return resume_remaining[0]
    return None


def _generate_truthfulness_followup(last_answer, job_title):
    """Ask deep technical follow-up to verify truthfulness"""
    system = (
        "Generate ONE specific technical follow-up question to verify "
        "if the candidate REALLY did what they claimed. Ask about "
        "specific implementation details, edge cases, or design decisions. "
        "Max 2 sentences. No intro text."
    )
    user = f"Job: {job_title}\nCandidate said: {last_answer}"
    return call_llm(system, user, max_tokens=80)


def _generate_followup(last_answer, job_title):
    system = (
        "Generate ONE short follow-up question based on the candidate's "
        "answer. Probe deeper. Max 2 sentences. No intro text."
    )
    user = f"Job: {job_title}\nAnswer: {last_answer}"
    return call_llm(system, user, max_tokens=80)


def evaluate_round3(conversation_history, job_title):
    if not conversation_history or len(conversation_history) < 2:
        return {
            "technical": 0, "communication": 0,
            "problem_solving": 0, "truthfulness": 0,
            "overall": 0,
            "strengths": "Not enough data",
            "weaknesses": "Interview incomplete",
            "verified_claims": "N/A",
            "suspicious_claims": "N/A"
        }
    
    recent = conversation_history[-30:]
    history = "\n".join(
        [f"{m['role'].upper()}: {m['text']}" for m in recent]
    )
    
    # Count non-answers
    candidate_answers = [m['text'] for m in recent if m['role'] == 'candidate']
    non_answer_count = 0
    total_answers = len(candidate_answers)
    
    non_answer_phrases = ["i don't know", "dont know", "no idea", 
                          "not sure", "skip", "no answer"]
    for ans in candidate_answers:
        ans_lower = ans.lower().strip()
        if len(ans.strip()) < 10 or any(p in ans_lower for p in non_answer_phrases):
            non_answer_count += 1
    
    non_answer_ratio = non_answer_count / total_answers if total_answers > 0 else 1
    
    system = (
        "You are a STRICT technical interviewer. Grade HARSHLY.\n\n"
        "SCORING RULES:\n"
        "- Wrong/vague/'I don't know' answers = 0-2 score\n"
        "- Partial correct = 3-5\n"
        "- Mostly correct = 6-8\n"
        "- Fully correct with depth = 9-10\n\n"
        "DO NOT give effort marks. Only actual knowledge counts.\n"
        "Count how many questions were answered CORRECTLY.\n\n"
        "Reply ONLY in valid JSON:\n"
        '{"technical":0-10,"communication":0-10,'
        '"problem_solving":0-10,"truthfulness":0-10,"overall":0-10,'
        '"correct_answers_count":number,"total_questions":number,'
        '"strengths":"2-3 specific strengths",'
        '"weaknesses":"specific weak areas",'
        '"verified_claims":"things they proved",'
        '"suspicious_claims":"vague/false claims"}'
    )
    user = f"Job: {job_title}\n\nInterview Transcript:\n{history}"
    
    try:
        result = call_llm(system, user, max_tokens=600)
        s = result.find("{")
        e = result.rfind("}") + 1
        parsed = json.loads(result[s:e])
        
        # Apply non-answer penalty
        if non_answer_ratio > 0.3:  # More than 30% non-answers
            penalty = 1 - (non_answer_ratio * 0.7)
            parsed["technical"] = round(parsed.get("technical", 0) * penalty, 1)
            parsed["problem_solving"] = round(parsed.get("problem_solving", 0) * penalty, 1)
            parsed["overall"] = round(parsed.get("overall", 0) * penalty, 1)
        
        defaults = {
            "technical": 0, "communication": 0,
            "problem_solving": 0, "truthfulness": 0,
            "overall": 0,
            "strengths": "Review manually",
            "weaknesses": "Multiple weak areas",
            "verified_claims": "None verified",
            "suspicious_claims": "Multiple unclear responses"
        }
        for k, v in defaults.items():
            if k not in parsed or parsed[k] is None:
                parsed[k] = v
        
        return parsed
    except Exception as e:
        print(f"Round 3 eval failed: {e}")
        return {
            "technical": 0, "communication": 0,
            "problem_solving": 0, "truthfulness": 0,
            "overall": 0,
            "strengths": "Evaluation failed",
            "weaknesses": "Could not analyze",
            "verified_claims": "N/A",
            "suspicious_claims": "N/A"
        }


def generate_final_report(name, job, scores, observations, flags):
    system = ("Generate short HR report. Include recommendation. "
              "Max 150 words. Professional tone.")
    user = (f"Candidate: {name}\nJob: {job}\nScores: {scores}\n"
            f"Observations: {observations}\nFlags: {flags}")
    return call_llm(system, user, max_tokens=200)

def detect_suspicious_answer(answer, response_time_secs):
    """
    Detect if answer is pre-written / copy-pasted / read
    Returns suspicion score (0-10)
    """
    flags = []
    
    # Too fast = suspicious (typed/pasted)
    word_count = len(answer.split())
    if word_count > 50 and response_time_secs < 5:
        flags.append("typed_too_fast")
    
    # Too perfect = suspicious (no fillers)
    fillers = ["um","uh","like","you know","actually","basically"]
    has_filler = any(f in answer.lower() for f in fillers)
    if word_count > 30 and not has_filler:
        flags.append("no_natural_fillers")
    
    # Too long answer
    if word_count > 200:
        flags.append("unusually_long")
    
    # LLM analysis for sophistication
    if word_count > 20:
        system = (
            "Analyze if this interview answer sounds rehearsed/read "
            "vs natural spoken. Reply ONLY: NATURAL or REHEARSED"
        )
        user = f"Answer: {answer}"
        try:
            result = call_llm(system, user, max_tokens=20)
            if "REHEARSED" in result.upper():
                flags.append("sounds_rehearsed")
        except:
            pass
    
    suspicion_score = len(flags) * 2.5  # max 10
    return {
        "suspicion_score": min(suspicion_score, 10),
        "flags": flags,
        "response_time": response_time_secs,
        "word_count": word_count
    }


def check_consistency(round1_answers, round3_answers):
    """
    Check if candidate gave consistent info across rounds
    """
    r1_text = " ".join(round1_answers)
    r3_text = " ".join(round3_answers)
    
    system = (
        "Check if two interview transcripts are CONSISTENT "
        "(same person, same background story). "
        "Reply ONLY in JSON: "
        '{"consistent":true/false,"issues":"brief"}'
    )
    user = f"Round1:\n{r1_text[:500]}\n\nRound3:\n{r3_text[:500]}"
    
    try:
        result = call_llm(system, user, max_tokens=100)
        import json
        s = result.find("{")
        e = result.rfind("}") + 1
        return json.loads(result[s:e])
    except:
        return {"consistent": True, "issues": "Parse error"}
    

def generate_aptitude_questions():
    system_prompt = """Generate exactly 20 aptitude MCQs.

5 questions EACH from these 4 sections (use EXACT section names):
- "Verbal": grammar, comprehension, sentence completion
- "Reasoning": coding-decoding, series, blood relations, puzzles
- "Numerical": percentages, ratios, profit-loss, time-work
- "Programming": pseudocode, loops, output prediction

Return ONLY valid JSON:
{
  "questions": [
    {"id":1,"section":"Verbal","question":"...","options":{"A":"...","B":"...","C":"...","D":"..."},"correct_answer":"A"}
  ]
}

All 20 questions in array. Keep questions SHORT, but not too short."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # BIGGER model for better JSON
            messages=[{"role": "user", "content": system_prompt}],
            temperature=0.8,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        result = json.loads(content)
        
        questions = result.get("questions", [])
        print(f"Generated {len(questions)} questions")  # Debug
        
        if len(questions) < 15:
            print("Too few questions, using fallback")
            return {"questions": _fallback_aptitude()}
        
        return result
    except Exception as e:
        print(f"Aptitude gen failed: {e}")
        import traceback
        traceback.print_exc()
        return {"questions": _fallback_aptitude()}


def _fallback_aptitude():
    """Fallback questions if LLM fails"""
    return [
        {"id":1,"section":"Verbal","question":"Choose synonym of 'Abundant':","options":{"A":"Plentiful","B":"Scarce","C":"Rare","D":"Empty"},"correct_answer":"A"},
        {"id":2,"section":"Verbal","question":"Choose antonym of 'Brave':","options":{"A":"Bold","B":"Cowardly","C":"Strong","D":"Daring"},"correct_answer":"B"},
        {"id":3,"section":"Verbal","question":"Fill: She ___ to school daily.","options":{"A":"go","B":"goes","C":"going","D":"went"},"correct_answer":"B"},
        {"id":4,"section":"Verbal","question":"Choose correctly spelled word:","options":{"A":"Recieve","B":"Receive","C":"Receeve","D":"Receave"},"correct_answer":"B"},
        {"id":5,"section":"Verbal","question":"'Break the ice' means:","options":{"A":"Cool down","B":"Start conversation","C":"Be cold","D":"Stop talking"},"correct_answer":"B"},
        {"id":6,"section":"Reasoning","question":"If CAT=24, DOG=26, what is BAT?","options":{"A":"22","B":"23","C":"24","D":"25"},"correct_answer":"A"},
        {"id":7,"section":"Reasoning","question":"Series: 2,4,8,16,?","options":{"A":"24","B":"30","C":"32","D":"36"},"correct_answer":"C"},
        {"id":8,"section":"Reasoning","question":"A is B's father. B is C's mother. C is A's:","options":{"A":"Son","B":"Daughter","C":"Grandchild","D":"Niece"},"correct_answer":"C"},
        {"id":9,"section":"Reasoning","question":"Odd one out: 9, 25, 49, 50","options":{"A":"9","B":"25","C":"49","D":"50"},"correct_answer":"D"},
        {"id":10,"section":"Reasoning","question":"If MONDAY=12, what is FRIDAY?","options":{"A":"6","B":"8","C":"10","D":"12"},"correct_answer":"A"},
        {"id":11,"section":"Numerical","question":"20% of 250 is:","options":{"A":"40","B":"45","C":"50","D":"55"},"correct_answer":"C"},
        {"id":12,"section":"Numerical","question":"CP=100, SP=120. Profit %?","options":{"A":"10%","B":"15%","C":"20%","D":"25%"},"correct_answer":"C"},
        {"id":13,"section":"Numerical","question":"Ratio 3:5, total=80. Smaller part?","options":{"A":"25","B":"30","C":"35","D":"40"},"correct_answer":"B"},
        {"id":14,"section":"Numerical","question":"Speed=60kmh, Time=2.5hr. Distance?","options":{"A":"120","B":"150","C":"180","D":"200"},"correct_answer":"B"},
        {"id":15,"section":"Numerical","question":"A does work in 10 days, B in 15. Together?","options":{"A":"5","B":"6","C":"7","D":"8"},"correct_answer":"B"},
        {"id":16,"section":"Programming","question":"Output: for(i=0;i<3;i++) print(i)","options":{"A":"0,1,2","B":"1,2,3","C":"0,1,2,3","D":"1,2"},"correct_answer":"A"},
        {"id":17,"section":"Programming","question":"Array [5,2,8,1]. After sort ascending:","options":{"A":"5,2,8,1","B":"1,2,5,8","C":"8,5,2,1","D":"1,5,2,8"},"correct_answer":"B"},
        {"id":18,"section":"Programming","question":"What does len('hello') return?","options":{"A":"4","B":"5","C":"6","D":"hello"},"correct_answer":"B"},
        {"id":19,"section":"Programming","question":"if(x>5) and x=3, result?","options":{"A":"True","B":"False","C":"Error","D":"None"},"correct_answer":"B"},
        {"id":20,"section":"Programming","question":"Reverse of 'abc':","options":{"A":"abc","B":"cba","C":"bca","D":"cab"},"correct_answer":"B"}
    ]

