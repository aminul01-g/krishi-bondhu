import asyncio
import uuid
from datetime import datetime
from sqlalchemy import text
from app.db import AsyncSessionLocal

async def seed_experts():
    """
    Seeds the agricultural_experts table with a diverse set of experts
    distributed across Bangladesh for testing geospatial queries.
    """
    experts = [
        {
            "id": str(uuid.uuid4()),
            "name": "Dr. Rahman",
            "phone_number": "01711000001",
            "email": "rahman@example.com",
            "region": "Dhaka",
            "credentials": "Senior Agronomist",
            "areas_of_expertise": ["rice", "pest_control"],
            "lat": 23.8103, "lon": 90.4125, # Dhaka center
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Engr. Karim",
            "phone_number": "01711000002",
            "email": "karim@example.com",
            "region": "Rajshahi",
            "credentials": "Soil Scientist",
            "areas_of_expertise": ["soil_health", "mango"],
            "lat": 24.3726, "lon": 88.8986, # Rajshahi center
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Sultana Begum",
            "phone_number": "01711000003",
            "email": "sultana@example.com",
            "region": "Sylhet",
            "credentials": "Tea Plantation Expert",
            "areas_of_expertise": ["tea", "irrigation"],
            "lat": 24.8938, "lon": 91.8688, # Sylhet center
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Abdullah Al-Mamun",
            "phone_number": "01711000004",
            "email": "mamun@example.com",
            "region": "Chittagong",
            "credentials": "Fisheries Specialist",
            "areas_of_expertise": ["shrimp", "aquaculture"],
            "lat": 22.3569, "lon": 91.8331, # Chittagong center
        },
    ]

    async with AsyncSessionLocal() as session:
        print(f"Seeding {len(experts)} experts...")
        for exp in experts:
            # Use PostGIS ST_SetSRID and ST_Point for geometry insertion
            query = text(
                """
                INSERT INTO agricultural_experts
                (id, name, phone_number, email, region, credentials, areas_of_expertise, region_geom, created_at)
                VALUES
                (:id, :name, :phone, :email, :region, :creds, :expertise,
                 ST_SetSRID(ST_Point(:lon, :lat), 4326), :created)
                """
            )
            await session.execute(query, {
                "id": exp["id"],
                "name": exp["name"],
                "phone": exp["phone_number"],
                "email": exp["email"],
                "region": exp["region"],
                "creds": exp["credentials"],
                "expertise": exp["areas_of_expertise"],
                "lat": exp["lat"],
                "lon": exp["lon"],
                "created": datetime.utcnow()
            })
        await session.commit()
        print("Expert seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed_experts())
