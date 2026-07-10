# KrishiBondhu — Feature Elevation Blueprint

**Goal:** Re-architect every feature so the product reads as a genuinely sophisticated
agricultural intelligence platform, not a functional demo. This is a *design* document
for approval — implementation happens feature-by-feature, deeply, in the phases below.

---

## 0. Honest baseline — what is solid vs. what "feels basic"

### Already solid (keep, don't rebuild)
- **Real NASA POWER integration** with Bangladesh monthly climate-average fallback (`weather_service._fetch_nasa_power`).
- **Sound Hargreaves–Samani + soil water-balance core** (`calculate_et0`, `calculate_water_balance`) — correct domain math (one radiation-input precision bug noted in §2.5).
- **PostGIS geospatial layer** (`geospatial_service` / FieldHub) — real spatial queries.
- **Vision tiers 1–2** (`vision_service`) — real model-based crop/soil diagnosis.
- **RAG scaffolding exists** (`embedding_service`) but is **not wired into chat**.
- **`get_farmer_context()` helper exists** but is **not wired into chat** (only a district label in `community.py`).

### Where the "basic" feeling comes from (verified in code)
1. **AI Chat is context-free & tool-less** — `krishi_crew.py` runs pure-LLM personas sequentially; the task prompt injects *only the raw message*. No farmer profile, GPS, crop history, or retrieved knowledge. `get_farmer_context()` is dead in chat.
2. **Market Intelligence is randomized mock** — `market_service.py:82` `price = base * random.uniform(0.9, 1.1)`, random distances; Prophet model trained on synthetic sine+noise (`train_market_model.py`); no real DAM/government price feed.
3. **Yield model trained on fake NDVI** — `get_satellite_ndvi()` returns `random.uniform(0.3, 0.85)` seeded by coordinates (NOT satellite); RF trained on synthetic data whose "historical yield" is just noise around the synthetic target → learns the generator, not agronomy.
4. **Agronomy risk is hardcoded rules** — growth stage = fixed day buckets; pest/disease = humidity/temp thresholds + `if district == "Pabna": locust alert`.
5. **Carbon is substring-matching + base-50 scoring** — only detects N/urea/diesel by keyword; score = `50 + 10/practice − emissions/500`; carbon markets = 3 hardcoded entries.
6. **Traceability QR is a mock URL** (`traceability_service.py:72`); vision Tier-3 hardcoded responses.
7. **Finance/insurance = flat heuristics** (flat premium %, simple thresholds).
8. **Frontend** — mostly CRUD/display; charts render obviously-synthetic data; no streaming, citations, spatial viz, progressive analytics, or offline-aware reactivity.

---

## 1. Architecture-level elevations (cross-cutting)

These lift *every* feature at once and are the highest-leverage changes:

| Layer | Today | Redesigned |
|---|---|---|
| **AI context** | chat prompt = raw message only | `FarmerContextAssembler` injects profile + GPS + crop history + season + retrieved knowledge into every agent task |
| **RAG** | embeddings computed, unused | `RetrievalLayer` over crop advisories / scheme docs / past Q&A → cited context for chat & recommendations |
| **Agent runtime** | sequential personas, no tools | **Tool-augmented crew**: router → planner → specialist agents that *call tools* (weather, market, yield, geospatial, diary) → validator with self-critique |
| **Provenance** | silent mock | every prediction carries `source` + `confidence` + `data_lineage` so the UI can be honest ("forecast from historical DAM series" vs "simulated") |
| **Data contracts** | each service invents its own shapes | shared `PredictionResult` / `Evidence` / `ConfidenceBand` schemas consumed identically by UI |
| **Async pipeline** | request/response only | background `task_worker` for heavy jobs (NDVI fetch, model inference, batch forecasts) with progress + result streaming |

---

## 2. Per-feature elevation

Each entry: **Current (shallow)** → **Redesign (sophisticated)** → **Backend algorithm/architecture** → **Frontend UX**.

### 2.1 AI Multi-Agent Chat (`krishi_crew` + ChatPage)
- **Now:** 2 sequential LLM personas, raw-message-only prompt, no tools, no memory, no citations.
- **Redesign:** Context-aware, tool-using multi-agent system with streaming, memory, and cited evidence.
- **Backend:**
  - `FarmerContextAssembler` → builds structured context block (profile, GPS, active crops, last N diary entries, current season, open alerts).
  - `RetrievalLayer` (RAG) → embeds query, retrieves top-k advisories/scheme docs/FAQ, returns with source IDs.
  - Agents get **tools**: `get_weather`, `get_market_prices`, `predict_yield`, `get_water_balance`, `search_diary`, `geocode`. Crew = Router → Planner → Specialist(s) → Critic. Each tool call logged as a trace.
  - Persist conversation + tool traces to memory (`memory.py`) for continuity.
- **Frontend:** Streaming tokens (SSE), visible "thinking/tools used" panel, cited sources chips, follow-up suggestion chips, Bengali/English toggle preserved.

### 2.2 Market Intelligence (`market_service` + MarketPage)
- **Now:** `base * random.uniform(0.9,1.1)`, random distances, Prophet on synthetic sine+noise.
- **Redesign:** Real price series + honest provenance + decision-grade forecasting.
- **Backend:**
  - Ingest real DAM / government Agricultural Marketing Dept daily prices (adapter pattern; CSV/API), with `source` tag.
  - Where real data absent, clearly label `simulated` and use a *calibrated* seasonal model, not `random`.
  - Train Prophet on **real** history (yearly + weekly seasonality, Bangladeshi festival/ harvest changepoints). Add `uncertainty intervals` (Prophet `interval_width`).
  - Nearby-market distance via **PostGIS** haversine from farmer GPS (not random ints).
  - `PriceAdvisor`: markdown "sell now vs hold" using forecast + storage-cost + spoilage model.
- **Frontend:** Real time-series charts with forecast bands, "best market within X km" map pin, freshness/provenance badge, sell/hold signal.

### 2.3 Yield Prediction + Season Planner (`yield_service` + PlannerPage)
- **Now:** fake NDVI from coords; RF trained on synthetic generator; hardcoded planting windows.
- **Redesign:** Remote-sensed health index + agronomy-grounded model + adaptive plan.
- **Backend:**
  - **Real NDVI** via GEE/Sentinel-Hub (or honest "latest available" with date). Failing that, derive a *plausible* index from weather + phenology, clearly flagged.
  - Retrain yield model on **agronomy-grounded** features (real NDVI trend, accumulated GDD, water balance deficit, historical farm yield) — either real farm data or a physically-motivated semi-synthetic generator (not uniform noise).
  - Output **prediction intervals**, not a point + fake confidence.
  - `SeasonPlanner`: planting window from real crop-calendar + GPS climate zone; plan steps conditioned on predicted water deficit & pest risk.
- **Frontend:** Yield projection with confidence band, "what-if" sliders (inputs, irrigation), calendar view of the season plan.

### 2.4 Agronomy / Crop Growth & Risk (`agronomy_service`)
- **Now:** growth stage = fixed day buckets; pest/disease = humidity/temp thresholds + `if Pabna: locust`.
- **Redesign:** GDD-driven phenology + location-aware risk model.
- **Backend:**
  - `predict_growth_stage` uses **accumulated GDD** vs crop-specific phenology curves (not day counts).
  - `evaluate_risk` becomes a **risk scorer**: disease pressure from T×RH×canopy-wetness windows; drought from water-balance depletion; pest from regional pest-calendar + trap/forecast feeds (extensible). Returns `level` + `probability` + `triggers`.
  - District/locust via a maintained regional alert feed, not a hardcoded string.
- **Frontend:** Phenology progress bar, risk gauges with drivers, "why" tooltips.

### 2.5 Weather & Irrigation (`weather_service` + WaterPage)
- **Now:** solid core, but (a) ET₀ fed **surface** solar radiation instead of **extraterrestrial Ra**, suppressing ET₀; (b) 7-day rain "forecast" is hardcoded monsoon magic (months 5–9, i==1/4).
- **Redesign:** Physically correct ET₀ + forecast-driven schedule.
- **Backend:**
  - Convert/obtain true **extraterrestrial radiation Ra** (or use the Penman–Monteith-ready inputs) so ET₀ is correct.
  - Drive the 7-day schedule from an actual **weather forecast** (NASA POWER forecast / Open-Meteo) instead of hardcoded rain injections.
  - `IrrigationOptimizer`: minimize water subject to MAD, factoring rainfall probability.
- **Frontend:** Corrected ET₀/balance readout, forecast-aware schedule, water-savings estimate.

### 2.6 Sustainability / Carbon (`sustainability_service` + SustainabilityPage)
- **Now:** keyword substring → emission factor; score = `50 + 10*n − emissions/500`; 3 hardcoded markets.
- **Redesign:** Transparent, auditable carbon accounting + matched incentives.
- **Backend:**
  - Parse diary inputs into **structured input events** (quantity, unit, type) via the structured-expense model, not free-text substring.
  - Real **IPCC Tier-1/2** emissions + sequestration with documented factors and per-practice uncertainty.
  - Score from a normalized, monotonic function with **explainable components**; grade band documented.
  - `CarbonMarketMatcher`: rule engine over *real* scheme eligibility (verified practices, region, score) returning rationale.
- **Frontend:** Decomposition stacked bar (emissions vs offsets), per-practice audit trail, matched schemes with eligibility reasons.

### 2.7 Soil Analysis (`soil_service` + SoilPage) & Vision (`vision_service`)
- **Now:** vision Tier-3 hardcoded; soil mostly passthrough.
- **Redesign:** Multi-modal diagnosis.
- **Backend:** Real soil/test interpretation (pH, NPK, OM → amendment plan via nutrient-balance model); vision tiers call the diagnosis model with **confidence + top class probabilities + bounding hints**; Tier-3 becomes a graceful, clearly-labeled fallback, not fake certainty.
- **Frontend:** Diagnostic card with confidence, alternative hypotheses, recommended lab tests, amendment calculator.

### 2.8 Traceability (`traceability_service` + TraceabilityPage)
- **Now:** `http://mock-qr-service.com/placeholder.png`.
- **Redesign:** Real, verifiable supply-chain provenance.
- **Backend:** Generate a real QR encoding a signed record id; store journey events (seed → harvest → pack → ship) with hashes; expose a public verify endpoint.
- **Frontend:** Scannable QR, timeline of journey events, consumer-facing trust view.

### 2.9 Community / Expert Q&A (`community_service` + CommunityPage)
- **Now:** `get_farmer_context` used only for a district label.
- **Redesign:** Context-rich, expert-assisted knowledge network.
- **Backend:** Route farmer questions to relevant experts using crop/topic/location matching; attach farmer context to expert tickets; RAG-suggest similar past answers; reputation + resolution tracking.
- **Frontend:** Topic/crop filters, expert match preview, "similar solved questions" panel.

### 2.10 Recommendations (`recommendation_service` + TipsPage)
- **Now:** (per analysis) rule-based tips.
- **Redesign:** A **reasoning layer** that synthesizes signals from weather, water, yield, market, pest-risk, and diary into prioritized, dated, *explainable* advisories ("Irrigate tomorrow: depletion 62% > MAD; rain prob 10%").
- **Frontend:** Priority-sorted advisory feed with source chips and snooze/done states.

### 2.11 Finance / Credit / Insurance (`finance_service` + FinancePage)
- **Now:** flat 5% premium, simple thresholds.
- **Redesign:** Risk-based, data-driven.
- **Backend:** Insurance premium from **yield-volatility + weather-exposure + historical loss** model; credit score from repayment + production consistency; scenario "if drought → payout" simulator.
- **Frontend:** Premium quote with drivers, payout simulator, affordability view.

### 2.12 Field Hub / Geospatial (`geospatial_service` + FieldHubPage)
- **Now:** PostGIS present, underused.
- **Redesign:** Spatial command center.
- **Backend:** Field polygons, NDVI-over-time per plot, nearest services/markets via PostGIS, zone-level risk aggregation.
- **Frontend:** Map-first dashboard, plot-level layers, tap-to-inspect.

### 2.13 Farm Diary, Emergency, Marketplace, Profile/Onboarding, Audio/TTS/SMS, Barcode/OCR
- **Diary:** structured input events (feeds carbon/yield/finance correctly) instead of free-text notes.
- **Emergency:** severity triage model + offline queue (`useEmergencyQueue`) + nearest responder via PostGIS.
- **Marketplace:** real listings with geo + trust signals; negotiate/escrow-light flow.
- **Profile/Onboarding:** richer farmer graph (plots, crops, equipment) feeding the context assembler.
- **Accessibility (TTS/SMS):** weave throughout (read advisories aloud, SMS fallback for low-connectivity) — not a separate afterthought.
- **Barcode/OCR:** structured capture of inputs/packages feeding diary + traceability.

---

## 3. Phased implementation roadmap (executable, feature-by-feature)

- **Phase 0 — Intelligence foundation (highest perceived-quality win, lowest risk):**
  wire `FarmerContextAssembler` + RAG + tool-augmented crew into chat; fix ET₀ Ra input.
- **Phase 1 — Data realism:** real DAM market feed + Prophet on real history; real/flagged NDVI; agronomy-grounded yield retrain; GDD phenology + risk scorer.
- **Phase 2 — Domain depth:** carbon accounting redesign; traceability real QR/hash; finance risk-based pricing; recommendations reasoning layer.
- **Phase 3 — Frontend elevation:** streaming chat w/ citations+traces; spatial Field Hub; live/progressive analytics; offline-aware reactivity; accessibility woven in.

Each phase is independently shippable; we implement **one feature deeply at a time** within it.

---

## 4. What I need from you before I start coding
1. Confirm the **phasing order** (or propose a different priority).
2. Confirm **data-source reality**: for Market/DAM and NDVI/Sentinel — do we have API keys / acceptable to use simulated-but-labeled data behind a clear "simulated" badge until real feeds are wired? This determines whether Phase 1 is "integrate real" or "honest simulation + interface ready for real."
3. Any **feature you consider out of scope** for this pass.
