import os
import asyncio
from ai_handler import AIHandler
from dotenv import load_dotenv

load_dotenv()

async def test_groq():
    print("Testing Groq LLM...")
    handler = AIHandler()
    try:
        desc = handler.generate_product_description("Botol Minum Thermos")
        print(f"Success! Description:\n{desc}\n")
        
        print("Testing gTTS (Voiceover)...")
        audio_path = "test_audio.mp3"
        success = await handler.text_to_speech("Halo, ini adalah tes suara dari Google TTS.", audio_path)
        if success:
            print(f"Success! Audio saved to {audio_path}")
        else:
            print("Failed to generate audio.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_groq())
