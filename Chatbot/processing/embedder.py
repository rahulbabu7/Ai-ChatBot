##without title


# import json
# import os
# from sentence_transformers import SentenceTransformer
# from tqdm import tqdm

# def load_chunks(path):
#     with open(path, 'r') as f:
#         return json.load(f)

# def save_embeddings(data, out_path):
#     os.makedirs(os.path.dirname(out_path), exist_ok=True)
#     with open(out_path, 'w') as f:
#         json.dump(data, f, indent=2)
#     print(f"✅ Saved {len(data)} embeddings to {out_path}")

# def embed_texts(chunks, model_name="all-MiniLM-L6-v2"):
#     model = SentenceTransformer(model_name)
#     embedded_chunks = []

#     texts = [chunk["content"] for chunk in chunks]
#     embeddings = model.encode(texts, show_progress_bar=True)

#     for chunk, embedding in zip(chunks, embeddings):
#         embedded_chunks.append({
#             "url": chunk["url"],
#             "content": chunk["content"],
#             "embedding": embedding.tolist()
#         })

#     return embedded_chunks

# if __name__ == "__main__":
#     input_path = "crawler/crawler/output/website_chunks.json"
#     output_path = "crawler/crawler/output/website_embeddings.json"

#     chunks = load_chunks(input_path)
#     embedded_chunks = embed_texts(chunks)
#     save_embeddings(embedded_chunks, output_path)




##with title
# 
# 
import json
import os
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

def load_chunks(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_embeddings(data, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(data)} embeddings to {out_path}")

def embed_texts(chunks, model_name="all-MiniLM-L6-v2"):
    model = SentenceTransformer(model_name)
    embedded_chunks = []

    texts = [chunk["content"] for chunk in chunks]
    embeddings = model.encode(texts, show_progress_bar=True)

    for chunk, embedding in zip(chunks, embeddings):
        embedded_chunks.append({
            "url": chunk["url"],
            "title": chunk.get("title", ""),
            "content": chunk["content"],
            "embedding": embedding.tolist()
        })

    return embedded_chunks

if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    input_path = os.path.join(base_dir, '..', 'crawler','crawler', 'output', 'website_chunks.json')
    output_path = os.path.join(base_dir, '..', 'crawler','crawler', 'output', 'website_embeddings.json')
    
    print(os.path.exists(input_path))
    chunks = load_chunks(input_path)
    embedded_chunks = embed_texts(chunks)
    save_embeddings(embedded_chunks, output_path)
