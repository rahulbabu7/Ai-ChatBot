"""
Enhanced Universal Web Scraper with Better Error Handling
"""

import asyncio
import json
import os
import re
import argparse
import traceback
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from typing import List, Dict, Set, Optional
from datetime import datetime


class IntelligentContentExtractor:
    """Intelligent content extraction that adapts to different website structures."""

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
        ('.container', 'generic_container'),  # More generic fallback
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
        """Extract content using multiple strategies with fallback."""
        try:
            # Get HTML
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
                print(f"⚠️  No main content found for {url}, using body fallback")
                # Last resort: use body
                main_content = soup.find('body')
                strategy = 'fallback_body'

            if not main_content:
                return None

            # Extract structured data
            headings = cls._extract_headings(soup)
            plain_text = cls._clean_text(main_content.get_text())

            # Relaxed quality check - accept pages with at least 50 characters
            if len(plain_text) < 50:
                print(f"⚠️  Content too short ({len(plain_text)} chars) for {url}")
                return None

            # Detect page type
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
            print(f"❌ Content extraction error for {url}: {e}")
            traceback.print_exc()
            return None

    @staticmethod
    async def _extract_title(page: Page, soup: BeautifulSoup) -> str:
        """Extract page title using multiple strategies."""
        try:
            # Try playwright's title
            title = await page.title()
            if title and len(title) > 3:
                return title.strip()
        except:
            pass

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
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta and meta.get('content'):
            return meta['content'].strip()

        og_meta = soup.find('meta', attrs={'property': 'og:description'})
        if og_meta and og_meta.get('content'):
            return og_meta['content'].strip()

        return ""

    @classmethod
    def _extract_main_content(cls, soup: BeautifulSoup) -> tuple[Optional[any], str]:
        """Extract main content using priority-based selector matching."""
        for selector, strategy in cls.CONTENT_SELECTORS:
            try:
                elements = soup.select(selector)
                best_element = None
                max_length = 0

                for element in elements:
                    text_length = len(element.get_text(strip=True))
                    if text_length > max_length and text_length > 100:  # Lowered threshold
                        max_length = text_length
                        best_element = element

                if best_element:
                    return best_element, strategy
            except Exception as e:
                print(f"⚠️  Selector '{selector}' failed: {e}")
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
                if text and 3 < len(text) < 200:
                    if not any(noise in text.lower() for noise in ['menu', 'navigation', 'skip to']):
                        headings.append(text)
        return headings[:max_headings]

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean and normalize extracted text."""
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = re.sub(r'\s+', ' ', line).strip()
            if len(line) >= 10:  # Lowered from 15
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
            'pricing': ['/pricing', '/plans', '/packages'],
            'career': ['/career', '/jobs', '/hiring', '/join-us'],
        }

        for page_type, patterns in url_patterns.items():
            if any(pattern in url_lower for pattern in patterns):
                return page_type

        if soup.find('form') and any(word in text_lower for word in ['email', 'message', 'contact']):
            return 'contact'

        if re.search(r'\$\s*\d+|price|pricing|cost', text_lower):
            return 'pricing'

        if len(text.split()) > 500 and len(soup.find_all(['p'])) > 5:
            return 'article'

        return 'general'

    @staticmethod
    def _assess_content_quality(text: str, headings: List[str]) -> float:
        """Assess content quality (0-1 score)."""
        score = 0.0

        word_count = len(text.split())
        if word_count > 50:  # Lowered threshold
            score += min(word_count / 1000, 0.3)

        if len(headings) >= 1:  # Lowered from 2
            score += 0.2

        paragraphs = text.split('\n\n')
        if len(paragraphs) >= 2:  # Lowered from 3
            score += 0.2

        unique_words = len(set(text.lower().split()))
        total_words = len(text.split())
        if total_words > 0:
            uniqueness = unique_words / total_words
            score += uniqueness * 0.3

        return min(score, 1.0)


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
        r'/pricing', r'/contact', r'/faq', r'/help'
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

                # Must be same domain
                if parsed.netloc and parsed.netloc != domain:
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

            # Combine and deduplicate
            all_links = list(dict.fromkeys(priority_links + valid_links))
            return all_links[:30]

        except Exception as e:
            print(f"⚠️  Link extraction error: {e}")
            return []


class UniversalWebScraper:
    """Universal web scraper that adapts to any website structure."""

    def __init__(
        self,
        start_url: str,
        output_file: str,
        max_pages: int = 50,
        min_quality_score: float = 0.2  # Lowered from 0.3
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
            'error_details': []
        }

        self.content_extractor = IntelligentContentExtractor()
        self.link_extractor = SmartLinkExtractor()

    async def scrape(self):
        """Main scraping orchestration."""
        print(f"\n🔧 Starting Playwright browser...")

        try:
            async with async_playwright() as p:
                # Launch browser with more permissive settings
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

                # Scraping loop
                while self.queue and len(self.results) < self.max_pages:
                    url = self.queue.pop(0)

                    if url in self.visited_urls:
                        continue

                    self.visited_urls.add(url)
                    self.stats['total_attempted'] += 1

                    await self._scrape_page(context, url)

                await browser.close()

                # Save results
                self._save_results()

                return 0  # Success

        except Exception as e:
            print(f"\n❌ FATAL ERROR: {e}")
            traceback.print_exc()
            self._save_results()  # Save whatever we got
            return 1  # Failure

    async def _scrape_page(self, context, url: str):
        """Scrape a single page with comprehensive error handling."""
        page = None
        try:
            page = await context.new_page()

            # Navigate with longer timeout
            print(f"🌐 Loading: {url}")
            await page.goto(url, wait_until='domcontentloaded', timeout=45000)

            # Wait for content to load
            await page.wait_for_timeout(3000)

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
        print("🎉 SCRAPING COMPLETE" if self.stats['successful'] > 0 else "⚠️  SCRAPING FINISHED WITH ISSUES")
        print("="*70)
        print(f"✅ Successfully scraped: {self.stats['successful']} pages")
        print(f"📊 Average quality score: {self.stats['avg_quality']:.2f}")
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


async def main():
    parser = argparse.ArgumentParser(
        description='Enhanced Universal Web Scraper - Works on any website'
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
