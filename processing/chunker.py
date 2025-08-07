# import json
# import os
# from nltk.tokenize import sent_tokenize
# import nltk

# # Download sentence tokenizer (only needs to happen once)
# nltk.download('punkt_tab')

# def load_crawled_data(json_path):
#     with open(json_path, 'r') as f:
#         return json.load(f)

# def chunk_text(text, chunk_size=500, overlap=50):
#     sentences = sent_tokenize(text)
#     chunks = []
#     current_chunk = []
#     total_words = 0

#     for sentence in sentences:
#         words = sentence.split()
#         if total_words + len(words) > chunk_size:
#             chunks.append(' '.join(current_chunk))
#             current_chunk = current_chunk[-overlap:]  # Keep overlap
#             total_words = sum(len(s.split()) for s in current_chunk)

#         current_chunk.append(sentence)
#         total_words += len(words)

#     if current_chunk:
#         chunks.append(' '.join(current_chunk))

#     return chunks

# def process_website_data(input_path):
#     raw_data = load_crawled_data(input_path)
#     all_chunks = []

#     for page in raw_data:
#         url = page.get('url', 'unknown')
#         text = page.get('content', '')
#         chunks = chunk_text(text)
#         for chunk in chunks:
#             all_chunks.append({
#                 'url': url,
#                 'content': chunk
#             })

#     return all_chunks

# def save_chunks(chunks, out_path=None):
#     if out_path is None:
#         output_dir = os.path.join(os.path.dirname(__file__), '..', 'crawler', 'crawler', 'output')
#         os.makedirs(output_dir, exist_ok=True)
#         out_path = os.path.join(output_dir, 'website_chunks.json')
#     else:
#         os.makedirs(os.path.dirname(out_path), exist_ok=True)

#     with open(out_path, "w") as f:
#         json.dump(chunks, f, indent=2)
#     print(f"✅ Saved {len(chunks)} chunks to {out_path}")

# if __name__ == "__main__":
#     # Define input and output paths relative to this script
#     base_dir = os.path.dirname(__file__)
#     input_path = os.path.join(base_dir, '..', 'crawler', 'crawler', 'output', 'website_content.json')
#     output_path = os.path.join(base_dir, '..', 'crawler', 'crawler', 'output', 'website_chunks.json')

#     chunks = process_website_data(input_path)
#     save_chunks(chunks, out_path=output_path)



import json
import os
import re
from nltk.tokenize import sent_tokenize
import nltk

# Download NLTK sentence tokenizer
nltk.download('punkt_tab')

def load_crawled_data(json_path):
    with open(json_path, 'r') as f:
        return json.load(f)

def clean_text(text):
    """Basic cleanup: remove emails, phones, extra whitespace."""
    text = re.sub(r'\S+@\S+', '', text)  # remove emails
    text = re.sub(r'\d{10,}', '', text)  # remove long digit strings (phone numbers)
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
            # Maintain overlap
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
        raw_text = page.get('content', '')
        text = clean_text(raw_text)
        chunks = chunk_text(text)

        for chunk in chunks:
            all_chunks.append({
                'url': url,
                'content': chunk
            })

    return all_chunks

def save_chunks(chunks, out_path=None):
    if out_path is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'crawler', 'crawler', 'output')
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, 'website_chunks.json')
    else:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(chunks, f, indent=2)

    print(f"✅ Saved {len(chunks)} chunks to {out_path}")

if __name__ == "__main__":
    # Define input and output paths
    base_dir = os.path.dirname(__file__)
    input_path = os.path.join(base_dir, '..', 'crawler', 'crawler', 'output', 'website_content.json')
    output_path = os.path.join(base_dir, '..', 'crawler', 'crawler', 'output', 'website_chunks.json')

    chunks = process_website_data(input_path)
    save_chunks(chunks, out_path=output_path)






# import json
# import os
# import re
# from pathlib import Path

# # Try importing NLTK, with fallback to basic sentence splitting
# try:
#     import nltk
#     from nltk.tokenize import sent_tokenize
    
#     # Download punkt data to a specific directory
#     nltk_data_dir = os.path.join(os.path.expanduser('~'), 'nltk_data')
#     os.makedirs(nltk_data_dir, exist_ok=True)
#     nltk.data.path.append(nltk_data_dir)
    
#     # Try both old and new punkt versions
#     punkt_available = False
    
#     # First try the new punkt_tab
#     try:
#         nltk.data.find('tokenizers/punkt_tab')
#         print("✅ NLTK punkt_tab already available")
#         punkt_available = True
#     except LookupError:
#         try:
#             print("📥 Downloading NLTK punkt_tab...")
#             nltk.download('punkt_tab', download_dir=nltk_data_dir)
#             punkt_available = True
#         except Exception as e:
#             print(f"⚠️ Failed to download punkt_tab: {e}")
    
#     # If punkt_tab failed, try the old punkt
#     if not punkt_available:
#         try:
#             nltk.data.find('tokenizers/punkt')
#             print("✅ NLTK punkt already available")
#             punkt_available = True
#         except LookupError:
#             try:
#                 print("📥 Downloading NLTK punkt...")
#                 nltk.download('punkt', download_dir=nltk_data_dir)
#                 punkt_available = True
#             except Exception as e:
#                 print(f"⚠️ Failed to download punkt: {e}")
    
#     NLTK_AVAILABLE = punkt_available
    
#     if not NLTK_AVAILABLE:
#         print("⚠️ NLTK punkt/punkt_tab not available, using regex-based sentence splitting")
        
# except ImportError:
#     print("⚠️ NLTK not available, using regex-based sentence splitting")
#     NLTK_AVAILABLE = False

# def simple_sent_tokenize(text):
#     """Fallback sentence tokenizer using regex"""
#     # More robust sentence splitting patterns
#     patterns = [
#         r'(?<=[.!?])\s+(?=[A-Z])',  # Standard sentence endings
#         r'(?<=[.!?])\s+(?=["\'A-Z])',  # With quotes
#         r'(?<=\.)\s+(?=[A-Z][a-z])',  # Period followed by capitalized word
#         r'(?<=[!?])\s+(?=[A-Z])',  # Exclamation and question marks
#     ]
    
#     # Apply the first pattern that works well
#     for pattern in patterns:
#         try:
#             sentences = re.split(pattern, text)
#             # Filter out empty sentences and very short ones
#             sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
#             if len(sentences) > 1:  # If we got multiple sentences, use this pattern
#                 return sentences
#         except:
#             continue
    
#     # If regex fails, split by paragraphs or use the whole text
#     paragraphs = text.split('\n\n')
#     if len(paragraphs) > 1:
#         return [p.strip() for p in paragraphs if p.strip()]
    
#     # Last resort: return the whole text as one chunk
#     return [text.strip()] if text.strip() else []

# def load_crawled_data(json_path):
#     """Load JSON data from file"""
#     try:
#         with open(json_path, 'r', encoding='utf-8') as f:
#             return json.load(f)
#     except FileNotFoundError:
#         print(f"❌ File not found: {json_path}")
#         return []
#     except json.JSONDecodeError as e:
#         print(f"❌ JSON decode error: {e}")
#         return []

# def chunk_text(text, chunk_size=500, overlap=50):
#     """
#     Split text into overlapping chunks
    
#     Args:
#         text: Input text to chunk
#         chunk_size: Maximum words per chunk
#         overlap: Number of words to overlap between chunks
#     """
#     if not text or not text.strip():
#         return []
    
#     # Choose tokenizer based on availability
#     if NLTK_AVAILABLE:
#         try:
#             sentences = sent_tokenize(text)
#         except Exception as e:
#             print(f"⚠️ NLTK tokenization failed, using fallback: {e}")
#             sentences = simple_sent_tokenize(text)
#     else:
#         sentences = simple_sent_tokenize(text)
    
#     if not sentences:
#         return [text]  # Return original text if no sentences found
    
#     chunks = []
#     current_chunk = []
#     current_word_count = 0
    
#     for sentence in sentences:
#         words = sentence.split()
#         sentence_word_count = len(words)
        
#         # If adding this sentence exceeds chunk size, save current chunk
#         if current_word_count + sentence_word_count > chunk_size and current_chunk:
#             chunks.append(' '.join(current_chunk))
            
#             # Create overlap by keeping last few sentences
#             overlap_sentences = []
#             overlap_words = 0
            
#             # Work backwards to get overlap
#             for i in range(len(current_chunk) - 1, -1, -1):
#                 sentence_words = current_chunk[i].split()
#                 if overlap_words + len(sentence_words) <= overlap:
#                     overlap_sentences.insert(0, current_chunk[i])
#                     overlap_words += len(sentence_words)
#                 else:
#                     break
            
#             current_chunk = overlap_sentences
#             current_word_count = overlap_words
        
#         current_chunk.append(sentence)
#         current_word_count += sentence_word_count
    
#     # Add the last chunk if it exists
#     if current_chunk:
#         chunks.append(' '.join(current_chunk))
    
#     return chunks

# def process_website_data(input_path):
#     """
#     Process website data and create chunks
    
#     Args:
#         input_path: Path to JSON file containing crawled data
#     """
#     print(f"📖 Loading data from: {input_path}")
#     raw_data = load_crawled_data(input_path)
    
#     if not raw_data:
#         print("❌ No data loaded")
#         return []
    
#     all_chunks = []
#     processed_pages = 0
    
#     for page in raw_data:
#         try:
#             url = page.get('url', 'unknown')
#             content = page.get('content', '')
            
#             if not content or not content.strip():
#                 print(f"⚠️ Empty content for URL: {url}")
#                 continue
            
#             chunks = chunk_text(content)
            
#             for i, chunk in enumerate(chunks):
#                 all_chunks.append({
#                     'url': url,
#                     'chunk_id': f"{url}_chunk_{i}",
#                     'content': chunk.strip(),
#                     'word_count': len(chunk.split())
#                 })
            
#             processed_pages += 1
#             print(f"✅ Processed {len(chunks)} chunks from: {url}")
            
#         except Exception as e:
#             print(f"❌ Error processing page: {e}")
#             continue
    
#     print(f"🎉 Total: {len(all_chunks)} chunks from {processed_pages} pages")
#     return all_chunks

# def save_chunks(chunks, out_path="crawler/output/website_chunks.json"):
#     """Save chunks to JSON file"""
#     try:
#         # Create output directory if it doesn't exist
#         os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
#         with open(out_path, "w", encoding='utf-8') as f:
#             json.dump(chunks, f, indent=2, ensure_ascii=False)
        
#         print(f"✅ Saved {len(chunks)} chunks to {out_path}")
        
#         # Print some statistics
#         if chunks:
#             word_counts = [chunk['word_count'] for chunk in chunks]
#             avg_words = sum(word_counts) / len(word_counts)
#             print(f"📊 Average chunk size: {avg_words:.1f} words")
#             print(f"📊 Size range: {min(word_counts)}-{max(word_counts)} words")
        
#     except Exception as e:
#         print(f"❌ Error saving chunks: {e}")

# def main():
#     """Main function"""
#     input_file = "crawler/crawler/output/website_content.json"
#     output_file = "crawler/crawler/output/website_chunks.json"
    
#     # Check if input file exists
#     if not os.path.exists(input_file):
#         print(f"❌ Input file not found: {input_file}")
#         print("Please check the file path.")
#         return
    
#     # Process the data
#     chunks = process_website_data(input_file)
    
#     if chunks:
#         save_chunks(chunks, output_file)
#     else:
#         print("❌ No chunks created")

# if __name__ == "__main__":
#     main()