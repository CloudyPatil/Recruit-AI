import os
import re
os.environ["DEEPFACE_HOME"] = "E:/deepface"

from deepface import DeepFace
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r'E:\Tesseract-OCR\tesseract.exe'


def extract_text_from_id(id_photo_path):
    """OCR text from ID document"""
    try:
        img = Image.open(id_photo_path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        print(f"OCR failed: {e}")
        return ""


def detect_document_type(text):
    """Detect ID document type"""
    text_lower = text.lower()
    
    if "aadhaar" in text_lower or "आधार" in text or re.search(r'\d{4}\s*\d{4}\s*\d{4}', text):
        return "Aadhar Card"
    if "permanent account number" in text_lower or "income tax" in text_lower or re.search(r'[A-Z]{5}\d{4}[A-Z]', text):
        return "PAN Card"
    if "driving licence" in text_lower or "driving license" in text_lower:
        return "Driving License"
    if "passport" in text_lower:
        return "Passport"
    if "voter" in text_lower or "election commission" in text_lower:
        return "Voter ID"
    if "student" in text_lower or "college" in text_lower or "university" in text_lower:
        return "College ID"
    
    return "Unknown Document"


def extract_name_from_id(text, doc_type):
    """Extract candidate name from ID text"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    # Patterns for different IDs
    if doc_type == "Aadhar Card":
        # Name usually appears before DOB
        for i, line in enumerate(lines):
            if "dob" in line.lower() or re.search(r'\d{2}/\d{2}/\d{4}', line):
                if i > 0:
                    return lines[i-1].strip()
    
    if doc_type == "PAN Card":
        # Name usually at top, all caps
        for line in lines[:5]:
            if line.isupper() and len(line.split()) >= 2 and len(line) > 6:
                if not any(x in line.lower() for x in ["income", "tax", "department", "govt", "india"]):
                    return line.strip()
    
    # Generic: find first 2-4 word line with caps
    for line in lines[:10]:
        words = line.split()
        if 2 <= len(words) <= 4:
            if all(w[0].isupper() for w in words if w):
                if not any(x in line.lower() for x in ["card", "government", "republic", "india"]):
                    return line.strip()
    
    return ""


def match_names(name1, name2):
    """Match two names with tolerance"""
    if not name1 or not name2:
        return {"match": False, "score": 0}
    
    # Normalize
    n1 = re.sub(r'[^a-z\s]', '', name1.lower()).strip()
    n2 = re.sub(r'[^a-z\s]', '', name2.lower()).strip()
    
    if not n1 or not n2:
        return {"match": False, "score": 0}
    
    words1 = set(n1.split())
    words2 = set(n2.split())
    
    common = words1.intersection(words2)
    total = max(len(words1), len(words2))
    
    score = (len(common) / total) * 100 if total > 0 else 0
    
    return {
        "match": score >= 50,  # At least 50% words match
        "score": round(score, 1),
        "id_name": name1,
        "resume_name": name2
    }


def verify_identity(id_photo_path, live_photo_path):
    """Face match between ID photo and live photo"""
    try:
        result = DeepFace.verify(
            img1_path=id_photo_path,
            img2_path=live_photo_path,
            model_name="Facenet",
            detector_backend="opencv",
            distance_metric="cosine",
            enforce_detection=False
        )
        
        distance = result["distance"]
        threshold = 0.55
        verified = distance < threshold
        confidence = round((1 - distance) * 100, 1)
        
        return {
            "verified": verified,
            "distance": round(distance, 3),
            "confidence": confidence,
            "threshold": threshold
        }
    except Exception as e:
        return {"verified": False, "error": str(e)}


def cleanup_temp_files(*paths):
    for p in paths:
        if os.path.exists(p):
            os.remove(p)