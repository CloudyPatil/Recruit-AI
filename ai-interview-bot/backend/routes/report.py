from flask import Blueprint, jsonify
from database.mysql_db import get_connection
from database.mongo_db import get_interview_log, save_interview_log
from services.groq_service import generate_final_report
from services.score_service import calculate_final_score

report_bp = Blueprint("report", __name__)


@report_bp.route("/generate/<interview_id>", methods=["POST"])
def generate_report(interview_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM interviews WHERE interview_id=%s",
        (interview_id,)
    )
    interview = cursor.fetchone()
    if not interview:
        return jsonify({"error": "Not found"}), 404

    # NEW - check if terminated
    is_terminated = interview["status"] == "terminated"

    final = calculate_final_score(
        interview["ml_score"], interview["round1_score"],
        interview["round2_score"], interview["round3_score"]
    )
    
    r1 = interview["round1_score"] or 0
    r3 = interview["round3_score"] or 0

    # Existing logic - but skip status change if terminated
    if not is_terminated:
        if r1 > 0 or r3 > 0:
            cursor.execute(
                "UPDATE interviews SET final_score=%s, status='completed' "
                "WHERE interview_id=%s", (final, interview_id)
            )   
        else:
            cursor.execute(
                "UPDATE interviews SET final_score=%s "
                "WHERE interview_id=%s", (final, interview_id)
            )
    else:
        cursor.execute(
            "UPDATE interviews SET final_score=%s "
            "WHERE interview_id=%s", (final, interview_id)
        )

    conn.commit()
    conn.close()

    log = get_interview_log(interview_id)
    flags = log.get("anti_cheat_logs", [])
    r3_eval = log.get("round3_evaluation", {})

    scores = {
        "ml_score": interview["ml_score"],
        "round1":   interview["round1_score"],
        "round2":   interview["round2_score"],
        "round3":   interview["round3_score"],
        "final":    final
    }

    observations = {
        "strengths":  r3_eval.get("strengths", "N/A"),
        "weaknesses": r3_eval.get("weaknesses", "N/A"),
        "verified_claims":   r3_eval.get("verified_claims", "N/A"),
        "suspicious_claims": r3_eval.get("suspicious_claims", "N/A"),
        "truthfulness_score": r3_eval.get("truthfulness", 0)
    }

    # NEW - termination summary
    if is_terminated:
        violation_summary = _summarize_violations(flags)
        ai_summary = (
            f"INTERVIEW TERMINATED due to violations. "
            f"Candidate was disqualified. "
            f"Total flags: {len(flags)}. "
            f"Violations: {violation_summary}. "
            f"This candidate should NOT be considered for the role."
        )
        recommendation = "DISQUALIFIED - TERMINATED"
        status_label = "TERMINATED"
    else:
        ai_summary = generate_final_report(
            interview["candidate_name"], interview["job_title"],
            scores, observations, len(flags)
        )
        recommendation = "RECOMMENDED" if final >= 60 else "NOT RECOMMENDED"
        status_label = "CLEAN" if len(flags) < 3 else "FLAGGED"

    report = {
        "candidate_name": interview["candidate_name"],
        "job_title":      interview["job_title"],
        "scores":         scores,
        "observations":   observations,
        "anti_cheat": {
            "total_flags": len(flags),
            "flags":       flags,
            "status":      status_label
        },
        "ai_summary":     ai_summary,
        "recommendation": recommendation,
        "terminated":     is_terminated
    }

    save_interview_log(interview_id, {"final_report": report})
    return jsonify(report)


def _summarize_violations(flags):
    """Group and count violation types"""
    if not flags:
        return "None"
    
    counts = {}
    for f in flags:
        ftype = f.get("type", "unknown").replace("_", " ").title()
        counts[ftype] = counts.get(ftype, 0) + 1
    
    return ", ".join([f"{k} ({v}x)" for k, v in counts.items()])


@report_bp.route("/get/<interview_id>", methods=["GET"])
def get_report(interview_id):
    log = get_interview_log(interview_id)
    if not log or "final_report" not in log:
        return jsonify({"error": "Report not ready"}), 404
    return jsonify(log["final_report"])