import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import AsyncSessionLocal
from app.models.db_models import AsyncTask
from app.core.dependencies import orchestrator
from app.core.logging import get_logger

logger = get_logger("task_worker")

async def process_task(task: AsyncTask, db: AsyncSession):
    """
    Processes a single async task based on its type.
    """
    logger.info(f"Processing task {task.id} of type {task.task_type} for user {task.user_id}")

    try:
        # Update status to processing
        task.status = "processing"
        await db.commit()

        result = None
        if task.task_type == "chat_analysis":
            # Mock or actual analysis logic
            # In a real scenario, this would involve scanning conversation history
            result = {"summary": "Analysis complete", "insights": ["User is interested in rice pests"]}
        elif task.task_type == "satellite_scan":
            # Mock or actual satellite scan logic
            result = {"status": "completed", "ndvi": 0.65, "health": "Good"}
        else:
            logger.warning(f"Unknown task type: {task.task_type}")
            result = {"error": f"Unsupported task type: {task.task_type}"}

        # Update task with result and mark as completed
        task.result = result
        task.status = "completed"
        await db.commit()
        logger.info(f"Task {task.id} completed successfully")

    except Exception as e:
        logger.exception(f"Error processing task {task.id}: {e}")
        task.status = "failed"
        task.result = {"error": str(e)}
        await db.commit()

async def task_worker_loop():
    """
    Background loop that polls for pending tasks in the database.
    """
    logger.info("Starting async task worker loop...")
    while True:
        try:
            async with AsyncSessionLocal() as db:
                # Fetch a pending task
                result = await db.execute(
                    select(AsyncTask).where(AsyncTask.status == "pending").limit(1)
                )
                task = result.scalars().first()

                if task:
                    await process_task(task, db)
                else:
                    # No tasks to process, wait a bit
                    await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(30)
