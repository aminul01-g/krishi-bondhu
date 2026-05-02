"""Seed script for Phase 3 database entities."""
import asyncio
from datetime import datetime, timedelta
from app.db import AsyncSessionLocal
from app.models.community_models import CommunityQuestion, AgriculturalExpert
from app.models.marketplace_models import Dealer, DealerInventory, VerifiedProduct
from app.models.emergency_models import InsuranceProvider


async def seed_phase3_data():
    async with AsyncSessionLocal() as session:
        # Create agricultural experts
        experts = [
            AgriculturalExpert(
                id="expert-001",
                name="Dr. Ayesha Rahman",
                phone_number="01710000001",
                email="ayesha@example.com",
                region="Dhaka",
                credentials="Extension Officer",
                areas_of_expertise=["rice", "vegetables", "soil_health"],
                response_time_avg_hours=3.5,
                total_answers=120,
                rating_avg=4.8,
                last_active_at=datetime.utcnow(),
            ),
            AgriculturalExpert(
                id="expert-002",
                name="Md. Karim Hossain",
                phone_number="01710000002",
                email="karim@example.com",
                region="Chittagong",
                credentials="Crop Protection Specialist",
                areas_of_expertise=["tomato", "potato", "pesticides"],
                response_time_avg_hours=2.2,
                total_answers=95,
                rating_avg=4.7,
                last_active_at=datetime.utcnow(),
            ),
        ]
        for expert in experts:
            session.add(expert)

        # Create sample community questions
        questions = [
            CommunityQuestion(
                farmer_id_hashed="farmer-001",
                question_text="আমার ধানের পাতা সোনালী হয়ে যাচ্ছে, কী করব?",
                crop_type="rice",
                growth_stage="vegetative",
                lat=23.80,
                lon=90.41,
                status="pending",
            ),
            CommunityQuestion(
                farmer_id_hashed="farmer-002",
                question_text="টমেটোর জন্য সঠিক সেচের ফ্রিকোয়েন্সি কত?",
                crop_type="tomato",
                growth_stage="fruiting",
                lat=22.36,
                lon=91.83,
                status="pending",
            ),
        ]
        for question in questions:
            session.add(question)

        # Create verified products
        products = [
            VerifiedProduct(
                barcode="8901234567890",
                qr_code="QR1234567890",
                product_name="SuperGrow Fertilizer",
                manufacturer="AgroTech Ltd.",
                batch_number="SGF-2026-001",
                active_ingredient="NPK 15-15-15",
                npk_ratio="15-15-15",
                dose_per_application="50 gm per decimal",
                expiry_date=(datetime.utcnow() + timedelta(days=365)).date(),
            ),
            VerifiedProduct(
                barcode="8909876543210",
                qr_code="QR9876543210",
                product_name="PestShield Insecticide",
                manufacturer="GreenField Agro",
                batch_number="PSI-2026-010",
                active_ingredient="Chlorpyrifos 20%",
                npk_ratio="",
                dose_per_application="20 ml per liter",
                expiry_date=(datetime.utcnow() + timedelta(days=180)).date(),
            ),
        ]
        for product in products:
            session.add(product)

        # Create dealer sample and inventory
        dealer = Dealer(
            name="Jamuna Agro Supplies",
            phone_number="01710000003",
            email="sales@jamunaagro.com",
            location_lat=23.75,
            location_lon=90.38,
            regions_served=["Dhaka", "Gazipur"],
            verified_at=datetime.utcnow(),
            is_verified=True,
            verification_status="verified",
        )
        session.add(dealer)
        await session.flush()

        dealer_inventory = DealerInventory(
            dealer_id=dealer.id,
            product_name="Premium Rice Seed",
            input_type="seed",
            crop_type="rice",
            batch_number="PR-2026-01",
            manufacturer="SeedCo",
            quantity_in_stock=250,
            price_bdt=180.0,
            expiry_date=(datetime.utcnow() + timedelta(days=540)).date(),
        )
        session.add(dealer_inventory)

        # Create insurance providers
        providers = [
            InsuranceProvider(
                name="GreenHarvest Insurance",
                email="support@greenharvest.com",
                phone_number="01710000004",
                api_endpoint="https://api.greenharvest.com/claims",
                api_key="GH-API-KEY-2026",
            ),
            InsuranceProvider(
                name="AgriCare Insurance",
                email="helpdesk@agricare.com",
                phone_number="01710000005",
                api_endpoint="https://api.agricare.com/submit_claim",
                api_key="AC-API-KEY-2026",
            ),
        ]
        for provider in providers:
            session.add(provider)

        await session.commit()
        print("Seeded Phase 3 sample data successfully.")


if __name__ == "__main__":
    asyncio.run(seed_phase3_data())
