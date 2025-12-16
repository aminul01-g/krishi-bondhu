
import os
import google.generativeai as genai
from dotenv import load_dotenv
from app.core.prompts import GEMINI_TRANSCRIPTION_PROMPT

load_dotenv()

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
            mime_type = "audio/webm"
            
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
             return {"text": "", "language": "en"}
        
        print(f"Transcription successful. Language: {language}, Text length: {len(transcript_text)}")
        return {"text": transcript_text, "language": language}
        
    except Exception as e:
        print(f"[ERROR] Audio transcription failed: {e}")
        import traceback
        traceback.print_exc()
        return {"text": "", "language": "en"}

def stt_node(state):
    print(f"[DEBUG] STT node: Starting")
    
    # If transcript already exists (from text input), detect language from it
    if state.get("transcript"):
        transcript = state["transcript"]
        detected_lang = detect_language_from_text(transcript)
        return {"transcript": transcript, "language": detected_lang}
    
    if not state.get("audio_path"):
        return {"transcript": "", "language": "en"}
    
    stt = transcribe_with_gemini(state["audio_path"])
    return {"transcript": stt.get("text", "").strip(), "language": stt.get("language", "en")}
