import sys
import os
import streamlit as st

# Add the inner 'crawler' folder to system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'crawler')))

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from crawler.spiders.website_scrap import WebsiteSpider  # Import Spider Correctly
import pandas as pd

st.title("🌐 Website Crawler UI")

allowed_domain = st.text_input("Enter Allowed Domain", "sjcetpalai.ac.in")
start_url = st.text_input("Enter Start URL", "https://sjcetpalai.ac.in/")

if st.button("🚀 Start Crawling"):
    if not allowed_domain or not start_url:
        st.error("Please provide both Domain and Start URL.")
    else:
        st.info("Crawling Started... Please wait.")

        # Run Scrapy Programmatically
        process = CrawlerProcess(get_project_settings())
        process.crawl(WebsiteSpider, allowed_domain=allowed_domain, start_url=start_url)
        process.start()  # This will block until the crawling finishes

        st.success("✅ Crawling Completed!")

        # Load and Show Output Data
        try:
            df = pd.read_json(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'crawler','crawler', 'output', 'website_content.json')))
            st.write(f"Scraped {len(df)} pages:")
            st.dataframe(df.head())
        except Exception as e:
            st.error(f"Error loading output: {e}")
