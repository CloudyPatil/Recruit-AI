import uuid
import os
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from services.groq_service import detect_suspicious_answer
from groq import Groq

from config import Config
from database.mysql_db import get_connection
from database.mongo_db import (
    save_interview_log, get_interview_log,
    add_conversation_message, interviews_col
)
from services.groq_service import (
    get_round1_questions, evaluate_soft_skill_answer, generate_round3_question_plan, get_next_round3_question,
    generate_opening_question, generate_followup_question,
    evaluate_round3
)
from services.score_service import (
    calculate_round1_score, calculate_round3_score
)
from services.anti_cheat import log_flag

interview_bp = Blueprint("interview", __name__)
groq_client = Groq(api_key=Config.GROQ_API_KEY)


@interview_bp.route("/create", methods=["POST"])
def create_interview():
    data = request.json
    interview_id = str(uuid.uuid4())
    link_token   = str(uuid.uuid4())
    expires = datetime.now() + timedelta(hours=24)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO interviews
        (interview_id, candidate_id, job_id, candidate_name,
         job_title, ml_score, link_token, link_expires, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'pending')
    """, (interview_id, data["candidate_id"], data["job_id"],
          data["candidate_name"], data["job_title"],
          data.get("ml_score", 0), link_token, expires))
    conn.commit()
    conn.close()

    save_interview_log(interview_id, {
    "interview_id":     interview_id,
    "candidate_name":   data["candidate_name"],
    "job_title":        data["job_title"],
    "resume_summary":   data.get("resume_summary", ""),
    "resume_data":      data.get("resume_data", {}),
    "experience_level": data.get("experience_level", "fresher"),
    "conversation_log": [],
    "anti_cheat_logs":  [],
    "round1_evals":     []
    })

    return jsonify({
        "interview_id":  interview_id,
        "link_token":    link_token,
        "expires":       expires.isoformat(),
        "interview_url": f"/interview/{link_token}"
    })


@interview_bp.route("/validate/<token>", methods=["GET"])
def validate_link(token):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM interviews WHERE link_token=%s", (token,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"valid": False, "error": "Link not found"}), 404
    if row["status"] == "terminated":
        return jsonify({"valid": False, "error": "Terminated"}), 403
    if row["status"] == "completed":
        return jsonify({"valid": False, "error": "Already completed"}), 403
    if datetime.utcnow() > row["link_expires"]:
        return jsonify({"valid": False, "error": "Link expired"}), 403

    return jsonify({
        "valid": True,
        "interview_id":   row["interview_id"],
        "candidate_name": row["candidate_name"],
        "job_title":      row["job_title"]
    })


@interview_bp.route("/round1/start/<interview_id>", methods=["POST"])
def round1_start(interview_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE interviews SET status='round1' WHERE interview_id=%s",
        (interview_id,)
    )
    cursor.execute(
        "SELECT job_title FROM interviews WHERE interview_id=%s",
        (interview_id,)
    )
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    
    job_title = row["job_title"] if row else ""
    log = get_interview_log(interview_id)
    resume = log.get("resume_summary", "") if log else ""
    level  = log.get("experience_level", "fresher") if log else "fresher"
    
    questions = get_round1_questions(resume, job_title, level)
    
    return jsonify({
        "questions":  questions,
        "time_limit": 15 * 60
    })


@interview_bp.route("/round1/answer", methods=["POST"])
def round1_answer():
    data = request.json
    evaluation = evaluate_soft_skill_answer(
        data["question"], data["answer"]
    )
    interviews_col.update_one(
        {"interview_id": data["interview_id"]},
        {"$push": {"round1_evals": {
            "question":   data["question"],
            "answer":     data["answer"],
            "evaluation": evaluation
        }}}
    )
    return jsonify({"evaluation": evaluation})


@interview_bp.route("/round1/complete", methods=["POST"])
def round1_complete():
    data = request.json
    interview_id = data["interview_id"]
    log = get_interview_log(interview_id)
    evals = [e["evaluation"] for e in log.get("round1_evals", [])]
    score = calculate_round1_score(evals)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE interviews SET round1_score=%s, status='round2' "
        "WHERE interview_id=%s", (score, interview_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"round1_score": score, "next_round": "aptitude"})


# ── Update round3_start ──
@interview_bp.route("/round3/start/<interview_id>", methods=["POST"])
def round3_start(interview_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE interviews SET status='round3' WHERE interview_id=%s",
        (interview_id,)
    )
    conn.commit()
    cursor.execute(
        "SELECT job_title FROM interviews WHERE interview_id=%s",
        (interview_id,)
    )
    row = cursor.fetchone()
    job_title = row["job_title"] if row else "Software Engineer"
    conn.close()

    log = get_interview_log(interview_id)
    resume = log.get("resume_summary", "")
    resume_data = log.get("resume_data", {})  # NEW
    
    # Generate plan with structured resume data
    plan = generate_round3_question_plan(resume, job_title, resume_data)
    
    interviews_col.update_one(
        {"interview_id": interview_id},
        {"$set": {"round3_plan": plan, "round3_asked": []}}
    )
    
    first_question = plan["technical"][0] if plan.get("technical") else plan["resume"][0]
    add_conversation_message(interview_id, "ai", first_question)
    
    interviews_col.update_one(
        {"interview_id": interview_id},
        {"$push": {"round3_asked": first_question}}
    )

    return jsonify({"question": first_question, "time_limit": 25 * 60})


# ── Update round3_respond ──
@interview_bp.route("/round3/respond", methods=["POST"])
def round3_respond():
    data = request.json
    interview_id = data["interview_id"]
    answer = data["answer"]
    q_count = data.get("question_count", 0)

    add_conversation_message(interview_id, "candidate", answer)

    # Suspicious answer check
    response_time = data.get("response_time", 10)
    suspicion = detect_suspicious_answer(answer, response_time)
    if suspicion["suspicion_score"] >= 5:
        from services.anti_cheat import log_flag
        log_flag(
            interview_id, "suspicious_answer",
            f"Score: {suspicion['suspicion_score']}"
        )

    # Total 15 questions max
    if q_count >= 13:
        return jsonify({
            "done": True,
            "message": "Thank you! That concludes our interview."
        })

    log = get_interview_log(interview_id)
    conversation = log.get("conversation_log", [])
    job_title = log.get("job_title", "")
    plan = log.get("round3_plan", {})
    asked = log.get("round3_asked", [])

    next_q = get_next_round3_question(plan, asked, conversation, job_title)
    
    if not next_q:
        return jsonify({
            "done": True,
            "message": "Thank you! We've covered all the topics."
        })
    
    add_conversation_message(interview_id, "ai", next_q)
    interviews_col.update_one(
        {"interview_id": interview_id},
        {"$push": {"round3_asked": next_q}}
    )

    return jsonify({"done": False, "question": next_q})


@interview_bp.route("/round3/complete", methods=["POST"])
def round3_complete():
    data = request.json
    interview_id = data["interview_id"]
    log = get_interview_log(interview_id)
    conversation = log.get("conversation_log", [])
    job_title = log.get("job_title", "")

    evaluation = evaluate_round3(conversation, job_title)
    score = calculate_round3_score(evaluation)

    interviews_col.update_one(
        {"interview_id": interview_id},
        {"$set": {"round3_evaluation": evaluation}}
    )

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE interviews SET round3_score=%s WHERE interview_id=%s",
        (score, interview_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"round3_score": score, "evaluation": evaluation})


@interview_bp.route("/flag", methods=["POST"])
def flag_event():
    data = request.json
    result = log_flag(
        data["interview_id"], data["flag_type"],
        data.get("detail", "")
    )
    return jsonify(result)


@interview_bp.route("/transcribe", methods=["POST"])
def transcribe_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio"}), 400

    audio_file = request.files["audio"]
    temp_path = "temp_audio.webm"
    audio_file.save(temp_path)

    transcript = ""
    try:
        with open(temp_path, "rb") as f:
            transcription = groq_client.audio.transcriptions.create(
                model = "whisper-large-v3-turbo",
                file  = f
            )
        transcript = transcription.text
    except Exception as e:
        print(f"Whisper error: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return jsonify({"transcript": transcript})

@interview_bp.route("/flag-count/<interview_id>", methods=["GET"])
def get_flag_count(interview_id):
    from database.mongo_db import get_interview_log
    log = get_interview_log(interview_id)
    flags = log.get("anti_cheat_logs", []) if log else []
    serious = [f for f in flags if f["type"] in 
               ["tab_switch","multiple_faces","no_face","looking_away"]]
    return jsonify({"count": len(serious)})

@interview_bp.route("/log/<interview_id>", methods=["GET"])
def get_log(interview_id):
    log = get_interview_log(interview_id)
    return jsonify(log or {})    