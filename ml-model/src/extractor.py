import pytesseract
from PIL import Image
import os
import pandas as pd

pytesseract.pytesseract.tesseract_cmd = r'E:\Tesseract-OCR\tesseract.exe'

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg')

def extract_from_image(path):
    try:
        img = Image.open(path).convert('L')
        text = pytesseract.image_to_string(img)
        return text.strip()
    except:
        return ""

def process_all(dataset_folder, output_csv):
    results = []
    skipped = 0
    
    for category in os.listdir(dataset_folder):
        cat_path = os.path.join(dataset_folder, category)
        if not os.path.isdir(cat_path):
            continue
            
        print(f"Processing: {category}")
        files = os.listdir(cat_path)
        
        for i, file in enumerate(files):
            if not file.lower().endswith(IMAGE_EXTENSIONS):
                skipped += 1
                continue
                
            file_path = os.path.join(cat_path, file)
            text = extract_from_image(file_path)
            
            if len(text) > 50:
                results.append({
                    'filename': file,
                    'category': category,
                    'text': text
                })
            
            if i % 50 == 0:
                print(f"  {i}/{len(files)} done")
                pd.DataFrame(results).to_csv(output_csv, index=False)
    
    df = pd.DataFrame(results)
    df.to_csv(output_csv, index=False)
    print(f"Images processed: {len(df)}")
    print(f"Skipped: {skipped}")
    return df

if __name__ == "__main__":
    os.makedirs("extracted_texts", exist_ok=True)
    process_all("dataset2", "extracted_texts/resumes.csv")