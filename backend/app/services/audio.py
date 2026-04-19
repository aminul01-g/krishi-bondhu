
import os
import mimetypes
import json
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from app.core.prompts import GEMINI_TRANSCRIPTION_PROMPT

load_dotenv()

try:
    from google.cloud import speech
except ImportError:
    speech = None

GOOGLE_SPEECH_CREDENTIALS_JSON = os.getenv("GOOGLE_SPEECH_CREDENTIALS_JSON") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
HUGGINGFACE_SPEECH_MODEL = os.getenv("HUGGINGFACE_SPEECH_MODEL", "openai/whisper-large-v2")

# Initialize Gemini model for audio (can reuse the one from LLM service or separate)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('models/gemini-2.5-flash')

def detect_language_from_text(text: str) -> str:
    """
    Detect language from text input.
    Returns "bn" for Bengali, "en" for English.
    """
    if not text or not text.strip():
        return "en"
    
    text = text.strip()
    
    bengali_char_count = 0
    english_char_count = 0
    
    for char in text:
        if '\u0980' <= char <= '\u09FF':
            bengali_char_count += 1
        elif char.isalpha() and ord(char) < 128:
            english_char_count += 1
    
    bengali_indicators = [
        "আমি", "তুমি", "আপনি", "কী", "কেন", "কখন", "কোথায়", "কিভাবে", 
        "ধন্যবাদ", "নমস্কার", "ফসল", "ধান", "আলু", "টমেটো", "রোগ", "পোকা",
        "কৃষি", "চাষ", "জমি", "বীজ", "সার", "পানি", "বৃষ্টি", "সূর্য",
        "কীটনাশক", "ফল", "শাক", "সবজি", "গাছ", "গাছপালা"
    ]
    has_bengali_words = any(word in text for word in bengali_indicators)
    
    if bengali_char_count > 0 or has_bengali_words:
        return "bn"
    elif english_char_count > 0 and bengali_char_count == 0:
        return "en"
    else:
        return "en"


def is_unclear_transcript(transcript: str) -> bool:
    if not transcript or not transcript.strip():
        return True
    normalized = transcript.strip()
    if normalized == "EMPTY_AUDIO":
        return True
    words = normalized.split()
    if len(words) <= 1:
        return True
    # If the transcript is extremely short and not a clear question, request repetition
    if len(words) <= 2 and len(normalized) < 15:
        return True
    return False


def transcribe_with_gemini(audio_path: str) -> dict:
    """
    Transcribe audio using Gemini API.
    """
    try:
        if not os.path.exists(audio_path):
            print(f"Audio file not found: {audio_path}")
            return {"text": "", "language": "en"}
        
        print(f"Reading audio file for Gemini: {audio_path}")
        import mimetypes
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
            
        mime_type, _ = mimetypes.guess_type(audio_path)
        if not mime_type:
            if audio_path.lower().endswith('.wav'):
                mime_type = 'audio/wav'
            elif audio_path.lower().endswith('.mp3'):
                mime_type = 'audio/mpeg'
            else:
                mime_type = 'audio/webm'
            
        print(f"Using audio MIME type: {mime_type}")
        print("Generating transcription with Gemini...")
        
        try:
            from google.generativeai.types import Part
            audio_part = Part.from_data(data=audio_data, mime_type=mime_type)
            response = gemini_model.generate_content([audio_part, GEMINI_TRANSCRIPTION_PROMPT])
        except ImportError:
            import base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            data_uri = f"data:{mime_type};base64,{audio_b64}"
            response = gemini_model.generate_content([data_uri, GEMINI_TRANSCRIPTION_PROMPT])
            
        if not response:
            raise Exception("Empty response from Gemini transcription")
            
        transcript_text = None
        if hasattr(response, 'text') and response.text:
            print(f"[DEBUG] Raw Gemini STT Response text: {response.text}")
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
        
        # Detect language
        language = detect_language_from_text(transcript_text)
        
        if transcript_text == "EMPTY_AUDIO":
             print(f"Transcription returned EMPTY_AUDIO. Returning empty string.")
             return {"text": "", "language": "en", "unclear": True}
        
        unclear = is_unclear_transcript(transcript_text)
        if unclear:
            print(f"Transcription looks unclear: {transcript_text}")
        else:
            print(f"Transcription successful. Language: {language}, Text length: {len(transcript_text)}")
        return {"text": transcript_text, "language": language, "unclear": unclear}
        
    except Exception as e:
        print(f"[ERROR] Audio transcription failed: {e}")
        import traceback
        traceback.print_exc()
        return {"text": "", "language": "en", "unclear": True}


def transcribe_with_google_speech(audio_path: str) -> dict:
    if speech is None:
        raise Exception("google-cloud-speech is not installed")
    if not GOOGLE_SPEECH_CREDENTIALS_JSON:
        raise Exception("Google Speech credentials are not configured")
    if not os.path.exists(audio_path):
        raise Exception(f"Audio file not found: {audio_path}")

    print(f"Transcribing with Google Speech-to-Text: {audio_path}")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_SPEECH_CREDENTIALS_JSON
    client = speech.SpeechClient()

    mime_type, _ = mimetypes.guess_type(audio_path)
    if not mime_type:
        mime_type = "audio/webm"

    encoding = speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED
    if mime_type == "audio/webm":
        encoding = speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
    elif mime_type == "audio/wav":
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
    elif mime_type in {"audio/mpeg", "audio/mp3"}:
        encoding = speech.RecognitionConfig.AudioEncoding.MP3

    with open(audio_path, 'rb') as f:
        audio_data = f.read()

    config = speech.RecognitionConfig(
        encoding=encoding,
        language_code="en-US",
        alternative_language_codes=["bn-BD"],
        enable_automatic_punctuation=False,
        max_alternatives=1,
        model="latest_long",
        use_enhanced=True
    )
    audio = speech.RecognitionAudio(content=audio_data)

    response = client.recognize(config=config, audio=audio)
    if not response.results:
        raise Exception("Google Speech returned no transcription results")

    transcript_text = " ".join([result.alternatives[0].transcript for result in response.results if result.alternatives])
    transcript_text = transcript_text.strip()
    if not transcript_text:
        raise Exception("Google Speech returned empty transcript")

    language = detect_language_from_text(transcript_text)
    unclear = is_unclear_transcript(transcript_text)
    return {"text": transcript_text, "language": language, "unclear": unclear}


def transcribe_with_huggingface_whisper(audio_path: str) -> dict:
    if not HUGGINGFACE_API_KEY:
        raise Exception("Hugging Face API key is not configured")
    if not os.path.exists(audio_path):
        raise Exception(f"Audio file not found: {audio_path}")

    url = f"https://api-inference.huggingface.co/models/{HUGGINGFACE_SPEECH_MODEL}"
    mime_type, _ = mimetypes.guess_type(audio_path)
    if not mime_type:
        mime_type = "application/octet-stream"

    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Accept": "application/json",
        "Content-Type": mime_type
    }

    with open(audio_path, 'rb') as f:
        audio_data = f.read()

    print(f"Transcribing with Hugging Face Whisper: {HUGGINGFACE_SPEECH_MODEL}")
    resp = requests.post(url, headers=headers, data=audio_data)
    if resp.status_code != 200:
        raise Exception(f"Hugging Face Whisper failed: {resp.status_code} {resp.text}")

    result = resp.json()
    transcript_text = result.get("text") if isinstance(result, dict) else None
    if not transcript_text:
        raise Exception(f"Hugging Face Whisper returned invalid response: {result}")

    transcript_text = transcript_text.strip()
    if not transcript_text:
        raise Exception("Hugging Face Whisper returned empty transcript")

    language = detect_language_from_text(transcript_text)
    unclear = is_unclear_transcript(transcript_text)
    return {"text": transcript_text, "language": language, "unclear": unclear}


def transcribe_audio(audio_path: str) -> dict:
    google_failure = None
    hf_failure = None

    try:
        result = transcribe_with_google_speech(audio_path)
        result["stt_source"] = "Google Speech-to-Text"
        result["stt_source_reason"] = "Succeeded"
        return result
    except Exception as google_error:
        google_failure = str(google_error)
        print(f"[WARN] Google Speech-to-Text fallback: {google_failure}")

    try:
        result = transcribe_with_huggingface_whisper(audio_path)
        result["stt_source"] = "Hugging Face Whisper"
        result["stt_source_reason"] = f"Google Speech failed: {google_failure}"
        return result
    except Exception as hf_error:
        hf_failure = str(hf_error)
        print(f"[WARN] Hugging Face Whisper fallback: {hf_failure}")

    result = transcribe_with_gemini(audio_path)
    result["stt_source"] = "Gemini"
    result["stt_source_reason"] = (
        f"Google Speech failed: {google_failure}; "
        f"Hugging Face Whisper failed: {hf_failure}"
    )
    return result


def stt_node(state):
    print(f"[DEBUG] STT node: Starting")
    
    # If transcript already exists (from text input), detect language from it
    if state.get("transcript"):
        transcript = state["transcript"]
        detected_lang = detect_language_from_text(transcript)
        return {"transcript": transcript, "language": detected_lang, "stt_source": "text_input"}
    
    if not state.get("audio_path"):
        return {"transcript": "", "language": "en", "unclear": True, "stt_source": None}
    
    stt = transcribe_audio(state["audio_path"])
    return {
        "transcript": stt.get("text", "").strip(),
        "language": stt.get("language", "en"),
        "unclear": stt.get("unclear", False),
        "stt_source": stt.get("stt_source", "unknown")
    }
