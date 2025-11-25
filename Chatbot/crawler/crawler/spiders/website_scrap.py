# import asyncio
# import json
# import os
# import re
# import argparse
# from urllib.parse import urljoin, urlparse
# from playwright.async_api import async_playwright, Page
# from bs4 import BeautifulSoup
# from typing import List, Dict, Set


# class PlaywrightScraper:
#     def __init__(self, start_url: str, output_file: str, max_pages: int = 50):
#         self.start_url = start_url
#         self.output_file = output_file
#         self.max_pages = max_pages
#         self.domain = urlparse(start_url).netloc

#         self.visited_urls: Set[str] = set()
#         self.results: List[Dict] = []
#         self.queue: List[str] = [start_url]

#         self.stats = {
#             'total_attempted': 0,
#             'successful': 0,
#             'skipped_content': 0,
#             'errors': 0
#         }

#         self.unwanted_extensions = (
#             '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx',
#             '.zip', '.mp4', '.mp3', '.avi', '.mov', '.xlsx', '.ppt',
#             '.css', '.js', '.xml', '.json', '.svg', '.ico'
#         )

#     async def scrape(self):
#         """Main scraping function."""
#         async with async_playwright() as p:
#             # Launch browser in headless mode
#             browser = await p.chromium.launch(headless=True)
#             context = await browser.new_context(
#                 viewport={'width': 1920, 'height': 1080},
#                 user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
#             )

#             print(f"\n{'='*60}")
#             print(f"🚀 Starting Playwright Scraper")
#             print(f"{'='*60}")
#             print(f"🌐 Domain: {self.domain}")
#             print(f"📄 Max pages: {self.max_pages}")
#             print(f"{'='*60}\n")

#             while self.queue and len(self.results) < self.max_pages:
#                 url = self.queue.pop(0)

#                 if url in self.visited_urls:
#                     continue

#                 self.visited_urls.add(url)
#                 self.stats['total_attempted'] += 1

#                 try:
#                     page = await context.new_page()

#                     # Navigate with timeout
#                     await page.goto(url, wait_until='networkidle', timeout=30000)

#                     # Wait for content to render
#                     await page.wait_for_timeout(2000)

#                     # Extract content
#                     content_data = await self._extract_content(page, url)

#                     if content_data:
#                         self.results.append(content_data)
#                         self.stats['successful'] += 1
#                         print(f"✅ [{len(self.results)}/{self.max_pages}] {url}")
#                         print(f"   📝 {content_data['word_count']} words | {content_data['content_type']}")

#                         # Extract and queue new links
#                         new_links = await self._extract_links(page)
#                         for link in new_links:
#                             if link not in self.visited_urls and link not in self.queue:
#                                 self.queue.append(link)
#                     else:
#                         self.stats['skipped_content'] += 1
#                         print(f"⚠️  Skipped (no content): {url}")

#                     await page.close()

#                 except Exception as e:
#                     self.stats['errors'] += 1
#                     print(f"❌ Error: {url} - {str(e)[:100]}")
#                     try:
#                         await page.close()
#                     except:
#                         pass

#             await browser.close()

#             # Save results
#             self._save_results()

#     async def _extract_content(self, page: Page, url: str) -> Dict:
#         """Extract content from page."""
#         try:
#             # Get page HTML
#             html = await page.content()
#             soup = BeautifulSoup(html, 'html.parser')

#             # Remove unwanted elements
#             for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
#                 element.decompose()

#             # Extract title
#             title = await page.title()
#             if not title:
#                 title_tag = soup.find('h1')
#                 title = title_tag.get_text().strip() if title_tag else ""

#             # Extract meta description
#             meta_desc = ""
#             meta_tag = soup.find('meta', attrs={'name': 'description'})
#             if meta_tag:
#                 meta_desc = meta_tag.get('content', '')
#             else:
#                 og_tag = soup.find('meta', attrs={'property': 'og:description'})
#                 if og_tag:
#                     meta_desc = og_tag.get('content', '')

#             # Extract headings
#             headings = []
#             for tag in ['h1', 'h2', 'h3']:
#                 for h in soup.find_all(tag):
#                     text = h.get_text().strip()
#                     if text:
#                         headings.append(text)
#             headings_text = ' | '.join(headings[:10])

#             # Extract main content with multiple strategies
#             main_content = None
#             strategy = "unknown"

#             # Strategy 1: Semantic HTML
#             for selector in ['main', 'article', '[role="main"]']:
#                 element = soup.select_one(selector)
#                 if element and len(element.get_text(strip=True)) > 200:
#                     main_content = element
#                     strategy = f"semantic:{selector}"
#                     break

#             # Strategy 2: React/Next.js containers
#             if not main_content:
#                 for selector in ['#root', '#app', '#__next', '#___gatsby']:
#                     element = soup.select_one(selector)
#                     if element and len(element.get_text(strip=True)) > 200:
#                         main_content = element
#                         strategy = f"react:{selector}"
#                         break

#             # Strategy 3: Content classes
#             if not main_content:
#                 for selector in ['.content', '#content', '.main-content', '.page-content']:
#                     element = soup.select_one(selector)
#                     if element and len(element.get_text(strip=True)) > 200:
#                         main_content = element
#                         strategy = f"class:{selector}"
#                         break

#             # Strategy 4: Body fallback
#             if not main_content:
#                 main_content = soup.find('body')
#                 strategy = "body_fallback"

#             if not main_content:
#                 return None

#             # Extract plain text
#             plain_text = self._clean_text(main_content.get_text())

#             if len(plain_text) < 50:
#                 return None

#             # Detect content type
#             content_type = self._detect_page_type(url, plain_text)

#             return {
#                 'url': url,
#                 'title': title,
#                 'content': plain_text,
#                 'meta_description': meta_desc,
#                 'headings': headings_text,
#                 'extraction_strategy': strategy,
#                 'content_type': content_type,
#                 'word_count': len(plain_text.split())
#             }

#         except Exception as e:
#             print(f"⚠️  Content extraction error: {e}")
#             return None

#     def _clean_text(self, text: str) -> str:
#         """Clean extracted text."""
#         # Split into lines and clean each
#         lines = text.split('\n')
#         cleaned_lines = []

#         for line in lines:
#             line = re.sub(r'\s+', ' ', line).strip()
#             if len(line) > 10:  # Only keep substantial lines
#                 cleaned_lines.append(line)

#         text = '\n\n'.join(cleaned_lines)

#         # Remove noise patterns
#         noise_patterns = [
#             r'Skip to content',
#             r'JavaScript disabled',
#             r'Cookie (policy|notice|consent)',
#             r'Accept cookies',
#             r'\[\s*\]', r'\(\s*\)',
#         ]
#         for pattern in noise_patterns:
#             text = re.sub(pattern, '', text, flags=re.IGNORECASE)

#         # Normalize whitespace
#         text = re.sub(r'\n{3,}', '\n\n', text)
#         return text.strip()

#     def _detect_page_type(self, url: str, text: str) -> str:
#         """Detect page type."""
#         url_lower = url.lower()

#         if any(x in url_lower for x in ['/product', '/item', '/shop', '/store']):
#             return 'product'
#         if any(x in url_lower for x in ['/blog', '/article', '/post', '/news']):
#             return 'article'
#         if any(x in url_lower for x in ['/about', '/contact', '/team']):
#             return 'about'
#         if any(x in url_lower for x in ['/service', '/feature', '/solution']):
#             return 'service'
#         if '/faq' in url_lower:
#             return 'faq'

#         return 'general'

#     async def _extract_links(self, page: Page) -> List[str]:
#         """Extract valid links from page."""
#         links = await page.eval_on_selector_all(
#             'a[href]',
#             '(elements) => elements.map(e => e.href)'
#         )

#         valid_links = []
#         for link in links:
#             parsed = urlparse(link)

#             # Only same domain
#             if parsed.netloc != self.domain:
#                 continue

#             # Skip unwanted extensions
#             if parsed.path.lower().endswith(self.unwanted_extensions):
#                 continue

#             # Skip anchors
#             clean_url = link.split('#')[0]

#             # Skip patterns
#             skip_patterns = [
#                 r'/login', r'/signin', r'/signup', r'/register',
#                 r'/cart', r'/checkout', r'/account',
#                 r'/search\?', r'/tag/', r'/category/'
#             ]

#             if any(re.search(pattern, clean_url.lower()) for pattern in skip_patterns):
#                 continue

#             valid_links.append(clean_url)

#         return list(set(valid_links))[:20]  # Limit to 20 new links per page

#     def _save_results(self):
#         """Save results to file."""
#         os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

#         with open(self.output_file, 'w', encoding='utf-8') as f:
#             json.dump(self.results, f, indent=2, ensure_ascii=False)

#         # Save stats
#         stats_file = self.output_file.replace('.json', '_stats.json')
#         with open(stats_file, 'w', encoding='utf-8') as f:
#             json.dump({
#                 'domain': self.domain,
#                 'start_url': self.start_url,
#                 'statistics': self.stats,
#                 'total_pages_saved': len(self.results)
#             }, f, indent=2)

#         print(f"\n{'='*60}")
#         print(f"🎉 SCRAPING COMPLETE")
#         print(f"{'='*60}")
#         print(f"✅ Successfully scraped: {self.stats['successful']} pages")
#         print(f"⚠️  Skipped (low content): {self.stats['skipped_content']} pages")
#         print(f"❌ Errors: {self.stats['errors']} pages")
#         print(f"📊 Total attempted: {self.stats['total_attempted']} pages")
#         print(f"💾 Saved to: {self.output_file}")
#         print(f"{'='*60}\n")


# async def main():
#     parser = argparse.ArgumentParser(description='Playwright Web Scraper for JavaScript sites')
#     parser.add_argument('url', help='Starting URL to scrape')
#     parser.add_argument('output', help='Output JSON file path')
#     parser.add_argument('--max-pages', type=int, default=50, help='Maximum pages to scrape')

#     args = parser.parse_args()

#     scraper = PlaywrightScraper(args.url, args.output, args.max_pages)
#     await scraper.scrape()


# if __name__ == '__main__':
#     asyncio.run(main())


"""
Enhanced Universal Web Scraper with Intelligent Content Extraction
Works on any website including SPAs, React, Next.js, etc.
"""

import asyncio
import json
import os
import re
import argparse
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
from typing import List, Dict, Set, Optional
from datetime import datetime


class IntelligentContentExtractor:
    """
    Intelligent content extraction that adapts to different website structures.
    """

    # Content selectors ordered by priority
    CONTENT_SELECTORS = [
        # Semantic HTML5
        ('main', 'semantic_main'),
        ('article', 'semantic_article'),
        ('[role="main"]', 'aria_main'),

        # Common CMS patterns
        ('.content-area', 'cms_content_area'),
        ('.post-content', 'cms_post_content'),
        ('.entry-content', 'cms_entry_content'),
        ('.article-content', 'cms_article_content'),

        # Framework-specific
        ('#root', 'react_root'),
        ('#app', 'vue_app'),
        ('#__next', 'nextjs_root'),
        ('#___gatsby', 'gatsby_root'),

        # Generic content containers
        ('.main-content', 'generic_main'),
        ('.page-content', 'generic_page'),
        ('#content', 'generic_content'),
        ('.container .content', 'generic_container'),
    ]

    # Elements to remove
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
        """
        Extract content using multiple strategies with fallback.
        """
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

            # Try content extraction strategies
            main_content, strategy = cls._extract_main_content(soup)

            if not main_content:
                return None

            # Extract structured data
            headings = cls._extract_headings(soup)
            plain_text = cls._clean_text(main_content.get_text())

            # Quality check
            if len(plain_text) < 100:
                return None

            # Detect page type and content characteristics
            page_type = cls._detect_page_type(url, plain_text, soup)
            content_quality = cls._assess_content_quality(plain_text, headings)

            return {
                'url': url,
                'title': title,
                'content': plain_text,
                'meta_description': meta_description,
                'headings': headings,
                'extraction_strategy': strategy,
                'content_type': page_type,
                'word_count': len(plain_text.split()),
                'quality_score': content_quality,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"⚠️ Content extraction error for {url}: {e}")
            return None

    @staticmethod
    async def _extract_title(page: Page, soup: BeautifulSoup) -> str:
        """Extract page title using multiple strategies."""
        # Try playwright's title
        title = await page.title()
        if title and len(title) > 3:
            return title.strip()

        # Try h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()

        # Try og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()

        # Try title tag
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()

        return "Untitled Page"

    @staticmethod
    def _extract_meta_description(soup: BeautifulSoup) -> str:
        """Extract meta description."""
        # Try meta description
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta and meta.get('content'):
            return meta['content'].strip()

        # Try og:description
        og_meta = soup.find('meta', attrs={'property': 'og:description'})
        if og_meta and og_meta.get('content'):
            return og_meta['content'].strip()

        return ""

    @classmethod
    def _extract_main_content(cls, soup: BeautifulSoup) -> tuple[Optional[any], str]:
        """
        Extract main content using priority-based selector matching.
        Returns (content_element, strategy_name)
        """
        # Try each selector in order
        for selector, strategy in cls.CONTENT_SELECTORS:
            try:
                elements = soup.select(selector)

                # Find the element with most text
                best_element = None
                max_length = 0

                for element in elements:
                    text_length = len(element.get_text(strip=True))
                    if text_length > max_length and text_length > 200:
                        max_length = text_length
                        best_element = element

                if best_element:
                    return best_element, strategy
            except:
                continue

        # Fallback to body
        body = soup.find('body')
        if body:
            return body, 'fallback_body'

        return None, 'failed'

    @staticmethod
    def _extract_headings(soup: BeautifulSoup, max_headings: int = 15) -> List[str]:
        """Extract meaningful headings."""
        headings = []

        for tag in ['h1', 'h2', 'h3']:
            for heading in soup.find_all(tag):
                text = heading.get_text().strip()
                # Filter out noise
                if text and len(text) > 3 and len(text) < 200:
                    if not any(noise in text.lower() for noise in ['menu', 'navigation', 'skip to']):
                        headings.append(text)

        return headings[:max_headings]

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean and normalize extracted text."""
        # Split into lines
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            # Normalize whitespace
            line = re.sub(r'\s+', ' ', line).strip()

            # Skip very short lines (likely noise)
            if len(line) < 15:
                continue

            # Skip lines that are just numbers or symbols
            if re.match(r'^[\d\s\-\.\(\)]+$', line):
                continue

            cleaned_lines.append(line)

        # Join with paragraph breaks
        text = '\n\n'.join(cleaned_lines)

        # Remove common noise patterns
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

        # Normalize multiple line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    @staticmethod
    def _detect_page_type(url: str, text: str, soup: BeautifulSoup) -> str:
        """Detect page type for better categorization."""
        url_lower = url.lower()
        text_lower = text.lower()

        # URL-based detection
        url_patterns = {
            'product': ['/product', '/item', '/shop', '/store', '/buy'],
            'blog': ['/blog', '/article', '/post', '/news', '/story'],
            'about': ['/about', '/who-we-are', '/our-story', '/company'],
            'contact': ['/contact', '/get-in-touch', '/reach-us'],
            'service': ['/service', '/services', '/what-we-do', '/solution'],
            'faq': ['/faq', '/help', '/support', '/questions'],
            'pricing': ['/pricing', '/plans', '/packages'],
            'career': ['/career', '/jobs', '/hiring', '/join-us'],
        }

        for page_type, patterns in url_patterns.items():
            if any(pattern in url_lower for pattern in patterns):
                return page_type

        # Content-based detection
        if soup.find('form') and any(word in text_lower for word in ['email', 'message', 'contact']):
            return 'contact'

        if re.search(r'\$\s*\d+|price|pricing|cost', text_lower):
            return 'pricing'

        if len(text.split()) > 500 and len(soup.find_all(['p'])) > 5:
            return 'article'

        return 'general'

    @staticmethod
    def _assess_content_quality(text: str, headings: List[str]) -> float:
        """
        Assess content quality (0-1 score).
        Higher score = better quality content.
        """
        score = 0.0

        # Word count (more words = better, up to a point)
        word_count = len(text.split())
        if word_count > 100:
            score += min(word_count / 1000, 0.3)

        # Has meaningful headings
        if len(headings) >= 2:
            score += 0.2

        # Paragraph structure
        paragraphs = text.split('\n\n')
        if len(paragraphs) >= 3:
            score += 0.2

        # Not too repetitive
        unique_words = len(set(text.lower().split()))
        total_words = len(text.split())
        if total_words > 0:
            uniqueness = unique_words / total_words
            score += uniqueness * 0.3

        return min(score, 1.0)


class SmartLinkExtractor:
    """Intelligent link extraction with filtering and prioritization."""

    SKIP_PATTERNS = [
        r'/login', r'/signin', r'/signup', r'/register', r'/auth',
        r'/cart', r'/checkout', r'/account', r'/profile',
        r'/search\?', r'/tag/', r'/category/', r'/author/',
        r'/feed', r'/rss', r'/api/', r'/download',
        r'\.pdf$', r'\.jpg$', r'\.png$', r'\.gif$',
        r'\.mp4$', r'\.mp3$', r'\.zip$', r'\.doc',
    ]

    PRIORITY_PATTERNS = [
        r'/about', r'/service', r'/product', r'/solution',
        r'/pricing', r'/contact', r'/faq', r'/help'
    ]

    @classmethod
    async def extract_links(cls, page: Page, base_url: str, domain: str) -> List[str]:
        """Extract and prioritize valid links."""
        try:
            # Extract all links
            raw_links = await page.eval_on_selector_all(
                'a[href]',
                '(elements) => elements.map(e => ({ href: e.href, text: e.innerText }))'
            )

            valid_links = []
            priority_links = []

            for link_data in raw_links:
                href = link_data.get('href', '')
                text = link_data.get('text', '').lower()

                parsed = urlparse(href)

                # Must be same domain
                if parsed.netloc != domain:
                    continue

                # Remove anchor
                clean_url = href.split('#')[0]

                # Skip patterns
                if any(re.search(pattern, clean_url.lower()) for pattern in cls.SKIP_PATTERNS):
                    continue

                # Check if priority
                is_priority = any(re.search(pattern, clean_url.lower()) for pattern in cls.PRIORITY_PATTERNS)

                if is_priority:
                    priority_links.append(clean_url)
                else:
                    valid_links.append(clean_url)

            # Combine: priority links first, then others
            all_links = list(dict.fromkeys(priority_links + valid_links))  # Remove duplicates, preserve order

            return all_links[:30]  # Limit to 30 links per page

        except Exception as e:
            print(f"⚠️ Link extraction error: {e}")
            return []


class UniversalWebScraper:
    """
    Universal web scraper that adapts to any website structure.
    """

    def __init__(
        self,
        start_url: str,
        output_file: str,
        max_pages: int = 50,
        min_quality_score: float = 0.3
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
            'avg_quality': 0.0
        }

        self.content_extractor = IntelligentContentExtractor()
        self.link_extractor = SmartLinkExtractor()

    async def scrape(self):
        """Main scraping orchestration."""
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            # Enable JavaScript
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            self._print_header()

            # Scraping loop
            while self.queue and len(self.results) < self.max_pages:
                url = self.queue.pop(0)

                if url in self.visited_urls:
                    continue

                self.visited_urls.add(url)
                self.stats['total_attempted'] += 1

                await self._scrape_page(context, url)

            await browser.close()

            # Save results and stats
            self._save_results()

    async def _scrape_page(self, context, url: str):
        """Scrape a single page."""
        page = None
        try:
            page = await context.new_page()

            # Navigate with timeout and wait for content
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(2000)  # Additional wait for dynamic content

            # Extract content
            content_data = await self.content_extractor.extract_content(page, url)

            if content_data:
                quality_score = content_data.get('quality_score', 0)

                if quality_score >= self.min_quality_score:
                    self.results.append(content_data)
                    self.stats['successful'] += 1
                    self.stats['avg_quality'] += quality_score

                    print(f"✅ [{len(self.results)}/{self.max_pages}] {url}")
                    print(f"   📝 {content_data['word_count']} words | Quality: {quality_score:.2f} | {content_data['content_type']}")

                    # Extract new links
                    new_links = await self.link_extractor.extract_links(page, url, self.domain)
                    for link in new_links:
                        if link not in self.visited_urls and link not in self.queue:
                            self.queue.append(link)
                else:
                    self.stats['low_quality'] += 1
                    print(f"⚠️ Low quality (score: {quality_score:.2f}): {url}")
            else:
                self.stats['low_quality'] += 1
                print(f"⚠️ No content extracted: {url}")

        except Exception as e:
            self.stats['errors'] += 1
            print(f"❌ Error: {url} - {str(e)[:100]}")
        finally:
            if page:
                await page.close()

    def _print_header(self):
        """Print scraper header."""
        print("\n" + "="*70)
        print("🚀 Enhanced Universal Web Scraper")
        print("="*70)
        print(f"🌐 Target: {self.start_url}")
        print(f"📊 Domain: {self.domain}")
        print(f"📄 Max pages: {self.max_pages}")
        print(f"⭐ Min quality: {self.min_quality_score}")
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
            'quality_threshold': self.min_quality_score
        }

        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, indent=2)

        # Print summary
        print("\n" + "="*70)
        print("🎉 SCRAPING COMPLETE")
        print("="*70)
        print(f"✅ Successfully scraped: {self.stats['successful']} pages")
        print(f"📊 Average quality score: {self.stats['avg_quality']:.2f}")
        print(f"⚠️  Low quality/no content: {self.stats['low_quality']} pages")
        print(f"❌ Errors: {self.stats['errors']} pages")
        print(f"📈 Total attempted: {self.stats['total_attempted']} pages")
        print(f"💾 Saved to: {self.output_file}")
        print(f"📋 Stats saved to: {stats_file}")
        print("="*70 + "\n")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(
        description='Enhanced Universal Web Scraper - Works on any website'
    )
    parser.add_argument(
        'url',
        help='Starting URL to scrape'
    )
    parser.add_argument(
        'output',
        help='Output JSON file path'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=50,
        help='Maximum pages to scrape (default: 50)'
    )
    parser.add_argument(
        '--min-quality',
        type=float,
        default=0.3,
        help='Minimum quality score (0-1, default: 0.3)'
    )

    args = parser.parse_args()

    scraper = UniversalWebScraper(
        start_url=args.url,
        output_file=args.output,
        max_pages=args.max_pages,
        min_quality_score=args.min_quality
    )

    await scraper.scrape()


if __name__ == '__main__':
    asyncio.run(main())
