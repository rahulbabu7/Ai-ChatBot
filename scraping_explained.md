# How Smart Assist AI Scrapes and Ingests Knowledge

---

## Overview — Three Sources of Knowledge

The platform can learn from three types of knowledge sources. All three end up in the same ChromaDB vector collection per tenant, searched together at query time.

| Source | How it enters the system | Tool used |
|---|---|---|
| Client website | Automated web crawl | Playwright + BeautifulSoup |
| PDF documents | Uploaded through admin dashboard | pdfminer |
| Custom Q&A | JSON file edited in admin dashboard | Direct embedding |

This document explains each in detail, with the web crawler getting the most attention because it is the most complex.

---

## Part 1: Web Crawling

### Why Not Just `requests` + `BeautifulSoup`?

A simple `requests.get(url)` fetches the raw HTML that the server sends. Many modern websites (React, Vue, Next.js, WordPress with Elementor) send an almost empty HTML shell and then build the page content using JavaScript after the page loads. If you scrape that HTML directly, you get nothing useful.

**Playwright** solves this. It launches a real Chromium browser (headless — no visible window), navigates to the URL, runs all JavaScript, waits for the page to fully render, and only then lets you read the final HTML. This is the same HTML a real user would see.

**Why Scrapy architecture alongside Playwright?** Scrapy provides the crawl management framework — the queue, the visited-URL tracking, the statistics, and the output. Playwright handles the rendering. The combination gives the robustness of Scrapy's crawler with the JS-rendering power of Playwright.

---

### Step 1: Sitemap Discovery (Before Any Crawling Starts)

The very first thing the crawler does — before opening a browser — is look for a sitemap.

```
sitemap.xml → sitemap_index.xml → robots.txt Sitemap: directive
```

**What is a sitemap?** A sitemap is an XML file that website owners publish to tell search engines about all their pages. It lists every URL the site wants indexed.

**Why use it?** Without a sitemap, the crawler has to start from the homepage and follow links one by one (breadth-first search). This is slow and may never reach deep or isolated pages. A sitemap gives us the full URL list immediately.

**What the code does:**
1. Tries to fetch `sitemap.xml`, then `sitemap_index.xml`
2. Reads `robots.txt` and looks for `Sitemap:` lines
3. If it finds a sitemap index (which links to child sitemaps), it recursively follows those too
4. Collects all page URLs from the sitemap

**URL filtering on sitemap results:** Not every URL in a sitemap is worth crawling. The code filters out:
- Pagination pages (`/page/2`, `/page/3`)
- Query string URLs (`?sort=price`)
- Tag and category archive pages (`/tag/`, `/category/`)
- Author pages (`/author/`)
- WordPress API endpoints (`/wp-json/`)
- Static files (`.jpg`, `.pdf`, `.zip`)
- Authentication pages (`/login`, `/cart`)

**Depth-based sorting:** After filtering, the remaining URLs are sorted by how deep they are in the site structure. A URL like `/about/` has depth 1. A URL like `/dept/cse/faculty/john-doe/` has depth 4. Shallow pages (about, services, contact, pricing) tend to have the most useful content. The top 50 shallowest URLs are queued first. The BFS crawler discovers deeper pages naturally through link-following.

**Why cap at 50 from the sitemap?** Large sites can have hundreds of low-value pages in their sitemap — staff profiles, blog posts from 2015, tag archive pages. Queuing all of them would make the crawl take hours. Capping at 50 and letting BFS discover more important pages via links is faster and produces better-quality content.

---

### Step 2: Playwright Browser Launch

Once the URL queue is ready, the Playwright browser starts:

```python
browser = await p.chromium.launch(headless=True, args=[
    '--disable-blink-features=AutomationControlled',
    '--no-sandbox',
    '--disable-dev-shm-usage'
])
```

- `headless=True` — no visible browser window, runs silently in the background
- `AutomationControlled=disabled` — hides the fact that this is an automated browser, preventing bot-detection scripts from blocking the crawler
- A fake `user_agent` string is set to look like a regular Chrome browser on Windows

---

### Step 3: Loading Each Page

For each URL in the queue:

1. **Navigate** to the URL and wait for `networkidle` — meaning no more network requests are being made. This ensures AJAX calls and lazy-loaded data have finished.

2. **Scroll the page** — some content only loads when you scroll down (lazy loading). The code scrolls the page 5 times in small steps to trigger this.

3. **Wait for dynamic content** — this is a sophisticated multi-strategy wait:
   - Detects if the page has animated counters (`data-to-value`, `data-purecounter-end`), loading spinners, or framework hydration markers
   - Uses a MutationObserver to detect when the DOM has stopped changing (stable for 500ms)
   - Specifically waits for animated number counters to reach their final values (important for pages showing statistics like "5000+ students")
   - Waits for lazy-loaded images to finish loading

4. **Extract dynamic values** — runs JavaScript inside the browser to capture animated counter values before they are read as plain numbers in the HTML. This is important for pages that show fees or statistics as animating numbers.

---

### Step 4: Noise Removal

Before extracting content, the code strips elements that add noise but no useful information:

```python
NOISE_SELECTORS = [
    'script', 'style', 'svg', 'iframe',
    'nav', 'header', 'footer', 'aside',
    '.navigation', '.menu', '.sidebar',
    '.cookie-notice', '.popup', '.modal',
    '.social-share', '.comments',
    '.entry-meta', '.post-meta',        # WordPress author/date noise
    '.breadcrumbs', '.read-more',
    ...
]
```

**Why remove these?** Navigation menus, footers, and sidebars contain the same links on every page. If you include them in the knowledge base, the chatbot will have hundreds of duplicate "Home | About | Services | Contact" strings polluting its index. Cookie banners, social share buttons, and comment sections are similarly useless for answering questions.

**Important exception:** Schema.org JSON-LD data lives inside `<script>` tags, which are in the noise list. So Schema.org extraction is done **before** noise removal runs.

---

### Step 5: Finding the Main Content

After noise removal, the code needs to identify which part of the page is the actual content (not the menu, not the sidebar). It tries a priority-ordered list of CSS selectors:

```python
CONTENT_SELECTORS = [
    ('main', 'semantic_main'),           # HTML5 semantic tag
    ('article', 'semantic_article'),     # Article tag
    ('[role="main"]', 'aria_main'),      # ARIA landmark
    ('.content-area', 'cms_content_area'),
    ('.post-content', 'cms_post_content'),
    ('#root', 'react_root'),             # React apps
    ('#__next', 'nextjs_root'),          # Next.js apps
    ('#___gatsby', 'gatsby_root'),       # Gatsby apps
    ...
]
```

It picks the selector that finds the element with the most text content. If nothing matches, it falls back to the `<body>` tag.

---

### Step 6: Content Extraction — Five Types

Once the main content container is found, five types of content are extracted separately:

#### 6a. Plain Text

Tables and lists are removed from a copy of the content first (to avoid duplicating them in the output), then `get_text()` extracts the remaining prose. Noise patterns are cleaned:
- "Skip to content", "Accept all cookies", "JavaScript is required" — stripped by regex
- Lines shorter than 10 characters — dropped (likely menu items or stray symbols)
- Lines that are pure numbers/punctuation — dropped

#### 6b. Tables → Markdown

Every `<table>` element is converted to markdown format:

```
| Column 1 | Column 2 | Column 3 |
| --- | --- | --- |
| Value A  | Value B  | Value C  |
```

The context before the table (the nearest heading or paragraph) is captured and stored alongside the markdown, so the chatbot knows what the table is about. The context after (notes like "* Subject to change") is also captured.

**Why convert to markdown?** The sentence-transformer embedding model works on text, not HTML. Markdown preserves the tabular structure in a text format that the model can process meaningfully. A table of fees with headers and values becomes a clear text structure rather than a blob of numbers.

#### 6c. Lists

Ordered (`<ol>`) and unordered (`<ul>`) lists are extracted with their preceding context (the heading or sentence that introduces the list). Navigation lists are excluded by checking the parent element's CSS classes for `nav`, `menu`, or `breadcrumb`. Only lists with at least 2 items are kept.

#### 6d. Important Notes and Disclaimers

Paragraphs or divs that begin with patterns like `Note:`, `Important:`, `Disclaimer:`, `Please note` or have CSS classes like `note`, `warning`, `alert` are collected separately. These are often critical information that users need but might be missed in plain text extraction.

#### 6e. Headings

H1 through H4 tags are extracted with their hierarchy level. Headings that contain navigation words (`menu`, `navigation`, `skip to`) are excluded.

---

### Step 7: Schema.org JSON-LD Extraction

**What is Schema.org?** Schema.org is a vocabulary that websites embed in their pages inside `<script type="application/ld+json">` tags to provide structured data to search engines. A page about a product might embed its name, price, and description in this format. A page with FAQs might embed all questions and answers.

**Why extract it?** This data is already structured and clean. If a page has a FAQPage schema, we get perfectly formatted question-answer pairs without having to parse messy HTML.

Three Schema.org types are handled:

- **FAQPage** — extracts all question-answer pairs:
  ```
  Q: What is the refund policy?
  A: Refunds are processed within 7 business days.
  ```

- **Product / Service** — extracts name, description, SKU, brand, and price

- **LocalBusiness** — extracts business name, phone, email, address, and opening hours

**Why extract before noise removal?** The `<script>` tag is in the noise selector list (because script tags generally contain JavaScript, not content). If noise removal ran first, the Schema.org data would be deleted. So `_extract_schema_org()` is called before `NOISE_SELECTORS` are applied.

---

### Step 8: FAQ Accordion Extraction

Many websites use HTML `<details>` and `<summary>` elements to create collapsible FAQ sections:

```html
<details>
  <summary>What is the admission process?</summary>
  <p>Submit your application online at...</p>
</details>
```

In a normal browser, these show as collapsed sections. A plain `get_text()` call would still extract the text, but it would be jumbled with no question-answer structure. The `_extract_details_accordions()` method finds every `<details>` element, reads the `<summary>` as the question, and reads the remaining content as the answer, outputting clean Q&A pairs:

```
Q: What is the admission process?
A: Submit your application online at...
```

---

### Step 9: CMS Noise Cleaning

After all content is assembled, a final regex cleaning pass removes WordPress/CMS metadata patterns that slip through:

- `By Author Name |` bylines
- ISO timestamps like `2021-07-04T10:00:00+05:30`
- `0 Comments` counts
- `Categories: X, Y, Z` lines
- `Tags: A, B` lines
- Standalone `Read More` links

---

### Step 10: Quality Filtering — What Gets Rejected

Not every page that loads is worth keeping. The code runs three rejection checks:

#### Archive / listing pages
If the extracted content contains 3 or more instances of the phrase "Read More", the page is almost certainly a blog index or category archive — a list of post titles with excerpt snippets. These contain no substantive knowledge, just navigation. Rejected.

#### Person / staff profile pages
Pages that match two or more of these patterns in their first 800 characters are rejected as contact cards:
- `mobile number:` or `mobile no:`
- `date of joining`
- `assistant/associate/senior professor`
- `designation:`
- `employee id:` or `staff id:`

A staff directory page for a university might have hundreds of these — they add no knowledge base value.

#### Stale pages
Pages whose Open Graph `article:modified_time` metadata shows they were last updated more than 2 years ago, and whose content does not mention any year from 2023 onwards, are considered stale and rejected. Old pricing pages or outdated event announcements would mislead the chatbot.

#### Quality score threshold
Each page gets a quality score (0–1) based on word count, number of tables, lists, headings, and vocabulary diversity. Pages scoring below 0.2 are discarded as too thin to be useful.

---

### Step 11: Link Extraction and BFS

After a page is successfully scraped, its links are extracted for the breadth-first queue. Priority links (URLs containing `/about`, `/service`, `/pricing`, `/faq`, `/contact`, `/admission`) are placed at the front of the queue ahead of generic links. Links are deduplicated and capped at 30 per page to prevent the queue from exploding on large sites.

The crawl continues until either the queue is empty or 50 pages have been successfully saved.

---

### What the Output Looks Like

For each page, the scraper saves a structured JSON object:

```json
{
  "url": "https://example.com/about",
  "title": "About Us",
  "content": "Full combined text including tables, lists, notes, Schema.org, accordions...",
  "meta_description": "We are a leading...",
  "structured_data": {
    "headings": [{"level": 1, "text": "About Our Company"}],
    "tables": [{"markdown": "| Fee | Amount |\n|---|---|\n| Tuition | ₹50,000 |", ...}],
    "lists": [{"items": ["Item A", "Item B"], "context": "Our services include"}],
    "notes": ["Note: Fees are subject to change"]
  },
  "metadata": {
    "content_type": "about",
    "quality_score": 0.74,
    "num_tables": 1,
    "num_lists": 3
  }
}
```

This JSON is saved as `website_content.json` in the client's data folder and is fed to the embedding pipeline.

---

## Part 2: PDF Ingestion

When a tenant uploads a PDF through the admin dashboard:

1. The file is saved to `client_data/{client_id}/pdfs/`
2. A Celery background task is triggered immediately
3. **pdfminer** extracts text from the PDF, handling:
   - Multi-column layouts
   - Embedded tables
   - Mixed fonts and sizes
4. The extracted text is passed to the UniversalChunker, the same chunker used for web content
5. Chunks are embedded and stored in ChromaDB with `source: "pdf"` metadata

**Why pdfminer over PyPDF2?** pdfminer performs lower-level PDF parsing and produces more accurate text extraction for complex layouts like two-column academic papers or fee structure tables. PyPDF2 is simpler but often mangles column ordering.

---

## Part 3: Custom Q&A

The admin can directly enter question-answer pairs through the dashboard. These are stored as a JSON file:

```json
[
  {"question": "What are your working hours?", "answer": "Monday to Friday, 9am to 6pm."},
  {"question": "Do you offer EMI?", "answer": "Yes, 0% EMI is available on all courses."}
]
```

These are embedded directly without chunking — each Q&A pair becomes one vector in ChromaDB with `source: "qa"` metadata.

**Disk cache for Q&A embeddings:** Computing embeddings is slow. If the admin adds one new Q&A pair, re-embedding the entire file would be wasteful. The system caches the computed embeddings in a `.pkl` file and checks the `custom_qa.json` modification time before each retrieval session. If the file has not changed, the cached embeddings are used. If the file changed, the cache is regenerated.

---

## Part 4: UniversalChunker — Splitting Content into Pieces

All three sources (web, PDF, Q&A) pass through the UniversalChunker before being stored in ChromaDB.

**Why chunk?** Embedding models have a maximum input length (typically 512 tokens). A full web page might be 5000 words. Storing it as one chunk means the embedding captures a vague average of the whole page. Retrieving it gives the LLM too much irrelevant text. Chunking splits content into focused pieces so each vector represents a specific topic.

**Type-aware chunk sizes:**

| Content type | Chunk size | Overlap | Why |
|---|---|---|---|
| General text | 1000 tokens | 200 | Standard prose |
| Narrative (blog, articles) | 1200 tokens | 250 | Longer context needed for coherent paragraphs |
| Structured (lists, Q&A) | 850 tokens | 160 | Shorter — structure provides its own context |
| Tables | up to 2000 tokens | 80 | Tables must not be split mid-row |

**Why overlap?** If a chunk ends mid-sentence and the answer spans the boundary between two chunks, neither chunk alone contains the full answer. Overlapping chunks ensure that boundary content appears in at least one chunk in context.

---

## Part 5: Storage in ChromaDB

After chunking, each chunk is:

1. **Encoded** by `multi-qa-mpnet-base-dot-v1` into a 768-dimensional vector
2. **Stored** in the tenant's ChromaDB collection with metadata:
   - `source`: `"crawl"`, `"pdf"`, or `"qa"`
   - `url`: the source URL (for citations shown to the user)
   - `page`: page number (for PDFs)

All three source types live in the same collection. At retrieval time, the hybrid retriever searches across all of them simultaneously — a user's question might be best answered by a combination of a web page paragraph and a custom Q&A pair.

**Source isolation on deletion:** When an admin deletes a source (e.g., deletes a PDF), the system uses ChromaDB's metadata filtering to delete only chunks where `source == "pdf"`, leaving web and Q&A chunks untouched. This runs immediately before any re-embedding task starts, ensuring the chatbot stops answering from that source right away.

---

## Summary: Why This Scraping Design Choices Matter

| Decision | Why it matters |
|---|---|
| Playwright over requests | Handles React, Vue, Next.js, WordPress Elementor — all JavaScript-heavy sites |
| Sitemap-first + BFS fallback | Gets the most important pages fast; does not miss isolated pages |
| Depth-sorted URL queue | Prioritises high-value shallow pages (About, Services, Pricing) over deep archive pages |
| Schema.org extraction before noise removal | Structured FAQ/Product data is perfectly clean — would be lost if extracted after |
| `<details>/<summary>` accordion extraction | Many FAQ sections use this pattern — plain `get_text()` misses the Q&A structure |
| Person profile and stale page rejection | Prevents useless data from polluting the knowledge base |
| Table → Markdown conversion | Preserves structured fee/spec data that the LLM needs to answer "How much does X cost?" |
| Dynamic counter extraction | Captures animated statistics (student count, fees) that only appear as numbers after JS runs |
| Type-aware chunk sizes | Prevents tables from being split mid-row; gives narrative text enough context |
| 50-page cap with depth sorting | Controls crawl time while maximising useful content coverage |
