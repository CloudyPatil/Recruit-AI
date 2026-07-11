import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

def seed():
    conn = pymysql.connect(
        host     = os.getenv("MYSQL_HOST"),
        user     = os.getenv("MYSQL_USER"),
        password = os.getenv("MYSQL_PASSWORD"),
        database = os.getenv("MYSQL_DB"),
        cursorclass = pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()

    # 100+ questions across categories
    questions = [
        # ─── LOGICAL (general) ───
        ("All cats are animals. Some animals are wild. So:",
         "All cats are wild","Some cats may be wild",
         "No cats are wild","All animals are cats","B",
         "general","easy","logical"),
        ("Find odd: Apple, Orange, Carrot, Banana",
         "Apple","Orange","Carrot","Banana","C",
         "general","easy","logical"),
        ("If MONDAY = NPOEBZ, then FRIDAY = ?",
         "GSJEBZ","GSJFBZ","GSJEAZ","FSJEBZ","A",
         "general","medium","logical"),
        ("Complete: AZ, BY, CX, ?",
         "DV","DW","EW","DU","B",
         "general","medium","logical"),
        ("Pointing to a man, woman says 'his mother is "
         "my mother's only daughter'. Man is?",
         "Brother","Son","Father","Husband","B",
         "general","medium","logical"),

        # ─── NUMERICAL (general) ───
        ("25% of 80 = ?",
         "15","20","25","30","B",
         "general","easy","numerical"),
        ("Average of 10, 20, 30, 40, 50?",
         "25","30","35","40","B",
         "general","easy","numerical"),
        ("If x+y=10, x-y=4, then x=?",
         "6","7","8","5","B",
         "general","easy","numerical"),
        ("Compound interest on 1000 at 10% for 2 years?",
         "200","210","220","100","B",
         "general","medium","numerical"),
        ("Speed 60km/hr, time 45min, distance?",
         "40km","45km","50km","55km","B",
         "general","medium","numerical"),
        ("Square root of 144?",
         "11","12","13","14","B",
         "general","easy","numerical"),
        ("LCM of 4 and 6?",
         "10","12","18","24","B",
         "general","easy","numerical"),
        ("If 5 men do work in 10 days, "
         "how many days for 10 men?",
         "3","4","5","6","C",
         "general","medium","numerical"),
        ("Profit 20% on cost 100, selling price?",
         "110","115","120","125","C",
         "general","easy","numerical"),
        ("Ratio 3:5, total 80, larger part?",
         "30","40","50","60","C",
         "general","medium","numerical"),

        # ─── VERBAL (general) ───
        ("Synonym of HAPPY:",
         "Sad","Joyful","Angry","Tired","B",
         "general","easy","verbal"),
        ("Antonym of BRAVE:",
         "Bold","Strong","Cowardly","Smart","C",
         "general","easy","verbal"),
        ("Synonym of INTELLIGENT:",
         "Dull","Smart","Lazy","Slow","B",
         "general","easy","verbal"),
        ("Choose correct: I ___ to school daily.",
         "go","goes","going","gone","A",
         "general","easy","verbal"),
        ("Plural of CHILD:",
         "Childs","Childes","Children","Childrens","C",
         "general","easy","verbal"),
        ("Antonym of EXPAND:",
         "Grow","Shrink","Build","Open","B",
         "general","easy","verbal"),
        ("Synonym of QUICK:",
         "Slow","Fast","Late","Long","B",
         "general","easy","verbal"),
        ("Correct: She ___ a book yesterday.",
         "read","reads","reading","is reading","A",
         "general","medium","verbal"),
        ("Spelling: which is correct?",
         "Recieve","Receive","Receeve","Receve","B",
         "general","easy","verbal"),
        ("Meaning of 'break a leg'?",
         "Get hurt","Good luck","Run away","Stop","B",
         "general","medium","verbal"),

        # ─── TECH DOMAIN ───
        ("OOP stands for?",
         "Object Oriented Programming",
         "Order Of Process",
         "Output Of Program",
         "Object Of Process","A",
         "tech","easy","domain"),
        ("Which is NOT a programming language?",
         "Python","Java","HTML","C++","C",
         "tech","easy","domain"),
        ("HTTP default port?",
         "21","80","443","8080","B",
         "tech","easy","domain"),
        ("HTTPS default port?",
         "21","80","443","8080","C",
         "tech","easy","domain"),
        ("Git is used for?",
         "Database","Version control","Web design","OS","B",
         "tech","easy","domain"),
        ("CPU stands for?",
         "Central Processing Unit",
         "Computer Personal Unit",
         "Central Program Unit",
         "Computer Process Unit","A",
         "tech","easy","domain"),
        ("Which is a NoSQL database?",
         "MySQL","PostgreSQL","MongoDB","Oracle","C",
         "tech","easy","domain"),
        ("React is a ___?",
         "Database","JavaScript library",
         "Operating system","Browser","B",
         "tech","easy","domain"),
        ("Which sorts fastest on average?",
         "Bubble Sort","Selection Sort","Quick Sort","Insertion Sort","C",
         "tech","medium","domain"),
        ("Binary of 10?",
         "1010","1100","1001","1110","A",
         "tech","medium","domain"),
        ("Which is a Python framework?",
         "Laravel","Django","Angular","Spring","B",
         "tech","easy","domain"),
        ("Time complexity of binary search?",
         "O(n)","O(log n)","O(n^2)","O(1)","B",
         "tech","medium","domain"),
        ("Which protocol sends emails?",
         "HTTP","FTP","SMTP","SSH","C",
         "tech","easy","domain"),
        ("What is JSON?",
         "JavaScript Object Notation",
         "Java Standard Object Name",
         "JavaScript Online Network",
         "Java System Object Note","A",
         "tech","easy","domain"),
        ("Which is a frontend framework?",
         "Django","Flask","React","Express","C",
         "tech","easy","domain"),
        ("SQL command to fetch data?",
         "GET","FETCH","SELECT","RETRIEVE","C",
         "tech","easy","domain"),
        ("Which is NOT OS?",
         "Windows","Linux","Oracle","macOS","C",
         "tech","easy","domain"),
        ("API stands for?",
         "Application Programming Interface",
         "Applied Program Interface",
         "Advanced Programming Interface",
         "Application Process Interface","A",
         "tech","easy","domain"),
        ("Docker is used for?",
         "Database","Containerization","UI design","Testing","B",
         "tech","medium","domain"),
        ("Which is a cloud platform?",
         "AWS","React","MongoDB","Django","A",
         "tech","easy","domain"),

        # ─── FINANCE DOMAIN ───
        ("GDP stands for?",
         "Gross Domestic Product",
         "General Domestic Process",
         "Gross Distributed Product",
         "Global Domestic Price","A",
         "finance","easy","domain"),
        ("Inflation means?",
         "Prices fall","Prices rise",
         "Prices stable","Currency stable","B",
         "finance","easy","domain"),
        ("ROI stands for?",
         "Return On Investment",
         "Rate Of Income",
         "Return Of Interest",
         "Revenue On Income","A",
         "finance","easy","domain"),
        ("Stock represents?",
         "Loan","Ownership","Tax","Debt","B",
         "finance","easy","domain"),
        ("IPO means?",
         "Initial Public Offering",
         "Internal Profit Order",
         "Income Public Order",
         "Investor Profit Output","A",
         "finance","medium","domain"),
    ]

    cursor.execute("SELECT COUNT(*) as cnt FROM aptitude_questions")
    existing = cursor.fetchone()["cnt"]
    
    if existing < 50:
        cursor.executemany("""
            INSERT INTO aptitude_questions
            (question_text,option_a,option_b,option_c,option_d,
             correct_answer,domain,difficulty,type)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, questions)
        print(f"✅ {len(questions)} new questions added")
    else:
        print(f"ℹ️ Already have {existing} questions")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed()