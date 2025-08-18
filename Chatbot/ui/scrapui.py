# import sys
# import os
# import streamlit as st

# # Add the inner 'crawler' folder to system path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'crawler')))

# from scrapy.crawler import CrawlerProcess
# from scrapy.utils.project import get_project_settings
# from crawler.spiders.website_scrap import WebsiteSpider  # Import Spider Correctly
# import pandas as pd

# st.title("🌐 Website Crawler UI")

# allowed_domain = st.text_input("Enter Allowed Domain", "sjcetpalai.ac.in")
# start_url = st.text_input("Enter Start URL", "https://sjcetpalai.ac.in/")

# if st.button("🚀 Start Crawling"):
#     if not allowed_domain or not start_url:
#         st.error("Please provide both Domain and Start URL.")
#     else:
#         st.info("Crawling Started... Please wait.")

#         # Run Scrapy Programmatically
#         process = CrawlerProcess(get_project_settings())
#         process.crawl(WebsiteSpider, allowed_domain=allowed_domain, start_url=start_url)
#         process.start()  # This will block until the crawling finishes

#         st.success("✅ Crawling Completed!")

#         # Load and Show Output Data
#         try:
#             df = pd.read_json(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'crawler','crawler', 'output', 'website_content.json')))
#             st.write(f"Scraped {len(df)} pages:")
#             st.dataframe(df.head())
#         except Exception as e:
#             st.error(f"Error loading output: {e}")


## updated thing with endpoints display
# 
# # 
import sys
import os
import streamlit as st
import pandas as pd
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# ✅ Add the main crawler folder to sys.path
crawler_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'crawler'))
sys.path.append(crawler_path)

from crawler.spiders.website_scrap import WebsiteSpider  # Import your spider

# Path to JSON output file
output_file = os.path.join(crawler_path,'crawler','output', 'website_content.json')

# Streamlit Page Setup
st.set_page_config(page_title="Website Crawler", layout="wide")
st.title("🌐 Website Crawler UI")

# Inputs
allowed_domain = st.text_input("Enter Allowed Domain", "sjcetpalai.ac.in")
start_url = st.text_input("Enter Start URL", "https://sjcetpalai.ac.in/")

if st.button("🚀 Start Crawling"):
    if not allowed_domain.strip() or not start_url.strip():
        st.error("❌ Please provide both Domain and Start URL.")
    else:
        st.info("⏳ Crawling Started... Please wait...")

        # Delete old output if exists
        if os.path.exists(output_file):
            os.remove(output_file)

        # Run Scrapy Programmatically
        process = CrawlerProcess(get_project_settings())
        process.crawl(WebsiteSpider, allowed_domain=allowed_domain.strip(), start_url=start_url.strip())
        process.start()

        st.success("✅ Crawling Completed!")

        # Load and Display Data
        if os.path.exists(output_file):
            try:
                df = pd.read_json(output_file)

                tab1, tab2 = st.tabs(["🔗 Endpoints", "📄 Full Page Data"])

                with tab1:
                    st.write(f"Found **{len(df)}** unique endpoints.")
                    st.dataframe(df[["url"]])

                with tab2:
                    st.write("Scraped Page Data:")
                    st.dataframe(df)
            except Exception as e:
                st.error(f"Error loading output: {e}")
        else:
            st.warning("⚠ No output file found. The spider may not have saved any data.")
