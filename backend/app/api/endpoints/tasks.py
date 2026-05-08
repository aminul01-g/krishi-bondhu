from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Any
from app.db import get_db
from app.models.db_models import AsyncTask, User
from app.core.dependencies import get_current_user

router = APIRouter()

@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve the status and result of a background task.
    """
    try:
        result = await db.execute(select(AsyncTask).where(AsyncTask.id == task_id))
        task = result.scalars().first()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Security check: Ensure the task belongs to the requesting user
        if task.user_id != current_user.external_id:
            raise HTTPException(status_code=403, detail="Access denied to this task")

        return {
            "id": task.id,
            "status": task.status,
            "result": task.result,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
