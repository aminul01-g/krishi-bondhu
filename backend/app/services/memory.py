import inspect
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import KnowledgeFact
from app.llm import init_llm_provider
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
    async def get_farm_history(db: AsyncSession, user_id: str) -> str:
        """Alias for farm history retrieval, kept for backwards compatibility."""
        return await MemoryService.get_user_memory(db, user_id)

    @staticmethod
    def _clean_json_payload(raw_text: str) -> str:
        cleaned = raw_text.strip()
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
        if cleaned.lower().startswith("json:"):
            cleaned = cleaned[len("json:"):].strip()
        if cleaned.lower().startswith("output:"):
            cleaned = cleaned[len("output:"):].strip()
        return cleaned

    @staticmethod
    async def _invoke_llm(llm: object, prompt: str):
        try:
            if hasattr(llm, "acall"):
                return await llm.acall(prompt)
            if hasattr(llm, "ainvoke"):
                return await llm.ainvoke(prompt)
            if hasattr(llm, "invoke"):
                return llm.invoke(prompt)
            if hasattr(llm, "call"):
                return llm.call(prompt)
            if callable(llm):
                result = llm(prompt)
                if inspect.isawaitable(result):
                    return await result
                return result
        except Exception as invoke_error:
            logger.warning(f"Interpreter LLM invocation failed: {invoke_error}")
        return None

    @staticmethod
    def _extract_text_content(result: object) -> str:
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            if "content" in result:
                return result["content"]
            if "text" in result:
                return result["text"]
        if hasattr(result, "content"):
            return getattr(result, "content")
        if hasattr(result, "text"):
            return getattr(result, "text")
        if hasattr(result, "choices"):
            choices = getattr(result, "choices")
            if isinstance(choices, (list, tuple)) and choices:
                first = choices[0]
                if hasattr(first, "message") and getattr(first.message, "content", None):
                    return first.message.content
                if hasattr(first, "text"):
                    return first.text
        if hasattr(result, "generations"):
            generations = getattr(result, "generations")
            if isinstance(generations, (list, tuple)) and generations:
                first = generations[0]
                if hasattr(first, "text"):
                    return first.text
        return str(result)

    @staticmethod
    async def extract_and_save_facts(db: AsyncSession, user_id: str, conversation_text: str, conv_id: int = None):
        """Use a fast LLM to extract key agricultural facts from a conversation and save them."""
        try:
            llm = init_llm_provider()
            if llm is None:
                logger.warning("Shared LLM provider is unavailable for memory extraction.")
                return

            system_prompt = (
                "You are an agricultural data extractor. Extract key facts about a farm from the user's input. "
                "Output ONLY a JSON list of objects with 'key' and 'value'. "
                "Keys should be standard like 'crop_planted', 'soil_condition', 'land_size', 'pest_issue', 'planting_date'. "
                "Example: [{\"key\": \"crop_planted\", \"value\": \"Aman Rice\"}]"
            )

            extraction_prompt = (
                f"{system_prompt}\n\nExtract facts from this conversation:\n{conversation_text}"
            )

            result = await MemoryService._invoke_llm(llm, extraction_prompt)
            raw_content = MemoryService._extract_text_content(result)

            if not raw_content:
                logger.warning("Interpreter LLM did not return a usable response for memory extraction.")
                return

            cleaned = MemoryService._clean_json_payload(raw_content)
            new_facts = []

            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    new_facts = [parsed]
                elif isinstance(parsed, list):
                    new_facts = parsed
            except json.JSONDecodeError:
                match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.S)
                if match:
                    try:
                        parsed = json.loads(match.group(1))
                        if isinstance(parsed, dict):
                            new_facts = [parsed]
                        elif isinstance(parsed, list):
                            new_facts = parsed
                    except json.JSONDecodeError as nested_error:
                        logger.warning(f"Failed to parse extracted JSON payload: {nested_error}")

            if not new_facts:
                logger.info("No structured facts were extracted from the conversation.")
                return

            for fact in new_facts:
                if not isinstance(fact, dict):
                    continue
                key = fact.get("key")
                val = fact.get("value")
                if key and val:
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
                        new_fact = KnowledgeFact(
                            user_id=user_id,
                            fact_key=key,
                            fact_value=str(val),
                            source_conv_id=conv_id
                        )
                        db.add(new_fact)

            await db.commit()
            logger.info(f"Extracted and saved {len(new_facts)} facts for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to extract facts: {e}")
            try:
                await db.rollback()
            except Exception:
                logger.exception("Failed to rollback transaction after memory extraction failure.")
