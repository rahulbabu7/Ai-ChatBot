import scrapy
from urllib.parse import urljoin, urlparse
from w3lib.html import remove_tags_with_content, remove_tags, replace_entities, replace_escape_chars
import json
import os
import re


class WebsiteSpider(scrapy.Spider):
    name = 'website_scrap'
    
    def __init__(self, allowed_domain='', start_url='', output_file='', *args, **kwargs):
        super(WebsiteSpider, self).__init__(*args, **kwargs)
        self.allowed_domain = allowed_domain.strip().lower()
        self.allowed_domains = [self.allowed_domain]
        self.start_urls = [start_url]
        self.unwanted_extensions = (
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx', 
            '.zip', '.mp4', '.mp3', '.avi', '.mov', '.xlsx', '.ppt'
        )
        self.results = []
        self.visited_urls = set()
        self.output_file = output_file
    
    def parse(self, response):
        """Enhanced parsing with better content extraction."""
        # Only process HTML pages
        if 'text/html' not in response.headers.get('Content-Type', b'').decode():
            return
        
        # Check domain
        parsed = urlparse(response.url)
        if parsed.hostname and not parsed.hostname.endswith(self.allowed_domain):
            return
        
        # Avoid duplicates
        if response.url in self.visited_urls:
            return
        self.visited_urls.add(response.url)
        
        # Extract title
        title = response.css('title::text').get(default='').strip()
        
        # Extract meta description (useful context)
        meta_desc = response.css('meta[name="description"]::attr(content)').get()
        if not meta_desc:
            meta_desc = response.css('meta[property="og:description"]::attr(content)').get()
        meta_desc = meta_desc.strip() if meta_desc else ""
        
        # Extract main headings for additional context
        headings = []
        for h in ['h1', 'h2', 'h3']:
            headings.extend(response.css(f'{h}::text').getall())
        headings_text = ' | '.join([h.strip() for h in headings if h.strip()])
        
        # Try to extract main content area first (better quality)
        main_content = response.css('main, article, .content, #content, .main-content, #main').get()
        
        # Fallback to body if no main content found
        if not main_content:
            main_content = response.css('body').get()
        
        plain_text = ""
        if main_content:
            # Remove unwanted elements (more comprehensive)
            clean_html = remove_tags_with_content(
                main_content, 
                ('script', 'style', 'noscript', 'iframe', 'nav', 'footer', 
                 'header', 'aside', 'form', 'button', 'svg', 'canvas')
            )
            
            # Add spacing after block elements for better readability
            for tag in ['</p>', '</div>', '</li>', '<br>', '</h1>', '</h2>', 
                       '</h3>', '</h4>', '</h5>', '</h6>', '</section>', '</article>']:
                clean_html = clean_html.replace(tag, tag + ' ')
            
            # Remove tags and clean
            plain_text = remove_tags(clean_html)
            plain_text = replace_entities(plain_text)
            plain_text = replace_escape_chars(plain_text)
            
            # Better whitespace normalization
            plain_text = re.sub(r'\s+', ' ', plain_text).strip()
            
            # Remove common navigation phrases that add noise
            noise_patterns = [
                r'Skip to (main )?content',
                r'JavaScript (is )?disabled',
                r'Cookie (policy|notice|consent)',
                r'Accept (all )?cookies?',
            ]
            for pattern in noise_patterns:
                plain_text = re.sub(pattern, '', plain_text, flags=re.IGNORECASE)
        
        # Only save if we have meaningful content
        if plain_text and len(plain_text.strip()) > 50:
            self.results.append({
                'url': response.url,
                'title': title,
                'content': plain_text,
                'meta_description': meta_desc,
                'headings': headings_text
            })
            self.logger.info(f"✅ Scraped: {response.url} ({len(plain_text)} chars)")
        else:
            self.logger.warning(f"⚠️ Skipped (insufficient content): {response.url}")
        
        # Follow links
        for href in response.css('a::attr(href)').getall():
            next_url = urljoin(response.url, href)
            parsed_link = urlparse(next_url)
            
            # Skip unwanted file types
            if parsed_link.path.lower().endswith(self.unwanted_extensions):
                continue
            
            # Skip anchors on same page
            if parsed_link.fragment and parsed_link.path == parsed.path:
                continue
            
            # Only follow links within allowed domain
            if parsed_link.hostname == self.allowed_domain:
                yield scrapy.Request(next_url, callback=self.parse, errback=self.errback_httpbin)
    
    def errback_httpbin(self, failure):
        """Handle request failures gracefully."""
        self.logger.error(f"❌ Request failed: {failure.request.url}")
    
    def closed(self, reason):
        """Save results when spider closes."""
        if not self.output_file:
            output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
            os.makedirs(output_dir, exist_ok=True)
            self.output_file = os.path.join(output_dir, 'website_content_new.json')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        
        # Save results
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"🎉 Scraped {len(self.results)} pages")
        self.logger.info(f"💾 Saved to: {self.output_file}")