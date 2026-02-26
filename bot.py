import os
import logging
import shutil
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from dotenv import load_dotenv

from ai_handler import AIHandler
from video_processor import VideoProcessor
from logger_config import logger
from scraper import TikTokShopScraper

# Load environment variables
load_dotenv()

# States for ConversationHandler
WAITING_FOR_IMAGES, WAITING_FOR_CONFIRMATION, WAITING_FOR_NAME = range(3)

# Keyboards
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("Selesai Unggah ✅")],
    [KeyboardButton("Batal ❌")]
], resize_keyboard=True)

CONFIRM_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("Lanjut ke Nama Produk ➡️")],
    [KeyboardButton("Tambah Foto Lagi ➕")],
    [KeyboardButton("Batal ❌")]
], resize_keyboard=True)

class TikTokBot:
    def __init__(self):
        logger.info("Bot class initialized")
        self.ai_handler = AIHandler()
        self.video_processor = VideoProcessor()
        self.scraper = TikTokShopScraper()
        self.temp_dir = "temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        # Create bot-specific temp folder
        self.bot_temp = os.path.join(self.temp_dir, "bot_uploads")
        if os.path.exists(self.bot_temp):
            shutil.rmtree(self.bot_temp)
        os.makedirs(self.bot_temp, exist_ok=True)
        # Create assets folder if not exists
        os.makedirs(os.path.join("assets", "music"), exist_ok=True)
        self.users_file = os.path.join("logs", "users.json")
        os.makedirs("logs", exist_ok=True)

    def _save_user_data(self, user):
        """Saves telegram user data to logs/users.json for dashboard tracking."""
        data = {}
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, "r") as f:
                    data = json.load(f)
            except: data = {}
        
        user_id = str(user.id)
        data[user_id] = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "last_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            with open(self.users_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save user data: {e}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"User {user.username} (ID: {user.id}) started the bot")
        self._save_user_data(user)
        context.user_data['images'] = []
        context.user_data['product_name'] = None
        
        welcome_text = (
            f"🌟 *Halo {user.first_name}! Selamat Datang di TikTok Affiliate Bot* 🌟\n\n"
            "Saya akan membantu Anda membuat video promosi TikTok yang menarik secara otomatis! 🚀\n\n"
            "*Cara Cepat Mulai:*\n"
            "🔗 **Kirim Link TikTok Shop** untuk download gambar otomatis.\n"
            "   _ATAU_\n"
            "🖼 **Kirim foto-foto produk** Anda manual.\n\n"
            "1️⃣ Unggah/Scan Produk.\n"
            "2️⃣ Klik ✅ *Selesai Unggah*.\n"
            "3️⃣ Masukkan **Nama Produk**.\n"
            "4️⃣ Video viral Anda siap! ✨\n\n"
            "Silakan kirim Link atau Foto pertama Anda!"
        )
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=MAIN_KEYBOARD,
            parse_mode='Markdown'
        )
        return WAITING_FOR_IMAGES

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "📖 *Pusat Bantuan TikTok Affiliate Bot*\n\n"
            "❓ *Kenapa harus pakai bot ini?*\n"
            "- Suara AI mirip manusia asli (TikTok Viral style).\n"
            "- Optimasi deskripsi otomatis untuk SEO TikTok.\n"
            "- Slide transisi otomatis antar gambar.\n\n"
            "🛠 *Perintah:* \n"
            "/start - Mulai ulang proses\n"
            "/help - Lihat menu ini\n"
            "/cancel - Batalkan proses berjalan\n\n"
            "📝 *Tips sukses affiliate:* \n"
            "Masukan nama produk yang spesifik agar AI bisa membuat deskripsi yang lebih akurat dan persuasif."
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main handler for text and links (Bulk Scraper)."""
        text = update.message.text
        chat_id = update.message.chat_id
        
        # Check for TikTok links
        urls = self.scraper.extract_urls(text)
        if urls:
            # Limit to 10 links for safety/efficiency
            urls = urls[:10]
            num_links = len(urls)
            
            plural = "link" if num_links == 1 else f"{num_links} link"
            status_msg = await update.message.reply_text(f"🔍 Mendeteksi {plural} TikTok Shop... Sedang mengambil data ⏳")
            
            all_images = []
            all_product_names = []
            captcha_hit = False
            
            for i, url in enumerate(urls):
                try:
                    if num_links > 1:
                        await status_msg.edit_text(f"⏳ Sedang memproses link {i+1} dari {num_links}...")
                    
                    result = self.scraper.scrape_product(url)
                    if result['success'] and result.get('image_urls'):
                        # Add to product names list
                        if result['product_name'] not in all_product_names:
                            all_product_names.append(result['product_name'])
                        
                        # Use less images per product if bulk to avoid too long video
                        # If 1 link: use up to 6, if 10 links: use up to 2 per product
                        limit = 6 if num_links == 1 else 3
                        img_urls = result['image_urls'][:limit]
                        
                        paths = self.scraper.download_images(img_urls, chat_id)
                        all_images.extend(paths)
                    elif result.get('is_captcha'):
                        captcha_hit = True
                except Exception as e:
                    logger.error(f"Error processing link {url}: {e}")

            if all_images:
                if 'images' not in context.user_data:
                    context.user_data['images'] = []
                context.user_data['images'].extend(all_images)
                
                # Combine product names (suggest first one or join first few)
                if all_product_names:
                    main_name = all_product_names[0]
                    if len(all_product_names) > 1:
                        # Append " (Bulk)" or similar if it's a collection
                        context.user_data['product_name'] = f"{main_name} & lainnya"
                    else:
                        context.user_data['product_name'] = main_name
                
                await status_msg.delete()
                # Transition to confirmation summary
                return await self.finish_upload(update, context)
            else:
                if captcha_hit:
                    await status_msg.edit_text("🚧 *Akses Terbatas (CAPTCHA):* Tiktok memblokir akses otomatis. Silakan upload foto manual.")
                else:
                    await status_msg.edit_text("❌ Tidak dapat menemukan data produk dari link tersebut. Pastikan link benar atau unggah foto manual.")
        
        return WAITING_FOR_IMAGES

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if 'images' not in context.user_data:
            context.user_data['images'] = []
        
        chat_id = update.message.chat_id
        photo_file = await update.message.photo[-1].get_file()
        
        image_idx = len(context.user_data['images'])
        image_path = os.path.join(self.temp_dir, f"img_{chat_id}_{image_idx}.jpg")
        await photo_file.download_to_drive(image_path)
        
        context.user_data['images'].append(image_path)
        
        total = len(context.user_data['images'])
        logger.info(f"User {chat_id} uploaded image {total}")
        await update.message.reply_text(
            f"📥 Gambar ke-{total} berhasil diterima.\n"
            f"Total: {total} gambar.\n\n"
            "Kirim lagi atau klik 'Selesai Unggah'.",
            reply_markup=MAIN_KEYBOARD
        )
        return WAITING_FOR_IMAGES

    async def finish_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        images = context.user_data.get('images', [])
        if not images:
            await update.message.reply_text("Silakan kirim minimal satu foto produk terlebih dahulu.")
            return WAITING_FOR_IMAGES
        
        summary_text = (
            "📋 *Ringkasan Konten:*\n\n"
            f"🖼 **Total Foto:** {len(images)} foto\n"
            f"⏳ **Estimasi Durasi:** {len(images) * 3} detik\n"
            "🎙 **Voiceover:** TikTok Indonesia (Female)\n"
            "🎶 **Background Music:** " + ("Aktif ✅" if any(f.startswith("background.") for f in (os.listdir("assets/music") if os.path.exists("assets/music") else [])) else "Non-aktif ❌") + "\n\n"
            "Apakah Anda ingin melanjutkan ke pemberian nama produk?"
        )
        
        await update.message.reply_text(
            summary_text,
            reply_markup=CONFIRM_KEYBOARD,
            parse_mode='Markdown'
        )
        return WAITING_FOR_CONFIRMATION

    async def ask_for_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        suggested_name = context.user_data.get('product_name', '')
        text = "📝 Oke! Silakan masukkan **Nama Produk** Anda:"
        if suggested_name:
            text = f"📝 Saya menemukan nama produk:\n\n`{suggested_name}`\n\nSilakan konfirmasi dengan mengirim ulang namanya (atau ganti dengan nama lain) agar AI bisa membuat deskripsi:"
            
        await update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
        return WAITING_FOR_NAME

    async def cleanup_user_data(self, chat_id, context):
        """Deletes temporary files related to a specific chat session."""
        images = context.user_data.get('images', [])
        for img in images:
            if os.path.exists(img):
                try: os.remove(img)
                except: pass
        
        audio_path = os.path.join(self.temp_dir, f"audio_{chat_id}.mp3")
        video_path = os.path.join(self.temp_dir, f"video_{chat_id}.mp4")
        
        for path in [audio_path, video_path]:
            if os.path.exists(path):
                try: os.remove(path)
                except: pass
        
        context.user_data['images'] = []

    async def handle_product_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        product_name = update.message.text
        chat_id = update.message.chat_id
        images = context.user_data.get('images', [])
        
        # Initial status
        status_msg = await update.message.reply_text("⏳ Persiapan dimulai...")
        
        async def update_progress(step, total_steps, description):
            progress = int((step / total_steps) * 10)
            bar = "█" * progress + "░" * (10 - progress)
            text = f"🚀 *Sedang Memproses Konten Anda*\n\n`[{bar}]` {int(step/total_steps*100)}%\n\n✨ {description}"
            try:
                await status_msg.edit_text(text, parse_mode='Markdown')
            except: pass

        try:
            # 1. Generate Description
            await update_progress(1, 4, "✍️ Sedang menulis deskripsi produk yang persuasif...")
            logger.info(f"Generating description for product: {product_name}")
            try:
                description = self.ai_handler.generate_product_description(product_name)
            except Exception as e:
                raise Exception(f"Gagal membuat deskripsi (Groq): {e}")
            
            # 2. Text to Speech
            await update_progress(2, 4, "🎙️ Menghasilkan pengisi suara AI (TikTok Voice)...")
            audio_path = os.path.join(self.temp_dir, f"audio_{chat_id}.mp3")
            success_tts = await self.ai_handler.text_to_speech(description, audio_path)
            
            if not success_tts:
                raise Exception("Gagal menghasilkan suara (TTS).")

            # 3. Create Video
            await update_progress(3, 4, "🎬 Mengolah video slideshow, musik & subtitle...")
            video_path = os.path.join(self.temp_dir, f"video_{chat_id}.mp4")
            
            # Look for any background soundtrack (MP3, MP4, MOV, etc.)
            music_dir = os.path.join("assets", "music")
            bg_files = [f for f in os.listdir(music_dir) if f.startswith("background.")] if os.path.exists(music_dir) else []
            music_path = os.path.join(music_dir, bg_files[0]) if bg_files else None
            
            try:
                self.video_processor.create_video_from_images_and_audio(
                    images, 
                    audio_path, 
                    video_path, 
                    bg_music_path=music_path,
                    description=description
                )
            except Exception as e:
                raise Exception(f"Gagal mengolah video (FFmpeg): {e}")
            
            # 4. Finalizing
            await update_progress(4, 4, "✨ Video hampir siap! Sedang mengunggah...")
            
            with open(video_path, 'rb') as video:
                await update.message.reply_video(
                    video=video, 
                    caption=f"📦 *Produk:* {product_name}\n\n*Salin Deskripsi:* \n```{description}```",
                    parse_mode='Markdown',
                    write_timeout=300
                )
            
            await status_msg.delete()
            await self.cleanup_user_data(chat_id, context)
            await update.message.reply_text("✅ *Video Berhasil Dibuat!* \nKetik /start atau kirim foto lagi untuk buat yang baru.", parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error detail: {e}")
            await update.message.reply_text(f"❌ *Gagal:* {str(e)}", parse_mode='Markdown')
            await self.cleanup_user_data(chat_id, context)
            
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat_id
        await self.cleanup_user_data(chat_id, context)
        await update.message.reply_text("❌ Proses dibatalkan. Ketik /start untuk mulai lagi.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    def run(self):
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            print("Error: TELEGRAM_BOT_TOKEN not found in .env")
            return

        # Menambahkan timeout global pada aplikasi
        app = ApplicationBuilder().token(token).read_timeout(300).write_timeout(300).build()

        # Command handlers
        app.add_handler(CommandHandler("help", self.help_command))

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                WAITING_FOR_IMAGES: [
                    MessageHandler(filters.PHOTO, self.handle_image),
                    MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^Selesai Unggah ✅$") & ~filters.Regex("^Batal ❌$"), self.handle_message),
                    MessageHandler(filters.Regex("^Selesai Unggah ✅$"), self.finish_upload),
                    MessageHandler(filters.Regex("^Batal ❌$"), self.cancel)
                ],
                WAITING_FOR_CONFIRMATION: [
                    MessageHandler(filters.Regex("^Lanjut ke Nama Produk ➡️$"), self.ask_for_name),
                    MessageHandler(filters.Regex("^Tambah Foto Lagi ➕$"), self.start), # Just reuse start or return state
                    MessageHandler(filters.Regex("^Batal ❌$"), self.cancel)
                ],
                WAITING_FOR_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_product_name)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel), MessageHandler(filters.Regex("^Batal ❌$"), self.cancel)],
        )

        app.add_handler(conv_handler)
        print("Bot is running...")
        app.run_polling()

if __name__ == "__main__":
    bot = TikTokBot()
    bot.run()
