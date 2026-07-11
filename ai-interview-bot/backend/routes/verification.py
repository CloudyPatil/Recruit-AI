import os
from flask import Blueprint, request, jsonify
from services.identity_service import (
    verify_identity, cleanup_temp_files,
    extract_text_from_id, detect_document_type,
    extract_name_from_id, match_names
)
from database.mongo_db import get_interview_log, interviews_col
from database.mysql_db import get_connection

verify_bp = Blueprint("verify", __name__)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@verify_bp.route("/document/<interview_id>", methods=["POST"])
def verify_document(interview_id):
    """Step 1 + 2: Upload ID, validate type, match name"""
    if "id_photo" not in request.files:
        return jsonify({"error": "ID photo required"}), 400

    id_photo = request.files["id_photo"]
    id_path = os.path.join(UPLOAD_DIR, f"{interview_id}_id.jpg")
    id_photo.save(id_path)

    # Step 1: OCR + Detect type
    text = extract_text_from_id(id_path)
    doc_type = detect_document_type(text)
    
    if doc_type == "Unknown Document":
        cleanup_temp_files(id_path)
        return jsonify({
            "valid": False,
            "error": "Could not identify document. Please upload a valid ID (Aadhar/PAN/License/College ID)"
        }), 400

    # Step 2: Extract name from ID
    id_name = extract_name_from_id(text, doc_type)
    
    # Get candidate name from interview
    log = get_interview_log(interview_id)
    resume_name = log.get("candidate_name", "") if log else ""

    if not id_name:
        return jsonify({
            "valid": True,
            "doc_type": doc_type,
            "name_check": {"match": False, "score": 0, "error": "Could not extract name from ID"},
            "warning": "Name extraction failed - proceeding with face match"
        })

    # Name matching
    name_match = match_names(id_name, resume_name)
    
    # Save to log
    interviews_col.update_one(
        {"interview_id": interview_id},
        {"$set": {
            "verification": {
                "doc_type": doc_type,
                "id_name": id_name,
                "name_match": name_match
            }
        }}
    )

    return jsonify({
        "valid": True,
        "doc_type": doc_type,
        "name_check": name_match,
        "id_path": id_path  # for face verification step
    })


@verify_bp.route("/face/<interview_id>", methods=["POST"])
def verify_face(interview_id):
    """Step 3: Face match between ID and live"""
    if "live_photo" not in request.files:
        return jsonify({"error": "Live photo required"}), 400

    live_photo = request.files["live_photo"]
    id_path = os.path.join(UPLOAD_DIR, f"{interview_id}_id.jpg")
    live_path = os.path.join(UPLOAD_DIR, f"{interview_id}_live.jpg")

    if not os.path.exists(id_path):
        return jsonify({"error": "Please upload ID first"}), 400

    live_photo.save(live_path)

    result = verify_identity(id_path, live_path)

    # Save final verification
    interviews_col.update_one(
        {"interview_id": interview_id},
        {"$set": {"verification.face_match": result}}
    )

    cleanup_temp_files(live_path)
    return jsonify(result)


# Keep old endpoint for backward compat
@verify_bp.route("/identity/<interview_id>", methods=["POST"])
def verify_candidate(interview_id):
    """OLD endpoint - kept for compatibility"""
    if "id_photo" not in request.files or "live_photo" not in request.files:
        return jsonify({"error": "Both photos required"}), 400

    id_photo = request.files["id_photo"]
    live_photo = request.files["live_photo"]

    id_path = os.path.join(UPLOAD_DIR, f"{interview_id}_id.jpg")
    live_path = os.path.join(UPLOAD_DIR, f"{interview_id}_live.jpg")

    id_photo.save(id_path)
    live_photo.save(live_path)

    result = verify_identity(id_path, live_path)
    cleanup_temp_files(live_path)
    return jsonify(result)


@verify_bp.route("/system-check", methods=["POST"])
def system_check():
    data = request.json
    checks = {
        "browser_supported": data.get("browser", False),
        "camera_working": data.get("camera", False),
        "mic_working": data.get("mic", False),
        "internet_speed": data.get("speed", 0)
    }
    all_pass = all([
        checks["browser_supported"],
        checks["camera_working"],
        checks["mic_working"]
    ])
    return jsonify({"passed": all_pass, "checks": checks})