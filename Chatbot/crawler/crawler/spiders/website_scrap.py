"""
Enhanced Universal Web Scraper with Structure Preservation
Preserves tables, lists, notes, and contextual relationships
"""

import asyncio
import json
import os
import re
import argparse
import traceback
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup, NavigableString
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime


class StructuredContentExtractor:
    """Extracts content while preserving structure (tables, lists, notes)."""

    CONTENT_SELECTORS = [
        ('main', 'semantic_main'),
        ('article', 'semantic_article'),
        ('[role="main"]', 'aria_main'),
        ('.content-area', 'cms_content_area'),
        ('.post-content', 'cms_post_content'),
        ('.entry-content', 'cms_entry_content'),
        ('.article-content', 'cms_article_content'),
        ('#root', 'react_root'),
        ('#app', 'vue_app'),
        ('#__next', 'nextjs_root'),
        ('#___gatsby', 'gatsby_root'),
        ('.main-content', 'generic_main'),
        ('.page-content', 'generic_page'),
        ('#content', 'generic_content'),
        ('.container', 'generic_container'),
    ]

    NOISE_SELECTORS = [
        'script', 'style', 'svg', 'iframe',
        'nav', 'header', 'footer', 'aside',
        '.navigation', '.nav', '.menu',
        '.sidebar', '.widget', '.advertisement',
        '.cookie-notice', '.popup', '.modal',
        '.social-share', '.comments', '.related-posts'
    ]

    @classmethod
    async def extract_content(cls, page: Page, url: str) -> Optional[Dict[str, any]]:
        """Extract content with structure preservation."""
        try:
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Remove noise
            for selector in cls.NOISE_SELECTORS:
                for element in soup.select(selector):
                    element.decompose()

            # Extract metadata
            title = await cls._extract_title(page, soup)
            meta_description = cls._extract_meta_description(soup)

            # Extract main content container
            main_content, strategy = cls._extract_main_content(soup)

            if not main_content:
                print(f"⚠️  No main content found for {url}, using body fallback")
                main_content = soup.find('body')
                strategy = 'fallback_body'

            if not main_content:
                return None

            # Extract structured elements
            tables = cls._extract_tables_with_context(main_content)
            lists = cls._extract_lists(main_content)
            notes = cls._extract_notes(main_content)
            headings = cls._extract_headings(main_content)

            # Extract clean text (without tables/lists to avoid duplication)
            text_content = cls._extract_text_content(main_content)

            # Build comprehensive structured content
            combined_content = cls._build_structured_content(
                text_content, tables, lists, notes, headings
            )

            # Quality checks
            if len(combined_content) < 100:
                print(f"⚠️  Content too short ({len(combined_content)} chars) for {url}")
                return None

            # Detect content characteristics
            page_type = cls._detect_page_type(url, combined_content, soup)
            content_quality = cls._assess_content_quality(combined_content, tables, lists, headings)
            financial_info = cls._detect_financial_content(combined_content)

            return {
                'url': url,
                'title': title,
                'content': combined_content,
                'meta_description': meta_description,
                'structured_data': {
                    'headings': headings,
                    'tables': tables,
                    'lists': lists,
                    'notes': notes
                },
                'metadata': {
                    'extraction_strategy': strategy,
                    'content_type': page_type,
                    'has_tables': len(tables) > 0,
                    'num_tables': len(tables),
                    'has_lists': len(lists) > 0,
                    'num_lists': len(lists),
                    'has_notes': len(notes) > 0,
                    'num_notes': len(notes),
                    'financial_info': financial_info,
                    'word_count': len(combined_content.split()),
                    'quality_score': content_quality,
                },
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"❌ Content extraction error for {url}: {e}")
            traceback.print_exc()
            return None

    @staticmethod
    def _extract_tables_with_context(content: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract tables in markdown format with surrounding context."""
        tables_data = []

        for idx, table in enumerate(content.find_all('table'), 1):
            try:
                # Get context before table (heading or paragraph)
                context_before = []
                prev = table.find_previous(['h1', 'h2', 'h3', 'h4', 'p'])
                if prev:
                    text = prev.get_text().strip()
                    if text and len(text) < 300:
                        context_before.append(text)

                # Convert table to markdown
                markdown_table = StructuredContentExtractor._table_to_markdown(table)

                if not markdown_table:
                    continue

                # Get context after table (notes, captions)
                context_after = []
                next_elem = table.find_next(['p', 'caption', 'div'])
                if next_elem:
                    text = next_elem.get_text().strip()
                    # Check if it's explanatory text (contains "note", starts with *, etc.)
                    if text and len(text) < 300 and (
                        'note' in text.lower()[:20] or
                        text.startswith('*') or
                        text.startswith('Note')
                    ):
                        context_after.append(text)

                # Check for caption
                caption = table.find('caption')
                if caption:
                    context_before.insert(0, caption.get_text().strip())

                tables_data.append({
                    'table_id': f'table_{idx}',
                    'context_before': ' '.join(context_before),
                    'markdown': markdown_table,
                    'context_after': ' '.join(context_after),
                    'num_rows': len(table.find_all('tr')),
                    'num_cols': len(table.find('tr').find_all(['td', 'th'])) if table.find('tr') else 0
                })

            except Exception as e:
                print(f"⚠️  Table extraction error: {e}")
                continue

        return tables_data

    @staticmethod
    def _table_to_markdown(table) -> str:
        """Convert HTML table to markdown format."""
        try:
            rows = []

            # Extract headers
            headers = []
            thead = table.find('thead')
            if thead:
                header_row = thead.find('tr')
                if header_row:
                    headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]

            # If no thead, try first row
            if not headers:
                first_row = table.find('tr')
                if first_row:
                    headers = [th.get_text().strip() for th in first_row.find_all(['th', 'td'])]

            if headers:
                # Clean headers
                headers = [h if h else f'Column_{i+1}' for i, h in enumerate(headers)]
                rows.append('| ' + ' | '.join(headers) + ' |')
                rows.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')

            # Extract data rows
            tbody = table.find('tbody') or table
            data_rows = tbody.find_all('tr')

            # Skip first row if it was used as header
            start_idx = 1 if not thead and headers else 0

            for tr in data_rows[start_idx:]:
                cells = [td.get_text().strip().replace('\n', ' ').replace('|', '\\|')
                        for td in tr.find_all(['td', 'th'])]
                if cells and any(cell for cell in cells):  # Skip empty rows
                    # Pad cells if needed
                    if headers and len(cells) < len(headers):
                        cells.extend([''] * (len(headers) - len(cells)))
                    rows.append('| ' + ' | '.join(cells) + ' |')

            return '\n'.join(rows) if len(rows) > 2 else ''

        except Exception as e:
            print(f"⚠️  Markdown conversion error: {e}")
            return ''

    @staticmethod
    def _extract_lists(content: BeautifulSoup) -> List[Dict[str, any]]:
        """Extract ordered and unordered lists with context."""
        lists_data = []

        for idx, list_elem in enumerate(content.find_all(['ul', 'ol']), 1):
            try:
                # Skip if it's a navigation list
                parent_classes = ' '.join(list_elem.get('class', []))
                if any(nav in parent_classes.lower() for nav in ['nav', 'menu', 'breadcrumb']):
                    continue

                # Get preceding context
                context = ""
                prev = list_elem.find_previous(['h1', 'h2', 'h3', 'h4', 'p'])
                if prev:
                    text = prev.get_text().strip()
                    if text and len(text) < 200:
                        context = text

                # Extract list items
                items = []
                for li in list_elem.find_all('li', recursive=False):
                    item_text = li.get_text().strip()
                    if item_text and len(item_text) > 2:
                        items.append(item_text)

                if items and len(items) >= 2:  # At least 2 items to be meaningful
                    lists_data.append({
                        'list_id': f'list_{idx}',
                        'type': 'ordered' if list_elem.name == 'ol' else 'unordered',
                        'context': context,
                        'items': items,
                        'num_items': len(items)
                    })

            except Exception as e:
                print(f"⚠️  List extraction error: {e}")
                continue

        return lists_data

    @staticmethod
    def _extract_notes(content: BeautifulSoup) -> List[str]:
        """Extract important notes, disclaimers, and caveats."""
        notes = []
        note_patterns = [
            r'^\s*Note\s*\d*\s*:',
            r'^\s*\*+\s*Note',
            r'^\s*Important\s*:',
            r'^\s*Disclaimer\s*:',
            r'^\s*Please note',
            r'^\s*\*\s*[A-Z]'  # Lines starting with * and capital letter
        ]

        # Find paragraphs or divs that look like notes
        for elem in content.find_all(['p', 'div', 'span']):
            text = elem.get_text().strip()

            # Check if starts with note pattern
            if any(re.match(pattern, text, re.IGNORECASE) for pattern in note_patterns):
                if 20 < len(text) < 500:  # Reasonable note length
                    notes.append(text)
                    continue

            # Check for note/important classes
            classes = ' '.join(elem.get('class', [])).lower()
            if any(keyword in classes for keyword in ['note', 'important', 'disclaimer', 'warning', 'alert']):
                if text and 20 < len(text) < 500:
                    notes.append(text)

        # Deduplicate and limit
        notes = list(dict.fromkeys(notes))[:10]
        return notes

    @staticmethod
    def _extract_headings(content: BeautifulSoup, max_headings: int = 20) -> List[Dict[str, str]]:
        """Extract headings with hierarchy."""
        headings = []
        for tag in ['h1', 'h2', 'h3', 'h4']:
            for heading in content.find_all(tag):
                text = heading.get_text().strip()
                if text and 3 < len(text) < 200:
                    if not any(noise in text.lower() for noise in ['menu', 'navigation', 'skip to']):
                        headings.append({
                            'level': int(tag[1]),
                            'text': text
                        })
        return headings[:max_headings]

    @staticmethod
    def _extract_text_content(content: BeautifulSoup) -> str:
        """Extract clean text while avoiding duplication of structured elements."""
        # Clone content to avoid modifying original
        content_copy = BeautifulSoup(str(content), 'html.parser')

        # Remove tables and lists to avoid duplication
        for elem in content_copy.find_all(['table', 'ul', 'ol']):
            elem.decompose()

        # Get text
        text = content_copy.get_text()

        # Clean text
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = re.sub(r'\s+', ' ', line).strip()
            if len(line) >= 10:
                if not re.match(r'^[\d\s\-\.\(\)]+$', line):
                    cleaned_lines.append(line)

        text = '\n\n'.join(cleaned_lines)

        # Remove noise patterns
        noise_patterns = [
            r'Skip to (main )?content',
            r'Cookie (policy|notice|consent)',
            r'Accept (all )?cookies',
            r'This site uses cookies',
            r'JavaScript (is )?(disabled|required)',
            r'Loading\.{3,}',
            r'Share on (Facebook|Twitter|LinkedIn)',
        ]

        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @staticmethod
    def _build_structured_content(
        text: str,
        tables: List[Dict],
        lists: List[Dict],
        notes: List[str],
        headings: List[Dict]
    ) -> str:
        """Combine all extracted content into a well-structured format."""
        parts = []

        # Main text content
        if text:
            parts.append(text)

        # Add tables with context
        if tables:
            parts.append("\n\n" + "="*50)
            parts.append("STRUCTURED TABLES")
            parts.append("="*50)

            for table in tables:
                if table['context_before']:
                    parts.append(f"\n**Context:** {table['context_before']}")

                parts.append(f"\n{table['markdown']}")

                if table['context_after']:
                    parts.append(f"\n**Note:** {table['context_after']}")

                parts.append("")  # Empty line between tables

        # Add important lists
        if lists:
            parts.append("\n" + "="*50)
            parts.append("IMPORTANT LISTS")
            parts.append("="*50)

            for lst in lists:
                if lst['context']:
                    parts.append(f"\n**{lst['context']}**")

                marker = '1.' if lst['type'] == 'ordered' else '-'
                for i, item in enumerate(lst['items'], 1):
                    if lst['type'] == 'ordered':
                        parts.append(f"{i}. {item}")
                    else:
                        parts.append(f"- {item}")
                parts.append("")

        # Add notes and disclaimers
        if notes:
            parts.append("\n" + "="*50)
            parts.append("IMPORTANT NOTES")
            parts.append("="*50)

            for i, note in enumerate(notes, 1):
                parts.append(f"\n{i}. {note}")

        return '\n'.join(parts)

    @staticmethod
    async def _extract_title(page: Page, soup: BeautifulSoup) -> str:
        """Extract page title using multiple strategies."""
        try:
            title = await page.title()
            if title and len(title) > 3:
                return title.strip()
        except:
            pass

        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()

        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()

        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()

        return "Untitled Page"

    @staticmethod
    def _extract_meta_description(soup: BeautifulSoup) -> str:
        """Extract meta description."""
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta and meta.get('content'):
            return meta['content'].strip()

        og_meta = soup.find('meta', attrs={'property': 'og:description'})
        if og_meta and og_meta.get('content'):
            return og_meta['content'].strip()

        return ""

    @classmethod
    def _extract_main_content(cls, soup: BeautifulSoup) -> Tuple[Optional[any], str]:
        """Extract main content using priority-based selector matching."""
        for selector, strategy in cls.CONTENT_SELECTORS:
            try:
                elements = soup.select(selector)
                best_element = None
                max_length = 0

                for element in elements:
                    text_length = len(element.get_text(strip=True))
                    if text_length > max_length and text_length > 100:
                        max_length = text_length
                        best_element = element

                if best_element:
                    return best_element, strategy
            except Exception as e:
                print(f"⚠️  Selector '{selector}' failed: {e}")
                continue

        body = soup.find('body')
        if body:
            return body, 'fallback_body'

        return None, 'failed'

    @staticmethod
    def _detect_page_type(url: str, text: str, soup: BeautifulSoup) -> str:
        """Detect page type."""
        url_lower = url.lower()
        text_lower = text.lower()

        url_patterns = {
            'product': ['/product', '/item', '/shop', '/store', '/buy'],
            'blog': ['/blog', '/article', '/post', '/news', '/story'],
            'about': ['/about', '/who-we-are', '/our-story', '/company'],
            'contact': ['/contact', '/get-in-touch', '/reach-us'],
            'service': ['/service', '/services', '/what-we-do', '/solution'],
            'faq': ['/faq', '/help', '/support', '/questions'],
            'pricing': ['/pricing', '/plans', '/packages', '/fees', '/scholarship'],
            'career': ['/career', '/jobs', '/hiring', '/join-us'],
            'admission': ['/admission', '/admissions', '/apply', '/enroll'],
        }

        for page_type, patterns in url_patterns.items():
            if any(pattern in url_lower for pattern in patterns):
                return page_type

        if soup.find('form') and any(word in text_lower for word in ['email', 'message', 'contact']):
            return 'contact'

        if re.search(r'₹|Rs\.?\s*\d|price|pricing|cost|fee', text_lower):
            return 'pricing'

        if len(text.split()) > 500 and len(soup.find_all(['p'])) > 5:
            return 'article'

        return 'general'

    @staticmethod
    def _assess_content_quality(
        text: str,
        tables: List[Dict],
        lists: List[Dict],
        headings: List[Dict]
    ) -> float:
        """Assess content quality (0-1 score)."""
        score = 0.0

        # Text content quality
        word_count = len(text.split())
        if word_count > 50:
            score += min(word_count / 1000, 0.25)

        # Structured content bonus
        if tables:
            score += min(len(tables) * 0.15, 0.25)

        if lists:
            score += min(len(lists) * 0.05, 0.1)

        # Headings
        if headings:
            score += min(len(headings) * 0.02, 0.15)

        # Paragraphs
        paragraphs = text.split('\n\n')
        if len(paragraphs) >= 2:
            score += 0.15

        # Vocabulary diversity
        unique_words = len(set(text.lower().split()))
        total_words = len(text.split())
        if total_words > 0:
            uniqueness = unique_words / total_words
            score += uniqueness * 0.1

        return min(score, 1.0)

    @staticmethod
    def _detect_financial_content(text: str) -> Dict[str, bool]:
        """Detect financial/pricing content."""
        text_lower = text.lower()
        return {
            'has_pricing': bool(re.search(r'₹|rs\.?\s*\d|price|cost|fee|tuition', text_lower)),
            'has_scholarships': bool(re.search(r'scholarship|discount|waiver|financial aid', text_lower)),
            'has_calculations': bool(re.search(r'total|after|before|net|final|per year|per semester', text_lower)),
            'has_tables': 'table' in text_lower or '|' in text,
        }


class SmartLinkExtractor:
    """Intelligent link extraction with filtering."""

    SKIP_PATTERNS = [
        r'/login', r'/signin', r'/signup', r'/register', r'/auth',
        r'/cart', r'/checkout', r'/account', r'/profile',
        r'/search\?', r'/tag/', r'/category/', r'/author/',
        r'/feed', r'/rss', r'/api/', r'/download',
        r'\.pdf$', r'\.jpg$', r'\.png$', r'\.gif$',
        r'\.mp4$', r'\.mp3$', r'\.zip$', r'\.doc',
        r'mailto:', r'tel:', r'javascript:',
    ]

    PRIORITY_PATTERNS = [
        r'/about', r'/service', r'/product', r'/solution',
        r'/pricing', r'/contact', r'/faq', r'/help',
        r'/admission', r'/scholarship', r'/fee'
    ]

    @classmethod
    async def extract_links(cls, page: Page, base_url: str, domain: str) -> List[str]:
        """Extract and prioritize valid links."""
        try:
            raw_links = await page.eval_on_selector_all(
                'a[href]',
                '(elements) => elements.map(e => e.href)'
            )

            valid_links = []
            priority_links = []

            for href in raw_links:
                if not href or not isinstance(href, str):
                    continue

                parsed = urlparse(href)

                if parsed.netloc and parsed.netloc != domain:
                    continue

                clean_url = href.split('#')[0]

                if any(re.search(pattern, clean_url.lower()) for pattern in cls.SKIP_PATTERNS):
                    continue

                is_priority = any(re.search(pattern, clean_url.lower()) for pattern in cls.PRIORITY_PATTERNS)

                if is_priority:
                    priority_links.append(clean_url)
                else:
                    valid_links.append(clean_url)

            all_links = list(dict.fromkeys(priority_links + valid_links))
            return all_links[:30]

        except Exception as e:
            print(f"⚠️  Link extraction error: {e}")
            return []


class UniversalWebScraper:
    """Universal web scraper with structure preservation."""

    def __init__(
        self,
        start_url: str,
        output_file: str,
        max_pages: int = 50,
        min_quality_score: float = 0.2
    ):
        self.start_url = start_url
        self.output_file = output_file
        self.max_pages = max_pages
        self.min_quality_score = min_quality_score
        self.domain = urlparse(start_url).netloc

        self.visited_urls: Set[str] = set()
        self.results: List[Dict] = []
        self.queue: List[str] = [start_url]

        self.stats = {
            'total_attempted': 0,
            'successful': 0,
            'low_quality': 0,
            'errors': 0,
            'avg_quality': 0.0,
            'total_tables': 0,
            'total_lists': 0,
            'total_notes': 0,
            'error_details': []
        }

        self.content_extractor = StructuredContentExtractor()
        self.link_extractor = SmartLinkExtractor()

    async def scrape(self):
        """Main scraping orchestration."""
        print(f"\n🔧 Starting Playwright browser...")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox'
                    ]
                )

                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )

                await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                self._print_header()

                while self.queue and len(self.results) < self.max_pages:
                    url = self.queue.pop(0)

                    if url in self.visited_urls:
                        continue

                    self.visited_urls.add(url)
                    self.stats['total_attempted'] += 1

                    await self._scrape_page(context, url)

                await browser.close()
                self._save_results()

                return 0

        except Exception as e:
            print(f"\n❌ FATAL ERROR: {e}")
            traceback.print_exc()
            self._save_results()
            return 1

    async def _scrape_page(self, context, url: str):
        """Scrape a single page with comprehensive error handling."""
        page = None
        try:
            page = await context.new_page()

            print(f"🌐 Loading: {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=45000)
            await page.wait_for_timeout(3000)

            content_data = await self.content_extractor.extract_content(page, url)

            if content_data:
                quality_score = content_data['metadata']['quality_score']

                if quality_score >= self.min_quality_score:
                    self.results.append(content_data)
                    self.stats['successful'] += 1
                    self.stats['avg_quality'] += quality_score

                    # Update structure stats
                    self.stats['total_tables'] += content_data['metadata']['num_tables']
                    self.stats['total_lists'] += content_data['metadata']['num_lists']
                    self.stats['total_notes'] += content_data['metadata']['num_notes']

                    print(f"✅ [{len(self.results)}/{self.max_pages}] {url}")
                    print(f"   📝 {content_data['metadata']['word_count']} words | "
                          f"Quality: {quality_score:.2f} | "
                          f"{content_data['metadata']['content_type']} | "
                          f"Tables: {content_data['metadata']['num_tables']} | "
                          f"Lists: {content_data['metadata']['num_lists']}")

                    new_links = await self.link_extractor.extract_links(page, url, self.domain)
                    for link in new_links:
                        if link not in self.visited_urls and link not in self.queue:
                            self.queue.append(link)
                else:
                    self.stats['low_quality'] += 1
                    print(f"⚠️  Low quality (score: {quality_score:.2f}): {url}")
            else:
                self.stats['low_quality'] += 1
                print(f"⚠️  No content extracted: {url}")

        except PlaywrightTimeoutError:
            self.stats['errors'] += 1
            error_msg = f"Timeout loading {url}"
            print(f"⏱️  {error_msg}")
            self.stats['error_details'].append(error_msg)
        except Exception as e:
            self.stats['errors'] += 1
            error_msg = f"{url}: {str(e)[:100]}"
            print(f"❌ {error_msg}")
            self.stats['error_details'].append(error_msg)
            traceback.print_exc()
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass

    def _print_header(self):
        """Print scraper header."""
        print("\n" + "="*70)
        print("🚀 Enhanced Structure-Preserving Web Scraper")
        print("="*70 + "\n")

    def _save_results(self):
        """Save scraping results and statistics."""
        os.makedirs(os.path.dirname(self.output_file) or '.', exist_ok=True)

        # Save main results
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        # Calculate final stats
        if self.stats['successful'] > 0:
            self.stats['avg_quality'] /= self.stats['successful']

        # Save statistics
        stats_file = self.output_file.replace('.json', '_stats.json')
        stats_data = {
            'domain': self.domain,
            'start_url': self.start_url,
            'scrape_time': datetime.now().isoformat(),
            'statistics': self.stats,
            'total_pages_saved': len(self.results),
            'quality_threshold': self.min_quality_score,
            'structure_summary': {
                'total_tables_extracted': self.stats['total_tables'],
                'total_lists_extracted': self.stats['total_lists'],
                'total_notes_extracted': self.stats['total_notes'],
                'avg_tables_per_page': self.stats['total_tables'] / max(self.stats['successful'], 1),
                'avg_lists_per_page': self.stats['total_lists'] / max(self.stats['successful'], 1)
            }
        }

        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, indent=2)

        # Save a human-readable summary
        self._save_readable_summary()

        # Print summary
        print("\n" + "="*70)
        print("🎉 SCRAPING COMPLETE" if self.stats['successful'] > 0 else "⚠️  SCRAPING FINISHED WITH ISSUES")
        print("="*70)
        print(f"✅ Successfully scraped: {self.stats['successful']} pages")
        print(f"📊 Average quality score: {self.stats['avg_quality']:.2f}")
        print(f"📋 Total tables extracted: {self.stats['total_tables']}")
        print(f"📝 Total lists extracted: {self.stats['total_lists']}")
        print(f"⚠️  Total notes extracted: {self.stats['total_notes']}")
        print(f"⚠️  Low quality/no content: {self.stats['low_quality']} pages")
        print(f"❌ Errors: {self.stats['errors']} pages")
        print(f"📈 Total attempted: {self.stats['total_attempted']} pages")
        print(f"💾 Saved to: {self.output_file}")
        print(f"📋 Stats saved to: {stats_file}")

        if self.stats['error_details']:
            print(f"\n📝 Error details ({len(self.stats['error_details'])} errors):")
            for i, error in enumerate(self.stats['error_details'][:5], 1):
                print(f"   {i}. {error}")
            if len(self.stats['error_details']) > 5:
                print(f"   ... and {len(self.stats['error_details']) - 5} more")

        print("="*70 + "\n")

    def _save_readable_summary(self):
        """Save a human-readable markdown summary of scraped content."""
        summary_file = self.output_file.replace('.json', '_summary.md')

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"# Web Scraping Summary\n\n")
            f.write(f"**Domain:** {self.domain}\n")
            f.write(f"**Scraped:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Pages:** {len(self.results)}\n\n")
            f.write("---\n\n")

            for idx, page in enumerate(self.results, 1):
                f.write(f"## {idx}. {page['title']}\n\n")
                f.write(f"**URL:** {page['url']}\n")
                f.write(f"**Type:** {page['metadata']['content_type']}\n")
                f.write(f"**Quality:** {page['metadata']['quality_score']:.2f}\n")

                if page['structured_data']['tables']:
                    f.write(f"**Tables:** {len(page['structured_data']['tables'])}\n")
                if page['structured_data']['lists']:
                    f.write(f"**Lists:** {len(page['structured_data']['lists'])}\n")
                if page['structured_data']['notes']:
                    f.write(f"**Notes:** {len(page['structured_data']['notes'])}\n")

                f.write("\n### Headings\n\n")
                for heading in page['structured_data']['headings'][:5]:
                    f.write(f"{'#' * (heading['level'] + 1)} {heading['text']}\n")

                if page['meta_description']:
                    f.write(f"\n**Description:** {page['meta_description']}\n")

                f.write("\n---\n\n")

        print(f"📄 Readable summary saved to: {summary_file}")


async def main():
    parser = argparse.ArgumentParser(
        description='Enhanced Structure-Preserving Web Scraper - Preserves tables, lists, and context'
    )
    parser.add_argument('url', help='Starting URL to scrape')
    parser.add_argument('output', help='Output JSON file path')
    parser.add_argument('--max-pages', type=int, default=50, help='Maximum pages to scrape (default: 50)')
    parser.add_argument('--min-quality', type=float, default=0.2, help='Minimum quality score (0-1, default: 0.2)')

    args = parser.parse_args()

    scraper = UniversalWebScraper(
        start_url=args.url,
        output_file=args.output,
        max_pages=args.max_pages,
        min_quality_score=args.min_quality
    )

    exit_code = await scraper.scrape()
    exit(exit_code)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
        exit(1)
