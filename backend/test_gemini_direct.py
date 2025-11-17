#!/usr/bin/env python3
"""
Direct test of Gemini API to identify issues
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
    
    # Get API key
    api_key = os.getenv('GEMINI_API_KEY', 'AIzaSyDlWQCKSKKtHl1wLQvnb9QaPRUODn8sMQ0')
    
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found")
        sys.exit(1)
    
    print(f"✅ API Key found: {api_key[:20]}...")
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    print("✅ Gemini API configured")
    
    # Test 1: Simple text generation without system instruction
    print("\n🧪 Test 1: Simple text generation...")
    try:
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content('Say "Hello" in one word')
        print(f"✅ Test 1 successful: {response.text.strip()}")
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Test 2: With system instruction parameter
    print("\n🧪 Test 2: With system_instruction parameter...")
    try:
        system_instruction = "You are a helpful assistant."
        model_with_system = genai.GenerativeModel(
            'models/gemini-2.5-flash',
            system_instruction=system_instruction
        )
        response = model_with_system.generate_content('Say "Hello" in one word')
        print(f"✅ Test 2 successful: {response.text.strip()}")
    except Exception as e:
        print(f"⚠️  Test 2 failed (system_instruction may not be supported): {e}")
        print(f"   Error type: {type(e).__name__}")
        print("   This is okay - we have fallback in the code")
    
    # Test 3: Longer prompt (like intent extraction)
    print("\n🧪 Test 3: Intent extraction style prompt...")
    try:
        prompt = """Transcript: My rice crop has yellow spots on the leaves

Extract the information as JSON:"""
        system_instruction = """You are an information extraction assistant.
Extract and return ONLY valid JSON with these exact keys:
- crop: string or null
- symptoms: string
- need_image: boolean
- note: string

Return ONLY the JSON object, no other text."""
        
        try:
            model_with_system = genai.GenerativeModel(
                'models/gemini-2.5-flash',
                system_instruction=system_instruction
            )
            response = model_with_system.generate_content(prompt)
        except:
            # Fallback
            fallback_prompt = f"{system_instruction}\n\n{prompt}"
            response = model.generate_content(fallback_prompt)
        
        print(f"✅ Test 3 successful: {response.text.strip()[:200]}")
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Test 4: Reasoning node style prompt
    print("\n🧪 Test 4: Reasoning node style prompt...")
    try:
        prompt = """Based on the following information, provide a helpful response to the farmer:

CONTEXT INFORMATION:
Farmer's query/question: What should I do about yellow spots on my rice leaves?
Identified crop: rice

Please provide:
1. A direct answer to the farmer's question
2. Practical, actionable advice
3. Specific recommendations when applicable
4. Any relevant warnings or considerations

Respond in English."""
        
        system_instruction = """You are FarmAssist, a helpful AI assistant for farmers in Bangladesh.
Provide clear, practical advice in Bengali or English based on the farmer's query."""
        
        try:
            model_with_system = genai.GenerativeModel(
                'models/gemini-2.5-flash',
                system_instruction=system_instruction
            )
            response = model_with_system.generate_content(prompt)
        except:
            # Fallback
            fallback_prompt = f"{system_instruction}\n\n{prompt}"
            response = model.generate_content(fallback_prompt)
        
        print(f"✅ Test 4 successful: {response.text.strip()[:200]}")
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n✅ All tests passed! Gemini API is working correctly.")
    print("   If you're still seeing errors in the main app, check:")
    print("   1. Server console logs for [ERROR] messages")
    print("   2. That the API key has sufficient quota")
    print("   3. Network connectivity to Google's servers")
    
except ImportError as e:
    print(f"❌ Error: Missing dependency - {e}")
    print("   Run: pip install google-generativeai python-dotenv")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

