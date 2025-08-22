## updated thing with endpoints display
# 
# 
# import scrapy
# from urllib.parse import urljoin, urlparse
# from w3lib.html import remove_tags_with_content, remove_tags, replace_entities, replace_escape_chars
# import json
# import os
# import re

# class WebsiteSpider(scrapy.Spider):
#     name = 'website_scrap'

#     def __init__(self, allowed_domain='', start_url='', *args, **kwargs):
#         super(WebsiteSpider, self).__init__(*args, **kwargs)
#         self.allowed_domain = allowed_domain.strip().lower()
#         self.allowed_domains = [self.allowed_domain]  # For Scrapy filtering
#         self.start_urls = [start_url]
#         self.unwanted_extensions = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx', '.zip')
#         self.results = []       # Store full data
#         self.visited_urls = set()  # Prevent re-visiting

#     def parse(self, response):
#         # Only process HTML
#         if 'text/html' not in response.headers.get('Content-Type', b'').decode():
#             return

#         parsed = urlparse(response.url)
#         # Skip subdomains
#         if parsed.hostname != self.allowed_domain:
#             return

#         if response.url in self.visited_urls:
#             return
#         self.visited_urls.add(response.url)

#         # Get page title
#         title = response.css('title::text').get(default='').strip()

#         # Extract and clean body HTML
#         body_html = response.css('body').get()
#         plain_text = ""
#         if body_html:
#             clean_html = remove_tags_with_content(body_html, ('script', 'style', 'noscript', 'iframe', 'nav', 'footer'))

#             # Add spaces after block-level tags for readability
#             for tag in ['</p>', '</div>', '</li>', '<br>', '</h1>', '</h2>', '</h3>', '</h4>']:
#                 clean_html = clean_html.replace(tag, tag + ' ')

#             plain_text = remove_tags(clean_html)
#             plain_text = replace_entities(plain_text)
#             plain_text = replace_escape_chars(plain_text)
#             plain_text = re.sub(r'\s+', ' ', plain_text).strip()

#         # Save result (even if no content, we keep endpoint list)
#         self.results.append({
#             'url': response.url,
#             'title': title,
#             'content': plain_text
#         })

#         # Follow internal links
#         for href in response.css('a::attr(href)').getall():
#             next_url = urljoin(response.url, href)
#             parsed_link = urlparse(next_url)

#             # Skip unwanted files
#             if parsed_link.path.lower().endswith(self.unwanted_extensions):
#                 continue

#             # Follow only exact main domain (no subdomains)
#             if parsed_link.hostname == self.allowed_domain:
#                 yield scrapy.Request(next_url, callback=self.parse)

#     def closed(self, reason):
#         # Save JSON output
#         output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
#         os.makedirs(output_dir, exist_ok=True)

#         with open(os.path.join(output_dir, 'website_content.json'), 'w', encoding='utf-8') as f:
#             json.dump(self.results, f, indent=2, ensure_ascii=False)


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
        self.unwanted_extensions = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx', '.zip')
        self.results = []
        self.visited_urls = set()
        # NEW: per-client output target
        self.output_file = output_file  # absolute path recommended

    def parse(self, response):
        if 'text/html' not in response.headers.get('Content-Type', b'').decode():
            return

        parsed = urlparse(response.url)
        if parsed.hostname and not parsed.hostname.endswith(self.allowed_domain):
            return

        if response.url in self.visited_urls:
            return
        self.visited_urls.add(response.url)

        title = response.css('title::text').get(default='').strip()

        body_html = response.css('body').get()
        plain_text = ""
        if body_html:
            clean_html = remove_tags_with_content(body_html, ('script', 'style', 'noscript', 'iframe', 'nav', 'footer'))
            for tag in ['</p>', '</div>', '</li>', '<br>', '</h1>', '</h2>', '</h3>', '</h4>']:
                clean_html = clean_html.replace(tag, tag + ' ')
            plain_text = remove_tags(clean_html)
            plain_text = replace_entities(plain_text)
            plain_text = replace_escape_chars(plain_text)
            plain_text = re.sub(r'\s+', ' ', plain_text).strip()

        self.results.append({'url': response.url, 'title': title, 'content': plain_text})

        for href in response.css('a::attr(href)').getall():
            next_url = urljoin(response.url, href)
            parsed_link = urlparse(next_url)
            if parsed_link.path.lower().endswith(self.unwanted_extensions):
                continue
            if parsed_link.hostname == self.allowed_domain:
                yield scrapy.Request(next_url, callback=self.parse)

    def closed(self, reason):
        # Save JSON where backend asked us to
        if not self.output_file:
            # fallback to old path if not provided
            output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
            os.makedirs(output_dir, exist_ok=True)
            self.output_file = os.path.join(output_dir, 'website_content_new.json')

        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

