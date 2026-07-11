import subprocess
import sys

def check(name, import_name=None):
    try:
        __import__(import_name or name)
        print(f"✅ {name}")
        return True
    except:
        print(f"❌ {name} - pip install {name}")
        return False

# Python Libraries
print("=== PYTHON LIBRARIES ===")
check("pytesseract")
check("PIL", "PIL")
check("pandas")
check("numpy")
check("sklearn", "sklearn")
check("sentence_transformers", "sentence_transformers")
check("spacy")
check("cv2", "cv2")

# Tesseract OCR
print("\n=== TESSERACT OCR ===")
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'E:\Tesseract-OCR\tesseract.exe'
    ver = pytesseract.get_tesseract_version()
    print(f"✅ Tesseract {ver}")
except:
    print("❌ Tesseract - Download from github.com/UB-Mannheim/tesseract/wiki")

# spaCy model
print("\n=== SPACY MODEL ===")
try:
    import spacy
    spacy.load("en_core_web_sm")
    print("✅ en_core_web_sm")
except:
    print("❌ Run: python -m spacy download en_core_web_sm")

print("\n=== DONE ===")