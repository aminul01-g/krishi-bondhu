from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import KnowledgeFact
from app.config.model_config import model_registry
import json
import logging

logger = logging.getLogger("MemoryService")

class MemoryService:
    @staticmethod
    async def get_user_memory(db: AsyncSession, user_id: str) -> str:
        """Fetch all known facts about the user's farm as a formatted string."""
        try:
            result = await db.execute(
                select(KnowledgeFact).where(KnowledgeFact.user_id == user_id)
            )
            facts = result.scalars().all()
            if not facts:
                return "No previous farm history found."
            
            memory_lines = [f"- {f.fact_key}: {f.fact_value}" for f in facts]
            return "\n".join(memory_lines)
        except Exception as e:
            logger.error(f"Error fetching memory: {e}")
            return "Error retrieving farm history."

    @staticmethod
    async def extract_and_save_facts(db: AsyncSession, user_id: str, conversation_text: str, conv_id: int = None):
        """Use a fast LLM to extract key agricultural facts from a conversation and save them."""
        try:
            llm = model_registry.get_interpreter_llm()
            
            system_prompt = (
                "You are an agricultural data extractor. Extract key facts about a farm from the user's input. "
                "Output ONLY a JSON list of objects with 'key' and 'value'. "
                "Keys should be standard like 'crop_planted', 'soil_condition', 'land_size', 'pest_issue', 'planting_date'. "
                "Example: [{\"key\": \"crop_planted\", \"value\": \"Aman Rice\"}]"
            )
            
            # Simple sync call for extraction (wrapped in a thread if needed, but here we use ainvoke if available)
            # For simplicity in this env, we use the model's invoke pattern
            extraction_prompt = f"Extract facts from this conversation: {conversation_text}"
            
            # We assume the model supports basic string input for extraction
            result = await llm.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": extraction_prompt}
            ])
            
            raw_content = result.content if hasattr(result, 'content') else str(result)
            # Clean JSON
            json_str = raw_content.replace("```json", "").replace("```", "").strip()
            new_facts = json.loads(json_str)
            
            for fact in new_facts:
                key = fact.get("key")
                val = fact.get("value")
                if key and val:
                    # Check if fact exists to update or create
                    existing_result = await db.execute(
                        select(KnowledgeFact).where(
                            KnowledgeFact.user_id == user_id,
                            KnowledgeFact.fact_key == key
                        )
                    )
                    existing = existing_result.scalars().first()
                    
                    if existing:
                        existing.fact_value = str(val)
                        existing.source_conv_id = conv_id
                    else:
                        new_f = KnowledgeFact(
                            user_id=user_id,
                            fact_key=key,
                            fact_value=str(val),
                            source_conv_id=conv_id
                        )
                        db.add(new_f)
            
            await db.commit()
            logger.info(f"Extracted and saved {len(new_facts)} facts for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to extract facts: {e}")
            await db.rollback()
