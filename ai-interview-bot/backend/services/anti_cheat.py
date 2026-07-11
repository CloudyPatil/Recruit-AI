from datetime import datetime
from database.mongo_db import add_anticheat_flag, get_interview_log
from database.mysql_db import get_connection

def log_flag(interview_id, flag_type, detail=""):
    flag = {
        "type":   flag_type,
        "detail": detail,
        "timestamp": datetime.utcnow().isoformat()
    }
    add_anticheat_flag(interview_id, flag)
    return check_terminate(interview_id)


def check_terminate(interview_id):
    log = get_interview_log(interview_id)
    flags = log.get("anti_cheat_logs", []) if log else []
    
    # SERIOUS - instant terminate threshold
    serious_types = {
        "tab_switch", 
        "multiple_faces", 
        "suspicious_object"
    }
    
    # WARNING - need more to terminate
    warning_types = {
        "no_face", 
        "looking_away",
        "window_blur"
    }
    
    serious_count = sum(
        1 for f in flags 
        if f["type"] in serious_types
    )
    
    warning_count = sum(
        1 for f in flags 
        if f["type"] in warning_types
    )
    
    # Terminate rules:
    # - 3 serious flags
    # - OR 10 warnings
    should_terminate = (
        serious_count >= 3 or 
        warning_count >= 10
    )
    
    if should_terminate:
        terminate_interview(interview_id)
        return {
            "action": "terminate", 
            "count": serious_count + warning_count
        }
    
    return {
        "action": "warn", 
        "count": serious_count + warning_count
    }


def terminate_interview(interview_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE interviews SET status='terminated' WHERE interview_id=%s",
        (interview_id,)
    )
    conn.commit()
    conn.close()