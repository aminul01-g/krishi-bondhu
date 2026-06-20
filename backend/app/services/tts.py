
import os
import re
from gtts import gTTS
from uuid import uuid4
from app.api.utils import UPLOAD_DIR
import time

# Maximum characters sent to TTS to avoid excessively long audio files
TTS_MAX_CHARS = 600

def clean_text_for_tts(text: str) -> str:
    """
    Clean text for TTS by removing markdown, special symbols, and formatting.
    """
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
            tts = gTTS(text[:TTS_MAX_CHARS], lang=lang if lang else "en")  # Limit length
            tts.save(tts_path)
            
            # Verify fallback file was created with retry logic
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


def generate_tts(text: str, language: str = "bn") -> str:
    """
    Public API for TTS generation used by API endpoints.

    Normalises the language code (e.g. 'bn-BD' → 'bn') so that gTTS
    accepts it, truncates the input to TTS_MAX_CHARS characters, cleans
    markdown/formatting, then delegates to synthesize_tts.

    Args:
        text: The text to synthesise. Will be truncated to TTS_MAX_CHARS.
        language: BCP-47 or ISO 639-1 language code. Defaults to 'bn' (Bengali).

    Returns:
        Absolute file path of the generated .mp3 audio file.
    """
    # Normalise language code: 'bn-BD' → 'bn', 'en-US' → 'en', etc.
    lang_code = language.split("-")[0].lower() if language else "bn"

    # Truncate before cleaning so we don't waste compute on discarded text
    truncated = text[:TTS_MAX_CHARS]

    return synthesize_tts(truncated, lang=lang_code)
