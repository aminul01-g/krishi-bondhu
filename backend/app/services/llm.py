
import os
import json
from dotenv import load_dotenv
from app.core.prompts import (
    INTENT_EXTRACTION_SYSTEM_INSTRUCTION, 
    REASONING_VOICE_INSTRUCTION, 
    REASONING_IMAGE_INSTRUCTION, 
    REASONING_CHAT_INSTRUCTION
)
from app.services.audio import detect_language_from_text

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")

# Hugging Face Configuration
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "google/gemma-4-31B-it")
# Initialize HF Client lazily if key is present
hf_client = None

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

def _init_hf_client():
    global hf_client
    if hf_client is None and HUGGINGFACE_API_KEY:
        from huggingface_hub import InferenceClient
        hf_client = InferenceClient(model=HUGGINGFACE_MODEL, token=HUGGINGFACE_API_KEY)
    return hf_client


def call_huggingface_llm(prompt: str, system_instruction: str = None) -> str:
    """Call Hugging Face Inference API"""
    if not HUGGINGFACE_API_KEY:
        raise Exception("Hugging Face provider selected but HUGGINGFACE_API_KEY is not configured.")

    try:
        client = _init_hf_client()
        if not client:
            raise Exception("Failed to initialize Hugging Face client.")

        # Use chat completion format (messages API)
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        response = client.chat_completion(
            messages=messages,
            max_tokens=1024,
            temperature=0.7
        )

        if hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content.strip()

        raise Exception("Empty response from Hugging Face.")
    except Exception as e:
        print(f"[ERROR] HuggingFace LLM call failed: {e}")
        raise


def call_llm(prompt: str, system_instruction: str = None) -> str:
    """Wrapper to call the configured LLM provider"""
    if LLM_PROVIDER == "huggingface":
        try:
            return call_huggingface_llm(prompt, system_instruction)
        except Exception as e:
            print(f"[WARN] Hugging Face failed, trying Gemini fallback: {e}")
            if GEMINI_API_KEY:
                return call_gemini_llm(prompt, system_instruction)
            raise
    else:
        return call_gemini_llm(prompt, system_instruction)

def call_gemini_llm(prompt: str, system_instruction: str = None) -> str:
    if not GEMINI_API_KEY:
        raise Exception("Gemini provider selected but GEMINI_API_KEY is not configured.")

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)

        if system_instruction:
            final_prompt = f"{system_instruction}\n\n{prompt}"
        else:
            final_prompt = prompt

        response = genai.GenerativeModel(GEMINI_MODEL).generate_content(final_prompt)

        result_text = None
        if hasattr(response, 'text') and response.text:
            result_text = response.text
        elif hasattr(response, 'parts'):
            result_text = ''.join([part.text for part in response.parts if hasattr(part, 'text')])

        if not result_text:
            raise Exception("Empty response from Gemini.")

        return result_text.strip()
    except Exception as e:
        print(f"[ERROR] Gemini LLM call failed: {e}")
        raise

def intent_node(state):
    transcript = state.get("transcript", "")
    
    language = state.get("language", "en")
    if transcript and (not language or language not in ["bn", "en"]):
        language = detect_language_from_text(transcript)
    
    if not transcript:
        existing_messages = state.get("messages", []) or [{"role":"user", "content": ""}]
        return {"messages": existing_messages, "crop": None, "language": language}
    
    prompt = f"Transcript: {transcript}\n\nExtract the information as JSON:"
    
    try:
        response_text = call_llm(prompt, INTENT_EXTRACTION_SYSTEM_INSTRUCTION)
        
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        parsed = json.loads(response_text)
    except Exception as e:
        print(f"Error in intent extraction: {e}")
        parsed = {"crop": None, "symptoms": transcript, "need_image": False, "note": transcript}
    
    updates = {
        "messages": state.get("messages", []) + [{"role":"user", "content": transcript}],
        "language": language
    }
    
    if parsed.get("crop"):
        updates["crop"] = parsed["crop"]
    if parsed.get("need_image"):
        updates["need_image"] = parsed["need_image"]
    
    return updates

def reasoning_node(state):
    transcript = state.get("transcript", "").strip()
    language = state.get("language", "en")
    has_image = bool(state.get("image_path"))
    has_audio = bool(state.get("audio_path"))
    
    if not language or language not in ["bn", "en"]:
        language = detect_language_from_text(transcript) if transcript else "en"
    
    input_type = "text"
    if has_audio:
        input_type = "voice"
    elif has_image and not transcript:
        input_type = "image_only"
    elif has_image and transcript:
        input_type = "image_with_text"
    
    if not transcript and not has_image:
        return {"reply_text": "Please provide a question, upload an image, or record your voice to get assistance."}
    
    if input_type == "voice":
        system_instruction = REASONING_VOICE_INSTRUCTION
    elif "image" in input_type:
        system_instruction = REASONING_IMAGE_INSTRUCTION
    else:
        system_instruction = REASONING_CHAT_INSTRUCTION
        
    # Construct prompt with context
    context_parts = [f"Language: {language}"]
    if state.get('crop'):
        context_parts.append(f"Identified Crop: {state['crop']}")
    if state.get('vision_result'):
        context_parts.append(f"Visual Analysis: {json.dumps(state['vision_result'])}")
    if state.get('weather_forecast'):
        context_parts.append(f"Weather: {json.dumps(state['weather_forecast'])}")
    
    prompt = f"Context: {', '.join(context_parts)}\n\nUser Query: {transcript}"
    
    try:
        reply = call_llm(prompt, system_instruction)
    except Exception as e:
        print(f"[ERROR] reasoning_node LLM failed: {e}")
        return {
            "reply_text": "I apologize, but I'm experiencing technical difficulties with the language model. Please check your backend API key configuration.",
            "tts_path": None
        }

    # Generate TTS if needed (for voice/audio inputs)
    tts_path = None
    if has_audio:
         from app.services.tts import synthesize_tts
         # Generate TTS in the same language as the response
         tts_lang = detect_language_from_text(reply)
         tts_path = synthesize_tts(reply, lang=tts_lang)
    
    return {"reply_text": reply, "tts_path": tts_path}
