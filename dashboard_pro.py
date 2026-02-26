from flask import Flask, render_template_string, request, send_from_directory, redirect, url_for, flash, session
import os
import re
import uuid
import shutil
import time
import asyncio
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from ai_handler import AIHandler
from video_processor import VideoProcessor
from scraper import TikTokShopScraper
from logger_config import logger

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "tiktok_bot_pro_secret_key_v4")

# Paths & Config
UPLOAD_FOLDER = "temp/web_uploads"
MUSIC_FOLDER = "assets/music"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MUSIC_FOLDER, exist_ok=True)

DASHBOARD_AUTH_KEY = os.getenv("DASHBOARD_AUTH_KEY", "admin123")

# Initialize Handlers
ai_handler = AIHandler()
video_processor = VideoProcessor()
scraper = TikTokShopScraper()

# --- Security Decorator ---
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# --- UI Assets (Shared) ---
BASE_CSS = """
:root {
    --primary: #10b981;
    --secondary: #fbbf24;
}
.sidebar-transition { transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1); }
.glass-panel { 
    background: rgba(255, 255, 255, 0.85); 
    backdrop-filter: blur(20px); 
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.4); 
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
}
.glass-input {
    background: rgba(248, 250, 252, 0.6);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(226, 232, 240, 0.8);
    transition: all 0.3s ease;
}
.glass-input:focus {
    background: #ffffff;
    box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.15);
    border-color: #34d399;
}
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(203, 213, 225, 0.6); border-radius: 20px; border: 2px solid transparent; background-clip: padding-box; }
::-webkit-scrollbar-thumb:hover { background-color: rgba(148, 163, 184, 0.8); }

.animated-bg {
    background: linear-gradient(-45deg, #f8fafc, #f0fdf4, #fefce8, #f8fafc);
    background-size: 400% 400%;
    animation: gradientBG 15s ease infinite;
}
@keyframes gradientBG {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

input[type="file"]::file-selector-button {
    border: none;
    background: #10b981;
    padding: 0.5rem 1.5rem;
    border-radius: 9999px;
    color: white;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s ease;
    margin-right: 1.5rem;
}
.animate-bounce-short { animation: bounce 1s ease-in-out infinite; }
@keyframes bounce { 0%, 100% { transform: translateY(-5%); } 50% { transform: translateY(0); } }
"""

LAYOUT_START = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - TikTok Bot PRO</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Outfit', sans-serif; }
        """ + BASE_CSS + """
    </style>
</head>
<body class="animated-bg text-slate-800 min-h-screen flex overflow-x-hidden selection:bg-emerald-200 selection:text-emerald-900">
    
    <!-- Mobile Header -->
    <header class="lg:hidden fixed top-0 left-0 w-full glass-panel z-40 px-6 py-4 flex items-center justify-between border-b border-white/40">
        <div class="flex items-center gap-3">
            <div class="w-8 h-8 bg-gradient-to-br from-emerald-400 to-yellow-400 rounded-lg flex items-center justify-center text-white text-sm shadow-md">🚀</div>
            <h1 class="text-xl font-black tracking-tight text-slate-800">BOT<span class="text-emerald-500">PRO</span></h1>
        </div>
        <button id="mobile-menu-btn" class="p-2 bg-white/50 backdrop-blur-sm rounded-lg text-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-400 shadow-sm border border-slate-200">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
        </button>
    </header>

    <!-- Mobile Overlay -->
    <div id="sidebar-overlay" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-40 hidden lg:hidden transition-opacity duration-300 opacity-0 cursor-pointer"></div>

    <!-- Sidebar -->
    <aside id="sidebar" class="sidebar-transition w-72 glass-panel h-screen fixed left-0 top-0 z-50 flex flex-col border-r border-white/40 transform -translate-x-full lg:translate-x-0">
        <div class="p-8">
            <div class="flex items-center justify-between mb-12">
                <div class="flex items-center gap-4 group cursor-pointer">
                    <div class="w-12 h-12 bg-gradient-to-br from-emerald-400 via-emerald-500 to-yellow-400 rounded-2xl flex items-center justify-center text-white text-2xl shadow-lg shadow-emerald-200/50 group-hover:shadow-emerald-300/60 group-hover:scale-105 transition-all duration-300">🚀</div>
                    <h1 class="text-2xl font-black tracking-tight text-slate-800">BOT<span class="text-emerald-500">PRO</span></h1>
                </div>
                <button id="close-sidebar-btn" class="lg:hidden p-2 text-slate-400 hover:text-rose-500 rounded-full hover:bg-rose-50 transition-colors">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            
            <nav class="space-y-3 relative">
                <a href="/" class="group flex items-center gap-4 px-5 py-4 rounded-2xl font-bold transition-all duration-300 hover:scale-[1.02] {{ 'text-emerald-700 bg-emerald-50/80 shadow-sm border border-emerald-100/50' if active == 'dashboard' else 'text-slate-500 hover:bg-white/60 hover:text-slate-800' }}">
                    <span class="text-xl">📊</span> Dashboard
                </a>
                <a href="/create_affiliate" class="group flex items-center gap-4 px-5 py-4 rounded-2xl font-bold transition-all duration-300 hover:scale-[1.02] {{ 'text-emerald-700 bg-emerald-50/80 shadow-sm border border-emerald-100/50' if active == 'create_affiliate' else 'text-slate-500 hover:bg-white/60 hover:text-slate-800' }}">
                    <span class="text-xl group-hover:animate-bounce-short">🎬</span> Affiliate Creator
                </a>
                <a href="/create_music" class="group flex items-center gap-4 px-5 py-4 rounded-2xl font-bold transition-all duration-300 hover:scale-[1.02] {{ 'text-emerald-700 bg-emerald-50/80 shadow-sm border border-emerald-100/50' if active == 'create_music' else 'text-slate-500 hover:bg-white/60 hover:text-slate-800' }}">
                    <span class="text-xl">🎶</span> Music Video AI
                </a>
                <a href="/gallery" class="group flex items-center gap-4 px-5 py-4 rounded-2xl font-bold transition-all duration-300 hover:scale-[1.02] {{ 'text-emerald-700 bg-emerald-50/80 shadow-sm border border-emerald-100/50' if active == 'gallery' else 'text-slate-500 hover:bg-white/60 hover:text-slate-800' }}">
                    <span class="text-xl">🖼️</span> Galeri Video
                </a>
                <a href="/users" class="group flex items-center gap-4 px-5 py-4 rounded-2xl font-bold transition-all duration-300 hover:scale-[1.02] {{ 'text-emerald-700 bg-emerald-50/80 shadow-sm border border-emerald-100/50' if active == 'users' else 'text-slate-500 hover:bg-white/60 hover:text-slate-800' }}">
                    <span class="text-xl">👥</span> Pengguna Bot
                </a>
                <a href="/settings" class="group flex items-center gap-4 px-5 py-4 rounded-2xl font-bold transition-all duration-300 hover:scale-[1.02] {{ 'text-emerald-700 bg-emerald-50/80 shadow-sm border border-emerald-100/50' if active == 'settings' else 'text-slate-500 hover:bg-white/60 hover:text-slate-800' }}">
                    <span class="text-xl">⚙️</span> Pengaturan
                </a>
            </nav>
        </div>

        <div class="mt-auto p-8 text-center backdrop-blur-md bg-white/30 border-t border-white/50">
            <a href="/logout" class="group flex items-center gap-4 px-5 py-4 rounded-2xl font-bold text-rose-500 hover:bg-rose-50/80 transition-all duration-300 hover:scale-[1.02] mb-6">
                <span class="text-xl group-hover:-translate-x-1 transition-transform">🚪</span> Logout
            </a>
            <div class="inline-block px-4 py-1.5 rounded-full bg-emerald-100/50 text-emerald-600 text-[10px] font-black uppercase tracking-widest border border-emerald-200/50 mt-4">
                VERSION 4.0 PRO
            </div>
        </div>
    </aside>

    <main class="flex-1 lg:ml-72 min-h-screen pt-24 pb-10 px-4 md:px-8 lg:pt-10 lg:px-12 relative z-10 w-full overflow-hidden">
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <div class="mb-8 p-4 bg-emerald-50 border border-emerald-100 text-emerald-700 rounded-2xl flex items-center gap-3 animate-pulse shadow-sm">
                <span class="text-xl">✨</span> {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}
"""

LAYOUT_END = """
    </main>
    <script>
        const menuBtn = document.getElementById('mobile-menu-btn');
        const closeBtn = document.getElementById('close-sidebar-btn');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');

        function toggleSidebar() {
            const isClosed = sidebar.classList.contains('-translate-x-full');
            if (isClosed) {
                sidebar.classList.remove('-translate-x-full');
                overlay.classList.remove('hidden');
                setTimeout(() => overlay.classList.remove('opacity-0'), 10);
            } else {
                sidebar.classList.add('-translate-x-full');
                overlay.classList.add('opacity-0');
                setTimeout(() => overlay.classList.add('hidden'), 300);
            }
        }

        if (menuBtn) menuBtn.addEventListener('click', toggleSidebar);
        if (closeBtn) closeBtn.addEventListener('click', toggleSidebar);
        if (overlay) overlay.addEventListener('click', toggleSidebar);
    </script>
</body>
</html>
"""

STATS_CONTENT = """
    <header class="mb-10">
        <h2 class="text-3xl font-black text-slate-800 tracking-tight">Capaian Bot</h2>
        <p class="text-slate-500 mt-1 font-medium italic">Statistik performa dan aktivitas sistem real-time.</p>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <div class="glass-panel p-8 rounded-[2rem] relative overflow-hidden group hover:scale-[1.02] transition-all duration-300">
            <div class="absolute top-0 right-0 w-24 h-24 bg-emerald-500/10 rounded-bl-[4rem] flex items-center justify-center text-2xl group-hover:bg-emerald-500/20 transition-all">👤</div>
            <div class="text-slate-400 font-bold text-xs uppercase tracking-widest mb-1">Total Pengguna</div>
            <div class="text-4xl font-black text-slate-800">{{ stats.total_users }}</div>
        </div>
        <div class="glass-panel p-8 rounded-[2rem] relative overflow-hidden group hover:scale-[1.02] transition-all duration-300">
            <div class="absolute top-0 right-0 w-24 h-24 bg-yellow-500/10 rounded-bl-[4rem] flex items-center justify-center text-2xl group-hover:bg-yellow-500/20 transition-all">🎬</div>
            <div class="text-slate-400 font-bold text-xs uppercase tracking-widest mb-1">Video Dibuat</div>
            <div class="text-4xl font-black text-slate-800">{{ stats.videos_created }}</div>
        </div>
        <div class="glass-panel p-8 rounded-[2rem] relative overflow-hidden group hover:scale-[1.02] transition-all duration-300">
            <div class="absolute top-0 right-0 w-24 h-24 bg-indigo-500/10 rounded-bl-[4rem] flex items-center justify-center text-2xl group-hover:bg-indigo-500/20 transition-all">🖼️</div>
            <div class="text-slate-400 font-bold text-xs uppercase tracking-widest mb-1">Foto Diproses</div>
            <div class="text-4xl font-black text-slate-800">{{ stats.images_processed }}</div>
        </div>
    </div>
"""

AFFILIATE_CREATOR_CONTENT = """
    <header class="mb-12">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-100/50 text-emerald-600 text-xs font-bold mb-4 border border-emerald-200/50">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Affiliate Engine Ready
        </div>
        <h2 class="text-4xl md:text-5xl font-black text-slate-800 tracking-tight leading-tight">Video <span class="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-yellow-400">Affiliate.</span></h2>
        <p class="text-slate-500 mt-2 text-lg font-medium max-w-2xl">Ubah URL Produk TikTok menjadi video promosi viral dalam hitungan detik.</p>
    </header>

    <div class="max-w-4xl relative">
        <div class="glass-panel p-6 sm:p-12 rounded-[2.5rem] relative z-10">
            <form action="/generate_affiliate" method="post" enctype="multipart/form-data" id="creator-form" class="space-y-10">
                <div class="space-y-8">
                    <div class="group">
                        <label class="block text-xs font-black text-slate-400 uppercase tracking-widest mb-4">🔗 Link Produk TikTok Shop (Opsional)</label>
                        <input type="url" name="url" placeholder="Paste link produk di sini..." class="w-full p-5 glass-input rounded-2xl outline-none font-medium placeholder:text-slate-300">
                        <p class="mt-2 text-[10px] text-slate-400 font-bold italic">Jika dikosongkan, Nama Produk dan Foto Manual wajib diisi.</p>
                    </div>
                    <div class="group">
                        <label class="block text-xs font-black text-slate-400 uppercase tracking-widest mb-4">🏷️ Nama Produk (Opsional)</label>
                        <input type="text" name="product_name" placeholder="Kosongkan jika ingin dideteksi otomatis" class="w-full p-5 glass-input rounded-2xl outline-none font-medium placeholder:text-slate-300">
                    </div>
                    <div class="group">
                        <label class="block text-xs font-black text-slate-400 uppercase tracking-widest mb-4">📸 Upload Gambar Manual (Opsional)</label>
                        <input type="file" name="images" multiple accept="image/*" class="w-full glass-input p-3 rounded-2xl">
                        <p class="mt-2 text-[10px] text-slate-400 font-bold italic">Jika diisi, link TikTok hanya digunakan untuk mengambil naskah/script.</p>
                    </div>
                </div>
                
                <button type="submit" class="w-full py-6 bg-gradient-to-r from-emerald-500 to-emerald-400 text-white font-black text-xl rounded-2xl shadow-xl hover:scale-[1.01] active:scale-[0.98] transition-all">
                    🚀 MULAI PRODUKSI VIDEO
                </button>
            </form>
        </div>

        {% if result_video %}
        <div class="mt-12 glass-panel p-8 md:p-10 rounded-[2.5rem] border-2 border-emerald-400 animate-in slide-in-from-bottom-10">
            <div class="flex items-center gap-4 mb-8">
                <div class="w-14 h-14 bg-emerald-500 rounded-2xl flex items-center justify-center text-2xl text-white">✨</div>
                <div>
                    <h3 class="text-2xl font-black text-slate-800">Video Siap Digunakan!</h3>
                    <p class="text-emerald-600 font-bold">Konten affiliate Anda telah diproses sempurna.</p>
                </div>
            </div>
            
            {% if description %}
            <div class="mb-8 rounded-3xl bg-slate-900 p-6 md:p-8 relative">
                <div class="flex justify-between items-center mb-6">
                    <span class="text-[10px] font-black text-emerald-400 uppercase tracking-widest">📜 Naskah Viral AI</span>
                    <button onclick="copyDesc()" class="text-xs font-black text-white bg-emerald-500 px-4 py-2 rounded-lg hover:bg-emerald-400 transition-colors" id="btn-copy-main">SALIN</button>
                </div>
                <div id="ai-desc" class="text-slate-300 font-medium leading-loose text-sm italic">{{ description }}</div>
            </div>
            {% endif %}

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <a href="/download/{{ result_video }}" class="flex items-center justify-center gap-3 py-5 bg-emerald-500 text-white font-black rounded-2xl hover:bg-emerald-600 transition-all shadow-lg shadow-emerald-100">📥 DOWNLOAD MP4</a>
                <a href="/gallery" class="flex items-center justify-center gap-3 py-5 bg-yellow-400 text-white font-black rounded-2xl hover:bg-yellow-500 transition-all">🖼️ KE GALERI</a>
            </div>
        </div>
        <script>
            function copyDesc() {
                var text = document.getElementById("ai-desc").innerText;
                navigator.clipboard.writeText(text).then(function() {
                    const btn = document.getElementById("btn-copy-main");
                    btn.innerHTML = "✅ TERSALIN!";
                    setTimeout(() => { btn.innerHTML = "SALIN"; }, 2000);
                });
            }
        </script>
        {% endif %}

        <!-- Loading Overlay -->
        <div id="loading-overlay" class="fixed inset-0 bg-white/90 backdrop-blur-xl z-[100] hidden flex-col items-center justify-center text-center p-8">
            <div class="relative w-40 h-40 mb-10">
                <div class="absolute inset-0 border-8 border-slate-100 rounded-full"></div>
                <div class="absolute inset-0 border-8 border-emerald-500 rounded-full border-t-transparent animate-spin"></div>
                <div class="absolute inset-0 flex items-center justify-center text-5xl animate-bounce">🎬</div>
            </div>
            <h2 class="text-3xl font-black text-slate-800 mb-4 tracking-tight">PROSES PRODUKSI...</h2>
            <div id="status-text" class="text-lg font-bold text-emerald-600 bg-emerald-50 px-8 py-3 rounded-2xl border border-emerald-100">Inisialisasi sistem...</div>
            <p class="mt-8 text-slate-400 font-medium max-w-xs">Mohon tunggu sebentar, AI sedang meracik video viral Anda.</p>
        </div>
        <script>
            document.getElementById('creator-form').onsubmit = function() {
                document.getElementById('loading-overlay').classList.remove('hidden');
                document.getElementById('loading-overlay').classList.add('flex');
                const statuses = ["🚀 Connecting...", "🧠 Groq AI Hooking...", "⚡ TTS Generating...", "🎨 Compositing...", "📽️ Final Rendering..."];
                let i = 0;
                setInterval(() => {
                    document.getElementById('status-text').innerText = statuses[i % statuses.length];
                    i++;
                }, 3000);
            };
        </script>
    </div>
"""

MUSIC_CREATOR_CONTENT = """
    <header class="mb-12">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-100/50 text-emerald-600 text-xs font-bold mb-4 border border-emerald-200/50">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> AI Music Artist Active
        </div>
        <h2 class="text-4xl md:text-5xl font-black text-slate-800 tracking-tight leading-tight">Music <span class="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-yellow-400">Visualizer.</span></h2>
        <p class="text-slate-500 mt-2 text-lg font-medium max-w-2xl">Ubah Audio musik menjadi visual estetik buatan AI (Pollinations.ai).</p>
    </header>

    <div class="max-w-4xl relative">
        <div class="glass-panel p-6 sm:p-12 rounded-[2.5rem]">
            <form action="/generate_music" method="post" enctype="multipart/form-data" id="music-form" class="space-y-10">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-10">
                    <div class="space-y-8">
                        <div class="group">
                            <label class="block text-xs font-black text-slate-400 uppercase tracking-widest mb-4">🎵 Upload Audio (MP3/MP4)</label>
                            <input type="file" name="audio" accept="audio/*,video/*" required class="w-full glass-input p-3 rounded-2xl">
                        </div>
                        <div class="group">
                            <label class="block text-xs font-black text-slate-400 uppercase tracking-widest mb-4">🧠 AI Visual Prompt (Auto-generate)</label>
                            <input type="text" name="image_prompt" placeholder="E.g., Cinematic cyberpunk sky..." class="w-full p-5 glass-input rounded-2xl outline-none">
                        </div>
                    </div>
                    <div class="space-y-8">
                        <div class="group">
                            <label class="block text-xs font-black text-slate-400 uppercase tracking-widest mb-4">🎬 Pilih Model AI</label>
                            <select name="ai_model" class="w-full p-5 glass-input rounded-2xl outline-none font-bold">
                                <option value="flux">⚡ FLUX (Realistic)</option>
                                <option value="zimage">🎬 ZIMAGE (Cinematic)</option>
                            </select>
                        </div>
                        <div class="group">
                            <label class="block text-xs font-black text-slate-400 uppercase tracking-widest mb-4">📸 Atau Upload Manual (Foto Vertikal)</label>
                            <input type="file" name="images" multiple accept="image/*" class="w-full glass-input p-3 rounded-2xl">
                        </div>
                    </div>
                </div>
                
                <button type="submit" id="music-submit-btn" class="w-full py-6 bg-gradient-to-r from-emerald-500 via-emerald-400 to-yellow-400 text-white font-black text-xl rounded-2xl shadow-xl transition-all">
                    🚀 CREATE MUSIC VIDEO AI
                </button>

                <!-- Inline Progress Bar -->
                <div id="music-loading" class="hidden animate-in fade-in duration-500">
                    <div class="glass-panel rounded-[2rem] p-8 border border-emerald-200/50">
                        <div class="flex items-center justify-between mb-4">
                            <span id="music-status-text" class="text-emerald-700 font-extrabold text-sm uppercase tracking-widest">⏳ Sedang mengolah...</span>
                            <span id="music-percent" class="text-emerald-500 font-black text-sm bg-white px-3 py-1 rounded-full">0%</span>
                        </div>
                        <div class="w-full h-3 bg-slate-100 rounded-full overflow-hidden p-[2px]">
                            <div id="music-bar" class="w-0 h-full bg-gradient-to-r from-emerald-500 to-yellow-400 rounded-full transition-all duration-700 shadow-sm"></div>
                        </div>
                    </div>
                </div>
            </form>
        </div>

        {% if result_music %}
        <div class="mt-12 glass-panel p-10 rounded-[2.5rem] border-2 border-emerald-400 animate-in slide-in-from-bottom-10">
            <h3 class="text-2xl font-black text-slate-800 mb-6">Music Video Berhasil!</h3>
            <div class="aspect-video bg-black rounded-2xl overflow-hidden mb-8 shadow-inner">
                <video class="w-full h-full" controls><source src="/download/{{ result_music }}" type="video/mp4"></video>
            </div>
            <a href="/download/{{ result_music }}" class="block w-full py-5 bg-emerald-500 text-white font-black rounded-2xl text-center shadow-lg">📥 DOWNLOAD HASIL</a>
        </div>
        {% endif %}

        <script>
            document.getElementById('music-form').onsubmit = function() {
                document.getElementById('music-submit-btn').classList.add('hidden');
                document.getElementById('music-loading').classList.remove('hidden');
                const steps = [
                    { t: "🎨 Memanggil Seniman AI...", p: 20 },
                    { t: "🎭 Menghasilkan Visual...", p: 45 },
                    { t: "🎵 Meracik Audio...", p: 70 },
                    { t: "⚡ Rendering Final...", p: 95 }
                ];
                let i = 0;
                setInterval(() => {
                    if(i < steps.length) {
                        document.getElementById('music-status-text').innerText = steps[i].t;
                        document.getElementById('music-bar').style.width = steps[i].p + '%';
                        document.getElementById('music-percent').innerText = steps[i].p + '%';
                        i++;
                    }
                }, 4000);
            };
        </script>
    </div>
"""

GALLERY_CONTENT = """
    <header class="mb-12">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-100/50 text-emerald-600 text-xs font-bold mb-4">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span> Galeri Masterpiece
        </div>
        <h2 class="text-4xl md:text-5xl font-black text-slate-800 tracking-tight leading-tight">Gudang <span class="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-yellow-400">Konten.</span></h2>
        <p class="text-slate-500 mt-2 text-lg font-medium max-w-2xl">Semua hasil kreasi video affiliate dan musik Anda tersimpan rapi di sini.</p>
    </header>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
        {% for video in videos %}
        <div class="glass-panel rounded-[2rem] overflow-hidden group hover:scale-[1.02] hover:-translate-y-1 transition-all">
            <div class="relative aspect-[9/16] bg-slate-900">
                <video class="w-full h-full object-cover" controls preload="metadata">
                    <source src="/download/{{ video.path }}" type="video/mp4">
                </video>
                <div class="absolute top-4 left-4 flex gap-2">
                    <span class="px-3 py-1 bg-black/40 backdrop-blur-md rounded-full text-white text-[9px] font-black uppercase tracking-widest border border-white/20">PRO</span>
                </div>
            </div>
            <div class="p-6">
                <h4 class="font-black text-slate-800 text-lg mb-2 line-clamp-1 italic" title="{{ video.name }}">{{ video.name }}</h4>
                
                {% if video.script %}
                <div class="mb-5 p-4 bg-slate-900/90 rounded-2xl relative group/script">
                    <p class="text-[10px] text-emerald-400 font-black uppercase tracking-widest mb-2 flex justify-between">
                        <span>📝 AI Naskah / Prompt</span>
                        <button onclick="copyGalleryText(this)" data-text="{{ video.script }}" class="hover:text-white transition-colors">SALIN</button>
                    </p>
                    <div class="text-slate-300 text-[11px] leading-relaxed line-clamp-3 font-medium">{{ video.script }}</div>
                </div>
                {% endif %}

                <div class="flex items-center justify-between mt-auto">
                    <span class="text-[9px] font-black text-slate-400 uppercase tracking-widest bg-slate-50 px-3 py-1.5 rounded-lg">{{ video.date }}</span>
                    <form action="/delete_video" method="post">
                        <input type="hidden" name="path" value="{{ video.path }}">
                        <button type="submit" class="p-2.5 bg-rose-50 text-rose-500 rounded-xl hover:bg-rose-500 hover:text-white transition-all shadow-sm" onclick="return confirm('Hapus mahakarya ini?')">🗑️</button>
                    </form>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>

    {% if not videos %}
    <div class="text-center py-32 glass-panel rounded-[3rem] border-dashed border-2 border-emerald-100">
        <div class="text-8xl mb-8">🗂️</div>
        <h3 class="text-2xl font-black text-slate-800 mb-10">Belum ada karya yang tersimpan.</h3>
        <a href="/create_affiliate" class="px-10 py-4 bg-emerald-500 text-white font-black rounded-2xl hover:bg-emerald-600 transition-all">MULAI BERKREASI</a>
    </div>
    {% endif %}

    <script>
        function copyGalleryText(btn) {
            const text = btn.getAttribute('data-text');
            navigator.clipboard.writeText(text).then(() => {
                const oldText = btn.innerText;
                btn.innerText = "✅ COPIED";
                setTimeout(() => btn.innerText = oldText, 2000);
            });
        }
    </script>
"""

USERS_CONTENT = """
    <header class="mb-12">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-100/50 text-emerald-600 text-xs font-bold mb-4">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> User Tracking Active
        </div>
        <h2 class="text-4xl md:text-5xl font-black text-slate-800 tracking-tight leading-tight">Pengguna <span class="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-yellow-400">Bot.</span></h2>
        <p class="text-slate-500 mt-2 text-lg font-medium max-w-2xl">Daftar pengguna Telegram yang pernah berinteraksi dengan sistem.</p>
    </header>

    <div class="glass-panel rounded-[2.5rem] overflow-hidden">
        <div class="overflow-x-auto">
            <table class="w-full text-left">
                <thead class="bg-slate-50/50 border-b border-slate-100">
                    <tr>
                        <th class="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">User ID</th>
                        <th class="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Nama / Username</th>
                        <th class="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Terakhir Aktif</th>
                        <th class="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Status</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                    {% for uid, user in users.items() %}
                    <tr class="hover:bg-emerald-50/30 transition-colors">
                        <td class="px-8 py-6 font-bold text-slate-400 text-sm">#{{ uid }}</td>
                        <td class="px-8 py-6">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 bg-gradient-to-br from-slate-100 to-slate-200 rounded-xl flex items-center justify-center text-lg shadow-sm">👤</div>
                                <div>
                                    <div class="font-black text-slate-800">{{ user.first_name }} {{ user.last_name or '' }}</div>
                                    <div class="text-xs font-bold text-emerald-600">@{{ user.username or 'NoUsername' }}</div>
                                </div>
                            </div>
                        </td>
                        <td class="px-8 py-6 text-sm font-bold text-slate-500 italic">{{ user.last_seen }}</td>
                        <td class="px-8 py-6">
                            <span class="px-4 py-1.5 bg-emerald-100 text-emerald-600 rounded-full text-[10px] font-black uppercase tracking-widest border border-emerald-200/50">AKTIF</span>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    {% if not users %}
    <div class="text-center py-20 bg-white/50 rounded-[2.5rem] border-dashed border-2 border-slate-200 mt-10">
        <p class="font-bold text-slate-400">Belum ada data pengguna yang tercatat.</p>
    </div>
    {% endif %}
"""

SETTINGS_CONTENT = """
    <header class="mb-10">
        <h2 class="text-3xl font-black text-slate-800 tracking-tight">Pusat Sistem</h2>
        <p class="text-slate-500 mt-1 font-medium italic">Konfigurasi vokal, musik latar, dan integrasi API.</p>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-10">
        <!-- Background Music -->
        <div class="glass-panel p-8 md:p-10 rounded-[2.5rem]">
            <div class="flex items-center gap-4 mb-8">
                <div class="w-14 h-14 bg-yellow-400 rounded-2xl flex items-center justify-center text-2xl text-white">🎵</div>
                <h3 class="text-xl font-extrabold text-slate-800">Background Music</h3>
            </div>
            <div class="bg-emerald-50/50 p-5 rounded-2xl mb-8 border border-emerald-100">
                <p class="text-[10px] font-black text-slate-400 uppercase mb-1">Aset Aktif Affiliate</p>
                <div class="font-bold text-emerald-700 truncate italic">✓ {{ current_music }}</div>
            </div>
            <form action="/upload_music" method="post" enctype="multipart/form-data" class="space-y-6">
                <input type="file" name="music" accept="audio/*,video/*" required class="w-full glass-input p-3 rounded-2xl">
                <button type="submit" class="w-full py-5 bg-emerald-500 text-white font-black rounded-2xl hover:bg-emerald-600 transition-all shadow-lg">SIMPAN ASET</button>
            </form>
        </div>
        
        <!-- Status Health -->
        <div class="glass-panel p-8 md:p-10 rounded-[2.5rem]">
            <div class="flex items-center gap-4 mb-8">
                <div class="w-14 h-14 bg-emerald-500 rounded-2xl flex items-center justify-center text-2xl text-white">🏥</div>
                <h3 class="text-xl font-extrabold text-slate-800">System Status</h3>
            </div>
            <div class="space-y-4">
                <div class="flex justify-between p-4 bg-white/50 rounded-2xl">
                    <span class="font-bold text-slate-500">API Pollinations</span>
                    <span class="text-emerald-500 font-bold italic">Stable</span>
                </div>
                <div class="flex justify-between p-4 bg-white/50 rounded-2xl">
                    <span class="font-bold text-slate-500">Groq AI Engine</span>
                    <span class="text-emerald-500 font-bold italic">Online</span>
                </div>
                <div class="flex justify-between p-4 bg-white/50 rounded-2xl">
                    <span class="font-bold text-slate-500">FFmpeg Accelerator</span>
                    <span class="text-emerald-500 font-bold italic">Ready</span>
                </div>
            </div>
        </div>
    </div>
"""

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8"><title>Portal Keamanan - Music Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;700;800;900&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Outfit', sans-serif; }
        .animated-bg {
            background: linear-gradient(-45deg, #f8fafc, #f0fdf4, #fefce8, #f8fafc);
            background-size: 400% 400%;
            animation: gradientBG 15s ease infinite;
        }
        @keyframes gradientBG {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        .glass-panel { 
            background: rgba(255, 255, 255, 0.85); 
            backdrop-filter: blur(20px); 
            border: 1px solid rgba(255, 255, 255, 0.4); 
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
        }
    </style>
</head>
<body class="animated-bg flex items-center justify-center min-h-screen">
    <div class="w-full max-w-md glass-panel p-12 rounded-[3.5rem] text-center relative z-10 mx-6">
        <div class="w-24 h-24 bg-gradient-to-br from-emerald-400 via-emerald-500 to-yellow-400 rounded-3xl flex items-center justify-center text-white text-5xl mx-auto mb-10 shadow-xl shadow-emerald-200/50 hover:scale-110 hover:rotate-6 transition-all duration-500">🚀</div>
        <h1 class="text-4xl font-black text-slate-800 tracking-tight mb-2 uppercase">BOT<span class="text-emerald-500">PRO</span></h1>
        <p class="text-slate-500 font-medium mb-12">Dashboard Access Portal</p>
        <form method="POST" class="space-y-8">
            <div class="relative group">
                <input type="password" name="auth_key" placeholder="Enter Access Code" required 
                       class="w-full p-6 glass-input border-2 border-transparent border-b-slate-200 rounded-2xl text-center text-xl font-bold tracking-widest outline-none focus:bg-white focus:border-emerald-400 transition-all">
            </div>
            <button type="submit" class="w-full py-6 rounded-2xl shadow-xl shadow-emerald-200/50 hover:shadow-emerald-300 active:scale-[0.98] transition-all relative overflow-hidden bg-gradient-to-r from-emerald-500 to-emerald-400">
                <span class="relative z-10 text-white font-black tracking-widest text-lg">LOGIN SECURELY ✨</span>
            </button>
        </form>
    </div>
</body>
</html>
"""

# --- Helper Logic ---
def get_stats():
    stats = {"total_users": 0, "videos_created": 0, "images_processed": 0}
    try:
        # Load real users from JSON
        users_file = os.path.join("logs", "users.json")
        if os.path.exists(users_file):
            import json
            with open(users_file, "r") as f:
                users_data = json.load(f)
                stats["total_users"] = len(users_data)
        
        # Simple stats based on gallery files
        if os.path.exists(UPLOAD_FOLDER):
            all_files = os.listdir(UPLOAD_FOLDER)
            videos = [f for f in all_files if f.endswith('.mp4')]
            stats["videos_created"] = len(videos)
            stats["images_processed"] = len(videos) * 5 # average 5 images per video
    except Exception: pass
    return stats

# --- Routes ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"): return redirect(url_for("index"))
    if request.method == "POST":
        if request.form.get("auth_key") == DASHBOARD_AUTH_KEY:
            session["authenticated"] = True
            return redirect(url_for("index"))
        flash("Kunci Akses Salah.")
    return render_template_string(LOGIN_HTML)

@app.route("/logout")
def logout():
    session.pop("authenticated", None)
    return redirect(url_for("login"))

@app.route("/")
@require_auth
def index():
    return render_template_string(LAYOUT_START + STATS_CONTENT + LAYOUT_END, title="Dashboard Statistics", active="dashboard", stats=get_stats())

@app.route("/create_affiliate")
@require_auth
def create_affiliate():
    return render_template_string(LAYOUT_START + AFFILIATE_CREATOR_CONTENT + LAYOUT_END, title="Affiliate Video Creator", active="create_affiliate")

@app.route("/create_music")
@require_auth
def create_music():
    return render_template_string(LAYOUT_START + MUSIC_CREATOR_CONTENT + LAYOUT_END, title="Music Video AI Artist", active="create_music")

@app.route("/generate_affiliate", methods=["POST"])
@require_auth
def generate_affiliate():
    url = request.form.get("url")
    product_name = request.form.get("product_name")
    manual_images = request.files.getlist("images")
    
    # Validation
    if not url:
        if not product_name or not manual_images or manual_images[0].filename == '':
            flash("Jika Link kosong, Anda WAJIB mengisi Nama Produk dan Upload Foto Manual!")
            return redirect(url_for("create_affiliate"))
    
    try:
        session_id = str(uuid.uuid4())[:8]
        session_dir = os.path.join(UPLOAD_FOLDER, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # 1. Handle Info & Script
        scraped_name, scraped_images = None, []
        if url:
            scraped_name, scraped_images = scraper.scrape_product_images(url)
        
        # 2. AI Script
        target_name = product_name or scraped_name or "Produk Viral"
        description = ai_handler.generate_product_description(target_name)
        
        # 3. Handle Images
        local_images = []
        # Priority: Manual Upload -> Scraped
        if manual_images and manual_images[0].filename != '':
            for i, img in enumerate(manual_images[:10]):
                path = os.path.join(session_dir, f"manual_img_{i}.jpg")
                img.save(path)
                local_images.append(path)
        else:
            # Current case: URL must exist if manual_images missing (checked in validation)
            if not scraped_images:
                flash("Gagal mendapatkan gambar. Berikan link valid atau upload foto manual.")
                return redirect(url_for("create_affiliate"))
            for i, img_url in enumerate(scraped_images[:6]):
                img_path = os.path.join(session_dir, f"img_{i}.jpg")
                if scraper.download_image(img_url, img_path):
                    local_images.append(img_path)
        
        # 4. Audio (TTS)
        audio_path = os.path.join(session_dir, f"audio_{session_id}.mp3")
        asyncio.run(ai_handler.text_to_speech(description, audio_path))
        
        # 5. Mix with Music if exists
        bg_music = None
        for file in os.listdir(MUSIC_FOLDER):
            if file.startswith("background"):
                bg_music = os.path.join(MUSIC_FOLDER, file)
                break
        
        if bg_music:
            mixed_audio = os.path.join(session_dir, f"mixed_{session_id}.mp3")
            if video_processor.mix_audio_with_bg_music(audio_path, bg_music, mixed_audio):
                audio_path = mixed_audio
                
        # 6. Render
        video_path = os.path.join(session_dir, f"video_{session_id}.mp4")
        # Save script txt for gallery
        with open(os.path.join(session_dir, "script.txt"), "w", encoding='utf-8') as f:
            f.write(description)
            
        success = video_processor.create_video_from_images_and_audio(local_images, audio_path, video_path)
        
        if success:
            return render_template_string(LAYOUT_START + AFFILIATE_CREATOR_CONTENT + LAYOUT_END, 
                                          title="Video Created", active="create_affiliate", 
                                          result_video=f"{session_id}/video_{session_id}.mp4",
                                          description=description)
    except Exception as e:
        logger.error(f"Affiliate Gen Error: {e}")
        flash(f"Error Produksi: {e}")
        
    return redirect(url_for("create_affiliate"))

@app.route("/generate_music", methods=["POST"])
@require_auth
def generate_music():
    audio_file = request.files.get("audio")
    manual_images = request.files.getlist("images")
    image_prompt = request.form.get("image_prompt")
    ai_model = request.form.get("ai_model", "flux")
    
    if not audio_file:
        flash("Wajib upload file audio!")
        return redirect(url_for("create_music"))
        
    try:
        session_id = str(uuid.uuid4())[:8]
        session_dir = os.path.join(UPLOAD_FOLDER, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # 1. Save Audio
        audio_name = f"music_{session_id}_{audio_file.filename}"
        audio_path = os.path.join(session_dir, audio_name)
        audio_file.save(audio_path)
        
        # 2. Get Images
        local_images = []
        # Save manual images if uploaded
        if manual_images and manual_images[0].filename != '':
            for i, img in enumerate(manual_images[:10]):
                path = os.path.join(session_dir, f"man_{i}.jpg")
                img.save(path)
                local_images.append(path)
        
        # If no manual images or prompt provided, use AI
        if not local_images or image_prompt:
            prompt = image_prompt or audio_file.filename.split('.')[0]
            ai_images = ai_handler.generate_images_from_prompt(prompt, count=5, model=ai_model)
            for i, img_path in enumerate(ai_images):
                new_path = os.path.join(session_dir, os.path.basename(img_path))
                shutil.copy(img_path, new_path)
                local_images.append(new_path)
                
        # 3. Render
        video_path = os.path.join(session_dir, f"music_video_{session_id}.mp4")
        
        # Save prompt for gallery display
        prompt_to_save = image_prompt or audio_file.filename.split('.')[0]
        with open(os.path.join(session_dir, "script.txt"), "w", encoding='utf-8') as f:
            f.write(prompt_to_save)
            
        success = video_processor.create_video_from_images_and_audio(local_images, audio_path, video_path)
        
        if success:
            return render_template_string(LAYOUT_START + MUSIC_CREATOR_CONTENT + LAYOUT_END, 
                                          title="Music Video Ready", active="create_music", 
                                          result_music=f"{session_id}/music_video_{session_id}.mp4")
    except Exception as e:
        logger.error(f"Music Gen Error: {e}")
        flash(f"Error Music Gen: {e}")
        
    return redirect(url_for("create_music"))

@app.route("/gallery")
@require_auth
def gallery():
    videos = []
    if os.path.exists(UPLOAD_FOLDER):
        for session_id in os.listdir(UPLOAD_FOLDER):
            session_dir = os.path.join(UPLOAD_FOLDER, session_id)
            if os.path.isdir(session_dir):
                for f in os.listdir(session_dir):
                    if f.endswith(".mp4"):
                        path = f"{session_id}/{f}"
                        # Try to get script
                        script = ""
                        script_path = os.path.join(session_dir, "script.txt")
                        if os.path.exists(script_path):
                            with open(script_path, "r", encoding='utf-8') as sf:
                                script = sf.read()
                        
                        mtime = os.path.getmtime(os.path.join(session_dir, f))
                        videos.append({
                            "name": f, "path": path, "script": script,
                            "date": datetime.fromtimestamp(mtime).strftime("%d %b %Y, %H:%M"),
                            "raw_time": mtime
                        })
    videos.sort(key=lambda x: x['raw_time'], reverse=True)
    return render_template_string(LAYOUT_START + GALLERY_CONTENT + LAYOUT_END, title="Media Gallery", active="gallery", videos=videos)

@app.route("/users")
@require_auth
def users_list():
    users_data = {}
    users_file = os.path.join("logs", "users.json")
    if os.path.exists(users_file):
        import json
        try:
            with open(users_file, "r") as f:
                users_data = json.load(f)
        except: pass
    return render_template_string(LAYOUT_START + USERS_CONTENT + LAYOUT_END, title="Telegram Users", active="users", users=users_data)

@app.route("/settings")
@require_auth
def settings():
    current_music = "Default (Belum diupload)"
    for file in os.listdir(MUSIC_FOLDER):
        if file.startswith("background"):
            current_music = file
            break
    return render_template_string(LAYOUT_START + SETTINGS_CONTENT + LAYOUT_END, title="System Settings", active="settings", current_music=current_music)

@app.route("/upload_music", methods=["POST"])
@require_auth
def upload_music():
    file = request.files.get("music")
    if file:
        # Clear old background music
        for f in os.listdir(MUSIC_FOLDER):
            if f.startswith("background"): os.remove(os.path.join(MUSIC_FOLDER, f))
        
        ext = file.filename.split('.')[-1]
        file.save(os.path.join(MUSIC_FOLDER, f"background.{ext}"))
        flash("Musik latar berhasil masuk sistem!")
    return redirect(url_for("settings"))

@app.route("/delete_video", methods=["POST"])
@require_auth
def delete_video():
    path = request.form.get("path")
    if path:
        full_path = os.path.join(UPLOAD_FOLDER, path)
        session_dir = os.path.dirname(full_path)
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
            flash("Karya berhasil dihapus.")
    return redirect(url_for("gallery"))

@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
