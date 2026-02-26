from flask import Flask, render_template_string, request, send_from_directory, redirect, url_for, flash, session
import os
import re
import uuid
import shutil
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from ai_handler import AIHandler
from video_processor import VideoProcessor
from scraper import TikTokShopScraper
from logger_config import logger

load_dotenv()

app = Flask(__name__)
app.secret_key = "tiktok_bot_secret_key"

# Paths
LOG_FILE = "logs/bot_activity.log"
UPLOAD_FOLDER = "temp/web_uploads"
MUSIC_FOLDER = "assets/music"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MUSIC_FOLDER, exist_ok=True)

# Security
DASHBOARD_AUTH_KEY = os.getenv("DASHBOARD_AUTH_KEY", "admin123") # Default for fallback

# Initialize Handlers
ai_handler = AIHandler()
video_processor = VideoProcessor()
scraper = TikTokShopScraper()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

BASE_CSS = """
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
"""

LAYOUT_START = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - TikTok Bot Pro</title>
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
                <a href="/create" class="group flex items-center gap-4 px-5 py-4 rounded-2xl font-bold transition-all duration-300 hover:scale-[1.02] {{ 'text-emerald-700 bg-emerald-50/80 shadow-sm border border-emerald-100/50' if active == 'create' else 'text-slate-500 hover:bg-white/60 hover:text-slate-800' }}">
                    <span class="text-xl">🎬</span> Video Creator
                </a>
                <a href="/gallery" class="group flex items-center gap-4 px-5 py-4 rounded-2xl font-bold transition-all duration-300 hover:scale-[1.02] {{ 'text-emerald-700 bg-emerald-50/80 shadow-sm border border-emerald-100/50' if active == 'gallery' else 'text-slate-500 hover:bg-white/60 hover:text-slate-800' }}">
                    <span class="text-xl">🖼️</span> Galeri Video
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
                VERSION 4.0 FRESH
            </div>
        </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 lg:ml-72 min-h-screen pt-24 pb-10 px-4 md:px-8 lg:pt-10 lg:px-12 relative z-10 w-full overflow-hidden">
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <div class="mb-8 p-4 bg-emerald-50 border border-emerald-100 text-emerald-700 rounded-2xl flex items-center gap-3 animate-pulse">
                <span class="text-xl">✨</span> {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}
"""

LAYOUT_END = """
    </main>
    <script>
        // Mobile Sidebar Toggle UI
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

INDEX_CONTENT = """
    <header class="mb-10">
        <h2 class="text-3xl font-black text-slate-800 tracking-tight">Capaian Bot</h2>
        <p class="text-slate-500 mt-1 font-medium">Statistik performa dan aktivitas sistem real-time.</p>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <div class="glass-panel p-8 rounded-[2rem] relative overflow-hidden group hover:scale-[1.02] transition-all duration-300">
            <div class="absolute top-0 right-0 w-24 h-24 bg-emerald-500/10 rounded-bl-[4rem] flex items-center justify-center transition-transform group-hover:scale-110 group-hover:bg-emerald-500/20">👤</div>
            <div class="text-slate-400 font-bold text-xs uppercase tracking-widest mb-1">Total Pengguna</div>
            <div class="text-4xl font-black text-slate-800">{{ stats.total_users }}</div>
        </div>
        <div class="glass-panel p-8 rounded-[2rem] relative overflow-hidden group hover:scale-[1.02] transition-all duration-300">
            <div class="absolute top-0 right-0 w-24 h-24 bg-yellow-500/10 rounded-bl-[4rem] flex items-center justify-center transition-transform group-hover:scale-110 group-hover:bg-yellow-500/20">🎬</div>
            <div class="text-slate-400 font-bold text-xs uppercase tracking-widest mb-1">Video Dibuat</div>
            <div class="text-4xl font-black text-slate-800">{{ stats.videos_created }}</div>
        </div>
        <div class="glass-panel p-8 rounded-[2rem] relative overflow-hidden group hover:scale-[1.02] transition-all duration-300">
            <div class="absolute top-0 right-0 w-24 h-24 bg-indigo-500/10 rounded-bl-[4rem] flex items-center justify-center transition-transform group-hover:scale-110 group-hover:bg-indigo-500/20">🖼️</div>
            <div class="text-slate-400 font-bold text-xs uppercase tracking-widest mb-1">Foto Diproses</div>
            <div class="text-4xl font-black text-slate-800">{{ stats.images_processed }}</div>
        </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-10">
        <div class="bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-sm">
            <div class="flex items-center justify-between mb-8">
                <h3 class="text-xl font-extrabold text-slate-800 flex items-center gap-3">
                    <span class="w-3 h-3 bg-emerald-500 rounded-full animate-ping"></span> 
                    Aktivitas Terbaru
                </h3>
            </div>
            <div class="space-y-4 max-h-[500px] overflow-y-auto pr-4 custom-scrollbar flex flex-col-reverse">
                {% for log in logs %}
                    <div class="p-4 rounded-2xl bg-slate-50 border border-slate-100 transition-hover hover:border-emerald-200">
                        <div class="flex justify-between items-start gap-4">
                            <p class="text-sm font-semibold text-slate-700 leading-relaxed">{{ log.message }}</p>
                            <span class="text-[10px] font-black uppercase text-slate-400 bg-white px-2 py-1 rounded-lg border border-slate-100 shrink-0">{{ log.time.split(' ')[1] }}</span>
                        </div>
                        <div class="mt-2 text-[10px] font-bold {{ 'text-emerald-500' if log.level == 'INFO' else 'text-rose-500' }}">{{ log.level }}</div>
                    </div>
                {% endfor %}
            </div>
        </div>

        <div class="bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-sm">
            <h3 class="text-xl font-extrabold text-slate-800 mb-8">Pengguna Aktif</h3>
            <div class="space-y-4">
                {% for user in active_users[:8] %}
                    <div class="flex items-center justify-between p-5 rounded-[1.5rem] bg-gradient-to-r from-slate-50 to-transparent border border-slate-100">
                        <div class="flex items-center gap-4">
                            <div class="w-12 h-12 rounded-full bg-white border border-slate-100 flex items-center justify-center text-xl shadow-sm">👤</div>
                            <div>
                                <div class="font-black text-slate-800">{{ user.id }}</div>
                                <div class="text-xs text-slate-400 font-medium">Terakhir: {{ user.last_seen }}</div>
                            </div>
                        </div>
                        <div class="text-emerald-500 text-sm font-black italic">Active</div>
                    </div>
                {% endfor %}
                {% if not active_users %}
                    <div class="text-center py-20 bg-slate-50 rounded-[2rem] border border-dashed border-slate-200">
                        <div class="text-5xl mb-4">💤</div>
                        <p class="text-slate-400 font-bold">Belum ada pengguna aktif</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
"""

CREATE_CONTENT = """
    <header class="mb-10">
        <h2 class="text-3xl font-black text-slate-800 tracking-tight">Mesin Kreator</h2>
        <p class="text-slate-500 mt-1 font-medium">Buat video promosi viral hanya dalam hitungan detik.</p>
    </header>

    <div class="max-w-4xl">
        <div class="bg-white p-10 rounded-[2.5rem] border border-slate-100 shadow-xl shadow-slate-200/50">
            <form action="/generate" method="post" enctype="multipart/form-data" id="creator-form" class="space-y-10">
                <!-- Links Area -->
                <div>
                    <label class="block text-xs font-black text-slate-400 uppercase tracking-[0.2em] mb-4">🔗 Link Produk (TikTok Shop)</label>
                    <textarea name="product_links" placeholder="Tempel link produk di sini (mendukung banyak link sekaligus)..." class="min-h-[160px] resize-none focus:ring-4 focus:ring-emerald-100 focus:border-emerald-500"></textarea>
                </div>
                
                <!-- Divider -->
                <div class="relative py-4">
                    <div class="absolute inset-0 flex items-center"><div class="w-full border-t border-slate-100"></div></div>
                    <div class="relative flex justify-center"><span class="bg-white px-6 text-xs font-black text-slate-300 uppercase tracking-widest">Atau Manual</span></div>
                </div>

                <!-- Photos Area -->
                <div>
                    <label class="block text-xs font-black text-slate-400 uppercase tracking-[0.2em] mb-4">🖼️ Upload Foto Produk</label>
                    <div class="relative group">
                        <input type="file" name="images" multiple accept="image/*" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" id="file-upload">
                        <div class="border-4 border-dashed border-slate-100 rounded-[2rem] p-12 text-center bg-slate-50/50 transition-all group-hover:bg-emerald-50 group-hover:border-emerald-200">
                            <div class="w-20 h-20 bg-white rounded-3xl flex items-center justify-center text-3xl mx-auto mb-6 shadow-sm group-hover:scale-110 transition-transform">📤</div>
                            <h4 class="text-lg font-extrabold text-slate-700">Pilih atau Tarik Foto</h4>
                            <p class="text-slate-400 text-sm mt-2 font-medium">Mendukung format PNG, JPG, JPEG, dan WebP</p>
                        </div>
                    </div>
                </div>

                <!-- Product Name -->
                <div>
                    <label class="block text-xs font-black text-slate-400 uppercase tracking-[0.2em] mb-4">🏷️ Nama Produk (Opsional)</label>
                    <input type="text" name="product_name" placeholder="Kosongkan jika ingin dideteksi otomatis oleh AI" class="focus:ring-4 focus:ring-emerald-100 focus:border-emerald-500">
                </div>
                
                <button type="submit" class="w-full py-6 bg-gradient-to-r from-emerald-500 to-emerald-400 text-white font-black text-xl rounded-2xl shadow-lg shadow-emerald-200 hover:shadow-emerald-300 transform active:scale-[0.98] transition-all">
                    🚀 MULAI PRODUKSI VIDEO
                </button>
            </form>
        </div>

        <!-- Result Card -->
        {% if result_video %}
        <div class="mt-12 bg-white p-10 rounded-[2.5rem] border-4 border-emerald-400 shadow-2xl animate-in slide-in-from-bottom-10 duration-500">
            <div class="flex items-center gap-4 mb-8">
                <div class="w-14 h-14 bg-emerald-500 rounded-2xl flex items-center justify-center text-2xl shadow-lg shadow-emerald-200">✨</div>
                <div>
                    <h3 class="text-2xl font-black text-slate-800">Video Siap Digunakan!</h3>
                    <p class="text-emerald-600 font-bold">Konten affiliate Anda telah diproses sempurna.</p>
                </div>
            </div>
            
            {% if description %}
            <div class="mb-8 rounded-[1.5rem] bg-slate-900 p-8 relative group">
                <div class="flex justify-between items-center mb-6">
                    <span class="text-[10px] font-black text-emerald-400 uppercase tracking-[0.2em]">📜 Naskah Viral AI</span>
                    <button onclick="copyDesc()" class="text-xs font-black text-white bg-emerald-500 px-4 py-2 rounded-lg hover:bg-emerald-400 transition-colors" id="btn-copy-main">SALIN TEKS</button>
                </div>
                <div id="ai-desc" class="text-slate-300 font-medium leading-loose text-sm italic">{{ description }}</div>
            </div>
            {% endif %}

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <a href="/download/{{ result_video }}" class="flex items-center justify-center gap-3 py-5 bg-emerald-500 text-white font-black rounded-2xl hover:bg-emerald-600 transition-all shadow-lg shadow-emerald-100">
                    📥 DOWNLOAD MP4
                </a>
                <a href="/gallery" class="flex items-center justify-center gap-3 py-5 bg-yellow-400 text-white font-black rounded-2xl hover:bg-yellow-500 transition-all shadow-lg shadow-yellow-100">
                    🖼️ LIHAT DI GALERI
                </a>
            </div>
        </div>
        <script>
            function copyDesc() {
                var text = document.getElementById("ai-desc").innerText;
                navigator.clipboard.writeText(text).then(function() {
                    const btn = document.getElementById("btn-copy-main");
                    btn.innerHTML = "✅ TERSALIN!";
                    setTimeout(() => { btn.innerHTML = "SALIN TEKS"; }, 2000);
                });
            }
        </script>
        {% endif %}

        <!-- Loading Overlay Fresh -->
        <div id="loading-overlay" class="fixed inset-0 bg-slate-50/90 backdrop-blur-xl z-[100] hidden flex-col items-center justify-center text-center p-8">
            <div class="relative w-48 h-48 mb-10">
                <div class="absolute inset-0 border-8 border-slate-100 rounded-full"></div>
                <div class="absolute inset-0 border-8 border-emerald-500 rounded-full border-t-transparent animate-spin"></div>
                <div class="absolute inset-0 flex items-center justify-center text-6xl animate-bounce">🎬</div>
            </div>
            <h2 class="text-4xl font-black text-slate-800 mb-4 tracking-tight">PROSES PRODUKSI...</h2>
            <div id="status-text" class="text-xl font-bold text-emerald-600 bg-emerald-50 px-8 py-3 rounded-2xl border border-emerald-100">Inisialisasi server...</div>
            <p class="mt-8 text-slate-400 font-medium max-w-sm">Mohon tunggu, AI sedang meracik naskah dan menggabungkan video untuk Anda.</p>
        </div>

        <script>
            document.getElementById('creator-form').onsubmit = function() {
                document.getElementById('loading-overlay').classList.remove('hidden');
                document.getElementById('loading-overlay').classList.add('flex');
                const statuses = [
                    "🚀 Menghubungkan ke API Tiktok...",
                    "🧠 Groq AI: Merancang naskah persuasif...",
                    "⚡ TTS: Menciptakan suara AI manusiawi...",
                    "🎨 Compositing: Menambal transisi halus...",
                    "📽️ Rendering: Memproses video Kualitas Tinggi..."
                ];
                let i = 0;
                setInterval(() => {
                    const statusEl = document.getElementById('status-text');
                    if(statusEl) {
                        statusEl.style.opacity = '0';
                        setTimeout(() => {
                            statusEl.innerText = statuses[i % statuses.length];
                            statusEl.style.opacity = '1';
                        }, 300);
                    }
                    i++;
                }, 3000);
            };
        </script>
    </div>
"""

GALLERY_CONTENT = """
    <header class="mb-10">
        <h2 class="text-3xl font-black text-slate-800 tracking-tight">Galeri Karya</h2>
        <p class="text-slate-500 mt-1 font-medium">Koleksi video affiliate yang siap dipublikasikan.</p>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-2 xxl:grid-cols-3 gap-8">
        {% for video in videos %}
        <div class="bg-white rounded-[2rem] overflow-hidden border border-slate-100 shadow-sm hover:shadow-xl hover:shadow-slate-200/50 transition-all flex flex-col group">
            <div class="relative aspect-[9/16] bg-slate-900 group-hover:scale-[1.02] transition-transform duration-500 overflow-hidden">
                <video class="w-full h-full object-cover" controls preload="none">
                    <source src="/download/{{ video.path }}" type="video/mp4">
                </video>
            </div>
            
            <div class="p-6 flex-1 flex flex-col">
                <div class="flex items-center justify-between mb-4">
                    <span class="text-xs font-black text-slate-300 uppercase tracking-widest">{{ video.date }}</span>
                    <span class="w-2 h-2 bg-emerald-500 rounded-full"></span>
                </div>
                <h4 class="font-extrabold text-slate-800 text-lg mb-4 line-clamp-1" title="{{ video.name }}">{{ video.name }}</h4>
                
                {% if video.script %}
                <div class="bg-slate-50 border border-slate-100 rounded-2xl p-4 mb-6 group/script">
                    <div class="flex justify-between items-center mb-3">
                        <span class="text-[10px] font-black text-slate-400 tracking-widest uppercase">📜 Naskah Video</span>
                        <button onclick="copyGalleryScript('script-{{ loop.index }}')" class="text-[10px] font-black text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-100 hover:bg-white transition-all">SALIN</button>
                    </div>
                    <div id="script-{{ loop.index }}" class="text-xs text-slate-500 leading-relaxed font-medium italic h-20 overflow-y-auto pr-2 custom-scrollbar">{{ video.script }}</div>
                </div>
                {% endif %}
                
                <div class="mt-auto grid grid-cols-5 gap-3">
                    <a href="/download/{{ video.path }}" class="col-span-4 py-3.5 bg-slate-900 text-white font-black text-sm rounded-xl text-center hover:bg-slate-800 transition-all">
                        DOWNLOAD MP4
                    </a>
                    <form action="/delete_video" method="post" class="col-span-1">
                        <input type="hidden" name="path" value="{{ video.path }}">
                        <button type="submit" class="w-full h-full py-3.5 bg-rose-50 text-rose-500 border border-rose-100 rounded-xl flex items-center justify-center hover:bg-rose-500 hover:text-white transition-all" onclick="return confirm('Hapus permanen?')">
                            🗑️
                        </button>
                    </form>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>

    <script>
        function copyGalleryScript(id) {
            const text = document.getElementById(id).innerText;
            navigator.clipboard.writeText(text).then(() => {
                alert("Naskah berhasil disalin ke clipboard! 📋 ✨");
            });
        }
    </script>
    
    {% if not videos %}
    <div class="text-center py-40 bg-white rounded-[3rem] border border-dashed border-slate-200">
        <div class="text-8xl mb-10 transform scale-110">🎬</div>
        <h3 class="text-3xl font-black text-slate-800 mb-4">Galeri Masih Kosong</h3>
        <p class="text-slate-400 font-medium max-w-sm mx-auto mb-10">Mulai buat video pertama Anda dengan mesin kreator kami yang super cepat.</p>
        <a href="/create" class="inline-flex items-center gap-3 px-10 py-5 bg-emerald-500 text-white font-black rounded-2xl hover:bg-emerald-600 transition-all shadow-lg shadow-emerald-100">
            🚀 BUAT VIDEO SEKARANG
        </a>
    </div>
    {% endif %}
"""

SETTINGS_CONTENT = """
    <header class="mb-10">
        <h2 class="text-3xl font-black text-slate-800 tracking-tight">Pusat Sistem</h2>
        <p class="text-slate-500 mt-1 font-medium">Atur aset, mesin AI, dan performa keseluruhan bot.</p>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-10">
        <!-- Background Music -->
        <div class="bg-white p-10 rounded-[2.5rem] border border-slate-100 shadow-sm">
            <div class="flex items-center gap-4 mb-8">
                <div class="w-14 h-14 bg-yellow-400 rounded-2xl flex items-center justify-center text-2xl shadow-lg shadow-yellow-100">🎵</div>
                <h3 class="text-xl font-extrabold text-slate-800">Soundtrack Utama</h3>
            </div>
            
            <div class="bg-slate-50/50 p-6 rounded-2xl border border-slate-100 mb-8">
                <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">File Aktif Sekarang</p>
                <div class="flex items-center gap-3">
                    <span class="text-emerald-500 text-xl font-black italic">✓</span>
                    <span class="font-bold text-slate-700">{{ current_music }}</span>
                </div>
            </div>
            
            <form action="/upload_music" method="post" enctype="multipart/form-data" class="space-y-6">
                <div>
                    <label class="block text-xs font-black text-slate-400 uppercase tracking-widest mb-3">Upload File Baru (MP3, MP4, MOV)</label>
                    <input type="file" name="music" accept="audio/*,video/*" required class="bg-slate-50 border-slate-100">
                </div>
                <button type="submit" class="w-full py-5 bg-emerald-500 text-white font-black rounded-2xl hover:bg-emerald-600 transition-all shadow-lg shadow-emerald-100">
                    UPDATE & SIMPAN ASET
                </button>
            </form>
        </div>
        
        <!-- Health Monitor -->
        <div class="bg-white p-10 rounded-[2.5rem] border border-slate-100 shadow-sm">
            <div class="flex items-center gap-4 mb-8">
                <div class="w-14 h-14 bg-emerald-500 rounded-2xl flex items-center justify-center text-2xl shadow-lg shadow-emerald-100">🏥</div>
                <h3 class="text-xl font-extrabold text-slate-800">Status Kesehatan</h3>
            </div>
            
            <div class="space-y-4">
                <div class="flex items-center justify-between p-5 rounded-2xl bg-slate-50 border border-slate-100">
                    <div class="font-bold text-slate-600">Mesin AI Groq</div>
                    <span class="px-4 py-1.5 bg-emerald-500 text-white text-[10px] font-black rounded-full uppercase">Normal</span>
                </div>
                <div class="flex items-center justify-between p-5 rounded-2xl bg-slate-50 border border-slate-100">
                    <div class="font-bold text-slate-600">Video Core FFmpeg</div>
                    <span class="px-4 py-1.5 bg-emerald-500 text-white text-[10px] font-black rounded-full uppercase">Ready</span>
                </div>
                <div class="flex items-center justify-between p-5 rounded-2xl bg-slate-50 border border-slate-100">
                    <div class="font-bold text-slate-600">Penyimpanan Temp</div>
                    <span class="text-emerald-600 font-extrabold">{{ storage_used }} MB</span>
                </div>
            </div>

            <div class="mt-12 text-center pt-8 border-t border-slate-50">
                <div class="text-xl font-black text-slate-800">BOT<span class="text-emerald-500">PRO</span> <span class="text-yellow-400">FRESH</span></div>
                <p class="text-slate-400 text-[10px] font-bold mt-1 uppercase tracking-widest">Premium Affiliate Automation Engine</p>
                <p class="text-slate-300 text-[9px] mt-4">Handcrafted with precision by Antigravity v4.0</p>
            </div>
        </div>
    </div>
"""
# Function definitions and routes follow...

def get_dashboard_data():
    if not os.path.exists(LOG_FILE):
        return [], {"total_users": 0, "videos_created": 0, "images_processed": 0, "errors": 0}, []
    
    parsed_logs = []
    stats = {"total_users": 0, "videos_created": 0, "images_processed": 0, "errors": 0}
    unique_users = {}
    
    try:
        with open(LOG_FILE, "r", encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                parts = line.split(" - ")
                if len(parts) >= 4:
                    time_str, level, msg = parts[0], parts[2], parts[3].strip()
                    parsed_logs.append({"time": time_str, "level": level, "message": msg})
                    if "Selesai! Mengirimkan video" in msg: stats["videos_created"] += 1
                    if "uploaded image" in msg: stats["images_processed"] += 1
                    user_match = re.search(r"User (.*?) \(ID: (\d+)\)|User (\d+) uploaded", msg)
                    if user_match:
                        uid = user_match.group(2) or user_match.group(3)
                        if uid: unique_users[uid] = time_str
        stats["total_users"] = len(unique_users)
        active_users = [{"id": uid, "last_seen": time} for uid, time in unique_users.items()]
        active_users.sort(key=lambda x: x["last_seen"], reverse=True)
        return parsed_logs[-100:], stats, active_users
    except:
        return [], stats, []

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("index"))
    
    if request.method == "POST":
        key = request.form.get("auth_key")
        if key == DASHBOARD_AUTH_KEY:
            session["authenticated"] = True
            flash("Welcome back, Commander!")
            return redirect(url_for("index"))
        else:
            flash("Invalid access key. Access denied.")
            
    # Fresh Login Page Template using Tailwind
    return render_template_string("""
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - TikTok Bot Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap" rel="stylesheet">
    <style>body { font-family: 'Plus Jakarta Sans', sans-serif; }</style>
</head>
<body class="bg-slate-50 flex items-center justify-center min-h-screen p-6">
    <div class="w-full max-w-md bg-white p-10 rounded-[2.5rem] border border-slate-100 shadow-2xl shadow-slate-200/50 text-center">
        <div class="w-16 h-16 bg-gradient-to-br from-emerald-400 to-yellow-400 rounded-2xl flex items-center justify-center text-white text-3xl mx-auto mb-8 shadow-lg shadow-emerald-100 italic">🚀</div>
        <h1 class="text-2xl font-black text-slate-800 mb-2">Akses Terkunci</h1>
        <p class="text-slate-400 font-medium mb-10">Masukkan kode akses Anda untuk melanjutkan ke dashboard bot.</p>
        
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <div class="mb-8 p-4 bg-rose-50 border border-rose-100 text-rose-500 rounded-2xl text-sm font-bold">
                ⚠️ {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <form method="POST" class="space-y-6">
            <div class="text-left">
                <label class="block text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-3 ml-2">KODE AKSES RAHASIA</label>
                <input type="password" name="auth_key" placeholder="••••••••" required 
                       class="w-full p-5 bg-slate-50 border border-slate-100 rounded-2xl focus:ring-4 focus:ring-emerald-100 focus:border-emerald-500 transition-all text-center text-xl tracking-widest outline-none">
            </div>
            <button type="submit" class="w-full py-5 bg-slate-900 text-white font-black rounded-2xl hover:bg-emerald-500 transition-all shadow-lg hover:shadow-emerald-200">
                MASUK KE DASHBOARD
            </button>
        </form>
        
        <p class="mt-12 text-[10px] font-bold text-slate-300 uppercase tracking-widest">Enterprise Edition v4.0 Fresh</p>
    </div>
</body>
</html>
""")

@app.route("/logout")
def logout():
    session.pop("authenticated", None)
    flash("You have been logged out.")
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    logs, stats, active_users = get_dashboard_data()
    return render_template_string(LAYOUT_START + INDEX_CONTENT + LAYOUT_END, title="Dashboard", active="dashboard", logs=logs, stats=stats, active_users=active_users)

@app.route("/create")
@login_required
def create():
    return render_template_string(LAYOUT_START + CREATE_CONTENT + LAYOUT_END, title="Create Video", active="create")

@app.route("/gallery")
@login_required
def gallery():
    videos = []
    if os.path.exists(UPLOAD_FOLDER):
        for root, dirs, files in os.walk(UPLOAD_FOLDER):
            for file in files:
                if file.endswith(".mp4"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, UPLOAD_FOLDER).replace("\\", "/")
                    
                    # Read corresponding script if exists
                    script_content = ""
                    script_path = full_path.replace(".mp4", "_script.txt")
                    if os.path.exists(script_path):
                        try:
                            with open(script_path, "r", encoding='utf-8') as f:
                                script_content = f.read()
                        except: pass
                        
                    stat = os.stat(full_path)
                    videos.append({
                        "name": file,
                        "path": rel_path,
                        "script": script_content,
                        "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "timestamp": stat.st_mtime
                    })
    videos.sort(key=lambda x: x["timestamp"], reverse=True)
    return render_template_string(LAYOUT_START + GALLERY_CONTENT + LAYOUT_END, title="Gallery", active="gallery", videos=videos)

@app.route("/delete_video", methods=["POST"])
@login_required
def delete_video():
    path = request.form.get("path")
    if path:
        full_path = os.path.join(UPLOAD_FOLDER, path)
        if os.path.exists(full_path):
            os.remove(full_path)
            # Try to remove parent dir if empty
            parent = os.path.dirname(full_path)
            try: 
                if not os.listdir(parent): os.rmdir(parent)
            except: pass
            flash("Video berhasil dihapus.")
    return redirect(url_for("gallery"))

@app.route("/settings")
@login_required
def settings():
    music_files = [f for f in os.listdir(MUSIC_FOLDER) if f.startswith("background.")]
    current = music_files[0] if music_files else "None"
    
    # Calculate storage
    total_size = 0
    if os.path.exists(UPLOAD_FOLDER):
        for root, dirs, files in os.walk(UPLOAD_FOLDER):
            for f in files: total_size += os.path.getsize(os.path.join(root, f))
    
    return render_template_string(LAYOUT_START + SETTINGS_CONTENT + LAYOUT_END, title="Settings", active="settings", current_music=current, storage_used=round(total_size/(1024*1024), 2))

@app.route("/upload_music", methods=["POST"])
@login_required
def upload_music():
    file = request.files.get("music")
    if file:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext in ['.mp3', '.mp4', '.mov', '.wav', '.m4a']:
            # Remove existing background files first
            for f in os.listdir(MUSIC_FOLDER):
                if f.startswith("background."):
                    try: os.remove(os.path.join(MUSIC_FOLDER, f))
                    except: pass
            
            target = os.path.join(MUSIC_FOLDER, f"background{ext}")
            file.save(target)
            flash(f"Background music ({ext}) berhasil diperbarui!")
        else:
            flash("Format file tidak didukung. Gunakan MP3, MP4, MOV, atau WAV.")
    return redirect(url_for("settings"))

@app.route("/generate", methods=["GET", "POST"])
@login_required
def generate():
    if request.method == "GET":
        return redirect(url_for("create"))
    product_name = request.form.get("product_name")
    links_text = request.form.get("product_links", "")
    files = request.files.getlist("images")
    
    urls = scraper.extract_urls(links_text)[:10]
    if not product_name and not urls and (not files or files[0].filename == ''):
        flash("Mohon masukkan link, nama produk, atau upload foto.")
        return redirect(url_for("create"))
    
    session_id = str(uuid.uuid4().hex[:8])
    session_dir = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    image_paths = []
    scraped_name = ""
    
    if urls:
        num_links = len(urls)
        for i, url in enumerate(urls):
            try:
                result = scraper.scrape_product(url)
                if result['success'] and result.get('image_urls'):
                    if not scraped_name: scraped_name = result['product_name']
                    limit = 6 if num_links == 1 else 3
                    img_urls = result['image_urls'][:limit]
                    for j, img_url in enumerate(img_urls):
                        try:
                            import requests
                            resp = requests.get(img_url, headers=scraper.headers, timeout=10)
                            if resp.status_code == 200:
                                path = os.path.join(session_dir, f"scraped_{i}_{j}.jpg")
                                with open(path, "wb") as f: f.write(resp.content)
                                image_paths.append(path)
                        except: continue
            except: continue

    if not product_name:
        product_name = scraped_name if scraped_name else "New Product"
        if len(urls) > 1: product_name += " & others"

    if files and files[0].filename != '':
        for i, file in enumerate(files):
            path = os.path.join(session_dir, f"manual_{i}.jpg")
            file.save(path)
            image_paths.append(path)
    
    if not image_paths:
        flash("Error: No images found.")
        return redirect(url_for("create"))

    try:
        description = ai_handler.generate_product_description(product_name)
        audio_path = os.path.join(session_dir, "voice.mp3")
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        if not loop.run_until_complete(ai_handler.text_to_speech(description, audio_path)):
            raise Exception("TTS Failed")
        
        # 4. Generate Video
        video_path = os.path.join(session_dir, f"tiktok_video_{session_id}.mp4")
        script_path = os.path.join(session_dir, f"tiktok_video_{session_id}_script.txt")
        
        # Save script to txt for gallery persistence
        with open(script_path, "w", encoding='utf-8') as f:
            f.write(description)
            
        success = video_processor.create_video_from_images_and_audio(image_paths, audio_path, video_path)
        
        if success:
            logger.info(f"Video created successfully for {product_name or scraped_name}")
            return render_template_string(LAYOUT_START + CREATE_CONTENT + LAYOUT_END, 
                                         title="Video Created", 
                                         active="create", 
                                         result_video=f"{session_id}/tiktok_video_{session_id}.mp4",
                                         description=description)
    except Exception as e:
        flash(f"Error: {e}")
        return redirect(url_for("create"))

@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    # host='0.0.0.0' allows access from other devices on same WiFi
    app.run(debug=True, host='0.0.0.0', port=5000)
