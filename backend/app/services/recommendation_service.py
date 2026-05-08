
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import SoilTestLog, IrrigationLog, CuratedTip, KnowledgeFact
from app.core.dependencies import orchestrator
import logging

logger = logging.getLogger("RecommendationService")

class RecommendationService:
    @staticmethod
    async def get_personalized_recommendations(db: AsyncSession, user_id: str):
        """
        Analyzes soil and irrigation logs to provide personalized tips.
        """
        try:
            # 1. Get the most recent soil and irrigation logs
            soil_result = await db.execute(
                select(SoilTestLog).where(SoilTestLog.user_id == user_id).order_by(SoilTestLog.timestamp.desc()).limit(1)
            )
            latest_soil = soil_result.scalars().first()

            irr_result = await db.execute(
                select(IrrigationLog).where(IrrigationLog.user_id == user_id).order_by(IrrigationLog.timestamp.desc()).limit(1)
            )
            latest_irr = irr_result.scalars().first()

            # 2. Get the user's current crop from KnowledgeFacts
            crop_result = await db.execute(
                select(KnowledgeFact).where(KnowledgeFact.user_id == user_id, KnowledgeFact.fact_key == "crop_planted")
            )
            crop_fact = crop_result.scalars().first()
            crop = crop_fact.fact_value if crop_fact else "Unknown"

            # 3. Fetch matching Curated Tips based on crop
            tips_result = await db.execute(
                select(CuratedTip).where(CuratedTip.crop == crop.lower())
            )
            tips = tips_result.scalars().all()

            # 4. Prepare context for the LLM to synthesize a personalized recommendation
            context = {
                "crop": crop,
                "latest_soil": {
                    "ph": latest_soil.derived_ph if latest_soil else "Unknown",
                    "texture": latest_soil.derived_texture if latest_soil else "Unknown",
                    "recommendations": latest_soil.recommendations if latest_soil else "None"
                },
                "latest_irrigation": {
                    "moisture_index": latest_irr.soil_moisture_index if latest_irr else "Unknown",
                    "last_advice": latest_irr.advice if latest_irr else "None"
                },
                "available_tips": [tip.tip_text_bn for tip in tips]
            }

            # 5. Use the Orchestrator/LLM to create a personalized response in Bengali
            prompt = (
                f"Based on the following farm data for a user growing {crop}, "
                f"create a personalized advice message in Bengali. "
                f"Data: {context}. "
                "Combine the curated tips with the soil and irrigation status. "
                "Be encouraging and specific."
            )

            initial_state = {
                "transcript": prompt,
                "user_id": user_id,
                "messages": []
            }

            result = await orchestrator.ainvoke(initial_state)
            return {
                "personalized_advice": result.get("reply_text", "আপনার ফসলের জন্য বিশেষ পরামর্শ তৈরি করা সম্ভব হয়নি।"),
                "supporting_tips": [tip.tip_text_bn for tip in tips],
                "data_snapshot": context
            }

        except Exception as e:
            logger.error(f"Error generating personalized recommendations: {e}")
            return {"error": str(e)}
