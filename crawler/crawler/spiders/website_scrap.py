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
#         self.allowed_domains = [allowed_domain]
#         self.start_urls = [start_url]
#         self.unwanted_extensions = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx', '.zip')
#         self.results = []

#     def parse(self, response):
#         if 'text/html' not in response.headers.get('Content-Type', b'').decode():
#             return

#         body_html = response.css('body').get()
#         clean_html = remove_tags_with_content(body_html, ('script', 'style', 'noscript', 'iframe'))

#         # Add space after block-level tags to avoid concatenation
#         block_tags = ['</p>', '</div>', '</li>', '<br>', '</h1>', '</h2>', '</h3>', '</h4>']
#         for tag in block_tags:
#             clean_html = clean_html.replace(tag, tag + ' ')

#         plain_text = remove_tags(clean_html)
#         plain_text = replace_entities(plain_text)
#         plain_text = replace_escape_chars(plain_text)
#         plain_text = re.sub(r'\s+', ' ', plain_text).strip()

#         self.results.append({
#             'url': response.url,
#             'content': plain_text
#         })

#         for href in response.css('a::attr(href)').getall():
#             next_url = urljoin(response.url, href)
#             parsed_url = urlparse(next_url)

#             if parsed_url.path.lower().endswith(self.unwanted_extensions):
#                 continue

#             if self.allowed_domains[0] in parsed_url.netloc:
#                 yield scrapy.Request(next_url, callback=self.parse)

#     def closed(self, reason):
#         output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
#         os.makedirs(output_dir, exist_ok=True)
#         with open(os.path.join(output_dir, 'website_content.json'), 'w') as f:
#             json.dump(self.results, f, indent=2)


import scrapy
from urllib.parse import urljoin, urlparse
from w3lib.html import remove_tags_with_content, remove_tags, replace_entities, replace_escape_chars
import json
import os
import re

class WebsiteSpider(scrapy.Spider):
    name = 'website_scrap'

    def __init__(self, allowed_domain='', start_url='', *args, **kwargs):
        super(WebsiteSpider, self).__init__(*args, **kwargs)
        self.allowed_domains = [allowed_domain]
        self.start_urls = [start_url]
        self.unwanted_extensions = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx', '.zip')
        self.results = []

    def parse(self, response):
        if 'text/html' not in response.headers.get('Content-Type', b'').decode():
            return

        # Optional: grab title
        title = response.css('title::text').get(default='').strip()

        body_html = response.css('body').get()
        if not body_html:
            return

        # Clean unwanted tags
        clean_html = remove_tags_with_content(body_html, ('script', 'style', 'noscript', 'iframe', 'nav', 'footer'))

        # Add space after block-level tags
        block_tags = ['</p>', '</div>', '</li>', '<br>', '</h1>', '</h2>', '</h3>', '</h4>']
        for tag in block_tags:
            clean_html = clean_html.replace(tag, tag + ' ')

        plain_text = remove_tags(clean_html)
        plain_text = replace_entities(plain_text)
        plain_text = replace_escape_chars(plain_text)
        plain_text = re.sub(r'\s+', ' ', plain_text).strip()

        # 🚫 Skip near-empty or copyright-only pages
        if len(plain_text) < 100 or 'copyright' in plain_text.lower():
            return

        self.results.append({
            'url': response.url,
            'title': title,
            'content': plain_text
        })

        for href in response.css('a::attr(href)').getall():
            next_url = urljoin(response.url, href)
            parsed_url = urlparse(next_url)

            if parsed_url.path.lower().endswith(self.unwanted_extensions):
                continue

            if self.allowed_domains[0] in parsed_url.netloc:
                yield scrapy.Request(next_url, callback=self.parse)

    def closed(self, reason):
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, 'website_content.json'), 'w') as f:
            json.dump(self.results, f, indent=2)


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
#         self.allowed_domains = [allowed_domain]
#         self.start_urls = [start_url]
#         self.unwanted_extensions = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx', '.zip')
#         self.results = []

#     def parse(self, response):
#         if 'text/html' not in response.headers.get('Content-Type', b'').decode():
#             return

#         title = response.css('title::text').get(default='').strip()
#         body_html = response.css('body').get()
#         if not body_html:
#             return

#         # Clean HTML
#         clean_html = remove_tags_with_content(body_html, ('script', 'style', 'noscript', 'iframe', 'nav', 'footer'))
#         block_tags = ['</p>', '</div>', '</li>', '<br>', '</h1>', '</h2>', '</h3>', '</h4>']
#         for tag in block_tags:
#             clean_html = clean_html.replace(tag, tag + ' ')
#         plain_text = remove_tags(clean_html)
#         plain_text = replace_entities(plain_text)
#         plain_text = replace_escape_chars(plain_text)
#         plain_text = re.sub(r'\s+', ' ', plain_text).strip()

#         if len(plain_text) < 100 or 'copyright' in plain_text.lower():
#             return

#         structured_data = {
#             "url": response.url,
#             "title": title,
#             "fees": self.extract_fees(plain_text),
#             "bus_routes": self.extract_bus_routes(plain_text),
#             "contacts": self.extract_contacts(plain_text),
#             "resources": self.extract_resources(plain_text),
#             "committees": self.extract_committees(plain_text),
#             "raw_content": plain_text  # optional: for backup
#         }

#         self.results.append(structured_data)

#         for href in response.css('a::attr(href)').getall():
#             next_url = urljoin(response.url, href)
#             parsed_url = urlparse(next_url)
#             if parsed_url.path.lower().endswith(self.unwanted_extensions):
#                 continue
#             if self.allowed_domains[0] in parsed_url.netloc:
#                 yield scrapy.Request(next_url, callback=self.parse)

#     def extract_fees(self, text):
#         fee_pattern = re.findall(r'([A-Za-z \(\)\&]+(?:Fee|Charges|Deposit)[^\d]{0,10})(\d{1,3}(?:[,.\d]{0,10}))/-', text)
#         return [{"type": fee[0].strip(), "amount": fee[1].strip()} for fee in fee_pattern]

#     def extract_bus_routes(self, text):
#         route_pattern = re.findall(
#             r'SJCET - ([A-Za-z0-9 \(\)-]+)(Ms\.|Mr\.|Dr\.) ([A-Za-z. ]+)([A-Z]{2,4})?(\d{10})',
#             text
#         )
#         return [
#             {
#                 "route": "SJCET - " + r[0].strip(),
#                 "staff": r[1] + " " + r[2].strip(),
#                 "department": r[3] or "",
#                 "contact": r[4]
#             }
#             for r in route_pattern
#         ]

#     def extract_contacts(self, text):
#         contact_pattern = re.findall(r'(Mr\.|Ms\.|Dr\.) ([A-Za-z. ]+)[A-Z]{2,4}?(\d{10})', text)
#         return [
#             {
#                 "name": r[0] + " " + r[1].strip(),
#                 "contact": r[2]
#             }
#             for r in contact_pattern
#         ]

#     def extract_resources(self, text):
#         resource_pattern = re.findall(
#             r'(Elsevier|IEEE|EBSCO|DELNET|NDL|NPTEL)[^\n]*?((https?:\/\/|www\.)[^\s]+)',
#             text
#         )
#         return [
#             {
#                 "publisher": r[0],
#                 "url": r[1]
#             }
#             for r in resource_pattern
#         ]

#     def extract_committees(self, text):
#         committees = []
#         match = re.findall(r'(STEERING COMMITEE|TECHNICAL EXPERT COMMITEE|ORGANIZING COMMITTEE)', text)
#         for m in match:
#             committees.append({"name": m})
#         return committees

#     def closed(self, reason):
#         output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
#         os.makedirs(output_dir, exist_ok=True)
#         with open(os.path.join(output_dir, 'website_content.json'), 'w', encoding='utf-8') as f:
#             json.dump(self.results, f, indent=2, ensure_ascii=False)




# ###
# import scrapy
# from urllib.parse import urljoin, urlparse
# from w3lib.html import remove_tags_with_content, replace_escape_chars, replace_entities, remove_tags
# import re

# class WebsiteSpider(scrapy.Spider):
#     name = 'website_scrap'
#     allowed_domains = ['sjcetpalai.ac.in']
#     start_urls = ['https://sjcetpalai.ac.in/']
#     unwanted_extensions = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.doc', '.docx', '.zip')

#     def parse(self, response):
#         if 'text/html' not in response.headers.get('Content-Type', b'').decode():
#             return  # Skip non-HTML pages

#         body_html = response.css('body').get()

#         # Clean unwanted tags first
#         clean_html = remove_tags_with_content(body_html, ('script', 'style', 'noscript', 'iframe'))

#         # Ensure block-level tags are replaced with spaces or newlines
#         block_tags = ['</p>', '</div>', '</li>', '<br>', '</h1>', '</h2>', '</h3>', '</h4>']
#         for tag in block_tags:
#             clean_html = clean_html.replace(tag, tag + ' ')  # Add space after tag

#         # Now remove all remaining tags
#         plain_text = remove_tags(clean_html)

#         # Decode HTML entities (like &amp;)
#         plain_text = replace_entities(plain_text)
#         plain_text = replace_escape_chars(plain_text)

#         # Clean up extra whitespaces
#         plain_text = re.sub(r'\s+', ' ', plain_text).strip()

#         yield {
#             'url': response.url,
#             'content': plain_text
#         }

#         # Follow internal links, skip unwanted files
#         for href in response.css('a::attr(href)').getall():
#             next_url = urljoin(response.url, href)
#             parsed_url = urlparse(next_url)

#             if parsed_url.path.lower().endswith(self.unwanted_extensions):
#                 continue

#             if self.allowed_domains[0] in parsed_url.netloc:
#                 yield scrapy.Request(next_url, callback=self.parse)
###