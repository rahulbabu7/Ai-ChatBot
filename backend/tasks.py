# import os
# import sys
# import subprocess
# from celery import chain
# from celery.utils.log import get_task_logger

# from backend.celery_app import celery_app
# from backend.db import add_task, update_task

# # Add Chatbot/LLM path
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# CHATBOT_LLM_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/llm"))
# sys.path.append(CHATBOT_LLM_DIR)
# from llm_service import chat_with_model, explain_context

# logger = get_task_logger(__name__)

# CRAWLER_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/crawler"))
# CLIENTS_DIR = os.path.join(BASE_DIR, "client_data")
# os.makedirs(CLIENTS_DIR, exist_ok=True)


# def run_subprocess_sync(cmd: list, cwd: str = None):
#     result = subprocess.run(
#         cmd,
#         cwd=cwd,
#         capture_output=True,
#         text=True,
#         check=False,
#         timeout=3600,
#     )
#     return result.returncode, result.stdout, result.stderr


# @celery_app.task(bind=True)
# def crawl_website_task(self, client_id: str, allowed_domain: str, start_url: str):
#     task_id = self.request.id
#     add_task(task_id, client_id, "Crawl Website", status="queued")

#     logger.info(f"Starting crawl for client {client_id}, domain {allowed_domain}")
#     self.update_state(state="PROGRESS", meta={"progress": 10, "message": "Starting website crawl..."})
#     update_task(task_id, "running", "Starting crawl...")

#     client_dir = os.path.join(CLIENTS_DIR, client_id)
#     os.makedirs(client_dir, exist_ok=True)
#     output_file = os.path.join(client_dir, "website_content.json")

#     cmd = [
#         "scrapy",
#         "crawl",
#         "website_scrap",
#         "-a", f"allowed_domain={allowed_domain}",
#         "-a", f"start_url={start_url}",
#         "-a", f"output_file={output_file}",
#     ]

#     self.update_state(state="PROGRESS", meta={"progress": 50, "message": "Crawling website..."})
#     returncode, stdout, stderr = run_subprocess_sync(cmd, CRAWLER_DIR)

#     if returncode != 0:
#         update_task(task_id, "failed", stderr)
#         raise Exception(f"Crawling failed: {stderr}")

#     update_task(task_id, "completed", f"Crawled pages saved to {output_file}")
#     return {"client_id": client_id, "output_file": output_file}


# @celery_app.task(bind=True)
# def run_embeddings_task(self, prev_result):
#     task_id = self.request.id
#     client_id = prev_result["client_id"]
#     add_task(task_id, client_id, "Run Embeddings", status="queued")

#     logger.info(f"Starting embeddings for client {client_id}")
#     self.update_state(state="PROGRESS", meta={"progress": 10, "message": "Starting embeddings..."})
#     update_task(task_id, "running", "Generating embeddings...")

#     script_path = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/processing/embed_pipeline.py"))
#     cmd = [sys.executable, script_path, client_id]

#     self.update_state(state="PROGRESS", meta={"progress": 50, "message": "Processing embeddings..."})
#     returncode, stdout, stderr = run_subprocess_sync(cmd)

#     if returncode != 0:
#         update_task(task_id, "failed", stderr)
#         raise Exception(f"Embeddings failed: {stderr}")

#     update_task(task_id, "completed", "Embeddings generated successfully")
#     return {"client_id": client_id, "embeddings": "Generated and stored"}



# @celery_app.task(bind=True)
# def crawl_and_embed_pipeline(self, client_id: str, allowed_domain: str, start_url: str):
#     # This is the high-level pipeline
#     logger.info(f"Starting combined crawl+embed for client {client_id}")
#     pipeline = chain(
#         crawl_website_task.s(client_id, allowed_domain, start_url),
#         run_embeddings_task.s(),
#     )
#     result = pipeline.apply_async()
#     return {"chain_task_id": result.id}


import os
import sys
import subprocess
from celery import chain
from celery.utils.log import get_task_logger

from backend.celery_app import celery_app
from backend.db import add_task, update_task

# Add Chatbot/LLM path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHATBOT_LLM_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/llm"))
sys.path.append(CHATBOT_LLM_DIR)
from llm_service import chat_with_model, explain_context

logger = get_task_logger(__name__)

CRAWLER_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/crawler"))
CLIENTS_DIR = os.path.join(BASE_DIR, "client_data")
os.makedirs(CLIENTS_DIR, exist_ok=True)


def run_subprocess_sync(cmd: list, cwd: str = None):
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=3600,
    )
    return result.returncode, result.stdout, result.stderr


@celery_app.task(bind=True)
def crawl_website_task(self, client_id: str, allowed_domain: str, start_url: str):
    """Crawl a website and save JSON content."""
    task_id = self.request.id
    add_task(task_id, client_id, "Crawl Website", status="queued")

    logger.info(f"Starting crawl for client {client_id}, domain {allowed_domain}")
    self.update_state(state="PROGRESS", meta={"progress": 10, "message": "Starting website crawl..."})
    update_task(task_id, "running", "Starting crawl...")

    client_dir = os.path.join(CLIENTS_DIR, client_id)
    os.makedirs(client_dir, exist_ok=True)
    output_file = os.path.join(client_dir, "website_content.json")

    cmd = [
        "scrapy",
        "crawl",
        "website_scrap",
        "-a", f"allowed_domain={allowed_domain}",
        "-a", f"start_url={start_url}",
        "-a", f"output_file={output_file}",
    ]

    self.update_state(state="PROGRESS", meta={"progress": 50, "message": "Crawling website..."})
    returncode, stdout, stderr = run_subprocess_sync(cmd, CRAWLER_DIR)

    if returncode != 0:
        update_task(task_id, "failed", stderr)
        raise Exception(f"Crawling failed: {stderr}")

    update_task(task_id, "completed", f"Crawled pages saved to {output_file}")
    return {"client_id": client_id, "output_file": output_file, "source_type": "crawl"}


@celery_app.task(bind=True)
def run_embeddings_task(self, prev_result):
    """Run embeddings on crawled website or uploaded PDF."""
    task_id = self.request.id
    client_id = prev_result["client_id"]
    source_type = prev_result.get("source_type", "crawl")  # default to crawl

    add_task(task_id, client_id, "Run Embeddings", status="queued")
    logger.info(f"Starting embeddings for client {client_id} (source: {source_type})")
    self.update_state(state="PROGRESS", meta={"progress": 10, "message": "Starting embeddings..."})
    update_task(task_id, "running", "Generating embeddings...")

    script_path = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/processing/embed_pipeline.py"))
    cmd = [sys.executable, script_path, client_id, source_type]

    self.update_state(state="PROGRESS", meta={"progress": 50, "message": "Processing embeddings..."})
    returncode, stdout, stderr = run_subprocess_sync(cmd)

    if returncode != 0:
        update_task(task_id, "failed", stderr)
        raise Exception(f"Embeddings failed: {stderr}")

    update_task(task_id, "completed", "Embeddings generated successfully")
    return {"client_id": client_id, "embeddings": "Generated and stored", "source_type": source_type}


@celery_app.task(bind=True)
def crawl_and_embed_pipeline(self, client_id: str, allowed_domain: str, start_url: str):
    """High-level pipeline for crawling website + embeddings."""
    logger.info(f"Starting combined crawl+embed for client {client_id}")
    pipeline = chain(
        crawl_website_task.s(client_id, allowed_domain, start_url),
        run_embeddings_task.s(),
    )
    result = pipeline.apply_async()
    return {"chain_task_id": result.id}


@celery_app.task(bind=True)
def pdf_embed_pipeline(self, client_id: str):
    """Pipeline to embed uploaded PDF directly."""
    logger.info(f"Starting PDF embedding for client {client_id}")
    # For PDFs, no crawling step; just run embeddings with source_type='pdf'
    result = run_embeddings_task.apply_async(args=({"client_id": client_id, "source_type": "pdf"},))
    return {"chain_task_id": result.id}