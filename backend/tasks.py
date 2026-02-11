import os
import sys
import subprocess
import asyncio
from celery import chain
from celery.utils.log import get_task_logger

from backend.celery_app import celery_app
from backend.database import async_session_maker
from backend.models import add_task, update_task

# Add Chatbot/LLM path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHATBOT_PROCESSING_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/processing"))
sys.path.append(CHATBOT_PROCESSING_DIR)

logger = get_task_logger(__name__)

CRAWLER_DIR = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/crawler"))
CLIENTS_DIR = os.path.abspath(os.path.join(BASE_DIR, "../client_data"))

os.makedirs(CLIENTS_DIR, exist_ok=True)


# -----------------------------------------------------------------------------
# Async Database Helpers for Celery (runs async functions in sync context)
# -----------------------------------------------------------------------------
def run_async(coro):
    """Helper to run async functions in Celery tasks"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If event loop is already running, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        # No event loop exists, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(coro)
    finally:
        # Don't close the loop in case it's needed for other tasks
        pass


async def db_add_task(task_id: str, client_id: str, name: str, status: str = "queued", info: str = None):
    """Async wrapper for add_task"""
    async with async_session_maker() as session:
        return await add_task(session, task_id, client_id, name, status, info)


async def db_update_task(task_id: str, status: str, info: str = None):
    """Async wrapper for update_task"""
    async with async_session_maker() as session:
        return await update_task(session, task_id, status, info)


# -----------------------------------------------------------------------------
# Subprocess Helper
# -----------------------------------------------------------------------------
def run_subprocess_sync(cmd: list, cwd: str = None):
    """Run subprocess command synchronously"""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=3600,
    )
    return result.returncode, result.stdout, result.stderr


# -----------------------------------------------------------------------------
# Celery Tasks
# -----------------------------------------------------------------------------
@celery_app.task(bind=True)
def crawl_website_task(self, client_id: str, allowed_domain: str, start_url: str, max_pages: int = 1000):
    """Crawl a website using Playwright and save JSON content."""
    import platform, shutil
    task_id = self.request.id

    # Add task to database
    run_async(db_add_task(task_id, client_id, "Crawl Website (Playwright)", status="queued"))

    logger.info(f"Starting Playwright crawl for client {client_id}, domain {allowed_domain}, start_url={start_url}")
    self.update_state(state="PROGRESS", meta={"progress": 10, "message": "Starting Playwright website crawl..."})
    run_async(db_update_task(task_id, "running", "Starting Playwright crawl..."))

    client_dir = os.path.join(CLIENTS_DIR, client_id)
    os.makedirs(client_dir, exist_ok=True)
    output_file = os.path.join(client_dir, "website_content.json")

    # Candidate script paths
    candidate_paths = [
        os.path.abspath(os.path.join(CRAWLER_DIR, "crawler", "spiders", "website_scrap.py")),
    ]

    scraper_script = None
    for p in candidate_paths:
        if os.path.exists(p):
            scraper_script = p
            break

    if not scraper_script:
        err = f"Playwright scraper not found. Checked: {candidate_paths}"
        logger.error(err)
        run_async(db_update_task(task_id, "failed", err))
        raise Exception(err)

    # Build the command
    cmd = [
        sys.executable,
        scraper_script,
        start_url,
        output_file,
        "--max-pages",
        str(max_pages)
    ]

    # Log environment + command for debugging
    logger.info(f"crawl_website_task invoked. worker pid={os.getpid()} python={sys.executable} platform={platform.platform()}")
    logger.info(f"Using scraper_script={scraper_script}")
    logger.info(f"Running cmd: {' '.join(cmd)}")
    logger.info(f"playwright binary in PATH: {shutil.which('playwright')}, python binary: {shutil.which(sys.executable)}")

    # Optional: ensure Playwright package is importable
    try:
        import playwright  # type: ignore
    except Exception:
        msg = "Playwright package not available in environment. Run: pip install playwright && playwright install chromium"
        logger.error(msg)
        run_async(db_update_task(task_id, "failed", msg))
        raise Exception(msg)

    self.update_state(state="PROGRESS", meta={"progress": 50, "message": "Crawling website with Playwright..."})

    # Run the scraper script synchronously and capture output
    returncode, stdout, stderr = run_subprocess_sync(cmd, cwd=os.path.dirname(scraper_script) or CRAWLER_DIR)

    # Save logs for debugging into client folder
    logs_dir = os.path.join(client_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    with open(os.path.join(logs_dir, f"playwright_crawl_{task_id}.stdout.log"), "w", encoding="utf-8") as f:
        f.write(stdout or "")
    with open(os.path.join(logs_dir, f"playwright_crawl_{task_id}.stderr.log"), "w", encoding="utf-8") as f:
        f.write(stderr or "")

    if returncode != 0:
        run_async(db_update_task(task_id, "failed", f"Playwright crawl failed: {stderr[:200]}"))
        logger.error(f"Playwright crawl failed for client {client_id}. rc={returncode}. see logs.")
        raise Exception(f"Playwright crawl failed: {stderr}")

    # Success
    run_async(db_update_task(task_id, "completed", f"Crawled pages saved to {output_file}"))
    logger.info(f"Playwright crawl completed for client {client_id}. Saved to {output_file}")

    # Detect all existing sources so we don't wipe PDF data during re-embed
    has_pdf = os.path.exists(os.path.join(client_dir, "custom_pdf.txt"))
    source_type = "both" if has_pdf else "crawl"

    return {"client_id": client_id, "output_file": output_file, "source_type": source_type}


@celery_app.task(bind=True)
def run_embeddings_task(self, prev_result):
    """Run embeddings using the enhanced UniversalEmbeddingPipeline."""
    task_id = self.request.id
    client_id = prev_result["client_id"]
    source_type = prev_result.get("source_type", "crawl")

    # Add task to database
    run_async(db_add_task(task_id, client_id, "Run Embeddings", status="queued"))

    logger.info(f"Starting embeddings for client {client_id} (source: {source_type})")
    self.update_state(state="PROGRESS", meta={"progress": 10, "message": "Starting embeddings..."})
    run_async(db_update_task(task_id, "running", "Generating embeddings..."))

    # Use the enhanced embed_pipeline.py script
    script_path = os.path.abspath(os.path.join(BASE_DIR, "../Chatbot/processing/embed_pipeline.py"))

    if not os.path.exists(script_path):
        err = f"Embedding script not found at {script_path}"
        logger.error(err)
        run_async(db_update_task(task_id, "failed", err))
        raise Exception(err)

    cmd = [sys.executable, script_path, client_id, "--source", source_type]

    self.update_state(state="PROGRESS", meta={"progress": 50, "message": "Processing embeddings..."})
    returncode, stdout, stderr = run_subprocess_sync(cmd)

    # Save logs
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    logs_dir = os.path.join(client_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    with open(os.path.join(logs_dir, f"embeddings_{task_id}.stdout.log"), "w", encoding="utf-8") as f:
        f.write(stdout or "")
    with open(os.path.join(logs_dir, f"embeddings_{task_id}.stderr.log"), "w", encoding="utf-8") as f:
        f.write(stderr or "")

    if returncode != 0:
        run_async(db_update_task(task_id, "failed", f"Embeddings failed: {stderr[:200]}"))
        logger.error(f"Embeddings failed for client {client_id}. See logs.")
        raise Exception(f"Embeddings failed: {stderr}")

    run_async(db_update_task(task_id, "completed", "Embeddings generated successfully"))
    logger.info(f"Embeddings completed for client {client_id}")
    return {"client_id": client_id, "embeddings": "Generated and stored", "source_type": source_type}


@celery_app.task(bind=True)
def crawl_and_embed_pipeline(self, client_id: str, allowed_domain: str, start_url: str, max_pages: int = 1000):
    """High-level pipeline for crawling website + embeddings."""
    logger.info(f"Starting combined crawl+embed for client {client_id}")

    # Create a chain of tasks
    pipeline = chain(
        crawl_website_task.s(client_id, allowed_domain, start_url, max_pages),
        run_embeddings_task.s(),
    )
    result = pipeline.apply_async()
    return {"chain_task_id": result.id}


@celery_app.task(bind=True)
def pdf_embed_pipeline(self, client_id: str):
    """Pipeline to embed uploaded PDF using enhanced pipeline."""
    logger.info(f"Starting PDF embedding for client {client_id}")

    # Detect all existing sources so we don't wipe website data
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    has_website = os.path.exists(os.path.join(client_dir, "website_content.json"))

    source_type = "both" if has_website else "pdf"

    result = run_embeddings_task.apply_async(
        args=({"client_id": client_id, "source_type": source_type},)
    )
    return {"chain_task_id": result.id}


@celery_app.task(bind=True)
def qa_embed_pipeline(self, client_id: str):
    """Pipeline to re-embed after Q&A updates."""
    logger.info(f"Starting Q&A re-embedding for client {client_id}")

    # Check what sources exist
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    has_website = os.path.exists(os.path.join(client_dir, "website_content.json"))
    has_pdf = os.path.exists(os.path.join(client_dir, "custom_pdf.txt"))

    # Determine source type
    if has_website and has_pdf:
        source_type = "both"
    elif has_pdf:
        source_type = "pdf"
    else:
        source_type = "crawl"

    result = run_embeddings_task.apply_async(
        args=({"client_id": client_id, "source_type": source_type},)
    )
    return {"chain_task_id": result.id}
