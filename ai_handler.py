import os
import asyncio
import uuid
import requests
import base64
import shutil
import subprocess
from groq import Groq
from openai import OpenAI
from dotenv import load_dotenv
from gtts import gTTS
from logger_config import logger

load_dotenv()

class AIHandler:
    def __init__(self):
        logger.info("Initializing AIHandler...")
        # Groq client for fast text generation
        self.groq_client = Groq(
            api_key=os.getenv("GROQ_API_KEY"),
            timeout=300.0
        )
        
        # OpenAI client for high-quality human-like TTS (Optional)
        self.openai_key = os.getenv("OPENAI_API_KEY")
        if self.openai_key:
            self.openai_client = OpenAI(api_key=self.openai_key)
        else:
            self.openai_client = None

    def generate_product_description(self, product_name):
        """Generates a high-engagement, short TikTok affiliate description (15-30s)."""
        prompt = f"""
        Tugas: Buat naskah video TikTok Affiliate yang VIRAL dan PERSUASIF untuk: {product_name}.
        
        TARGET DURASI: 15-30 detik (Sangat Singkat & To-the-point).
        
        KATEGORI HOOK (Pilih satu yang paling unik):
        1. THE SECRET: "Jujur, nyesel banget baru tau ada barang ginian..."
        2. THE PROBLEM: "Cowok/Cewek wajib punya ini kalau nggak mau..."
        3. THE VISUAL: "Liat deh, ini beneran life changer banget buat..."
        4. THE URGENCY: "Stop scroll! Barang ini lagi viral dan sisa dikit..."
        5. THE TEASE: "Kalian nggak akan percaya harga barang sekeren ini..."
        
        Struktur Naskah:
        1. HOOK UNIK (3-5 detik): Gunakan salah satu gaya di atas yang paling cocok.
        2. BODY (10-20 detik): Jelaskan 2 MANFAAT UTAMA yang paling 'ngena'. Fokus pada solusi.
        3. CALL TO ACTION (CTA): Ajak klik keranjang kuning SEKARANG sebelum kehabisan.
        
        Gaya Bahasa:
        - Bahasa gaul Jakarta/TikTok yang natural (pake 'lo/gue' atau 'kalian' yang sopan tapi asik).
        - Sangat ekspresif dan penuh energi.
        
        ATURAN KETAT:
        - HANYA keluarkan teks deskripsi. 
        - JANGAN gunakan tanda bintang (*), hashtag (#), emoji, atau markup.
        - Panjang teks WAJIB antara 40-70 kata (Agar durasi 15-30 detik).
        - Gunakan Bahasa Indonesia yang sangat natural, jangan kaku.
        """
        
        completion = self.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional TikTok content creator and affiliate marketer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=600
        )
        text = completion.choices[0].message.content
        return text.replace('*', '').replace('#', '').strip()

    async def text_to_speech(self, text, output_path):
        """Converts text to audio with chunking for TikTok TTS to bypass character limits."""
        
        # 1. Try OpenAI (If API Key provided)
        if self.openai_client:
            try:
                def save_openai():
                    response = self.openai_client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=text
                    )
                    response.stream_to_file(output_path)
                await asyncio.to_thread(save_openai)
                return True
            except Exception as e:
                logger.error(f"OpenAI TTS Error: {e}")

        # 2. Try TikTok TTS with Chunking (Support for long duration)
        try:
            import requests
            import base64
            import subprocess
            
            # Split text by sentences or punctuation to keep chunks natural
            import re
            sentences = re.split(r'([.!?\n]+)', text)
            chunks = []
            current_chunk = ""
            
            for part in sentences:
                if len(current_chunk) + len(part) < 200:
                    current_chunk += part
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = part
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            if not chunks:
                chunks = [text[:200]]

            logger.info(f"TikTok TTS: Splitting text into {len(chunks)} chunks for long duration.")
            
            chunk_files = []
            api_url = "https://tiktok-tts.weilnet.workers.dev/api/generation"
            
            temp_dir = os.path.dirname(output_path)
            
            async def generate_chunk(i, chunk_text):
                def call_tiktok_chunk():
                    payload = {"text": chunk_text, "voice": "id_001"}
                    try:
                        resp = requests.post(api_url, json=payload, timeout=60)
                        if resp.status_code == 200:
                            data = resp.json()
                            if "data" in data:
                                c_path = os.path.join(temp_dir, f"chunk_{i}_{uuid.uuid4().hex[:4]}.mp3")
                                with open(c_path, "wb") as f:
                                    f.write(base64.b64decode(data["data"]))
                                return (i, c_path)
                    except Exception as e:
                        logger.error(f"TTS Chunk {i} Error: {e}")
                    return (i, None)
                
                return await asyncio.to_thread(call_tiktok_chunk)

            # Generate all chunks in parallel
            tasks = [generate_chunk(i, chunk) for i, chunk in enumerate(chunks)]
            results = await asyncio.gather(*tasks)
            
            # Sort by index to maintain sequence
            results.sort(key=lambda x: x[0])
            chunk_files = [path for i, path in results if path]

            if chunk_files:
                # Merge chunks using FFmpeg
                if len(chunk_files) == 1:
                    shutil.move(chunk_files[0], output_path)
                    return True
                else:
                    # Create a concat file for FFmpeg
                    list_path = os.path.join(temp_dir, f"list_{uuid.uuid4().hex[:4]}.txt")
                    with open(list_path, "w", encoding='utf-8') as f:
                        for cf in chunk_files:
                            # FFmpeg needs escaped paths if they have spaces, but here we keep it simple
                            f.write(f"file '{os.path.abspath(cf)}'\n")
                    
                    merge_cmd = [
                        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                        '-i', list_path, '-c', 'copy', output_path
                    ]
                    
                    try:
                        subprocess.run(merge_cmd, capture_output=True, check=True)
                        # Cleanup
                        os.remove(list_path)
                        for cf in chunk_files:
                            try: os.remove(cf)
                            except: pass
                        return True
                    except Exception as e:
                        logger.error(f"FFmpeg Merge Error: {e}")
                        # Fallback: just use first chunk if merge fails
                        shutil.move(chunk_files[0], output_path)
                        return True
        except Exception as e:
            logger.error(f"TikTok TTS Multi-chunk Error: {e}")

        # 3. Fallback to gTTS
        try:
            def save_gtts():
                tts = gTTS(text=text, lang='id')
                tts.save(output_path)
            await asyncio.to_thread(save_gtts)
            return True
        except Exception as e:
            logger.error(f"gTTS Error: {e}")
            return False

    def generate_images_from_prompt(self, prompt, count=5, output_dir="temp/ai_images", model="flux"):
        """Generates multiple images from a prompt using Pollinations AI (Flux or Zimage model)."""
        os.makedirs(output_dir, exist_ok=True)
        image_paths = []
        
        api_key = os.getenv("POLLINATIONS_API_KEY")
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Clean prompt for URL
        clean_prompt = requests.utils.quote(prompt)
        
        logger.info(f"Generating {count} images for prompt: {prompt} using {model} model")
        
        for i in range(count):
            # Use integer seed as required by API
            import random
            seed = random.randint(0, 2147483647)
            
            # Use gen.pollinations.ai with specified model
            # Note: Removed nologo as it's not documented in the latest API
            url = f"https://gen.pollinations.ai/image/{clean_prompt}?seed={seed}&width=1080&height=1920&model={model}"
            
            try:
                resp = requests.get(url, headers=headers, timeout=60)
                if resp.status_code == 200:
                    output_filename = f"ai_gen_{model}_{seed}_{i}.jpg"
                    path = os.path.join(output_dir, output_filename)
                    with open(path, "wb") as f:
                        f.write(resp.content)
                    image_paths.append(path)
                    logger.info(f"Generated AI image {i+1}/{count}: {path}")
                else:
                    logger.error(f"Failed to generate image {i+1}: HTTP {resp.status_code} - {resp.text[:200]}")
            except Exception as e:
                logger.error(f"Error generating AI image {i+1}: {e}")
                
        return image_paths

if __name__ == "__main__":
    # Test script
    async def main():
        handler = AIHandler()
        desc = handler.generate_product_description("Botol Minum Viral")
        print(f"Description: {desc}")
        await handler.text_to_speech(desc, "test_output.mp3")
        print("Audio saved to test_output.mp3")

    asyncio.run(main())
