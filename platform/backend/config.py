from dotenv import load_dotenv
import os

load_dotenv()

MYSQL_HOST     = os.getenv("MYSQL_HOST")
MYSQL_USER     = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB       = os.getenv("MYSQL_DB")

MONGO_URI      = os.getenv("MONGO_URI")
MONGO_DB       = os.getenv("MONGO_DB")

SECRET_KEY     = os.getenv("SECRET_KEY")
ALGORITHM      = os.getenv("ALGORITHM")
TOKEN_EXPIRE   = int(os.getenv("ACCESS_TOKEN_EXPIRE"))

ML_URL         = os.getenv("ML_MODEL_URL")
BOT_URL        = os.getenv("INTERVIEW_BOT_URL")

# ====== ADD THESE TWO LINES ======
GMAIL_USER     = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")