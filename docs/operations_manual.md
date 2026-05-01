# ⚙️ KrishiBondhu Operations Manual

This manual details the production deployment strategies, hardware provisioning guidelines, and API specifications for the KrishiBondhu Multi-Agent backend.

## 1. Hardware Sizing & Model Quantization

Because KrishiBondhu loads multiple specialized Hugging Face models into VRAM, strict hardware provisioning is required for production.

### The Agronomist 70B Challenge
The primary model requested for the Agronomist Agent is `AI71ai/Llama-agrillm-3.3-70B`. 
- **Unquantized (FP16):** Requires ~140GB VRAM (e.g., 2x NVIDIA A100 80GB).
- **Quantized (INT4):** We utilize `BitsAndBytesConfig` (nf4) inside `model_config.py` to compress this. It requires ~40GB VRAM (e.g., 1x A6000 or 2x RTX 3090/4090).

### Automatic Fallback Mechanism
If your deployment environment (such as a basic Hugging Face Space or a standard VPS) lacks the required VRAM, the `ModelRegistry` will catch the `RuntimeError` during instantiation and seamlessly fall back to `FN-LLM-2B`. This ensures the API remains online even on CPU-only or low-VRAM edge devices.

## 2. API Documentation (Swagger Specs)

The FastAPI application automatically generates OpenAPI (Swagger) documentation available at `http://<domain>/docs`. Below are the critical endpoints interfacing with the React PWA.

### `POST /api/chat`
Handles standard text input and GPS coordinates.
- **Payload (multipart/form-data):**
  - `message` (string): The farmer's text query (Bengali or English).
  - `user_id` (string): Unique identifier for conversation continuity.
  - `lat` (float, optional): Latitude for Weather Advisor.
  - `lon` (float, optional): Longitude for Weather Advisor.
- **Response (JSON):**
  - `reply_text` (string): The agent's synthesized response.
  - `language` (string): Detected language ("bn" or "en").
  - `tts_path` (string): URI to the generated audio response.

### `POST /api/upload_audio`
Handles voice queries. Audio is processed by the local Whisper 16kHz pipeline before being passed to the Crew.
- **Payload (multipart/form-data):**
  - `file` (File Blob): The audio recording (.wav, .webm).
  - `user_id`, `lat`, `lon`, `image` (optional metadata).
- **Response (JSON):**
  - Includes `transcript` detailing what the Whisper model heard, along with the standard `reply_text`.

### `WS /api/ws/agent_status`
The WebSocket endpoint that streams real-time CrewAI progress.
- **Behavior:** Once connected, the server will emit JSON blobs containing `{ "message": "Agent working: agronomist_agent..." }` whenever a CrewAI step callback is triggered. This allows the frontend to show "thinking" indicators without polling.

## 3. Production Deployment Checklist

Before deploying via Docker Compose to a production VPS:

1. **Secure the `.env` file**: Ensure `DB_PASSWORD_SECRET` and `REDIS_URL` are strictly defined. Never commit `.env`.
2. **PostgreSQL Migrations**: If you update `db_models.py`, ensure you run `alembic upgrade head` inside the backend container to apply schema changes to the production DB.
3. **Redis Persistence**: Verify that the `redis` container is mounted to a persistent Docker volume, so cache keys survive container restarts.
4. **SSL Termination**: The provided `docker-compose.prod.yml` uses Nginx to terminate SSL on port 443. Ensure your Let's Encrypt certificates are properly mounted to `/etc/letsencrypt`.
5. **Prometheus Monitoring**: Ensure port 8000 `/metrics` is scraped by your Prometheus server to monitor API latency and HTTP 500 error rates.
