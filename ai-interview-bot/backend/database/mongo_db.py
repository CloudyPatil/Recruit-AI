from pymongo import MongoClient
from config import Config

client = MongoClient(Config.MONGO_URI)
db     = client[Config.MONGO_DB]
interviews_col = db["interview_logs"]

def save_interview_log(interview_id, data):
    interviews_col.update_one(
        {"interview_id": interview_id},
        {"$set": data},
        upsert=True
    )

def get_interview_log(interview_id):
    return interviews_col.find_one(
        {"interview_id": interview_id}, {"_id": 0}
    )

def add_conversation_message(interview_id, role, text):
    interviews_col.update_one(
        {"interview_id": interview_id},
        {"$push": {"conversation_log": {"role": role, "text": text}}},
        upsert=True
    )

def add_anticheat_flag(interview_id, flag):
    interviews_col.update_one(
        {"interview_id": interview_id},
        {"$push": {"anti_cheat_logs": flag}},
        upsert=True
    )