import pandas as pd
import random
import pickle
import os
from sentence_transformers import InputExample

def generate_pairs(csv_path):
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=['text','category'])
    df['text'] = df['text'].str[:500]
    
    groups = {}
    for cat, grp in df.groupby('category'):
        groups[cat] = grp['text'].tolist()
    
    categories = list(groups.keys())
    pairs = []
    
    for cat in categories:
        texts = groups[cat]
        if len(texts) < 2:
            continue
        
        # HIGH match
        for i in range(min(40, len(texts)-1)):
            pairs.append(InputExample(
                texts=[texts[i], texts[i+1]],
                label=0.85
            ))
        
        # LOW match
        other_cats = [c for c in categories if c != cat]
        for i in range(min(20, len(texts))):
            other = random.choice(other_cats)
            other_text = random.choice(groups[other])
            pairs.append(InputExample(
                texts=[texts[i], other_text],
                label=0.1
            ))
    
    random.shuffle(pairs)
    
    os.makedirs("models", exist_ok=True)
    with open('models/pairs.pkl','wb') as f:
        pickle.dump(pairs, f)
    
    print(f"Total pairs generated: {len(pairs)}")

if __name__ == "__main__":
    generate_pairs("extracted_texts/resumes.csv")