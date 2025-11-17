"""
LangGraph app wiring STT (Gemini), Vision, Weather, LLM steps, and TTS.
Using Google Gemini API for transcription and LLM tasks.
"""

from typing_extensions import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
import json, tempfile, os, requests, base64, time
from app.api.utils import save_audio_local
from app.models.vision import run_vision_classifier
from gtts import gTTS
from dotenv import load_dotenv
load_dotenv()

# Gemini API client
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDlWQCKSKKtHl1wLQvnb9QaPRUODn8sMQ0")
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini model
# Use gemini-2.5-flash (stable) or gemini-flash-latest (always latest)
gemini_model = genai.GenerativeModel('models/gemini-2.5-flash')  # Using Flash for faster responses

# State schema
class FarmState(TypedDict):
    audio_path: str
    transcript: str
    language: str
    user_id: str
    gps: dict
    crop: str
    image_path: str
    vision_result: dict
    weather_forecast: dict
    messages: Annotated[list, add_messages]
    reply_text: str
    tts_path: str

# --- helper functions ---
def transcribe_with_gemini(audio_path: str) -> dict:
    """
    Transcribe audio using Gemini API.
    Gemini 2.5 Flash supports audio files via direct file path or base64.
    Returns dict with keys: text, language (if available).
    """
    try:
        # Check if file exists
        if not os.path.exists(audio_path):
            print(f"Audio file not found: {audio_path}")
            return {"text": "", "language": "en"}
        
        # Read file and encode as base64 for Gemini API
        print(f"Reading audio file for Gemini: {audio_path}")
        import mimetypes
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(audio_path)
        if not mime_type:
            # Default to webm if unknown
            mime_type = "audio/webm"
        
        # Use Gemini to transcribe the audio - improved for Bengali/Bangla with better accuracy
        prompt = """You are an expert audio transcription assistant specializing in Bengali (Bangla) and English languages, with particular expertise in agricultural terminology.

CRITICAL TRANSCRIPTION RULES:
1. LANGUAGE DETECTION:
   - Listen carefully to identify if the speaker is using Bengali/Bangla or English
   - Bengali uses the Bengali script (বাংলা) with Unicode range 0980-09FF
   - If you hear Bengali words, transcribe in Bengali script
   - If you hear English words, transcribe in English

2. ACCURACY REQUIREMENTS:
   - Transcribe EXACTLY what you hear - word for word
   - Do NOT translate between languages
   - Do NOT add words that weren't spoken
   - Do NOT omit words that were spoken
   - Preserve the exact pronunciation and meaning
   - Handle regional accents (especially Bangladeshi Bengali dialect)

3. AGRICULTURAL TERMINOLOGY:
   - Be precise with crop names: ধান (rice), আলু (potato), টমেটো (tomato), গম (wheat)
   - Accurately transcribe disease names: রোগ, পোকা, পাতা পোড়া
   - Preserve technical farming terms in their original language

4. OUTPUT FORMAT:
   - Return ONLY the transcribed text
   - No explanations, no additional commentary
   - No language labels or prefixes
   - Just the pure transcription

Now transcribe the audio accurately:"""
        
        print("Generating transcription with Gemini...")
        # Pass file directly using Part.from_data
        try:
            from google.generativeai.types import Part
            audio_part = Part.from_data(data=audio_data, mime_type=mime_type)
            response = gemini_model.generate_content([audio_part, prompt])
        except ImportError:
            # Fallback: try passing file path directly (may work in some versions)
            try:
                response = gemini_model.generate_content([audio_path, prompt])
            except:
                # Last resort: encode as base64
                import base64
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                # Create a data URI
                data_uri = f"data:{mime_type};base64,{audio_b64}"
                response = gemini_model.generate_content([data_uri, prompt])
        
        # Handle different response structures
        if not response:
            raise Exception("Empty response from Gemini transcription")
        
        transcript_text = None
        if hasattr(response, 'text') and response.text:
            transcript_text = response.text
        elif hasattr(response, 'candidates') and response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                transcript_text = ''.join([part.text for part in candidate.content.parts if hasattr(part, 'text')])
            elif hasattr(candidate, 'text'):
                transcript_text = candidate.text
        
        if not transcript_text or not transcript_text.strip():
            raise Exception("Empty transcription from Gemini API")
        
        transcript_text = transcript_text.strip()
        
        # Detect language (improved detection with more Bengali characters)
        language = "en"  # Default
        transcript_lower = transcript_text.lower()
        
        # Comprehensive Bengali character detection (including all Bengali Unicode ranges)
        bengali_chars = "অআইঈউঊঋএঐওঔকখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহড়ঢ়য়"
        # Check for Bengali characters (Unicode range: 0980-09FF)
        has_bengali = False
        for char in transcript_text:
            if '\u0980' <= char <= '\u09FF':  # Bengali Unicode range
                has_bengali = True
                break
        
        # Also check for common Bengali words/phrases
        bengali_indicators = ["আমি", "তুমি", "আপনি", "কী", "কেন", "কখন", "কোথায়", "কিভাবে", "ধন্যবাদ", "নমস্কার"]
        has_bengali_words = any(word in transcript_text for word in bengali_indicators)
        
        if has_bengali or has_bengali_words:
            language = "bn"
            print(f"[DEBUG] Detected Bengali language from transcription")
        else:
            print(f"[DEBUG] Detected English language from transcription")
        
        print(f"Transcription successful. Language: {language}, Text length: {len(transcript_text)}")
        return {"text": transcript_text, "language": language}
    
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"[ERROR] Audio transcription failed!")
        print(f"[ERROR] Error type: {error_type}")
        print(f"[ERROR] Error message: {error_msg}")
        import traceback
        traceback.print_exc()
        # Return empty transcript - the flow can continue but won't have transcript
        return {"text": "", "language": "en"}

def call_open_meteo(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "hourly":"temperature_2m,relativehumidity_2m,precipitation", "timezone":"auto"}
    r = requests.get(url, params=params, timeout=10)
    try:
        return r.json()
    except Exception:
        return {}

def validate_response_language(response_text: str, expected_language: str) -> str:
    """
    Validate that the response matches the expected language.
    If it doesn't, attempt to correct it or return a warning.
    Returns the (possibly corrected) response text.
    """
    if not response_text or not expected_language:
        return response_text
    
    # Detect actual language of response
    actual_language = detect_language_from_text(response_text)
    
    # If languages match, return as-is
    if actual_language == expected_language:
        print(f"[DEBUG] Response language validation: PASSED ({expected_language})")
        return response_text
    
    # Languages don't match - log warning
    print(f"[WARNING] Response language mismatch!")
    print(f"[WARNING] Expected: {expected_language}, Got: {actual_language}")
    print(f"[WARNING] Response preview: {response_text[:200]}...")
    
    # If response is in wrong language, we could try to regenerate
    # For now, just log and return - the LLM should have followed instructions
    # But we'll add a post-processing step to enforce language if needed
    
    # Count characters in each language to see if it's mixed
    bengali_chars = sum(1 for c in response_text if '\u0980' <= c <= '\u09FF')
    english_chars = sum(1 for c in response_text if c.isalpha() and ord(c) < 128)
    
    if expected_language == "bn" and bengali_chars == 0 and english_chars > 0:
        # Response is in English but should be Bengali
        print(f"[ERROR] Response is in English but should be in Bengali!")
        # Could add logic here to request regeneration, but for now just warn
    elif expected_language == "en" and bengali_chars > 0 and english_chars == 0:
        # Response is in Bengali but should be English
        print(f"[ERROR] Response is in Bengali but should be in English!")
    
    return response_text

def clean_text_for_tts(text: str) -> str:
    """
    Clean text for TTS by removing markdown, special symbols, and formatting.
    """
    import re
    # Remove markdown bold/italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold** -> bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # *italic* -> italic
    text = re.sub(r'__([^_]+)__', r'\1', text)  # __bold__ -> bold
    text = re.sub(r'_([^_]+)_', r'\1', text)  # _italic_ -> italic
    
    # Remove markdown headers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # Remove markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Remove markdown code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Remove markdown lists
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Remove extra symbols that TTS shouldn't read
    text = re.sub(r'[#*_~`]', '', text)
    
    # Remove multiple spaces and newlines
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n+', '. ', text)
    
    # Clean up
    text = text.strip()
    
    return text

def synthesize_tts(text: str, lang: str="bn") -> str:
    """
    Save TTS mp3 using gTTS and return the filepath.
    Cleans text before TTS to remove markdown and special symbols.
    Uses UPLOAD_DIR for persistent storage instead of /tmp.
    """
    from app.api.utils import UPLOAD_DIR
    from uuid import uuid4
    
    # Clean text before TTS
    cleaned_text = clean_text_for_tts(text)
    
    if not cleaned_text or len(cleaned_text.strip()) < 1:
        print("[WARNING] Text is empty after cleaning, using original")
        cleaned_text = text.strip()
    
    # Use UPLOAD_DIR instead of /tmp for persistent storage
    tts_filename = f"{uuid4().hex}.mp3"
    tts_path = os.path.join(UPLOAD_DIR, tts_filename)
    
    # Ensure UPLOAD_DIR exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    try:
        tts = gTTS(cleaned_text, lang=lang if lang else "en")
        tts.save(tts_path)
        
        # Verify file was actually created with retry logic (race condition fix)
        import time
        max_retries = 5
        retry_count = 0
        while retry_count < max_retries:
            if os.path.exists(tts_path):
                file_size = os.path.getsize(tts_path)
                if file_size > 0:  # File has content
                    print(f"[DEBUG] TTS generated: {len(cleaned_text)} characters (cleaned from {len(text)} original)")
                    print(f"[DEBUG] TTS saved to: {tts_path} (file size: {file_size} bytes)")
                    return tts_path
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(0.1)  # 100ms delay between retries
        
        # If we get here, file wasn't created properly
        raise Exception(f"TTS file was not created at {tts_path} after {max_retries} retries")
    except Exception as e:
        print(f"[ERROR] TTS generation failed: {e}")
        import traceback
        traceback.print_exc()
        # Try with original text as fallback
        try:
            tts = gTTS(text[:500], lang=lang if lang else "en")  # Limit length
            tts.save(tts_path)
            
            # Verify fallback file was created with retry logic
            import time
            max_retries = 5
            retry_count = 0
            while retry_count < max_retries:
                if os.path.exists(tts_path):
                    file_size = os.path.getsize(tts_path)
                    if file_size > 0:  # File has content
                        print(f"[DEBUG] TTS fallback saved to: {tts_path} (file size: {file_size} bytes)")
                        return tts_path
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(0.1)
            
            raise Exception(f"TTS fallback file was not created at {tts_path} after {max_retries} retries")
        except Exception as e2:
            print(f"[ERROR] TTS fallback also failed: {e2}")
            import traceback
            traceback.print_exc()
            raise

def call_gemini_llm(prompt: str, system_instruction: str = None) -> str:
    """
    Call Gemini LLM with a prompt and optional system instruction.
    NOTE: Gemini 2.5 Flash SDK doesn't support system_instruction parameter in constructor,
    so we embed system instructions directly into the prompt.
    """
    try:
        print(f"[DEBUG] call_gemini_llm called with system_instruction: {bool(system_instruction)}")
        print(f"[DEBUG] Prompt length: {len(prompt)} characters")
        
        # Since system_instruction parameter is not supported, embed it directly in prompt
        if system_instruction:
            print("[DEBUG] Embedding system instruction directly in prompt...")
            # Put system instruction at the very beginning of the prompt
            final_prompt = f"{system_instruction}\n\n{prompt}"
        else:
            print("[DEBUG] No system instruction provided, using prompt as-is...")
            final_prompt = prompt
        
        print("[DEBUG] Generating content with Gemini...")
        response = gemini_model.generate_content(final_prompt)
        print("[DEBUG] Response received successfully")
        
        # Handle different response structures from Gemini
        if not response:
            raise Exception("Empty response object from Gemini API")
        
        # Try to get text from response - handle different response structures
        result_text = None
        try:
            if hasattr(response, 'text') and response.text:
                result_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                # Some responses have candidates array
                if len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        result_text = ''.join([part.text for part in candidate.content.parts if hasattr(part, 'text')])
                    elif hasattr(candidate, 'text'):
                        result_text = candidate.text
            elif hasattr(response, 'parts'):
                # Direct parts access
                result_text = ''.join([part.text for part in response.parts if hasattr(part, 'text')])
        except Exception as extract_err:
            print(f"[WARNING] Error extracting text from response: {extract_err}")
            # Try to get text directly as fallback
            if hasattr(response, 'text'):
                result_text = response.text
        
        if not result_text or not result_text.strip():
            # Check if response was blocked
            if hasattr(response, 'prompt_feedback'):
                feedback = response.prompt_feedback
                if hasattr(feedback, 'block_reason') and feedback.block_reason:
                    raise Exception(f"Response blocked: {feedback.block_reason}")
            raise Exception("Empty or invalid response from Gemini API - no text content found")
        
        result = result_text.strip()
        print(f"[DEBUG] Response length: {len(result)} characters")
        return result
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"[ERROR] Gemini LLM call failed!")
        print(f"[ERROR] Error type: {error_type}")
        print(f"[ERROR] Error message: {error_msg}")
        print(f"[ERROR] Full error details:")
        import traceback
        traceback.print_exc()
        
        # Check for specific error types
        if "429" in error_msg or "quota" in error_msg.lower() or "ResourceExhausted" in error_msg:
            print("[ERROR] Quota/rate limit error detected")
            return "I apologize, but the AI service is currently experiencing high demand. Please try again in a few moments."
        
        if "API key" in error_msg or "authentication" in error_msg.lower() or "401" in error_msg or "403" in error_msg:
            print("[ERROR] API key authentication error")
            return "There's an issue with the AI service authentication. Please check the API configuration."
        
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            print("[ERROR] Timeout error")
            return "The request took too long to process. Please try again with a shorter query."
        
        if "invalid" in error_msg.lower() or "bad request" in error_msg.lower() or "400" in error_msg:
            print("[ERROR] Invalid request error")
            return "The request format was invalid. Please try rephrasing your question."
        
        # Return error with more context for debugging
        print(f"[ERROR] Unknown error type - returning generic message")
        return f"I'm having trouble processing your request. Error: {error_type}. Please try again or contact support."

# --- nodes ---
def detect_language_from_text(text: str) -> str:
    """
    Detect language from text input (for chat/text queries).
    Returns "bn" for Bengali, "en" for English.
    Uses comprehensive detection including Unicode ranges and common words.
    """
    if not text or not text.strip():
        return "en"
    
    text = text.strip()
    
    # DEBUG: Show what we're detecting
    print(f"[DEBUG] detect_language_from_text: Input text length: {len(text)}")
    print(f"[DEBUG] detect_language_from_text: First 50 chars: {repr(text[:50])}")
    
    # Count Bengali vs English characters for more accurate detection
    bengali_char_count = 0
    english_char_count = 0
    
    for char in text:
        # Bengali Unicode range: 0980-09FF (includes all Bengali characters)
        if '\u0980' <= char <= '\u09FF':
            bengali_char_count += 1
        # English letters (basic Latin)
        elif char.isalpha() and ord(char) < 128:
            english_char_count += 1
    
    print(f"[DEBUG] detect_language_from_text: Bengali chars found: {bengali_char_count}, English chars: {english_char_count}")
    
    # Check for common Bengali words/phrases (expanded list)
    bengali_indicators = [
        "আমি", "তুমি", "আপনি", "কী", "কেন", "কখন", "কোথায়", "কিভাবে", 
        "ধন্যবাদ", "নমস্কার", "ফসল", "ধান", "আলু", "টমেটো", "রোগ", "পোকা",
        "কৃষি", "চাষ", "জমি", "বীজ", "সার", "পানি", "বৃষ্টি", "সূর্য",
        "কীটনাশক", "ফল", "শাক", "সবজি", "গাছ", "গাছপালা"
    ]
    has_bengali_words = any(word in text for word in bengali_indicators)
    
    print(f"[DEBUG] detect_language_from_text: Bengali words found: {has_bengali_words}")
    
    # Decision logic: Bengali if we have Bengali characters OR Bengali words
    # Also consider ratio if both are present
    if bengali_char_count > 0:
        # If we have Bengali characters, it's definitely Bengali
        print(f"[DEBUG] ✅ DETECTED BENGALI: Bengali chars: {bengali_char_count}")
        return "bn"
    elif has_bengali_words:
        # Bengali words detected even without Bengali script (transliterated)
        print(f"[DEBUG] ✅ DETECTED BENGALI: Bengali words found")
        return "bn"
    elif english_char_count > 0 and bengali_char_count == 0:
        # Only English characters
        print(f"[DEBUG] DETECTED ENGLISH: English chars: {english_char_count}, Bengali: 0")
        return "en"
    else:
        # Default to English if unclear
        print(f"[DEBUG] UNCLEAR: Defaulting to English")
        return "en"

def stt_node(state: FarmState):
    """
    Speech-to-text node: handles both audio transcription and text input language detection.
    For text input, detects language. For audio input, transcribes and detects language.
    ALWAYS returns language in the state.
    """
    print(f"[DEBUG] STT node: Starting")
    print(f"[DEBUG] STT node: Has transcript: {bool(state.get('transcript'))}")
    print(f"[DEBUG] STT node: Has audio_path: {bool(state.get('audio_path'))}")
    
    # If transcript already exists (from text input), detect language from it
    if state.get("transcript"):
        transcript = state["transcript"]
        print(f"[DEBUG] STT node: Transcript exists, length={len(transcript)}")
        print(f"[DEBUG] STT node: Transcript repr: {repr(transcript[:100])}")
        # Detect language from the transcript text
        detected_lang = detect_language_from_text(transcript)
        print(f"[DEBUG] STT node: 🔍 DETECTED LANGUAGE: {detected_lang} from text input")
        print(f"[DEBUG] STT node: Full transcript: {transcript[:100]}...")
        return {"transcript": transcript, "language": detected_lang}
    
    # If no audio path, still need to return a language (default to English)
    if not state.get("audio_path"):
        print("[DEBUG] STT node: No audio path and no transcript, defaulting to English")
        return {"transcript": "", "language": "en"}
    
    # Transcribe audio using Gemini
    print(f"[DEBUG] STT node: Transcribing audio from: {state['audio_path']}")
    stt = transcribe_with_gemini(state["audio_path"])
    transcript = stt.get("text", "").strip()
    detected_lang = stt.get("language", "en")
    
    print(f"[DEBUG] STT node: Transcription complete")
    print(f"[DEBUG] STT node: Detected language: {detected_lang}")
    print(f"[DEBUG] STT node: Transcript length: {len(transcript)} characters")
    if transcript:
        print(f"[DEBUG] STT node: Transcript preview: {transcript[:100]}...")
    
    return {"transcript": transcript, "language": detected_lang}

def intent_node(state: FarmState):
    """
    Ask Gemini to extract structured information from the transcript:
    crop, symptoms, need_image (bool). We use a small prompt and expect JSON back.
    ALSO detects language from the transcript if not already detected (for text input).
    """
    transcript = state.get("transcript", "")
    
    # CRITICAL: Detect language if not already detected (for text input, since stt_node is skipped)
    language = state.get("language", "en")
    if transcript and (not language or language not in ["bn", "en"]):
        language = detect_language_from_text(transcript)
        print(f"[DEBUG] Intent node: Detected language from transcript: {language}")
    
    if not transcript:
        # If no transcript, skip intent extraction and go to reasoning
        # Still add empty message to maintain flow
        existing_messages = state.get("messages", [])
        if not existing_messages:
            existing_messages = [{"role":"user", "content": ""}]
        return {
            "messages": existing_messages,
            "crop": None,
            "language": language
        }
    
    system_instruction = """You are an information extraction assistant for KrishiBondhu.
Your task is to analyze farmer queries and extract structured information.

Extract and return ONLY valid JSON with these exact keys:
- crop: string or null (the specific crop mentioned, e.g., "rice", "tomato", "potato", "wheat")
- symptoms: string (any symptoms, issues, or problems described by the farmer)
- need_image: boolean (true if the query suggests the farmer should upload an image for better diagnosis)
- note: string (a brief, one-sentence summary of what the farmer is asking about)

IMPORTANT:
- Return ONLY the JSON object, no explanations, no markdown formatting, just pure JSON
- If no crop is mentioned, set crop to null
- Be accurate in identifying crop names and symptoms
- Set need_image to true if the query is about visual problems (diseases, pests, leaf issues, etc.)"""
    
    prompt = f"Transcript: {transcript}\n\nExtract the information as JSON:"
    
    try:
        response_text = call_gemini_llm(prompt, system_instruction)
        
        # Try to extract JSON from response
        # Gemini might return JSON wrapped in markdown code blocks
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract values manually
            parsed = {
                "crop": None,
                "symptoms": transcript,
                "need_image": False,
                "note": response_text
            }
    except Exception as e:
        print(f"Error in intent extraction: {e}")
        parsed = {"crop": None, "symptoms": transcript, "need_image": False, "note": transcript}
    
    updates = {
        "messages": state.get("messages", []) + [{"role":"user", "content": transcript}],
        "language": language  # ALWAYS set the detected language
    }
    print(f"[DEBUG] Intent node: Setting language: {language}")
    
    # Don't set reply_text here - let reasoning_node handle it
    if parsed.get("crop"):
        updates["crop"] = parsed["crop"]
    if parsed.get("need_image"):
        updates["need_image"] = parsed["need_image"]
    
    return updates

def vision_node(state: FarmState):
    if not state.get("image_path"):
        return {}
    res = run_vision_classifier(state["image_path"])
    return {"vision_result": res}

def weather_node(state: FarmState):
    gps = state.get("gps")
    if not gps or not gps.get("lat") or not gps.get("lon"):
        return {}
    w = call_open_meteo(gps.get("lat"), gps.get("lon"))
    return {"weather_forecast": w}

def reasoning_node(state: FarmState):
    """
    Use Gemini to generate an intelligent response integrating all available information:
    transcript, vision results, weather data, and crop information.
    
    CRITICAL: Each request is independently processed - no carryover from previous requests.
    """
    transcript = state.get("transcript", "").strip()
    vision_result = state.get("vision_result", {}) or {}  # Ensure empty dict, not None
    weather_forecast = state.get("weather_forecast", {}) or {}  # Ensure empty dict, not None
    crop = state.get("crop", "")
    gps = state.get("gps", {}) or {}  # Ensure empty dict
    language = state.get("language", "en")
    has_image = bool(state.get("image_path"))
    has_audio = bool(state.get("audio_path"))
    
    # CRITICAL DEBUG: Log incoming state to catch contamination
    print(f"[DEBUG] ===== REASONING NODE START =====")
    print(f"[DEBUG] Transcript: {transcript[:100] if transcript else '(empty)'}...")
    print(f"[DEBUG] Crop detected: {crop if crop else '(none)'}")
    print(f"[DEBUG] Vision result keys: {list(vision_result.keys()) if vision_result else '(empty)'}")
    print(f"[DEBUG] Language: {language}")
    print(f"[DEBUG] Has image: {has_image}, Has audio: {has_audio}")
    print(f"[DEBUG] ===== END INCOMING STATE =====")
    
    # CRITICAL: If language not set, detect from transcript
    if not language or language not in ["bn", "en"]:
        if transcript:
            language = detect_language_from_text(transcript)
            print(f"[DEBUG] Reasoning node: Language not in state, detected from transcript: {language}")
        else:
            language = "en"  # Default to English
            print(f"[DEBUG] Reasoning node: No transcript, defaulting to English")
    
    print(f"[DEBUG] Reasoning node: Using language: {language} for response generation")
    
    # Determine input type for better system instruction
    input_type = "text"
    if has_audio:
        input_type = "voice"
    elif has_image and not transcript:
        input_type = "image_only"
    elif has_image and transcript:
        input_type = "image_with_text"
    
    # If no transcript and no image, return a helpful message
    if not transcript and not has_image:
        return {"reply_text": "Please provide a question, upload an image, or record your voice to get assistance."}
    
    # Enhanced system instruction based on input type
    if input_type == "voice":
        system_instruction = """You are KrishiBondhu, an intelligent voice assistant for farmers in Bangladesh. 
Your role is to help farmers with their agricultural questions and problems.

🚨 CRITICAL - PROCESS ONLY CURRENT REQUEST 🚨
- You are analyzing ONE farmer query in THIS conversation
- Do NOT reference, assume, or carry over any information from previous conversations or uploads
- Focus EXCLUSIVELY on the current question being asked
- Ignore any crops, images, or context mentioned in previous requests
- Answer ONLY what is asked in the current query

KEY RESPONSIBILITIES:
- Listen carefully to the farmer's voice query (transcribed text provided)
- Provide clear, practical, and actionable farming advice based ONLY on what the farmer actually asked
- CRITICALLY IMPORTANT: Respond in the EXACT SAME LANGUAGE as the farmer's query
  * If the farmer spoke in Bengali (বাংলা), you MUST respond ONLY in Bengali
  * If the farmer spoke in English, you MUST respond ONLY in English
  * Do NOT mix languages - use only the language the farmer used
- Be empathetic, patient, and understanding of farmer's concerns
- If disease or pest issues are mentioned, provide specific treatment recommendations
- Consider weather conditions when giving advice
- Use simple, easy-to-understand language suitable for farmers
- If an image is also provided, analyze it along with the voice query

ACCURACY REQUIREMENTS:
- Answer ONLY what the farmer asked - do NOT add information they didn't request
- Do NOT make up or hallucinate information
- If you're uncertain about something, say so clearly
- Base your advice on the actual query, not assumptions
- Do NOT invent crop names, diseases, or treatments that weren't mentioned
- Each image is a NEW request - do not assume it's the same crop from a previous query

RESPONSE GUIDELINES:
- Keep responses concise but comprehensive (2-4 sentences for simple queries, up to 6 for complex issues)
- Always provide actionable steps when possible
- If you detect crop diseases, suggest specific treatments (organic or chemical)
- Mention relevant weather considerations
- Be encouraging and supportive
- ALWAYS match the language of your response to the language of the farmer's voice query"""
    
    elif input_type == "image_only" or input_type == "image_with_text":
        system_instruction = """You are KrishiBondhu, an expert agricultural image analysis assistant for farmers in Bangladesh.
Your specialty is analyzing crop images to identify diseases, pests, nutrient deficiencies, and growth issues.

🚨 CRITICAL - PROCESS ONLY CURRENT IMAGE 🚨
- You are analyzing ONE image in THIS request
- Do NOT reference, assume, or carry over any information from previous image uploads
- Do NOT assume this is the same crop as a previous image - each image is analyzed independently
- Focus EXCLUSIVELY on what you see in the CURRENT image
- Ignore any context from previous conversations
- Analyze THIS image based on its own visual evidence ONLY

KEY RESPONSIBILITIES:
- Carefully examine the provided crop/plant image
- Identify ONLY what you can actually see in the image - do NOT invent or assume
- Provide specific, actionable treatment recommendations based on visible evidence
- Consider the crop type if mentioned or clearly visible in the image
- CRITICALLY IMPORTANT: Respond in the EXACT SAME LANGUAGE as the farmer's question (if provided)
  * If the farmer asked in Bengali (বাংলা), you MUST respond ONLY in Bengali
  * If the farmer asked in English, you MUST respond ONLY in English
  * If no question is provided, detect from context or default to Bengali for Bangladesh farmers
  * Do NOT mix languages - use only the language the farmer used
- Be precise about what you observe in the image

ACCURACY REQUIREMENTS:
- Describe ONLY what is visible in the image - do NOT make up details
- If you cannot clearly identify a disease or pest, say so explicitly
- Do NOT hallucinate or invent problems that aren't visible
- Base your analysis on actual visual evidence, not assumptions
- If the image quality is poor or unclear, mention this
- CRITICAL: Do not assume this is rice/wheat/any crop just because a previous image was that crop
- Each image is a FRESH analysis - identify the actual crop visible in THIS image

ANALYSIS GUIDELINES:
- Describe what you see in the image (leaf color, spots, damage, growth stage, etc.)
- Identify the specific problem ONLY if clearly visible (disease name, pest type, deficiency type)
- Provide treatment steps (immediate actions and long-term solutions)
- Suggest preventive measures
- If uncertain, clearly state what you can see and recommend consulting an agricultural expert
- Consider weather and location context when relevant
- ALWAYS match the language of your response to the language of the farmer's question"""
    
    else:  # text/chat
        system_instruction = """You are KrishiBondhu, a knowledgeable and friendly chat assistant for farmers in Bangladesh.
You help farmers with agricultural questions, farming advice, and problem-solving through text conversation.

🚨 CRITICAL INSTRUCTIONS 🚨
- You have access to BOTH the current message AND previous chat history (if available)
- YOU SHOULD use chat history to provide CONTINUOUS, CONTEXT-AWARE assistance
- Answer based on what the farmer is asking NOW, with full awareness of previous questions
- IMPORTANT: Only use previous context IF it's directly relevant to the current question
- If the current question asks about something different from before, treat it as a new topic
- Each new image is a separate request - don't assume it's the same crop as a previous image

KEY RESPONSIBILITIES:
- Answer farming questions clearly and accurately 
- Remember and reference previous conversations when relevant to help the farmer
- Provide practical, actionable advice
- Help with crop selection, planting, care, and harvesting
- Assist with disease and pest management
- Offer weather-based farming recommendations
- CRITICALLY IMPORTANT: Respond in the EXACT same language as the farmer's input
  * If the farmer writes in Bengali (বাংলা), you MUST respond in Bengali
  * If the farmer writes in English, you MUST respond in English
  * Do NOT mix languages - use only the language the farmer used
- Be conversational, friendly, and supportive
- Show that you remember previous discussions when relevant

USING CHAT HISTORY:
- ✅ DO reference previous questions when the farmer is following up or asking related questions
- ✅ DO remember crop information from earlier in the conversation
- ✅ DO provide continuous support by referencing earlier solutions you've suggested
- ✅ DO ask clarifying questions like "Is this the same rice crop we discussed earlier?"
- ❌ DON'T assume context if the farmer asks about something completely different
- ❌ DON'T reference images from previous messages unless explicitly asked
- ❌ DON'T assume a disease diagnosis from earlier applies to a new image

ACCURACY REQUIREMENTS:
- Answer ONLY what the farmer asked - do NOT add information they didn't request
- Do NOT make up or hallucinate information
- If you're uncertain about something, say so clearly in the same language
- Base your advice on the actual query, not assumptions
- Do NOT invent crop names, diseases, or treatments that weren't mentioned
- If the question is unclear, ask for clarification in the same language
- If a question requires identifying a new crop, ask or verify with the farmer

CONVERSATION GUIDELINES:
- Maintain a helpful, patient, and encouraging tone
- Ask clarifying questions if needed (in the same language as the farmer)
- Provide step-by-step guidance for complex tasks
- Reference local farming practices in Bangladesh when relevant
- If an image is attached, analyze it along with the text query
- ALWAYS match the language of your response to the language of the farmer's question
- Use the chat history to provide continuous, coherent support across multiple turns"""
    
    # Build comprehensive context for Gemini
    context_parts = []
    
    if transcript:
        context_parts.append(f"Farmer's query/question: {transcript}")
    elif has_image:
        context_parts.append("Farmer has uploaded an image for analysis (no text question provided).")
    
    if crop:
        context_parts.append(f"Identified crop: {crop}")
    
    if vision_result:
        if vision_result.get("disease") and vision_result.get("disease") != "no_detection":
            disease = vision_result.get("disease", "unknown")
            confidence = vision_result.get("confidence", 0)
            context_parts.append(f"Computer vision analysis detected: {disease} (confidence: {confidence:.1%})")
            if vision_result.get("raw_detections"):
                detections = vision_result.get("raw_detections", [])
                if detections:
                    context_parts.append(f"Number of detections: {len(detections)}")
        elif vision_result.get("error"):
            context_parts.append(f"Vision analysis note: {vision_result.get('error')}")
    
    if weather_forecast and weather_forecast.get("hourly"):
        hourly = weather_forecast["hourly"]
        weather_info = []
        if hourly.get("temperature_2m") and len(hourly["temperature_2m"]) > 0:
            temp = hourly["temperature_2m"][0]
            weather_info.append(f"Temperature: {temp}°C")
        if hourly.get("relativehumidity_2m") and len(hourly["relativehumidity_2m"]) > 0:
            humidity = hourly["relativehumidity_2m"][0]
            weather_info.append(f"Humidity: {humidity}%")
        if hourly.get("precipitation") and len(hourly["precipitation"]) > 0:
            precip = hourly["precipitation"][0]
            if precip > 0:
                weather_info.append(f"Expected precipitation: {precip}mm")
        if weather_info:
            context_parts.append(f"Weather conditions: {', '.join(weather_info)}")
    
    if gps.get("lat") and gps.get("lon"):
        context_parts.append(f"Farmer's location: Latitude {gps['lat']:.4f}, Longitude {gps['lon']:.4f} (Bangladesh)")
    
    # Determine response language - CRITICAL: Must match input language
    response_lang = "Bengali (বাংলা)" if language == "bn" else "English"
    if not language or language == "en":
        response_lang = "English"
    
    print(f"[DEBUG] Reasoning node: Response language selected: {response_lang} (code: {language})")
    
    # Add explicit language instruction to system instruction - STRONGER ENFORCEMENT
    if language == "bn":
        language_instruction = f"""

You MUST respond ONLY in Bengali (বাংলা). Every single word must be in Bengali script.

ABSOLUTE REQUIREMENTS FOR BENGALI RESPONSE:
- Write response using ONLY Bengali script (বাংলা characters: অ আ ই ঈ উ ঊ ঋ এ ঐ ও ঔ ক খ গ ঘ ঙ চ ছ জ ঝ ঞ ট ঠ ড ঢ ণ ত থ দ ধ ন প ফ ব ভ ম য র ল শ ষ স হ)
- Do NOT use ANY English words, numbers, or Latin characters
- Each word must be in Bengali
- Do NOT mix languages

Example of CORRECT Bengali response:
"আপনার ধানের পাতা হলুদ হওয়া সাধারণত পুষ্টির অভাব থেকে হয়। জিঙ্ক বা আয়রনের অভাব দেখা দেয় তখন পাতা হলুদ হয়ে যায়। আপনি ইউরিয়া সার প্রয়োগ করুন এবং সেচ প্রদান করুন।"

WRONG examples you MUST NOT do:
- "আপনার rice এর পাতা yellowing" ❌ (Has English words)
- "আপনার শসার nitrogen deficiency আছে" ❌ (Has English)
- "Your ধান has disease" ❌ (Mixed languages)

Remember: The user asked in Bengali. You MUST respond ONLY in Bengali script, no exceptions."""
    else:
        language_instruction = f"""

You MUST respond ONLY in English. Every single word must be in English.

ABSOLUTE REQUIREMENTS FOR ENGLISH RESPONSE:
- Write response using ONLY English words and characters
- Do NOT use ANY Bengali words or script
- Each word must be in English
- Do NOT mix languages

Example of CORRECT English response:
"Your rice leaves turning yellow typically indicates nutrient deficiency. It could be lack of nitrogen, zinc, or iron. Apply urea fertilizer and provide adequate irrigation."

WRONG examples you MUST NOT do:
- "আপনার rice has disease" ❌ (Has Bengali)
- "Your ধান needs আরো water" ❌ (Mixed)
- "Rice রোগ detected" ❌ (Mixed)

Remember: The user asked in English. You MUST respond ONLY in English, no exceptions."""
    
    context = "\n".join(context_parts) if context_parts else "No additional context available."
    
    # Build prompt based on input type with STRONG language enforcement
    if input_type == "image_only":
        prompt = f"""🚨 CRITICAL: Analyze ONLY the image provided in THIS request. Ignore any previous context.

Analyze the provided image and provide a comprehensive response to help the farmer.

CURRENT REQUEST CONTEXT (This is all you should consider):
{context}

CONTEXT ISOLATION: Do NOT reference any previous images, crops, or conversations. This image is analyzed independently.

Please:
1. Describe what you see in the image (crop type, growth stage, visible issues)
2. Identify any problems (diseases, pests, nutrient deficiencies, etc.) - ONLY based on what's visible
3. Provide specific treatment recommendations
4. Suggest preventive measures

{language_instruction}
The farmer's input language is: {response_lang}. You MUST respond in {response_lang}."""
        
        print(f"[DEBUG] Language in prompt for image_only: {response_lang}")
        print(f"[DEBUG] Language instruction included in prompt")
    
    elif input_type == "image_with_text":
        prompt = f"""🚨 CRITICAL: Analyze ONLY THIS image and question. Ignore any previous context, conversations, or images.

The farmer has provided both an image and a question. Analyze the image in context of their question.

CURRENT REQUEST CONTEXT (This is all you should consider):
{context}

CONTEXT ISOLATION: Do NOT reference previous images, crops, or conversations. Each request is independent.

Please:
1. Address the farmer's specific question
2. Analyze the image in relation to their question
3. Provide comprehensive advice combining both the question and image analysis
4. Give actionable recommendations

{language_instruction}
The farmer's input language is: {response_lang}. You MUST respond in {response_lang}."""
        
        print(f"[DEBUG] Language in prompt for image_with_text: {response_lang}")
        print(f"[DEBUG] Language instruction included in prompt")
    
    else:  # voice or text
        prompt = f"""🚨 CRITICAL: Answer ONLY THIS question. Do NOT reference previous queries, conversations, or context.

Based on the following information, provide a helpful and comprehensive response to the farmer.

CURRENT REQUEST CONTEXT (This is all you should consider):
{context}

CONTEXT ISOLATION: Each request is independent. Do NOT assume context from previous messages or uploads.

Please provide:
1. A direct answer to the farmer's question
2. Practical, actionable advice
3. Specific recommendations when applicable
4. Any relevant warnings or considerations

{language_instruction}
The farmer's input language is: {response_lang}. You MUST respond in {response_lang}. If the farmer asked in Bengali, respond in Bengali. If they asked in English, respond in English."""
        
        print(f"[DEBUG] Language in prompt for text/voice: {response_lang}")
        print(f"[DEBUG] Language instruction included in prompt")
    
    try:
        # If there's an image, include it for multimodal understanding
        if state.get("image_path") and os.path.exists(state["image_path"]):
            image_file = None
            try:
                print(f"Reading image for multimodal analysis: {state['image_path']}")
                # Read image file
                import mimetypes
                with open(state["image_path"], 'rb') as f:
                    image_data = f.read()
                
                # Determine MIME type
                mime_type, _ = mimetypes.guess_type(state["image_path"])
                if not mime_type:
                    mime_type = "image/jpeg"
                
                try:
                    # Use Part.from_data for image
                    from google.generativeai.types import Part
                    image_part = Part.from_data(data=image_data, mime_type=mime_type)
                    
                    # Use model with system instruction for image analysis
                    try:
                        model_with_system = genai.GenerativeModel(
                            'models/gemini-2.5-flash',
                            system_instruction=system_instruction
                        )
                    except:
                        # Fallback without system instruction
                        model_with_system = gemini_model
                        prompt = f"{system_instruction}\n\n{prompt}"
                    
                    print("Generating multimodal response with image...")
                    response = model_with_system.generate_content([image_part, prompt])
                    
                    # Handle different response structures
                    if not response:
                        raise Exception("Empty response from Gemini multimodal API")
                    
                    reply = None
                    if hasattr(response, 'text') and response.text:
                        reply = response.text
                    elif hasattr(response, 'candidates') and response.candidates and len(response.candidates) > 0:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            reply = ''.join([part.text for part in candidate.content.parts if hasattr(part, 'text')])
                        elif hasattr(candidate, 'text'):
                            reply = candidate.text
                    
                    if not reply or not reply.strip():
                        raise Exception("Empty reply from Gemini multimodal API")
                    
                    reply = reply.strip()
                    print("Multimodal response generated successfully")
                except ImportError:
                    # Part.from_data not available, try direct file path
                    try:
                        response = gemini_model.generate_content([state["image_path"], prompt])
                        if hasattr(response, 'text') and response.text:
                            reply = response.text.strip()
                        else:
                            raise Exception("Could not extract text from response")
                    except Exception as e2:
                        print(f"Error with direct file path: {e2}")
                        # Last resort: base64 encoding
                        import base64
                        image_b64 = base64.b64encode(image_data).decode('utf-8')
                        data_uri = f"data:{mime_type};base64,{image_b64}"
                        response = gemini_model.generate_content([data_uri, prompt])
                        if hasattr(response, 'text') and response.text:
                            reply = response.text.strip()
                        else:
                            raise Exception("Could not extract text from base64 response")
                except Exception as e:
                    print(f"Error with image in reasoning: {e}")
                    import traceback
                    traceback.print_exc()
                    reply = call_gemini_llm(prompt, system_instruction)
            except Exception as e:
                print(f"Error processing image with Gemini: {e}")
                import traceback
                traceback.print_exc()
                reply = call_gemini_llm(prompt, system_instruction)
        else:
            print("[DEBUG] Reasoning node - generating text-only response...")
            print(f"[DEBUG] Input type: {input_type}")
            print(f"[DEBUG] Has transcript: {bool(transcript)}")
            print(f"[DEBUG] Has image: {has_image}")
            print(f"[DEBUG] Language: {language}")
            reply = call_gemini_llm(prompt, system_instruction)
            print("[DEBUG] Response generated successfully")
        
        if not reply or reply.strip() == "":
            raise Exception("Empty reply from call_gemini_llm")
        
        # Validate and enforce response language - regenerate if wrong language
        actual_lang = detect_language_from_text(reply)
        max_retries = 2
        retry_count = 0
        
        while actual_lang != language and retry_count < max_retries:
            print(f"[WARNING] Response language mismatch! Expected: {language}, Got: {actual_lang}")
            print(f"[WARNING] Attempting to regenerate response (retry {retry_count + 1}/{max_retries})...")
            
            # Create a stronger prompt with explicit language correction
            response_lang_name = "Bengali (বাংলা)" if language == "bn" else "English"
            correction_prompt = f"""The previous response was in the wrong language. 

ORIGINAL QUERY: {transcript if transcript else 'Image analysis request'}

PREVIOUS RESPONSE (WRONG LANGUAGE): {reply[:200]}...

CRITICAL: You MUST respond in {response_lang_name} ONLY. The previous response was in {actual_lang} which is incorrect.

{language_instruction}

Please regenerate your response in {response_lang_name} ONLY."""
            
            try:
                if state.get("image_path") and os.path.exists(state["image_path"]):
                    # For image requests, regenerate with image
                    import mimetypes
                    with open(state["image_path"], 'rb') as f:
                        image_data = f.read()
                    mime_type, _ = mimetypes.guess_type(state["image_path"])
                    if not mime_type:
                        mime_type = "image/jpeg"
                    
                    try:
                        from google.generativeai.types import Part
                        image_part = Part.from_data(data=image_data, mime_type=mime_type)
                        try:
                            model_with_system = genai.GenerativeModel(
                                'models/gemini-2.5-flash',
                                system_instruction=system_instruction
                            )
                        except:
                            model_with_system = gemini_model
                            correction_prompt = f"{system_instruction}\n\n{correction_prompt}"
                        
                        response = model_with_system.generate_content([image_part, correction_prompt])
                        if hasattr(response, 'text') and response.text:
                            reply = response.text.strip()
                        elif hasattr(response, 'candidates') and response.candidates:
                            candidate = response.candidates[0]
                            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                                reply = ''.join([part.text for part in candidate.content.parts if hasattr(part, 'text')]).strip()
                            elif hasattr(candidate, 'text'):
                                reply = candidate.text.strip()
                    except:
                        reply = call_gemini_llm(correction_prompt, system_instruction)
                else:
                    reply = call_gemini_llm(correction_prompt, system_instruction)
                
                actual_lang = detect_language_from_text(reply)
                retry_count += 1
                
                if actual_lang == language:
                    print(f"[SUCCESS] Response regenerated successfully in correct language: {language}")
                    break
            except Exception as retry_err:
                print(f"[ERROR] Failed to regenerate response: {retry_err}")
                break
        
        # Final validation
        final_lang = detect_language_from_text(reply)
        if final_lang != language:
            print(f"[ERROR] Response still in wrong language after {retry_count} retries. Expected: {language}, Got: {final_lang}")
            print(f"[ERROR] Response preview: {reply[:300]}...")
        else:
            print(f"[SUCCESS] Response language validated: {language}")
        
        print(f"[DEBUG] Response length: {len(reply)} characters")
        print(f"[DEBUG] Final response language: {final_lang} (expected: {language})")
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"[ERROR] Reasoning node failed!")
        print(f"[ERROR] Error type: {error_type}")
        print(f"[ERROR] Error message: {error_msg}")
        import traceback
        traceback.print_exc()
        
        # Fallback response - always provide something helpful
        if transcript:
            # Try to provide basic advice based on keywords
            transcript_lower = transcript.lower()
            if "tomato" in transcript_lower or "tomato" in transcript_lower:
                reply = "In Bangladesh, tomatoes can be cultivated in two main seasons: winter (October-February) and summer (March-June). For winter cultivation, start seeds in September-October. Ensure well-drained soil, regular watering, and protection from cold. For summer, provide shade during peak heat. Use organic fertilizers and maintain proper spacing (60cm between plants)."
            elif "leaf" in transcript_lower or "disease" in transcript_lower:
                reply = "Leaf problems can be caused by various factors: fungal diseases (use fungicides), pests (apply neem oil), nutrient deficiencies (add balanced fertilizer), or water issues (ensure proper drainage). If you can share an image, I can provide more specific diagnosis."
            else:
                reply = f"Thank you for your question: '{transcript}'. I'm currently experiencing some technical difficulties, but here's general farming advice: Ensure proper soil preparation, adequate water supply, timely fertilization, and pest management. For specific crop advice, please try again in a moment."
        else:
            reply = "I received your request but couldn't process it fully. Please try again, or share more details about your farming question."
    
    # Ensure we always return a reply
    if not reply or reply.strip() == "":
        reply = "I'm here to help with your farming questions. Please try asking again or provide more details about your crop or problem."
    
    # CRITICAL: Return language in state so TTS node can use it
    return {
        "reply_text": reply,
        "language": language  # Ensure language is preserved for TTS
    }

def tts_node(state: FarmState):
    """
    Text-to-speech node: generates audio from reply text.
    Ensures correct language is used for TTS based on detected language or reply text.
    """
    reply_text = state.get("reply_text", "")
    if not reply_text or reply_text.strip() == "":
        print("[DEBUG] TTS node: No reply text, skipping TTS")
        return {}
    
    # Get language from state (detected from input)
    lang = state.get("language", None)
    
    # If language not in state, detect from reply text
    if not lang or not isinstance(lang, str):
        print("[DEBUG] TTS node: Language not in state, detecting from reply text")
        lang = detect_language_from_text(reply_text)
        print(f"[DEBUG] TTS node: Detected language from reply: {lang}")
    else:
        print(f"[DEBUG] TTS node: Using language from state: {lang}")
    
    # Validate that reply text matches the detected language
    reply_lang = detect_language_from_text(reply_text)
    if reply_lang != lang:
        print(f"[WARNING] TTS node: Language mismatch! State lang: {lang}, Reply lang: {reply_lang}")
        print(f"[WARNING] TTS node: Using reply text language for TTS: {reply_lang}")
        lang = reply_lang  # Use the actual language of the reply
    
    # Map language codes for gTTS (gTTS uses 'bn' for Bengali, 'en' for English)
    lang_map = {"bn": "bn", "en": "en", "bn-BD": "bn", "en-US": "en", "en-GB": "en"}
    tts_lang = lang_map.get(lang.lower() if lang else "en", "en")
    
    print(f"[DEBUG] TTS node: Generating TTS in language: {tts_lang}")
    print(f"[DEBUG] TTS node: Reply text length: {len(reply_text)} characters")
    
    try:
        path = synthesize_tts(reply_text, lang=tts_lang)
        
        # Verify file exists before returning
        if not os.path.exists(path):
            print(f"[ERROR] TTS file was returned but doesn't exist: {path}")
            raise Exception(f"TTS file not found at {path}")
        
        file_size = os.path.getsize(path)
        print(f"[DEBUG] TTS node: TTS generated successfully at: {path} (size: {file_size} bytes)")
        return {"tts_path": path}
    except Exception as e:
        print(f"[ERROR] TTS generation failed: {e}")
        import traceback
        traceback.print_exc()
        # Try with English as fallback
        try:
            print("[DEBUG] TTS node: Attempting fallback with English")
            path = synthesize_tts(reply_text[:500], lang="en")  # Limit length for fallback
            
            # Verify fallback file exists
            if os.path.exists(path):
                file_size = os.path.getsize(path)
                print(f"[DEBUG] TTS node: Fallback TTS generated at: {path} (size: {file_size} bytes)")
                return {"tts_path": path}
            else:
                print(f"[ERROR] TTS fallback file not found: {path}")
                return {}
        except Exception as e2:
            print(f"[ERROR] TTS fallback also failed: {e2}")
            import traceback
            traceback.print_exc()
            return {}

async def respond_node(state: FarmState):
    """
    Persist conversation to database.
    Gracefully handles database connection errors - the flow continues even if DB is unavailable.
    """
    from app.db import AsyncSessionLocal
    from app.models.db_models import Conversation, User
    from sqlalchemy import select
    from sqlalchemy.exc import OperationalError
    
    # Get user_id string from state
    user_id_str = state.get("user_id", "unknown")
    
    # Extract confidence and media_url from vision_result if available
    vision_result = state.get("vision_result", {})
    confidence = vision_result.get("confidence") if vision_result else None
    media_url = state.get("image_path")  # Store image path if available
    
    try:
        async with AsyncSessionLocal() as session:
            try:
                # Try to find or create user by external_id
                user = None
                if user_id_str and user_id_str != "unknown":
                    result = await session.execute(
                        select(User).where(User.external_id == user_id_str)
                    )
                    user = result.scalar_one_or_none()
                    if not user:
                        # Create new user if doesn't exist
                        user = User(external_id=user_id_str)
                        session.add(user)
                        await session.flush()  # Flush to get the user.id
                
                # Create conversation record
                conversation = Conversation(
                    user_id=user.id if user else None,
                    transcript=state.get("transcript", ""),
                    tts_path=state.get("tts_path", ""),
                    media_url=media_url,
                    confidence=confidence,
                    meta_data={
                        "user_id": user_id_str,
                        "crop": state.get("crop"),
                        "gps": state.get("gps"),
                        "language": state.get("language"),
                        "vision_result": state.get("vision_result"),
                        "weather_forecast": state.get("weather_forecast"),
                    }
                )
                session.add(conversation)
                await session.commit()
                await session.refresh(conversation)
                print(f"Successfully saved conversation to database for user: {user_id_str}")
            except (OperationalError, ConnectionRefusedError) as db_error:
                await session.rollback()
                # Database connection error - log but don't fail
                print(f"Database not available - conversation not saved: {db_error}")
                print("Note: The assistant will still work, but conversation history won't be stored.")
            except Exception as e:
                await session.rollback()
                # Other errors - log but don't fail the flow
                print(f"Error persisting conversation: {e}")
                import traceback
                traceback.print_exc()
    except (OperationalError, ConnectionRefusedError) as db_error:
        # Database connection failed at session creation level
        print(f"Database connection unavailable - conversation not saved: {db_error}")
        print("Note: The assistant will still work, but conversation history won't be stored.")
    except Exception as e:
        # Any other unexpected error
        print(f"Unexpected error in respond_node: {e}")
        import traceback
        traceback.print_exc()
    
    return {}

# Build graph
graph = StateGraph(FarmState)
graph.add_node("stt", stt_node)
graph.add_node("intent", intent_node)
graph.add_node("vision", vision_node)
graph.add_node("weather", weather_node)
graph.add_node("reason", reasoning_node)
graph.add_node("tts", tts_node)
graph.add_node("respond", respond_node)

# Conditional: if audio provided -> stt, else -> intent (for text/image-only)
def has_audio(state):
    # LangGraph conditional edges need to return the key string that matches the mapping
    if state.get("audio_path"):
        return "stt"
    return "intent"

graph.add_conditional_edges(START, has_audio, {"stt": "stt", "intent": "intent"})
graph.add_edge("stt", "intent")

# Conditional: if image provided -> vision else -> weather
def need_vision(state):
    # LangGraph conditional edges need to return the key string that matches the mapping
    if state.get("image_path"):
        return "vision"
    return "weather"

graph.add_conditional_edges("intent", need_vision, {"vision": "vision", "weather": "weather"})

graph.add_edge("vision", "weather")
graph.add_edge("weather", "reason")
graph.add_edge("reason", "tts")
graph.add_edge("tts", "respond")
graph.add_edge("respond", END)

app = graph.compile()

# allow simple CLI test
if __name__ == "__main__":
    import asyncio
    initial = {"audio_path": "/tmp/example.mp3", "user_id": "demo", "gps": {"lat": 23.7, "lon": 90.4}, "messages": []}
    # Note: LangGraph will handle async nodes internally
    out = app.invoke(initial)
    print(json.dumps(out, indent=2, default=str))
