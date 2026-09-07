import random
from flask import Blueprint, request, jsonify
from database.mysql_db import get_connection
from database.mongo_db import interviews_col, get_interview_log
from services.score_service import calculate_round2_score
from services.groq_service import generate_aptitude_questions

aptitude_bp = Blueprint("aptitude", __name__)


@aptitude_bp.route("/start/<interview_id>", methods=["POST"])
def start_aptitude(interview_id):
    log = get_interview_log(interview_id)
    cached_questions = log.get("aptitude_questions") if log else None
    
    if cached_questions:
        questions = cached_questions
    else:
        try:
            result = generate_aptitude_questions()
            questions = result.get("questions", [])
            interviews_col.update_one(
                {"interview_id": interview_id},
                {"$set": {"aptitude_questions": questions}}
            )
        except Exception as e:
            print(f"Aptitude generation failed: {e}")
            return jsonify({"error": "Failed to generate questions"}), 500
    
    # Group by section - normalize case
    sections = {}
    for q in questions:
        section = q.get("section", "General").strip().title()
        if section not in sections:
            sections[section] = []
        
        options_dict = q.get("options", {})
        options_list = [{"key": k, "text": v} for k, v in options_dict.items()]
        random.shuffle(options_list)
        
        sections[section].append({
            "question_id": q["id"],
            "question_text": q["question"],
            "options": options_list
        })
    
    # DEBUG
    print("Sections found:", list(sections.keys()))
    print("Questions per section:", {k: len(v) for k, v in sections.items()})
    
    ordered_sections = []
    used_keys = set()
    
    section_keywords = {
        "Verbal": ["verbal", "english", "comprehension", "grammar"],
        "Reasoning": ["reasoning", "logical", "logic"],
        "Numerical": ["numerical", "quantitative", "math", "arithmetic"],
        "Programming": ["programming", "coding", "computer"]
    }
    
    for display_name, keywords in section_keywords.items():
        for key in sections.keys():
            if key in used_keys:
                continue
            if any(kw in key.lower() for kw in keywords):
                ordered_sections.append({
                    "name": display_name,
                    "questions": sections[key]
                })
                used_keys.add(key)
                break

    for key in sections.keys():
        if key not in used_keys:
            ordered_sections.append({
                "name": key,
                "questions": sections[key]
            })
    
    # FALLBACK - if empty, put all in one section
    if not ordered_sections:
        all_qs = []
        for qs in sections.values():
            all_qs.extend(qs)
        ordered_sections = [{"name": "General", "questions": all_qs}]

    print("Ordered sections:", [(s["name"], len(s["questions"])) for s in ordered_sections])

    return jsonify({
        "sections": ordered_sections,
        "total_questions": len(questions),
        "time_per_q": 60,
        "time_limit": 20 * 60
    })


@aptitude_bp.route("/submit", methods=["POST"])
def submit_aptitude():
    data = request.json
    interview_id = data["interview_id"]
    answers = data["answers"]
    
    # Get cached questions
    log = get_interview_log(interview_id)
    questions = log.get("aptitude_questions", []) if log else []
    
    # Build questions list for scoring
    questions_for_score = [
        {
            "question_id": q["id"],
            "correct_answer": q["correct_answer"]
        }
        for q in questions
    ]
    
    score = calculate_round2_score(answers, questions_for_score)
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE interviews SET round2_score=%s, status='round3' "
        "WHERE interview_id=%s", (score, interview_id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({"round2_score": score, "next_round": "ai_interview"})