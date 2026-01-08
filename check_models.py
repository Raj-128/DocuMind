import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load your API Key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ Error: GOOGLE_API_KEY not found in .env file")
else:
    print(f"✅ Found API Key: {api_key[:5]}...*****")
    genai.configure(api_key=api_key)

    print("\n🔍 Checking available models...")
    try:
        count = 0
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"   👉 {m.name}")
                count += 1
        
        if count == 0:
            print("\n⚠️ No models found. Check if 'Generative Language API' is enabled in Google Cloud Console.")
        else:
            print(f"\n✅ Found {count} models available for use.")
            
    except Exception as e:
        print(f"\n❌ Error contacting Google: {e}")