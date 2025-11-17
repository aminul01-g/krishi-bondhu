#!/usr/bin/env python3
"""
Test script for audio upload endpoint
"""
import requests
import os
import sys
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000"
UPLOAD_ENDPOINT = f"{API_URL}/api/upload_audio"

def test_audio_upload(audio_file_path: str, user_id: str = "test_user", lat: float = 23.7, lon: float = 90.4):
    """
    Test audio upload to the API endpoint.
    
    Args:
        audio_file_path: Path to the audio file to upload
        user_id: User ID for the request
        lat: Latitude for GPS coordinates
        lon: Longitude for GPS coordinates
    """
    if not os.path.exists(audio_file_path):
        print(f"❌ Error: Audio file not found: {audio_file_path}")
        return False
    
    print(f"📤 Uploading audio file: {audio_file_path}")
    print(f"   User ID: {user_id}")
    print(f"   GPS: ({lat}, {lon})")
    print()
    
    try:
        with open(audio_file_path, 'rb') as f:
            files = {'file': (os.path.basename(audio_file_path), f, 'audio/webm')}
            data = {
                'user_id': user_id,
                'lat': lat,
                'lon': lon
            }
            
            response = requests.post(UPLOAD_ENDPOINT, files=files, data=data, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Upload successful!")
                print(f"   Transcript: {result.get('transcript', 'N/A')[:100]}...")
                print(f"   Language: {result.get('language', 'N/A')}")
                print(f"   Reply: {result.get('reply_text', 'N/A')[:100]}...")
                print(f"   TTS Path: {result.get('tts_path', 'N/A')}")
                
                # Test TTS download if available
                if result.get('tts_path'):
                    tts_path = result.get('tts_path')
                    tts_url = f"{API_URL}/api/get_tts?path={requests.utils.quote(tts_path)}"
                    print(f"\n📥 Testing TTS download: {tts_url}")
                    tts_response = requests.get(tts_url)
                    if tts_response.status_code == 200:
                        print("✅ TTS file downloaded successfully")
                        # Save TTS file
                        output_path = "test_output.mp3"
                        with open(output_path, 'wb') as tts_file:
                            tts_file.write(tts_response.content)
                        print(f"   Saved to: {output_path}")
                    else:
                        print(f"⚠️  TTS download failed: {tts_response.status_code}")
                
                return True
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: Could not connect to server at {API_URL}")
        print("   Make sure the server is running: python start_server.sh")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_conversations_endpoint():
    """Test the conversations endpoint."""
    print("\n📋 Testing conversations endpoint...")
    try:
        response = requests.get(f"{API_URL}/api/conversations")
        if response.status_code == 200:
            conversations = response.json()
            print(f"✅ Found {len(conversations)} conversations")
            if conversations:
                print(f"   Latest: {conversations[0].get('transcript', 'N/A')[:50]}...")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 FarmerAI Audio Upload Test")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{API_URL}/docs", timeout=5)
        print("✅ Server is running")
    except:
        print("❌ Server is not running. Please start it first:")
        print("   cd backend && ./start_server.sh")
        sys.exit(1)
    
    # Test with provided audio file or create a dummy test
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        test_audio_upload(audio_file)
    else:
        print("\n⚠️  No audio file provided.")
        print("   Usage: python test_audio_upload.py <audio_file.webm>")
        print("   Example: python test_audio_upload.py test_audio.webm")
        print("\n   You can record audio using the frontend or use any .webm file")
    
    # Test conversations endpoint
    test_conversations_endpoint()
    
    print("\n✅ Test completed!")

