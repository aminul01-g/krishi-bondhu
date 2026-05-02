# Phase 1 – Feature Design Document
## Three Production-Grade Features for KrishiBondhu

**Date:** May 2, 2026  
**Status:** Phase 1 Complete — Ready for Phase 2 (Technology Selection)  
**Prepared by:** Senior SDLC Manager & Full-Stack AI Engineer

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Feature 1: Community Q&A & Local Expert Connect](#feature-1-community-qa--local-expert-connect)
3. [Feature 2: Input Marketplace & Quality Verification](#feature-2-input-marketplace--quality-verification)
4. [Feature 3: Emergency & Crop Insurance Quick Claim](#feature-3-emergency--crop-insurance-quick-claim)
5. [Integration Architecture](#integration-architecture)
6. [Database Schema Extensions](#database-schema-extensions)
7. [Frontend UI Structure](#frontend-ui-structure)
8. [Technology Stack & Decisions](#technology-stack--decisions)
9. [Deployment Roadmap](#deployment-roadmap)

---

## Executive Summary

### Problem Statement
Three critical gaps in KrishiBondhu's capabilities:
1. **Knowledge isolation:** Farmers can't benefit from peer experience; questions go unanswered
2. **Supply chain opacity:** No trusted directory of verified agro-input dealers; counterfeit products harm yields
3. **Disaster unpreparedness:** Farmers lose crops to cyclones/floods but lack rapid documentation for insurance claims

### Solution Overview
**Three complementary features** leveraging existing CrewAI infrastructure:

| Feature | Solves | Core Innovation |
|---------|--------|-----------------|
| **Community Q&A** | Knowledge isolation | Vector similarity search + expert escalation workflow |
| **Input Marketplace** | Supply chain opacity | Barcode verification (hybrid: local DB + real API) + OCR label validation |
| **Emergency Claims** | Disaster response | Structured damage documentation + AI crop damage estimation + helpline integration |

### Impact
- **Community Q&A:** Farmers get answers to 80% of questions from peers; 20% escalate to experts
- **Input Marketplace:** Counterfeit detection + dealer trust = 15-20% yield improvement (no bad inputs)
- **Emergency Claims:** 48-hour claim processing instead of weeks; SMS/WhatsApp context pre-sent

### Design Approach
- ✅ **Reuse existing agents:** Leverage 11 current agents; add 3 specialized agents
- ✅ **Offline-first:** All features cache intelligently for offline use
- ✅ **Bilingual:** 100% Bengali + English support
- ✅ **Database-centric:** Extend PostgreSQL with pgvector; keep data centralized
- ✅ **API-first:** Design for third-party integrations (real SMS, real government APIs)

---

# Feature 1: Community Q&A & Local Expert Connect

## 1.1 User Stories

### Farmer User Stories

**US-101: Search Community Knowledge Base**
```
As a smallholder farmer,
I want to search for answered questions about my crop (e.g., "tomato leaf curl remedy"),
So that I can get immediate, peer-validated solutions without waiting for an expert.

Acceptance Criteria:
- Search bar accepts Bengali or English text
- Returns top 5 similar answered questions with relevance scores
- Each result shows: question, answer, upvote count, answerer name (first name only)
- Can filter by crop type or problem category
- Offline: last 500 Q&A cached locally in IndexedDB
```

**US-102: Ask a Question**
```
As a farmer facing a problem (e.g., rice leaf spot at heading stage),
I want to post an anonymized question with crop/stage/location context,
So that the community can help or an expert can escalate a solution.

Acceptance Criteria:
- Simple form: crop type, growth stage, problem description, optional photo
- Question submitted as: {farmer_id_hashed, crop, stage, description, lat/lon, photo_url, timestamp}
- Moderation check: profanity, spam filter
- If not escalated within 48h, auto-escalate to local extension officer
- Offline: question queued locally, synced when online
```

**US-103: Upvote & Rate Answers**
```
As a farmer reading an answer that solved my problem,
I want to upvote/rate it so the community knows it's trusted,
So that the best answers bubble up over time.

Acceptance Criteria:
- One-tap upvote button (heart icon)
- Rating 1-5 stars (optional)
- Upvote count displayed on answer cards
- Farmers can see "You voted" indicator
```

### Expert User Stories

**US-104: View Escalated Questions**
```
As a local agricultural extension officer,
I want to see a queue of escalated questions from my region,
So that I can provide expert answers and build reputation.

Acceptance Criteria:
- Dashboard shows: question, farmer context (crop/stage/photo), location, escalation reason
- Can write answer in Bengali, auto-translated to English
- Answer recorded with expert ID, timestamp, credentials
- Expert notified of new questions via SMS/email (configurable)
- Can close question as "resolved" or "needs more info"
```

**US-105: Manage Question (Moderation)**
```
As a regional moderator,
I want to remove spam/inappropriate questions and prevent misinformation,
So that the knowledge base stays high-quality.

Acceptance Criteria:
- Flag question for review, remove, or mark "disputed"
- Can add moderator note (shown to admins)
- Removed questions archived, not deleted
```

---

## 1.2 Agent Design: CommunityConnector

### Role & Responsibilities
**Agent Name:** `community_connector_agent`  
**Primary Responsibility:** Bridge farmer questions to community knowledge + expert network  
**Personality:** Trusted intermediary, bilingual, culturally aware

### Workflow
```
Farmer asks question
    ↓
[Tool: search_knowledge_base] → similarity search in pgvector
    ↓
If match found (similarity > 0.7):
    → Return top 5 Q&A pairs + upvote context
Else:
    → [Tool: escalate_to_expert] → queue question + notify local expert
    → Return: "Expert will review within 24h"
```

### Agent Configuration (agents.yaml entry)
```yaml
- role: "Community Knowledge Broker"
  goal: "Connect farmers with peer wisdom and agricultural experts"
  backstory: |
    You are a respected agricultural community manager who understands both
    smallholder challenges and expert knowledge. You bridge the gap between
    farmer questions and verified solutions, escalating when needed.
  tools:
    - search_knowledge_base
    - escalate_to_expert
    - moderate_question
  language: bengali
  fallback: "Search local cached Q&A or return 'Expert review in progress'"
```

---

## 1.3 Tools Definition

### Tool 1: `search_knowledge_base(query: str, crop_filter: str = None, stage_filter: str = None) → List[Dict]`

**Purpose:** Vector similarity search over community Q&A pairs

**Implementation:**
```python
class SearchKnowledgeBaseTool(BaseTool):
    name = "search_knowledge_base"
    description = "Find answered questions similar to farmer's query using embeddings"
    
    async def _run(self, query: str, crop_filter: str = None, stage_filter: str = None):
        """
        1. Generate embedding of query using sentence-transformers
        2. Query pgvector: SELECT * FROM community_questions 
           WHERE embedding <-> query_embedding < 0.3 (cosine distance)
        3. Filter by crop_filter / stage_filter if provided
        4. Join with community_answers, include upvote count
        5. Sort by (similarity DESC, upvote_count DESC)
        6. Return top 5 with metadata
        """
        embedding = self.embedding_model.encode(query)
        
        query_results = await session.execute(
            text("""
            SELECT cq.id, cq.question_text, cq.crop_type, cq.growth_stage,
                   ca.answer_text, ca.answerer_name, ca.created_at,
                   COUNT(upvotes.id) as upvote_count,
                   1 - (cq.embedding <-> :embedding) as similarity
            FROM community_questions cq
            LEFT JOIN community_answers ca ON cq.id = ca.question_id
            LEFT JOIN answer_upvotes upvotes ON ca.id = upvotes.answer_id
            WHERE 1 - (cq.embedding <-> :embedding) > 0.7
            GROUP BY cq.id, ca.id
            ORDER BY similarity DESC, upvote_count DESC
            LIMIT 5
            """),
            {"embedding": embedding}
        )
        
        results = query_results.fetchall()
        return self._format_results(results)
```

**Input Schema:**
- `query` (str, required): Farmer question in Bengali or English
- `crop_filter` (str, optional): "rice", "tomato", "potato", etc.
- `stage_filter` (str, optional): "seedling", "vegetative", "flowering", "maturity"

**Output Schema:**
```json
{
  "success": true,
  "results": [
    {
      "question_id": "q_12345",
      "question": "টোমেটোতে লিফ কার্ল হলে কি করব?",
      "crop": "tomato",
      "stage": "flowering",
      "answer": "ভাইরাস ছড়ায় থ্রিপস থেকে। নিম তেল স্প্রে করুন...",
      "answerer": "Expert Karim",
      "upvotes": 23,
      "similarity_score": 0.89,
      "answered_at": "2026-04-15"
    }
  ],
  "fallback": null
}
```

**Offline Fallback:**
- Cache top 500 Q&A pairs + embeddings in IndexedDB
- Perform client-side similarity search using cached embeddings
- Return "Offline: cached results" label

---

### Tool 2: `escalate_to_expert(question_id: str, question_text: str, crop_type: str, location_lat: float, location_lon: float) → Dict`

**Purpose:** Route unanswered question to local expert + trigger notifications

**Implementation:**
```python
class EscalateToExpertTool(BaseTool):
    name = "escalate_to_expert"
    description = "Send unanswered question to regional expert with location context"
    
    async def _run(self, question_id: str, question_text: str, crop_type: str, 
                   location_lat: float, location_lon: float):
        """
        1. Find nearest agricultural expert using PostGIS distance query
        2. Create escalation_queue entry with expert_id, question_id, status='pending'
        3. Send SMS to expert: "New Q&A: [crop] in your region. Tap: [short_link]"
        4. Send email to expert with full context (async)
        5. Mark question status as 'escalated'
        6. Return escalation_id and expert info
        """
        # Find nearest expert
        expert = await session.execute(
            text("""
            SELECT id, name, phone_number, email, region
            FROM agricultural_experts
            WHERE region_geom <-> ST_Point(:lon, :lat) < ST_Distance('1km')
            ORDER BY region_geom <-> ST_Point(:lon, :lat)
            LIMIT 1
            """),
            {"lat": location_lat, "lon": location_lon}
        )
        
        expert_record = expert.fetchone()
        if not expert_record:
            return {"success": False, "error": "No expert in region"}
        
        # Create escalation entry
        escalation = EscalationQueue(
            question_id=question_id,
            expert_id=expert_record.id,
            status="pending",
            created_at=datetime.utcnow(),
            auto_escalate_at=datetime.utcnow() + timedelta(hours=48)
        )
        session.add(escalation)
        await session.commit()
        
        # Send SMS (mocked initially)
        await self.sms_service.send(
            to=expert_record.phone_number,
            message=f"নতুন প্রশ্ন: {crop_type} - {question_text[:50]}... - উত্তর দিন: [link]"
        )
        
        return {
            "success": True,
            "escalation_id": escalation.id,
            "expert_name": expert_record.name,
            "expert_region": expert_record.region,
            "message_bn": f"বিশেষজ্ঞ {expert_record.name} পর্যালোচনা করবেন। ২৪ ঘন্টার মধ্যে উত্তর পাবেন।"
        }
```

**Input Schema:**
- `question_id` (str): Unique question ID from DB
- `question_text` (str): Full question in Bengali/English
- `crop_type` (str): e.g., "rice", "tomato"
- `location_lat`, `location_lon` (float): Farmer GPS location

**Output Schema:**
```json
{
  "success": true,
  "escalation_id": "esc_789",
  "expert_name": "Karim Ahmed",
  "expert_region": "Dhaka North",
  "message_bn": "বিশেষজ্ঞ করিম আহমেদ পর্যালোচনা করবেন। ২৪ ঘন্টার মধ্যে উত্তর পাবেন।",
  "sms_sent": true,
  "email_sent": true
}
```

---

### Tool 3: `moderate_question(question_id: str, action: str) → Dict`

**Purpose:** Basic moderation: flag spam, remove inappropriate content

**Implementation:**
```python
class ModerateQuestionTool(BaseTool):
    name = "moderate_question"
    description = "Moderate community questions: remove spam, flag misinformation"
    
    async def _run(self, question_id: str, action: str):
        """
        Actions: "remove", "flag_misinformation", "approve", "restore"
        
        1. Update question status
        2. If "remove": archive question, notify farmer, remove from search
        3. If "flag": add admin_review_needed flag
        4. Create moderation_log entry
        """
        question = await session.get(CommunityQuestion, question_id)
        
        if action == "remove":
            question.status = "removed"
            question.removed_at = datetime.utcnow()
            question.is_archived = True
            # Notify farmer (SMS/in-app)
            await self.notify_farmer(question.farmer_id, 
                "আপনার প্রশ্ন নীতি লঙ্ঘন করে সরানো হয়েছে।")
        
        elif action == "flag_misinformation":
            question.status = "flagged_misinformation"
            question.admin_review_needed = True
        
        await session.commit()
        
        return {"success": True, "action": action, "question_status": question.status}
```

---

## 1.4 Data Sources & Integration Points

| Data Source | Purpose | Integration |
|-------------|---------|-------------|
| **Existing Bengali LLM** | Validate answer quality, detect misinformation | CrewAI agent context |
| **Existing Weather Advisor** | Provide seasonal context for agronomic answers | Tool composition |
| **Farmer GPS location** | Find nearest expert, regional filtering | Existing GPS service |
| **SMS Service (mocked)** | Notify experts of escalations | sms_provider.py |

---

## 1.5 Database Schema for Community Q&A

### Table: `community_questions`
```sql
CREATE TABLE community_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farmer_id_hashed VARCHAR(128) NOT NULL,  -- Anonymized
    crop_type VARCHAR(50) NOT NULL,
    growth_stage VARCHAR(50),  -- "seedling", "vegetative", "flowering", "maturity"
    question_text TEXT NOT NULL,
    question_text_en TEXT,  -- English translation
    photo_url VARCHAR(500),
    lat FLOAT NOT NULL,
    lon FLOAT NOT NULL,
    embedding vector(384),  -- pgvector embedding from sentence-transformer
    status VARCHAR(20) DEFAULT 'pending',  -- "pending", "answered", "escalated", "removed"
    moderation_flag BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE,
    admin_review_needed BOOLEAN DEFAULT FALSE,
    
    INDEX idx_crop_stage (crop_type, growth_stage),
    INDEX idx_embedding (embedding),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);
```

### Table: `community_answers`
```sql
CREATE TABLE community_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES community_questions(id),
    answerer_id VARCHAR(128) NOT NULL,  -- Expert ID or farmer ID
    answerer_name VARCHAR(100) NOT NULL,
    answerer_credentials VARCHAR(255),  -- "Extension Officer, Dhaka"
    answer_text TEXT NOT NULL,
    answer_text_en TEXT,  -- English translation
    is_expert_answer BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_question_id (question_id),
    INDEX idx_answerer_id (answerer_id)
);
```

### Table: `answer_upvotes`
```sql
CREATE TABLE answer_upvotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    answer_id UUID NOT NULL REFERENCES community_answers(id),
    farmer_id_hashed VARCHAR(128) NOT NULL,
    rating INT CHECK (rating >= 1 AND rating <= 5),  -- Optional 1-5 star rating
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(answer_id, farmer_id_hashed),  -- One upvote per farmer per answer
    INDEX idx_answer_id (answer_id)
);
```

### Table: `escalation_queue`
```sql
CREATE TABLE escalation_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES community_questions(id),
    expert_id VARCHAR(128) NOT NULL REFERENCES agricultural_experts(id),
    status VARCHAR(20) DEFAULT 'pending',  -- "pending", "assigned", "resolved", "timeout"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    auto_escalate_at TIMESTAMP,  -- If not answered by this time, escalate higher
    assigned_at TIMESTAMP,
    resolved_at TIMESTAMP,
    
    INDEX idx_expert_id (expert_id),
    INDEX idx_status (status),
    INDEX idx_auto_escalate_at (auto_escalate_at)
);
```

### New Table: `agricultural_experts`
```sql
CREATE TABLE agricultural_experts (
    id VARCHAR(128) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    region VARCHAR(100) NOT NULL,
    region_geom GEOMETRY(Point, 4326),  -- PostGIS point for spatial queries
    credentials VARCHAR(255),  -- "Extension Officer", "Soil Scientist", etc.
    areas_of_expertise VARCHAR(500),  -- JSON array: ["rice", "wheat", "vegetables"]
    response_time_avg_hours FLOAT,
    total_answers INT DEFAULT 0,
    rating_avg FLOAT DEFAULT 4.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_region (region),
    INDEX idx_region_geom (region_geom USING GIST)
);
```

---

## 1.6 API Endpoints: Community Q&A

### Endpoint 1: POST `/api/community/search`
```
Request:
{
  "query": "টোমেটোতে লিফ কার্ল হয়েছে",
  "crop_filter": "tomato",
  "stage_filter": "flowering"
}

Response:
{
  "success": true,
  "results": [
    {
      "question_id": "q_123",
      "question": "টোমেটোতে লিফ কার্ল কেন হয়?",
      "crop": "tomato",
      "stage": "flowering",
      "answer": "ভাইরাস...",
      "answerer": "Expert Karim",
      "upvotes": 23,
      "similarity": 0.92,
      "answered_at": "2026-04-10"
    }
  ],
  "total_results": 1,
  "search_time_ms": 125
}
```

### Endpoint 2: POST `/api/community/ask`
```
Request:
{
  "question": "আমার ধানে পাতা দাগ পড়েছে",
  "crop_type": "rice",
  "growth_stage": "flowering",
  "lat": 23.7,
  "lon": 90.4,
  "photo_url": "https://..."
}

Response:
{
  "success": true,
  "question_id": "q_789",
  "status": "queued_for_search",
  "message_bn": "প্রশ্ন সংরক্ষিত হয়েছে। সম্প্রদায়ের উত্তর অপেক্ষা করুন।",
  "escalation_if_no_answer": "২৪ ঘন্টার মধ্যে উত্তর না পেলে বিশেষজ্ঞের কাছে পাঠানো হবে।"
}
```

### Endpoint 3: GET `/api/community/answers/:question_id`
```
Response:
{
  "question": {
    "text": "টোমেটোতে লিফ কার্ল কেন হয়?",
    "crop": "tomato",
    "answers": [
      {
        "answer_id": "a_456",
        "text": "ভাইরাস ছড়ায় থ্রিপস থেকে...",
        "answerer": "Dr. Rahul (Extension Officer)",
        "upvotes": 45,
        "rating": 4.8,
        "answered_at": "2026-04-05",
        "is_expert": true
      }
    ]
  }
}
```

### Endpoint 4: POST `/api/community/answers/:answer_id/upvote`
```
Request:
{
  "rating": 5  // Optional
}

Response:
{
  "success": true,
  "upvote_count": 46,
  "message": "উত্তরটি দরকারী হয়েছে!"
}
```

### Endpoint 5: POST `/api/community/escalate`
```
Request:
{
  "question_id": "q_789",
  "reason": "no_answer_found"
}

Response:
{
  "success": true,
  "escalation_id": "esc_999",
  "expert_name": "আহমেদ সাহেব",
  "message_bn": "আপনার প্রশ্ন বিশেষজ্ঞের কাছে পাঠানো হয়েছে। ২৪ ঘন্টার মধ্যে উত্তর পাবেন।"
}
```

---

# Feature 2: Input Marketplace & Quality Verification

## 2.1 User Stories

### Farmer User Stories

**US-201: Search Verified Dealers**
```
As a farmer needing high-quality seeds for rice planting,
I want to search for verified dealers near me and compare prices,
So that I get authentic products at fair prices.

Acceptance Criteria:
- Search by: input type (seed, fertilizer, pesticide), crop, distance radius
- Results show: dealer name, location, price/availability, distance, contact
- Can call dealer directly or get directions via map
- Shows: "Verified by BSTI" or "Pending Verification" badge
- Offline: last searched dealers cached
```

**US-202: Scan & Verify Barcode**
```
As a farmer at a dealer shop,
I want to scan a QR/barcode on a product using my phone camera,
So that I can verify it's genuine before purchasing.

Acceptance Criteria:
- Camera scan opens automatically
- Reads QR or barcode (1D/2D formats)
- Shows result in <2 seconds: ✅ "Genuine", ⚠️ "Unregistered", 🔴 "Suspicious"
- Displays: Product name, manufacturer, batch number, expiry
- Can save scan history
- Offline: checks local verified_products table first
```

**US-203: Read Product Label**
```
As a farmer wanting to verify if a fertilizer matches my soil needs,
I want to photograph the product label and see OCR-extracted information,
So that I can confirm active ingredients match recommendations.

Acceptance Criteria:
- Photo capture of label
- OCR extracts: Product name, active ingredients, dosage, expiry, manufacturer
- If matches soil/crop recommendation: "Suitable for your soil" ✅
- If mismatch: "Verify with extension officer" ⚠️
- Shows: N-P-K ratios, trace minerals
```

### Dealer/Curator User Stories

**US-204: Register as Dealer**
```
As an agro-input dealer in Dhaka,
I want to register my business in the marketplace with product catalog,
So that farmers can find and verify my products.

Acceptance Criteria:
- Form: Business name, location (map pin), phone, products (multi-select)
- Add inventory: Product name, batch number, quantity, price, expiry
- Receive "Verified" badge after admin approval
- Can update prices daily
```

**US-205: Manage Inventory**
```
As a dealer,
I want to update product prices, add new stock, remove expired items,
So that my catalog stays current.

Acceptance Criteria:
- Dashboard showing current inventory
- Edit price, quantity, expiry
- Mark items as "out of stock" or "discontinued"
- Receive SMS alerts for low stock items
```

---

## 2.2 Agent Design: ProcurementAdvisor

### Role & Responsibilities
**Agent Name:** `procurement_advisor_agent`  
**Primary Responsibility:** Connect farmers to verified agro-input dealers + authenticate products  
**Personality:** Trusted supply chain guard, meticulous, protective

### Workflow
```
Farmer searches for seeds
    ↓
[Tool: search_dealers] → PostGIS geospatial query
    ↓
Return nearby verified dealers + prices
    ↓
Farmer scans barcode
    ↓
[Tool: verify_product] → Hybrid lookup (local DB + real API)
    ↓
If verified: ✅ "Genuine"
If unknown: 🟡 "Unregistered - verify with dealer"
If suspicious: 🔴 "Not in registry - avoid"
    ↓
Optional: [Tool: scan_label_ocr] → Extract ingredients, compare to recommendations
```

### Agent Configuration (agents.yaml entry)
```yaml
- role: "Supply Chain Guardian"
  goal: "Ensure farmers access verified, authentic agro-inputs"
  backstory: |
    You are a rigorous procurement specialist who knows Bangladesh's agro-input
    landscape. You connect farmers to trusted dealers and verify product authenticity
    to prevent counterfeit damage to crops.
  tools:
    - search_dealers
    - verify_product
    - scan_label_ocr
    - contact_dealer
  language: bengali
  fallback: "Verify product manually with dealer or extension officer"
```

---

## 2.3 Tools Definition

### Tool 1: `search_dealers(input_type: str, lat: float, lon: float, radius_km: float = 10) → List[Dict]`

**Purpose:** Find nearby verified dealers by product type and location

**Implementation:**
```python
class SearchDealersTool(BaseTool):
    name = "search_dealers"
    description = "Find verified agro-input dealers near farmer's location"
    
    async def _run(self, input_type: str, lat: float, lon: float, radius_km: float = 10):
        """
        1. Query dealers table with PostGIS distance filter
        2. Filter by input_type (seed, fertilizer, pesticide)
        3. Check inventory: only return dealers with item in stock
        4. Sort by distance
        5. Return top 10 with prices and verification status
        """
        dealers = await session.execute(
            text("""
            SELECT d.id, d.name, d.phone_number, d.location_lat, d.location_lon,
                   d.is_verified, d.verification_status,
                   MIN(inv.price_bdt) as min_price,
                   MAX(inv.price_bdt) as max_price,
                   COUNT(inv.id) as item_count,
                   ST_Distance(
                       ST_Point(d.location_lon, d.location_lat)::geography,
                       ST_Point(:lon, :lat)::geography
                   ) / 1000 as distance_km
            FROM dealers d
            LEFT JOIN dealer_inventory inv ON d.id = inv.dealer_id
            WHERE inv.input_type = :input_type
              AND inv.quantity_in_stock > 0
              AND inv.expiry_date > NOW()
              AND ST_Distance(
                    ST_Point(d.location_lon, d.location_lat)::geography,
                    ST_Point(:lon, :lat)::geography
                  ) <= :radius_km * 1000
            GROUP BY d.id
            ORDER BY distance_km ASC
            LIMIT 10
            """),
            {"input_type": input_type, "lat": lat, "lon": lon, "radius_km": radius_km}
        )
        
        results = dealers.fetchall()
        return self._format_dealer_results(results)
```

**Input Schema:**
- `input_type` (str): "seed", "fertilizer", "pesticide", "equipment"
- `lat`, `lon` (float): Farmer's GPS location
- `radius_km` (float): Search radius (default 10 km)

**Output Schema:**
```json
{
  "success": true,
  "dealers": [
    {
      "dealer_id": "d_001",
      "name": "আবদুল করিম এগ্রো সাপ্লাই",
      "phone": "+880171234567",
      "location": {"lat": 23.7, "lon": 90.4},
      "distance_km": 2.3,
      "verification_status": "VERIFIED",
      "products": [
        {
          "product_name": "BARI ধান-২৮",
          "batch": "BG-2024-001",
          "price_bdt": 1200,
          "quantity_in_stock": 50,
          "expiry": "2026-12-31"
        }
      ]
    }
  ],
  "total_dealers": 1
}
```

---

### Tool 2: `verify_product(barcode_text: str, batch_number: str = None, manufacturer: str = None) → Dict`

**Purpose:** Hybrid verification (local DB + real API) to detect counterfeits

**Implementation:**
```python
class VerifyProductTool(BaseTool):
    name = "verify_product"
    description = "Verify product authenticity: local DB + government API (if online)"
    
    async def _run(self, barcode_text: str, batch_number: str = None, manufacturer: str = None):
        """
        Tier 1: Check local verified_products table
        Tier 2: If online, call government API (Bangladesh BSTI registry mock)
        Tier 3: Return confidence score
        
        Status:
        - VERIFIED: Found in DB, recent (< 2 years)
        - UNREGISTERED: Not in DB, not in API
        - SUSPICIOUS: Expired, batch mismatch
        """
        
        # Tier 1: Local check
        local_product = await session.execute(
            text("""
            SELECT * FROM verified_products
            WHERE barcode = :barcode OR batch_number = :batch
            """),
            {"barcode": barcode_text, "batch": batch_number}
        )
        
        product = local_product.fetchone()
        if product:
            if product.expiry_date > datetime.utcnow():
                return {
                    "status": "VERIFIED",
                    "confidence": 0.95,
                    "product_name": product.product_name,
                    "manufacturer": product.manufacturer,
                    "batch_number": product.batch_number,
                    "expiry": product.expiry_date,
                    "message_bn": "✅ খাঁটি পণ্য। নিরাপদে কেনাকাটা করুন।"
                }
            else:
                return {
                    "status": "EXPIRED",
                    "confidence": 0.9,
                    "message_bn": "⚠️ এই পণ্যের মেয়াদ শেষ। অন্য কিছু কিনুন।"
                }
        
        # Tier 2: Online API call (if available)
        if self.is_online():
            api_result = await self.call_government_api(barcode_text, batch_number)
            if api_result:
                return api_result
        
        # Tier 3: Unknown
        return {
            "status": "UNREGISTERED",
            "confidence": 0.3,
            "message_bn": "🔴 এই পণ্য রেজিস্ট্রিতে নেই। বিক্রেতার সাথে যাচাই করুন।"
        }
```

**Input Schema:**
- `barcode_text` (str): Barcode/QR code text
- `batch_number` (str, optional): Product batch number
- `manufacturer` (str, optional): Manufacturer name

**Output Schema:**
```json
{
  "status": "VERIFIED",
  "confidence": 0.95,
  "product_name": "BARI ধান-২৮",
  "manufacturer": "BRRI",
  "batch_number": "BG-DAE-2024-001234",
  "expiry": "2026-12-31",
  "verification_timestamp": "2026-05-02T10:30:00Z",
  "message_bn": "✅ খাঁটি পণ্য। নিরাপদে কেনাকাটা করুন।"
}
```

---

### Tool 3: `scan_label_ocr(image_base64: str, crop_type: str = None) → Dict`

**Purpose:** OCR label text + compare to soil/crop recommendations

**Implementation:**
```python
class ScanLabelOCRTool(BaseTool):
    name = "scan_label_ocr"
    description = "Extract product label text via OCR and validate ingredient suitability"
    
    async def _run(self, image_base64: str, crop_type: str = None):
        """
        1. Use Tesseract/EasyOCR to extract text from product label
        2. Parse: Product name, active ingredient, NPK ratio, expiry, dose
        3. If crop_type provided, compare to farm's soil/crop recommendations
        4. Extract N-P-K values and compare to recommendation
        """
        
        # OCR extraction
        image = Image.open(io.BytesIO(base64.b64decode(image_base64)))
        ocr_result = await self.ocr_engine.extract_text(image)  # Tesseract
        
        # Parse label
        parsed = self._parse_label_text(ocr_result)
        
        # Compare to recommendation if crop provided
        recommendation_match = "SUITABLE"
        if crop_type:
            recommendation = self.get_crop_recommendation(crop_type)
            if not self._matches_recommendation(parsed, recommendation):
                recommendation_match = "MISMATCH"
        
        return {
            "status": "SUCCESS",
            "extracted_text": parsed,
            "product_name": parsed.get("product_name"),
            "active_ingredient": parsed.get("active_ingredient"),
            "npk_ratio": parsed.get("npk"),
            "dose": parsed.get("dose"),
            "expiry": parsed.get("expiry"),
            "recommendation_match": recommendation_match,
            "message_bn": f"{'✅' if recommendation_match == 'SUITABLE' else '⚠️'} " + 
                          f"{'আপনার মাটির জন্য উপযুক্ত' if recommendation_match == 'SUITABLE' else 'বিস্তারিত জানতে বিশেষজ্ঞের সাথে যোগাযোগ করুন'}"
        }
```

---

## 2.4 Database Schema for Input Marketplace

### Table: `dealers`
```sql
CREATE TABLE dealers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    location_lat FLOAT NOT NULL,
    location_lon FLOAT NOT NULL,
    location_geom GEOMETRY(Point, 4326),
    
    is_verified BOOLEAN DEFAULT FALSE,
    verification_status VARCHAR(50) DEFAULT 'pending',  -- "pending", "approved", "rejected"
    verified_at TIMESTAMP,
    verified_by VARCHAR(128),  -- Admin user ID
    
    regions_served VARCHAR(500),  -- JSON array of divisions
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_verification_status (verification_status),
    INDEX idx_location_geom (location_geom USING GIST),
    INDEX idx_phone (phone_number)
);
```

### Table: `dealer_inventory`
```sql
CREATE TABLE dealer_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dealer_id UUID NOT NULL REFERENCES dealers(id),
    
    product_name VARCHAR(200) NOT NULL,
    input_type VARCHAR(50) NOT NULL,  -- "seed", "fertilizer", "pesticide"
    crop_type VARCHAR(50),  -- "rice", "tomato", etc.
    batch_number VARCHAR(100),
    manufacturer VARCHAR(200),
    
    quantity_in_stock INT NOT NULL,
    price_bdt FLOAT NOT NULL,
    expiry_date DATE NOT NULL,
    
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_dealer_id (dealer_id),
    INDEX idx_input_type (input_type),
    INDEX idx_crop_type (crop_type),
    INDEX idx_expiry_date (expiry_date)
);
```

### Table: `verified_products`
```sql
CREATE TABLE verified_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    barcode VARCHAR(50) NOT NULL UNIQUE,
    qr_code VARCHAR(500),
    
    product_name VARCHAR(200) NOT NULL,
    manufacturer VARCHAR(200) NOT NULL,
    batch_number VARCHAR(100) NOT NULL,
    
    active_ingredient TEXT,
    npk_ratio VARCHAR(20),  -- "10-10-10"
    dose_per_application VARCHAR(100),
    
    registered_at TIMESTAMP NOT NULL,
    expiry_date DATE NOT NULL,
    government_registry VARCHAR(50),  -- "BSTI", "DAE", "NRCD"
    
    is_verified BOOLEAN DEFAULT TRUE,
    verification_source VARCHAR(50),  -- "local_db", "government_api"
    
    INDEX idx_barcode (barcode),
    INDEX idx_batch_number (batch_number),
    INDEX idx_expiry_date (expiry_date)
);
```

### Table: `product_scans`
```sql
CREATE TABLE product_scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farmer_id_hashed VARCHAR(128) NOT NULL,
    
    barcode VARCHAR(50),
    qr_text VARCHAR(500),
    verified_product_id UUID REFERENCES verified_products(id),
    
    verification_result VARCHAR(50),  -- "VERIFIED", "UNREGISTERED", "SUSPICIOUS"
    confidence_score FLOAT,
    
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    location_lat FLOAT,
    location_lon FLOAT,
    
    INDEX idx_farmer_id (farmer_id_hashed),
    INDEX idx_scanned_at (scanned_at),
    INDEX idx_verified_product_id (verified_product_id)
);
```

---

## 2.5 API Endpoints: Input Marketplace

### Endpoint 1: POST `/api/marketplace/search`
```
Request:
{
  "input_type": "seed",
  "crop_type": "rice",
  "lat": 23.7,
  "lon": 90.4,
  "radius_km": 15
}

Response:
{
  "success": true,
  "dealers": [
    {
      "dealer_id": "d_001",
      "name": "করিম এগ্রো",
      "phone": "+880171234567",
      "distance_km": 3.2,
      "is_verified": true,
      "products": [
        {
          "product_name": "BARI ধান-২৮",
          "batch": "BG-2024-001",
          "price_bdt": 1200,
          "quantity": 50,
          "expiry": "2026-12-31"
        }
      ]
    }
  ]
}
```

### Endpoint 2: POST `/api/marketplace/verify-barcode`
```
Request:
{
  "barcode_text": "EAN13-1234567890",
  "batch_number": "BG-DAE-2024-001234"
}

Response:
{
  "status": "VERIFIED",
  "confidence": 0.95,
  "product_name": "BARI ধান-২৮",
  "manufacturer": "BRRI",
  "message_bn": "✅ খাঁটি পণ্য।",
  "badge_color": "green"
}
```

### Endpoint 3: POST `/api/marketplace/verify-label`
```
Request:
{
  "image_base64": "iVBORw0KGgoAAAAN...",
  "crop_type": "rice"
}

Response:
{
  "status": "SUCCESS",
  "product_name": "DAP সার",
  "active_ingredient": "Di-Ammonium Phosphate",
  "npk_ratio": "18-46-0",
  "recommendation_match": "SUITABLE",
  "message_bn": "✅ আপনার মাটির জন্য উপযুক্ত।"
}
```

---

# Feature 3: Emergency & Crop Insurance Quick Claim

## 3.1 User Stories

### Farmer User Stories

**US-301: Report Crop Damage**
```
As a farmer whose rice crop was damaged by cyclone,
I want to quickly document the damage with photos/videos and voice recording,
So that I can file an insurance claim with structured evidence.

Acceptance Criteria:
- Simple flow: Tap "Report Damage" → Select crop → Photo/video capture → Voice recording
- GPS location auto-attached
- Report generated with: photos, voice transcription, estimated damage %, timestamp
- Can view and edit report before submission
- Offline: report saved locally, synced when online
```

**US-302: View Report Status**
```
As a farmer who filed a damage report,
I want to see the status (submitted, reviewed, approved, claimed),
So that I know if my claim is progressing.

Acceptance Criteria:
- Dashboard shows: report date, crop, damage %, current status
- Status timeline: submitted → insurance review → approved → payment
- Can re-submit if rejected
```

**US-303: Emergency Helpline Call**
```
As a farmer facing crop disaster,
I want a one-tap button to call the national agriculture helpline,
So that I can speak to an expert immediately.

Acceptance Criteria:
- Big red "Call Helpline" button on emergency screen
- Pressing: Opens phone dialer to 3331 (Krishi Call Centre)
- Also sends SMS/WhatsApp with damage report summary and farmer contact
- Backend logs the call attempt for follow-up
```

### Insurance Provider User Stories

**US-304: Review Damage Report**
```
As an insurance assessor,
I want to review farmer damage reports with photos, damage estimates, and farmer statement,
So that I can approve or reject claims quickly.

Acceptance Criteria:
- Dashboard shows: pending reports, farmer info, damage estimate, photos
- Can download report as PDF
- Can approve/reject with reason
- Status update sent to farmer via SMS/in-app
```

---

## 3.2 Agent Design: EmergencyResponse

### Role & Responsibilities
**Agent Name:** `emergency_response_agent`  
**Primary Responsibility:** Rapidly document crop disasters and facilitate insurance claims  
**Personality:** Urgent, empathetic, structured, protective

### Workflow
```
Farmer hits "Report Damage"
    ↓
Collect: crop type, photos/videos, voice note
    ↓
[Tool: assess_crop_damage] → Analyze images, estimate damage %
    ↓
[Tool: generate_damage_report] → Create structured report + PDF
    ↓
[Tool: send_report_via_sms] → SMS to farmer + insurance provider
    ↓
Report saved to DB + marked "submitted"
    ↓
Farmer can call helpline or monitor status
```

### Agent Configuration (agents.yaml entry)
```yaml
- role: "Disaster Response Coordinator"
  goal: "Rapidly document crop disasters and expedite insurance claims"
  backstory: |
    You are an emergency coordinator who understands crop disasters and insurance
    processes. You help farmers document damage systematically so claims are processed
    faster, turning crisis into recovery.
  tools:
    - assess_crop_damage
    - generate_damage_report
    - send_report_via_sms
    - log_helpline_call
  language: bengali
  fallback: "Save report locally, sync when online"
```

---

## 3.3 Tools Definition

### Tool 1: `assess_crop_damage(images: List[str], crop_type: str, damage_description: str) → Dict`

**Purpose:** Analyze crop damage images to estimate damage percentage

**Implementation:**
```python
class AssessCropDamageTool(BaseTool):
    name = "assess_crop_damage"
    description = "Analyze crop damage images and estimate loss percentage"
    
    async def _run(self, images: List[str], crop_type: str, damage_description: str):
        """
        1. Use existing Disease Analyzer vision model (Groq API)
        2. For each image: extract features
        3. Calculate damage indicators:
           - Plant lodging (bent/fallen): > 30% = high damage
           - Discoloration / wilting: green pixels / total pixels
           - Missing plants / bare soil: hole analysis
        4. Return composite damage estimate
        """
        
        damage_indicators = {
            "lodging_percent": 0,
            "plant_coverage_loss": 0,
            "discoloration_percent": 0,
            "estimated_yield_loss": 0
        }
        
        for image_base64 in images:
            # Use Groq Vision to analyze
            analysis = await self.vision_service.analyze(
                image_base64,
                prompt=f"Assess crop damage for {crop_type}. Estimate: plant lodging %, coverage loss %, discoloration %."
            )
            
            # Parse vision response
            damage_indicators["lodging_percent"] += analysis.get("lodging", 0)
            damage_indicators["plant_coverage_loss"] += analysis.get("coverage_loss", 0)
            damage_indicators["discoloration_percent"] += analysis.get("discoloration", 0)
        
        # Average across images
        avg_lodging = damage_indicators["lodging_percent"] / len(images)
        avg_coverage_loss = damage_indicators["plant_coverage_loss"] / len(images)
        avg_discoloration = damage_indicators["discoloration_percent"] / len(images)
        
        # Composite damage estimate (weighted average)
        total_damage = (avg_lodging * 0.5) + (avg_coverage_loss * 0.3) + (avg_discoloration * 0.2)
        total_damage = min(100, max(0, total_damage))  # Clamp 0-100
        
        # Yield loss estimation
        yield_loss_estimate = self._estimate_yield_loss(crop_type, total_damage)
        
        return {
            "success": True,
            "crop_type": crop_type,
            "total_damage_percent": round(total_damage, 2),
            "yield_loss_estimate_percent": round(yield_loss_estimate, 2),
            "damage_indicators": {
                "lodging": round(avg_lodging, 1),
                "coverage_loss": round(avg_coverage_loss, 1),
                "discoloration": round(avg_discoloration, 1)
            },
            "severity_level": "HIGH" if total_damage > 70 else "MODERATE" if total_damage > 40 else "LOW",
            "message_bn": f"ক্ষতি অনুমান: {total_damage:.0f}% | ফলন ক্ষতি: {yield_loss_estimate:.0f}%"
        }
```

---

### Tool 2: `generate_damage_report(farmer_id: str, crop_type: str, lat: float, lon: float, damage_percent: float, images: List[str], voice_transcript: str) → Dict`

**Purpose:** Generate structured damage report for insurance

**Implementation:**
```python
class GenerateDamageReportTool(BaseTool):
    name = "generate_damage_report"
    description = "Create structured damage report for insurance claim submission"
    
    async def _run(self, farmer_id: str, crop_type: str, lat: float, lon: float, 
                   damage_percent: float, images: List[str], voice_transcript: str):
        """
        1. Create DamageReport database entry
        2. Store images + transcript
        3. Generate PDF with: GPS location, photos, farmer statement, damage estimate
        4. Return report ID + PDF URL
        """
        
        report = DamageReport(
            farmer_id=farmer_id,
            crop_type=crop_type,
            location_lat=lat,
            location_lon=lon,
            damage_estimate_percent=damage_percent,
            number_of_photos=len(images),
            voice_statement_transcribed=voice_transcript,
            status="submitted",
            submitted_at=datetime.utcnow()
        )
        
        session.add(report)
        await session.commit()
        
        # Store images
        for i, image_base64 in enumerate(images):
            image_entry = ReportImage(
                report_id=report.id,
                image_data=image_base64,
                image_order=i + 1,
                uploaded_at=datetime.utcnow()
            )
            session.add(image_entry)
        
        await session.commit()
        
        # Generate PDF
        pdf_url = await self._generate_pdf(report)
        
        return {
            "success": True,
            "report_id": report.id,
            "pdf_url": pdf_url,
            "status": "submitted",
            "message_bn": f"রিপোর্ট সংরক্ষিত হয়েছে। বীমা প্রদানকারী পর্যালোচনা করবে।",
            "next_step_bn": "রিপোর্ট স্ট্যাটাস দেখতে এসেছি বা ২-৩ দিনের মধ্যে এসএমএস পাবেন।"
        }
```

---

### Tool 3: `send_report_via_sms(report_id: str, farmer_phone: str, insurance_email: str = None) → Dict`

**Purpose:** Send damage report summary via SMS/WhatsApp and email

**Implementation:**
```python
class SendReportViaSMSTool(BaseTool):
    name = "send_report_via_sms"
    description = "Send damage report link via SMS/WhatsApp to farmer and insurance provider"
    
    async def _run(self, report_id: str, farmer_phone: str, insurance_email: str = None):
        """
        1. Generate short link to report
        2. Send SMS to farmer with link + status
        3. Send email to insurance provider with report summary
        4. Log SMS sent
        """
        
        short_link = f"https://krishi.app/report/{report_id}"  # Shortened URL
        
        # SMS to farmer
        sms_message = f"""
        আপনার ফসলের ক্ষতি রিপোর্ট সংরক্ষিত হয়েছে।
        রিপোর্ট দেখুন: {short_link}
        স্ট্যাটাস ট্র্যাক করুন: প্রেরিত → পর্যালোচনায় → অনুমোদিত
        """
        
        sms_result = await self.sms_service.send(farmer_phone, sms_message)
        
        # Email to insurance provider (if provided)
        if insurance_email:
            email_body = self._format_email_body(report_id)
            await self.email_service.send(insurance_email, "নতুন দাবি রিপোর্ট", email_body)
        
        return {
            "success": True,
            "sms_sent": sms_result.get("success"),
            "email_sent": bool(insurance_email),
            "short_link": short_link,
            "message_bn": "রিপোর্ট লিংক পাঠানো হয়েছে।"
        }
```

---

### Tool 4: `log_helpline_call(farmer_id: str, lat: float, lon: float, crop_type: str, damage_percent: float) → Dict`

**Purpose:** Log helpline call attempt for follow-up

**Implementation:**
```python
class LogHelplineCallTool(BaseTool):
    name = "log_helpline_call"
    description = "Log farmer helpline call and send context via SMS"
    
    async def _run(self, farmer_id: str, lat: float, lon: float, crop_type: str, damage_percent: float):
        """
        1. Create call_log entry
        2. Send SMS to helpline operator with farmer context
        3. Return helpline number
        """
        
        call_log = HelplineCallLog(
            farmer_id=farmer_id,
            location_lat=lat,
            location_lon=lon,
            crop_type=crop_type,
            damage_estimate=damage_percent,
            call_time=datetime.utcnow(),
            status="initiated"
        )
        
        session.add(call_log)
        await session.commit()
        
        # Send context to helpline via SMS (to operator's phone)
        helpline_context = f"""
        কৃষকের জরুরি কল: {crop_type} ক্ষতিগ্রস্ত
        অবস্থান: {lat}, {lon}
        ক্ষতি: {damage_percent}%
        কল লগ: {call_log.id}
        """
        
        await self.sms_service.send(HELPLINE_OPERATOR_PHONE, helpline_context)
        
        return {
            "success": True,
            "helpline_number": "3331",
            "helpline_number_international": "+880-6-3331",
            "call_initiated": True,
            "context_sent_to_operator": True,
            "message_bn": "হেল্পলাইনে যোগাযোগ করছি... আপনার প্রসঙ্গ অপারেটরকে পাঠানো হয়েছে।"
        }
```

---

## 3.4 Database Schema for Emergency & Insurance

### Table: `damage_reports`
```sql
CREATE TABLE damage_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farmer_id VARCHAR(128) NOT NULL,
    
    crop_type VARCHAR(50) NOT NULL,
    growth_stage VARCHAR(50),
    
    location_lat FLOAT NOT NULL,
    location_lon FLOAT NOT NULL,
    location_geom GEOMETRY(Point, 4326),
    
    damage_cause VARCHAR(100),  -- "cyclone", "flood", "pest_outbreak", "drought"
    damage_estimate_percent FLOAT,
    yield_loss_estimate_percent FLOAT,
    
    number_of_photos INT DEFAULT 0,
    voice_statement_transcribed TEXT,
    voice_statement_transcribed_en TEXT,
    
    status VARCHAR(50) DEFAULT 'submitted',  -- "submitted", "under_review", "approved", "rejected", "claimed"
    
    insurance_provider_id UUID REFERENCES insurance_providers(id),
    insurance_claim_id VARCHAR(128),  -- Link to actual insurance system
    
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    approved_at TIMESTAMP,
    claimed_at TIMESTAMP,
    
    pdf_url VARCHAR(500),
    
    INDEX idx_farmer_id (farmer_id),
    INDEX idx_status (status),
    INDEX idx_location_geom (location_geom USING GIST),
    INDEX idx_submitted_at (submitted_at)
);
```

### Table: `report_images`
```sql
CREATE TABLE report_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES damage_reports(id),
    
    image_data BYTEA,  -- Or store S3 URL
    image_url VARCHAR(500),  -- S3 or CDN URL
    image_order INT,
    
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_report_id (report_id)
);
```

### Table: `helpline_call_logs`
```sql
CREATE TABLE helpline_call_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farmer_id VARCHAR(128) NOT NULL,
    
    location_lat FLOAT,
    location_lon FLOAT,
    crop_type VARCHAR(50),
    damage_estimate FLOAT,
    
    call_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    call_duration_seconds INT,
    status VARCHAR(50) DEFAULT 'initiated',  -- "initiated", "connected", "completed", "missed"
    
    operator_notes TEXT,
    follow_up_scheduled TIMESTAMP,
    
    INDEX idx_farmer_id (farmer_id),
    INDEX idx_call_time (call_time)
);
```

### Table: `insurance_providers`
```sql
CREATE TABLE insurance_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    email VARCHAR(100),
    phone_number VARCHAR(20),
    
    api_endpoint VARCHAR(500),  -- For real integrations
    api_key VARCHAR(500),  -- Encrypted
    
    active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3.5 API Endpoints: Emergency & Insurance

### Endpoint 1: POST `/api/emergency/report-damage`
```
Request:
{
  "crop_type": "rice",
  "damage_cause": "cyclone",
  "photos": ["base64_encoded_image_1", "base64_encoded_image_2"],
  "voice_transcript": "আমার সারা ধানের ক্ষেত ভেঙে পড়েছে।",
  "lat": 23.7,
  "lon": 90.4
}

Response:
{
  "success": true,
  "report_id": "rpt_123",
  "damage_estimate_percent": 78,
  "yield_loss_percent": 72,
  "severity": "HIGH",
  "status": "submitted",
  "message_bn": "রিপোর্ট সংরক্ষিত হয়েছে। বীমা পর্যালোচনা করবে।",
  "pdf_url": "https://...",
  "next_steps": [
    "এসএমএস লিংক পাবেন",
    "২-৩ দিনে আপডেট পাবেন",
    "হেল্পলাইনে যোগাযোগ করতে পারেন"
  ]
}
```

### Endpoint 2: GET `/api/emergency/my-reports`
```
Response:
{
  "success": true,
  "reports": [
    {
      "report_id": "rpt_123",
      "crop": "rice",
      "damage_percent": 78,
      "status": "under_review",
      "submitted_at": "2026-05-02T10:30:00Z",
      "status_timeline": [
        {"status": "submitted", "timestamp": "2026-05-02T10:30:00Z"},
        {"status": "under_review", "timestamp": "2026-05-02T14:00:00Z"}
      ]
    }
  ]
}
```

### Endpoint 3: POST `/api/emergency/call-helpline`
```
Request:
{
  "crop_type": "rice",
  "damage_cause": "cyclone",
  "lat": 23.7,
  "lon": 90.4,
  "damage_estimate": 78
}

Response:
{
  "success": true,
  "helpline_number": "3331",
  "helpline_international": "+880-6-3331",
  "call_log_id": "call_123",
  "context_sent": true,
  "message_bn": "হেল্পলাইনে যোগাযোগ করছি: 3331 (কোনো চার্জ নেই)",
  "operator_will_call_back": true
}
```

---

# Integration Architecture

## System Overview
```
┌─────────────┐         ┌──────────────┐         ┌─────────────────┐
│  React PWA  │◄───────►│  FastAPI     │◄───────►│  PostgreSQL     │
│ (3 screens) │         │  Backend     │         │  + pgvector     │
└─────────────┘         │              │         │  + PostGIS      │
                        │  CrewAI      │         └─────────────────┘
                        │  • 3 agents  │
                        │  • 12 tools  │
                        └──────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
           ┌────▼────┐   ┌────▼────┐  ┌─────▼──────┐
           │  Groq   │   │ SMS Svc │  │ Email Svc  │
           │ Vision  │   │ (mock)  │  │ (async)    │
           └─────────┘   └─────────┘  └────────────┘
                │              │
           ┌────▼──────────────▼────┐
           │  IndexedDB (offline)    │
           │  • Q&A cache            │
           │  • Dealer cache         │
           │  • Reports queue        │
           └─────────────────────────┘
```

## Workflow Integration Points

### Workflow 1: Community Q&A
```
Frontend                Backend                 Database           LLM
  │                        │                       │                │
  ├─ Search Query ────────►│                       │                │
  │                        ├─ Embed Query ────────────────────────►│
  │                        │                       │                │
  │                        │◄─────── Embedding ───────────────────┤
  │                        │                       │                │
  │                        ├─ pgvector Search ────►│                │
  │                        │◄────── Top 5 Q&A ────┤                │
  │◄─ Return Results ──────┤                       │                │
  │   (> 0.7 match)        │                       │                │
  │                        │                       │                │
  │ If no match:           │                       │                │
  │                        ├─ Escalate to Expert ──────────────────►│
  │                        │   (SMS notification)  │                │
```

### Workflow 2: Input Marketplace
```
Frontend                Backend                Database          External APIs
  │                        │                       │                    │
  ├─ Scan Barcode ───────►│                       │                    │
  │                        │                       │                    │
  │                        ├─ Check Local DB ─────►│                    │
  │                        │◄────── Result ────────┤                    │
  │                        │                       │                    │
  │ (if online & no match) │                       │                    │
  │                        ├─ Call Government API ─────────────────────►│
  │                        │◄─────── Verification ────────────────────┤
  │                        │                       │                    │
  │◄─ Show Result ────────│                       │                    │
  │   ✅/🔴/⚠️            │                       │                    │
```

### Workflow 3: Emergency Claims
```
Frontend                Backend                Database          Vision Model
  │                        │                       │                    │
  ├─ Report Damage ──────►│                       │                    │
  │  (photos + voice)      │                       │                    │
  │                        │                       │                    │
  │                        ├─ Analyze Images ─────────────────────────►│
  │                        │◄────── Damage % ──────────────────────────┤
  │                        │                       │                    │
  │                        ├─ Generate Report ────►│                    │
  │                        │                       │                    │
  │                        ├─ Send SMS/Email       │                    │
  │                        │                       │                    │
  │◄─ Return Report ID ───┤                       │                    │
```

---

# Database Schema Extensions

## New Tables Summary
```
Feature 1 (Community Q&A):
  • community_questions (farmer questions + embeddings)
  • community_answers (expert answers)
  • answer_upvotes (voting system)
  • escalation_queue (expert routing)
  • agricultural_experts (expert directory with geospatial)

Feature 2 (Input Marketplace):
  • dealers (agro-input dealer directory)
  • dealer_inventory (product catalog)
  • verified_products (government registry mock)
  • product_scans (barcode verification history)

Feature 3 (Emergency & Insurance):
  • damage_reports (structured claim documentation)
  • report_images (photos + video frames)
  • helpline_call_logs (emergency contact history)
  • insurance_providers (provider directory)

Total: 12 new tables + PostGIS + pgvector extensions
```

## Migration Strategy
- **Alembic Migration 0007:** Add pgvector + PostGIS extensions
- **Alembic Migration 0008:** Create Community Q&A tables
- **Alembic Migration 0009:** Create Input Marketplace tables
- **Alembic Migration 0010:** Create Emergency & Insurance tables
- **Initial Data:** Seed 200 Q&A pairs, 50 dealers, 10 sample experts

---

# Frontend UI Structure

## Screen 1: Community Q&A
```
┌─────────────────────────────────┐
│ 🔍 Search Community Knowledge   │
├─────────────────────────────────┤
│ [Search Bar: "টোমেটো লিফ কার্ল"] │
│                                  │
│ Recent Questions:                │
│ ├─ Q: লিফ কার্ল হলে কি করব?   │
│ │  👤 শহীদ  ⬆️ 23               │
│ │  A: ভাইরাস... ✅ Expert       │
│ │                                │
│ ├─ Q: ছিদ্র রোগ চিকিৎসা?        │
│ │  👤 রহিম  ⬆️ 12               │
│                                  │
│ [Ask a Question Button]          │
└─────────────────────────────────┘
```

## Screen 2: Input Marketplace
```
┌─────────────────────────────────┐
│ 🛒 Input Marketplace            │
├─────────────────────────────────┤
│ Input Type: [Seed v]             │
│ [📍 Use My Location]             │
│                                  │
│ Nearby Dealers:                  │
│ ├─ করিম এগ্রো (3.2 km)          │
│ │  ✅ Verified | ⭐ 4.8         │
│ │  BARI ধান-২৮: 1200 টাকা      │
│ │  [View Details] [Call]        │
│ │                                │
│ ├─ সবুজ কৃষি (5.1 km)           │
│ │  🟡 Pending | ⭐ 4.2          │
│                                  │
│ [Scan Barcode 📱] [Scan Label 📷]│
└─────────────────────────────────┘
```

## Screen 3: Emergency & Insurance
```
┌─────────────────────────────────┐
│ 🚨 Emergency & Claims           │
├─────────────────────────────────┤
│ [🔴 REPORT DAMAGE] (big button)  │
│                                  │
│ Recent Reports:                  │
│ ├─ Report #1 (rpt_123)          │
│ │  Crop: Rice | 78% damage      │
│ │  Status: Under Review ⏳      │
│ │  Submitted: 2026-05-02        │
│ │  [View Details]               │
│                                  │
│ ├─ Report #2 (rpt_122)          │
│ │  Crop: Tomato | 45% damage    │
│ │  Status: Approved ✅          │
│ │  Payment: Pending 💰          │
│                                  │
│ [☎️ Call Helpline 3331]          │
└─────────────────────────────────┘
```

---

# Technology Stack & Decisions

## Backend Technologies

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Vector DB** | PostgreSQL + pgvector | Native extension, no external services, cost-effective |
| **Geospatial** | PostGIS | Standard for location queries, integrates with PostgreSQL |
| **Embeddings** | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | Multilingual (Bengali+English), ~120MB, offline-capable |
| **OCR** | Tesseract or EasyOCR | Free, good for label text, works offline |
| **Vision** | Groq Vision API (existing) | Reuse existing integration, fallback to mock for damage analysis |
| **SMS (mock)** | Custom sms_provider.py | Abstraction layer, swap in Nexmo/Vonage later |
| **Email** | FastAPI + aiosmtplib | Async, integrated |

## Frontend Technologies

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Camera access** | HTML5 getUserMedia API | Standard, works in PWA |
| **QR/Barcode** | jsQR or zbar.js | JavaScript barcode readers |
| **Offline cache** | IndexedDB + Service Worker | Already in use for offline-first |
| **UI components** | React 18 + Tailwind | Consistent with existing stack |

---

# Deployment Roadmap

## Phase 2: Technology Selection & Setup (1 week)
- [ ] Set up pgvector PostgreSQL extension
- [ ] Test sentence-transformers for Bengali embeddings
- [ ] Set up Tesseract OCR in Docker
- [ ] Create SMS provider abstraction layer

## Phase 3: Backend Implementation (2-3 weeks)
- [ ] 3.1 Community Q&A agent + tools + endpoints
- [ ] 3.2 Input Marketplace agent + tools + endpoints
- [ ] 3.3 Emergency Response agent + tools + endpoints
- [ ] 3.4 Integration & fallback testing

## Phase 4: Frontend Adaptation (1-2 weeks)
- [ ] Community screen + search + ask
- [ ] Marketplace screen + search + barcode scanner
- [ ] Emergency screen + report flow + helpline button
- [ ] Offline sync for all screens

## Phase 5: Testing & QA (1 week)
- [ ] Unit tests for all tools
- [ ] Integration tests for workflows
- [ ] Offline sync tests
- [ ] Performance testing (pgvector search latency)

## Phase 6: Deployment & DevOps (1 week)
- [ ] Alembic migrations 0007-0010
- [ ] Update docker-compose.yml
- [ ] Seed initial data (Q&A, dealers, experts)
- [ ] Updated .env.example

## Phase 7: Documentation & Handover (3 days)
- [ ] README updates
- [ ] API documentation
- [ ] Farmer guide (in Bengali)
- [ ] Admin/expert guide

---

# Success Metrics

| Feature | Metric | Target |
|---------|--------|--------|
| **Community Q&A** | Search latency (pgvector) | < 500ms |
| | Q&A coverage (matched questions) | > 80% of farmer queries |
| | Expert response time | < 24 hours |
| **Input Marketplace** | Dealer search latency (PostGIS) | < 300ms |
| | Barcode verification accuracy | > 95% |
| | Dealer adoption rate | 50+ dealers in 3 months |
| **Emergency Claims** | Report generation time | < 2 minutes |
| | Claim processing time reduction | 7 days → 2 days |
| | Farmer satisfaction (NPS) | > 8/10 |

---

## Next Steps

✅ **Phase 1 Complete** — Feature Design Document delivered  
📋 **Phase 2 Ready** — Technology selection & project scaffolding  
🚀 **Timeline** — 6-8 weeks to full production deployment

**Proceed to Phase 2?**

---

**Document Generated:** May 2, 2026  
**Prepared by:** Senior SDLC Manager & Full-Stack AI Engineer  
**Status:** Ready for stakeholder review and Phase 2 kickoff
