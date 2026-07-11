import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
    MYSQL_HOST     = os.getenv("MYSQL_HOST")
    MYSQL_USER     = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DB       = os.getenv("MYSQL_DB")
    MONGO_URI      = os.getenv("MONGO_URI")
    MONGO_DB       = os.getenv("MONGO_DB")
    SECRET_KEY     = os.getenv("SECRET_KEY")