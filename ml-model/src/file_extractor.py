import pytesseract
from PIL import Image
import PyPDF2
from docx import Document
from pdf2image import convert_from_bytes
import io

pytesseract.pytesseract.tesseract_cmd = r'E:\Tesseract-OCR\tesseract.exe'
POPPLER_PATH = r'E:\poppler\Library\bin'  # update if different

def extract_from_image_bytes(file_bytes):
    img = Image.open(io.BytesIO(file_bytes)).convert('L')
    return pytesseract.image_to_string(img).strip()

def extract_from_pdf_bytes(file_bytes):
    text = ""
    
    # Try direct text extraction first
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            text += page.extract_text() + "\n"
        text = text.strip()
    except:
        text = ""
    
    # If no text (scanned PDF), use OCR
    if len(text) < 50:
        try:
            pages = convert_from_bytes(file_bytes, dpi=200, poppler_path=POPPLER_PATH)
            for page in pages:
                text += pytesseract.image_to_string(page) + "\n"
        except Exception as e:
            print(f"PDF OCR error: {e}")
    
    return text.strip()

def extract_from_docx_bytes(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    text = "\n".join([p.text for p in doc.paragraphs])
    return text.strip()

def extract_text(file_bytes, filename):
    """Auto detect and extract"""
    name = filename.lower()
    
    if name.endswith(('.png','.jpg','.jpeg')):
        return extract_from_image_bytes(file_bytes)
    elif name.endswith('.pdf'):
        return extract_from_pdf_bytes(file_bytes)
    elif name.endswith('.docx'):
        return extract_from_docx_bytes(file_bytes)
    else:
        return ""