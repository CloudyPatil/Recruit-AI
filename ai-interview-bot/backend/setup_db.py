import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

def setup():
    conn = pymysql.connect(
        host     = os.getenv("MYSQL_HOST"),
        user     = os.getenv("MYSQL_USER"),
        password = os.getenv("MYSQL_PASSWORD"),
        database = os.getenv("MYSQL_DB"),
        cursorclass = pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()
    print("✅ Connected to MySQL")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            interview_id   VARCHAR(36) PRIMARY KEY,
            candidate_id   INT NOT NULL,
            job_id         INT NOT NULL,
            candidate_name VARCHAR(100),
            job_title      VARCHAR(100),
            status         ENUM('pending','round1','round2',
                                'round3','completed','terminated') 
                           DEFAULT 'pending',
            ml_score       FLOAT DEFAULT 0,
            round1_score   FLOAT DEFAULT 0,
            round2_score   FLOAT DEFAULT 0,
            round3_score   FLOAT DEFAULT 0,
            final_score    FLOAT DEFAULT 0,
            link_token     VARCHAR(100) UNIQUE,
            link_expires   DATETIME,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ interviews table ready")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aptitude_questions (
            question_id    INT AUTO_INCREMENT PRIMARY KEY,
            question_text  TEXT NOT NULL,
            option_a       VARCHAR(255),
            option_b       VARCHAR(255),
            option_c       VARCHAR(255),
            option_d       VARCHAR(255),
            correct_answer CHAR(1),
            domain         VARCHAR(50),
            difficulty     ENUM('easy','medium','hard'),
            type           VARCHAR(50)
        )
    """)
    print("✅ aptitude_questions table ready")

    questions = [
        ("If A > B and B > C, which is true?",
         "C > A","A > C","B > A","C = A","B",
         "general","easy","logical"),
        ("What is 15% of 200?",
         "25","30","35","20","B",
         "general","easy","numerical"),
        ("Synonym of ABUNDANT:",
         "Scarce","Plentiful","Empty","Rare","B",
         "general","easy","verbal"),
        ("What does SQL stand for?",
         "Structured Query Language","Simple Query Logic",
         "System Query Language","Standard Query List","A",
         "tech","easy","domain"),
        ("RAM stands for?",
         "Read Access Memory","Random Access Memory",
         "Read All Memory","Random All Memory","B",
         "tech","easy","domain"),
        ("Next number: 2, 4, 8, 16, ?",
         "20","24","32","28","C",
         "general","easy","numerical"),
        ("Antonym of TRANSPARENT:",
         "Clear","Obvious","Opaque","Bright","C",
         "general","easy","verbal"),
        ("What is an API?",
         "A database","A language",
         "Application Programming Interface","A browser","C",
         "tech","easy","domain"),
        ("If 3x + 5 = 20, x = ?",
         "3","4","5","6","C",
         "general","medium","numerical"),
        ("Choose correct sentence:",
         "He go to school","He goes to school",
         "He going to school","He gone to school","B",
         "general","easy","verbal"),
        ("Which is used for web styling?",
         "Python","CSS","Java","SQL","B",
         "tech","easy","domain"),
        ("Train travels 60km/hr, distance in 2.5 hours?",
         "120km","130km","150km","160km","C",
         "general","easy","numerical"),
        ("A is B's brother. B is C's sister. A to C?",
         "Sister","Brother","Father","Cousin","B",
         "general","easy","logical"),
        ("Odd one: Cat, Dog, Rose, Cow",
         "Cat","Dog","Rose","Cow","C",
         "general","easy","logical"),
        ("HTTP stands for?",
         "Hyper Text Transfer Protocol",
         "High Transfer Text Protocol",
         "Hyper Transfer Text Path",
         "Home Text Transfer Path","A",
         "tech","easy","domain"),
    ]

    cursor.execute("SELECT COUNT(*) as cnt FROM aptitude_questions")
    if cursor.fetchone()["cnt"] == 0:
        cursor.executemany("""
            INSERT INTO aptitude_questions
            (question_text,option_a,option_b,option_c,option_d,
             correct_answer,domain,difficulty,type)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, questions)
        print(f"✅ {len(questions)} questions inserted")
    else:
        print("ℹ️  Questions exist, skipping")

    conn.commit()
    conn.close()
    print("\n✅ Setup complete!")

if __name__ == "__main__":
    setup()