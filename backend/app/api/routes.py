from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import OperationalError
from app.db import get_db
from app.models.db_models import Conversation

router = APIRouter()

@router.get("/conversations")
async def get_conversations(db: AsyncSession = Depends(get_db)):
    """
    Get all conversations from the database, ordered by created_at descending.
    Returns conversations with id, user_id, transcript, confidence, and media_url.
    Gracefully handles database connection errors.
    """
    try:
        result = await db.execute(
            select(Conversation).order_by(Conversation.created_at.desc())
        )
        conversations = result.scalars().all()
        return [
            {
                "id": conv.id,
                "user_id": conv.user_id,
                "transcript": conv.transcript,
                "confidence": conv.confidence,
                "media_url": conv.media_url,
                "tts_path": conv.tts_path,
                "metadata": conv.meta_data,  # Using meta_data from model, but returning as metadata in API
                "created_at": conv.created_at.isoformat() if conv.created_at else None
            }
            for conv in conversations
        ]
    except (OperationalError, ConnectionRefusedError, Exception) as e:
        # Database not available - return empty list instead of crashing
        print(f"Database connection error (conversations endpoint): {e}")
        print("Returning empty conversations list - database may not be running")
        return []

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a specific conversation by ID.
    Gracefully handles database connection errors.
    """
    try:
        # Check if conversation exists
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Delete the conversation
        await db.execute(
            delete(Conversation).where(Conversation.id == conversation_id)
        )
        await db.commit()
        
        print(f"Successfully deleted conversation {conversation_id}")
        return {"message": "Conversation deleted successfully", "id": conversation_id}
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except (OperationalError, ConnectionRefusedError) as e:
        try:
            await db.rollback()
        except:
            pass
        print(f"Database connection error (delete conversation): {e}")
        raise HTTPException(status_code=503, detail="Database not available")
    except Exception as e:
        try:
            await db.rollback()
        except:
            pass
        print(f"Error deleting conversation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")