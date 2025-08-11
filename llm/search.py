import json
import os
import re

def search_in_scraped_data(search_terms, data_file="crawler/crawler/output/website_content.json"):
    """Search for terms in the raw scraped data"""
    
    if not os.path.exists(data_file):
        print(f"❌ File not found: {data_file}")
        return
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"🔍 Searching in {len(data)} scraped pages...")
    
    found_pages = []
    
    for page in data:
        url = page.get('url', '')
        title = page.get('title', '')
        content = page.get('content', '')
        
        # Check if any search term appears in the content (case-insensitive)
        for term in search_terms:
            if term.lower() in content.lower() or term.lower() in title.lower():
                found_pages.append({
                    'url': url,
                    'title': title,
                    'content': content,
                    'matched_term': term
                })
                break
    
    if found_pages:
        print(f"✅ Found {len(found_pages)} pages containing the search terms:")
        for i, page in enumerate(found_pages, 1):
            print(f"\n📄 Page {i}: {page['title']}")
            print(f"🔗 URL: {page['url']}")
            print(f"🎯 Matched term: {page['matched_term']}")
            
            # Show context around the matched term
            content = page['content']
            term = page['matched_term']
            
            # Find all occurrences of the term
            matches = []
            content_lower = content.lower()
            term_lower = term.lower()
            
            start = 0
            while True:
                pos = content_lower.find(term_lower, start)
                if pos == -1:
                    break
                matches.append(pos)
                start = pos + 1
            
            print(f"📝 Found {len(matches)} occurrence(s):")
            for j, pos in enumerate(matches[:3]):  # Show first 3 matches
                start_context = max(0, pos - 100)
                end_context = min(len(content), pos + len(term) + 100)
                context = content[start_context:end_context]
                
                print(f"   Match {j+1}: ...{context}...")
                print("-" * 50)
    else:
        print("❌ No pages found containing the search terms")

def search_in_chunks(search_terms, data_file="crawler/crawler/output/website_chunks.json"):
    """Search for terms in the chunked data"""
    
    if not os.path.exists(data_file):
        print(f"❌ File not found: {data_file}")
        return
    
    with open(data_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    print(f"🔍 Searching in {len(chunks)} chunks...")
    
    found_chunks = []
    
    for chunk in chunks:
        content = chunk.get('content', '')
        
        for term in search_terms:
            if term.lower() in content.lower():
                found_chunks.append({
                    'url': chunk.get('url', ''),
                    'title': chunk.get('title', ''),
                    'content': content,
                    'matched_term': term
                })
                break
    
    if found_chunks:
        print(f"✅ Found {len(found_chunks)} chunks containing the search terms:")
        for i, chunk in enumerate(found_chunks[:5], 1):  # Show first 5
            print(f"\n📄 Chunk {i}: {chunk['title']}")
            print(f"🔗 URL: {chunk['url']}")
            print(f"🎯 Matched term: {chunk['matched_term']}")
            print(f"📝 Content: {chunk['content'][:300]}...")
            print("-" * 50)
    else:
        print("❌ No chunks found containing the search terms")

if __name__ == "__main__":
    print("🔍 SEARCHING FOR PRINCIPAL INFORMATION")
    print("="*50)
    
    # Search terms related to principal
    principal_terms = [
        # "principal", "Principal", "PRINCIPAL",
        # "Dr.", "Dr ", "director", "Director",
        # "head", "Head", "dean", "Dean",
       "joby p p"
    ]
    
    print("\n1️⃣ Searching in raw scraped data:")
    print("-" * 30)
    search_in_scraped_data(principal_terms)
    
    print("\n2️⃣ Searching in chunked data:")
    print("-" * 30)
    search_in_chunks(principal_terms)
    
    print("\n💡 If no results found, try these search terms manually:")
    print("   - Names starting with common titles (Dr, Prof, Mr, Ms)")
    print("   - Look for an 'About' or 'Administration' page")
    print("   - Check if the college website has a staff directory")