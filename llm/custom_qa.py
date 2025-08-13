# from sentence_transformers import SentenceTransformer, util
# import json

# # Load model for question similarity
# qa_model = SentenceTransformer("all-MiniLM-L6-v2")

# def load_custom_qa(path="llm/custom_qa.json"):
#     with open(path, "r", encoding="utf-8") as f:
#         qa_pairs = json.load(f)
#     # Precompute embeddings for speed
#     for qa in qa_pairs:
#         qa["embedding"] = qa_model.encode(qa["questions"])
#     return qa_pairs

# # Load Q&A once
# custom_qa = load_custom_qa()

# def find_custom_answer(query, threshold=0.8):
#     """Return custom answer if similarity >= threshold, else None."""
#     query_emb = qa_model.encode(query)
#     best_score = 0
#     best_answer = None
#     for qa in custom_qa:
#         score = util.cos_sim(query_emb, qa["embedding"]).item()
#         if score > best_score:
#             best_score = score
#             best_answer = qa["answer"]
#     if best_score >= threshold:
#         return best_answer
#     return None



import json
import os
from sentence_transformers import SentenceTransformer, util

qa_model = SentenceTransformer("all-MiniLM-L6-v2")
CUSTOM_QA_PATH = os.path.join(os.path.dirname(__file__), "custom_qa.json")
def load_custom_qa(path=CUSTOM_QA_PATH):
    """
    Load custom Q&A pairs from JSON and precompute embeddings.
    JSON format:
    [
        {
            "questions": ["question 1", "question 2"],
            "answer": "answer text"
        }
    ]
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            qa_pairs = json.load(f)

        for qa in qa_pairs:
            qa["embeddings"] = [qa_model.encode(q) for q in qa["questions"]]

        print(f"✅ Loaded {len(qa_pairs)} custom Q&A entries from {path}")
        return qa_pairs

    except FileNotFoundError:
        print(f"⚠️ Custom Q&A file not found: {path}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return []

custom_qa = load_custom_qa()

def find_custom_answer(query, threshold=0.8):
    """Return custom answer if similarity >= threshold."""
    if not custom_qa:
        return None

    query_emb = qa_model.encode(query)
    best_score = 0
    best_answer = None

    for qa in custom_qa:
        for emb in qa["embeddings"]:
            score = util.cos_sim(query_emb, emb).item()
            if score > best_score:
                best_score = score
                best_answer = qa["answer"]

    if best_score >= threshold:
        print(f"✅ Found custom answer (similarity: {best_score:.2f})")
        return best_answer
    return None
