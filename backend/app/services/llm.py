
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
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "microsoft/DialoGPT-medium")
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

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        response = client.chat_completion(
            messages,
            max_tokens=1024,
            temperature=0.7
        )

        if hasattr(response, 'choices') and len(response.choices) > 0:
            choice = response.choices[0]
            if hasattr(choice, 'message') and getattr(choice.message, 'content', None):
                return choice.message.content.strip()
            if hasattr(choice, 'text') and choice.text:
                return choice.text.strip()

        raise Exception("Empty response from Hugging Face chat completion.")
    except Exception as chat_error:
        print(f"[WARN] Hugging Face chat completion failed: {chat_error}")
        try:
            response = client.text_generation(
                prompt,
                max_new_tokens=1024,
                temperature=0.7
            )

            if hasattr(response, 'generated_text') and response.generated_text:
                return response.generated_text.strip()
            if isinstance(response, str) and response.strip():
                return response.strip()

            raise Exception("Empty response from Hugging Face text generation.")
        except Exception as generation_error:
            print(f"[ERROR] Hugging Face text generation also failed: {generation_error}")
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
            else:
                return get_fallback_response(prompt, system_instruction)
    elif LLM_PROVIDER == "gemini":
        try:
            return call_gemini_llm(prompt, system_instruction)
        except Exception as e:
            print(f"[WARN] Gemini failed: {e}")
            return get_fallback_response(prompt, system_instruction)
    else:
        # Default to Gemini, then fallback
        try:
            return call_gemini_llm(prompt, system_instruction)
        except Exception as e:
            print(f"[WARN] Default LLM failed: {e}")
            return get_fallback_response(prompt, system_instruction)

def get_fallback_response(prompt: str, system_instruction: str = None) -> str:
    """Provide basic fallback responses when LLM is not available"""
    prompt_lower = prompt.lower()
    
    # Basic keyword-based responses for common farming queries
    if any(word in prompt_lower for word in ['rice', 'paddy', 'dhān']):
        return "For rice farming: Ensure proper water management, use balanced fertilizers, and watch for pests like stem borers. Plant during monsoon season for best results."
    
    elif any(word in prompt_lower for word in ['wheat', 'गेहूं', 'gandum']):
        return "For wheat: Plant in winter (November-December), ensure good drainage, and protect from rust disease. Use nitrogen-rich fertilizers."
    
    elif any(word in prompt_lower for word in ['potato', 'आलू', 'alu']):
        return "For potatoes: Plant in well-drained soil, provide adequate spacing, and watch for late blight. Harvest when leaves turn yellow."
    
    elif any(word in prompt_lower for word in ['disease', 'pest', 'problem', 'sick']):
        return "For crop diseases: Identify the problem early. Common solutions include proper spacing, crop rotation, organic pesticides, and consulting local agricultural extension services."
    
    elif any(word in prompt_lower for word in ['fertilizer', 'খাদ', 'khad']):
        return "For fertilizers: Use balanced NPK fertilizers based on soil testing. Organic options include compost, vermicompost, and bio-fertilizers. Apply at recommended rates."
    
    else:
        return "I'm currently operating in basic mode without AI services. For farming advice, please consult your local agricultural extension office or use resources from the Department of Agricultural Extension (DAE) in Bangladesh."

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
            "reply_text": "I apologize, but I'm experiencing technical difficulties. The system is operating in basic mode with limited responses. Please check your API key configuration for full AI functionality.",
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
