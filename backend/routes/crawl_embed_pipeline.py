from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from celery.result import AsyncResult
from sqlalchemy import select  
from backend.database import get_session
from backend.auth_utils import get_client_from_header
from backend.schemas import CrawlRequest, TaskResponse
from backend.models import get_tasks_for_client,User

# Import your Celery app and tasks
from backend.celery_app import celery_app
from backend.tasks import (
    crawl_and_embed_pipeline,
    crawl_website_task,
    run_embeddings_task
)

router = APIRouter(
    prefix='/client/me',
    tags=['tasks']
)

@router.get("/")
async def get_client(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Get current client information"""
    try:
        statement = select(User).where(User.client_id == client_id)
        result = await session.execute(statement)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Client not found")

        return {
            "name": user.name,
            "username": user.username,
            "email": user.email
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching client information: {str(e)}"
        )

@router.post("/crawl-and-embed", response_model=TaskResponse)
async def crawl_and_embed(
    req: CrawlRequest,
    client_id: str = Depends(get_client_from_header)
):
    """Queue a task to crawl website and embed documents"""
    try:
        task = crawl_and_embed_pipeline.delay(
            client_id,
            req.allowed_domain,
            req.start_url
        )
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message="Crawl+embed task queued."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error queuing crawl and embed task: {str(e)}"
        )


@router.post("/crawl", response_model=TaskResponse)
async def crawl_only(
    req: CrawlRequest,
    client_id: str = Depends(get_client_from_header)
):
    """Queue a task to crawl website only"""
    try:
        task = crawl_website_task.apply_async(
            args=[client_id, req.allowed_domain, req.start_url]
        )
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message="Crawl task queued."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error queuing crawl task: {str(e)}"
        )


@router.post("/embed", response_model=TaskResponse)
async def embed_only(
    client_id: str = Depends(get_client_from_header)
):
    """Queue a task to embed documents only"""
    try:
        task = run_embeddings_task.apply_async(args=[client_id])
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message="Embeddings task queued."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error queuing embed task: {str(e)}"
        )


@router.get("/tasks")
async def list_tasks(
    client_id: str = Depends(get_client_from_header),
    session: AsyncSession = Depends(get_session)
):
    """Return full history of tasks for this client, newest first"""
    try:
        tasks = await get_tasks_for_client(session, client_id)
        return {"tasks":tasks}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching tasks: {str(e)}"
        )


@router.get("/task-status/{task_id}")
async def get_task_status(
    task_id: str,
    client_id: str = Depends(get_client_from_header)
):
    """Get the status of a specific task"""
    try:
        result = AsyncResult(task_id, app=celery_app)

        if result.state == "PENDING":
            return {"status": "pending"}
        elif result.state == "STARTED":
            return {"status": "running", "info": result.info}
        elif result.state == "PROGRESS":
            return {"status": "running", "info": result.info}
        elif result.state == "SUCCESS":
            return {"status": "completed", "result": result.result}
        elif result.state == "FAILURE":
            return {"status": "failed", "error": str(result.result)}
        else:
            return {"status": result.state.lower(), "info": result.info}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching task status: {str(e)}"
        )
