
## with title
# 
import json
import os
import re
from nltk.tokenize import sent_tokenize
import nltk

# ✅ Correct tokenizer name
nltk.download('punkt_tab')

def load_crawled_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_text(text):
    """Basic cleanup: remove emails, phones, extra whitespace."""
    text = re.sub(r'\S+@\S+', '', text)  # remove emails
    text = re.sub(r'\d{10,}', '', text)  # remove long digit strings (phones)
    text = re.sub(r'\s+', ' ', text)     # normalize whitespace
    return text.strip()

def chunk_text(text, chunk_size=500, overlap=50):
    sentences = sent_tokenize(text)
    chunks = []
    current_chunk = []
    total_words = 0

    for sentence in sentences:
        words = sentence.split()
        if total_words + len(words) > chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = current_chunk[-overlap:]
            total_words = sum(len(s.split()) for s in current_chunk)

        current_chunk.append(sentence)
        total_words += len(words)

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

def process_website_data(input_path):
    raw_data = load_crawled_data(input_path)
    all_chunks = []

    for page in raw_data:
        url = page.get('url', 'unknown')
        title = page.get('title', '').strip()
        raw_text = page.get('content', '')
        if not raw_text.strip():
            continue

        text = clean_text(raw_text)
        chunks = chunk_text(text)

        for chunk in chunks:
            all_chunks.append({
                'url': url,
                'title': title,
                'content': chunk
            })

    return all_chunks

def save_chunks_json(chunks, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(chunks)} chunks to {out_path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    input_path = os.path.join(base_dir, '..', 'crawler','crawler', 'output', 'website_content.json')
    output_path_json = os.path.join(base_dir, '..', 'crawler','crawler', 'output', 'website_chunks.json')

    chunks = process_website_data(input_path)
    save_chunks_json(chunks, out_path=output_path_json)
