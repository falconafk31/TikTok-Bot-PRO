from flask import Flask, render_template_string, request, send_from_directory, redirect, url_for, flash, session
import os
import uuid
import shutil
import asyncio
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from ai_handler import AIHandler
from video_processor import VideoProcessor
from logger_config import logger
import time

load_dotenv()

app = Flask(__name__)
app.secret_key = "music_bot_secret_key"

# Paths
UPLOAD_FOLDER = "temp/music_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Security
DASHBOARD_AUTH_KEY = os.getenv("DASHBOARD_AUTH_KEY", "admin123")

# Initialize Handlers
ai_handler = AIHandler()
video_processor = VideoProcessor()

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

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

/* Animated Background Gradient */
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

/* Custom Input File Styling */
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
input[type="file"]::file-selector-button:hover {
    background: #059669;
    box-shadow: 0 4px 14px 0 rgba(16, 185, 129, 0.39);
}
"""

LAYOUT_START = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Music Video Pro</title>
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
            <div class="w-8 h-8 bg-gradient-to-br from-emerald-400 to-yellow-400 rounded-lg flex items-center justify-center text-white text-sm shadow-md">🎵</div>
            <h1 class="text-xl font-black tracking-tight text-slate-800">MUSIC<span class="text-emerald-500">PRO</span></h1>
        </div>
        <button id="mobile-menu-btn" class="p-2 bg-white/50 backdrop-blur-sm rounded-lg text-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-400 shadow-sm border border-slate-200">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
        </button>
    </header>

    <!-- Mobile Overlay -->
    <div id="sidebar-overlay" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-40 hidden lg:hidden transition-opacity duration-300 opacity-0 cursor-pointer"></div>

    <aside id="sidebar" class="sidebar-transition w-72 glass-panel h-screen fixed left-0 top-0 z-50 flex flex-col border-r border-white/40 transform -translate-x-full lg:translate-x-0">
        <div class="p-8">
            <div class="flex items-center justify-between mb-12">
                <div class="flex items-center gap-4 group cursor-pointer">
                    <div class="w-12 h-12 bg-gradient-to-br from-emerald-400 via-emerald-500 to-yellow-400 rounded-2xl flex items-center justify-center text-white text-2xl shadow-lg shadow-emerald-200/50 group-hover:shadow-emerald-300/60 group-hover:scale-105 transition-all duration-300">🎵</div>
                    <h1 class="text-2xl font-black tracking-tight text-slate-800">MUSIC<span class="text-emerald-500">PRO</span></h1>
                </div>
                <button id="close-sidebar-btn" class="lg:hidden p-2 text-slate-400 hover:text-rose-500 rounded-full hover:bg-rose-50 transition-colors">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <nav class="space-y-3 relative">
                <a href="/" class="group flex items-center gap-4 px-5 py-4 rounded-2xl font-bold transition-all duration-300 hover:scale-[1.02] {{ 'text-emerald-700 bg-emerald-50/80 shadow-sm border border-emerald-100/50' if active == 'dashboard' else 'text-slate-500 hover:bg-white/60 hover:text-slate-800' }}">
                    <span class="text-xl group-hover:animate-bounce-short">🎬</span> Music Creator
                </a>
                <a href="/gallery" class="group flex items-center gap-4 px-5 py-4 rounded-2xl font-bold transition-all duration-300 hover:scale-[1.02] {{ 'text-emerald-700 bg-emerald-50/80 shadow-sm border border-emerald-100/50' if active == 'gallery' else 'text-slate-500 hover:bg-white/60 hover:text-slate-800' }}">
                    <span class="text-xl group-hover:rotate-12 transition-transform">🖼️</span> Galeri Video
                </a>
                
                <div class="w-10/12 h-[1px] bg-gradient-to-r from-transparent via-slate-200 to-transparent mx-auto my-8"></div>
                
                <a href="/logout" class="group flex items-center gap-4 px-5 py-4 rounded-2xl font-bold text-rose-500 hover:bg-rose-50/80 transition-all duration-300 hover:scale-[1.02]">
                    <span class="text-xl group-hover:-translate-x-1 transition-transform">🚪</span> Logout
                </a>
            </nav>
        </div>
        <div class="mt-auto p-8 text-center backdrop-blur-md bg-white/30 border-t border-white/50">
            <div class="inline-block px-4 py-1.5 rounded-full bg-emerald-100/50 text-emerald-600 text-[10px] font-black uppercase tracking-widest border border-emerald-200/50">
                PRO VERSION 2.0
            </div>
        </div>
    </aside>

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

MUSIC_CREATE_CONTENT = """
    <header class="mb-12">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-100/50 text-emerald-600 text-xs font-bold mb-4 border border-emerald-200/50">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> AI Engine Active
        </div>
        <h2 class="text-4xl md:text-5xl font-black text-slate-800 tracking-tight leading-tight">Music Video <span class="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-yellow-400">Creator.</span></h2>
        <p class="text-slate-500 mt-2 text-lg font-medium max-w-2xl">Ubah musik Anda menjadi karya visual memukau dengan kekuatan AI generasi terbaru.</p>
    </header>

    <div class="max-w-4xl relative">
        <!-- Glow background effect -->
        <div class="absolute -inset-1 bg-gradient-to-r from-emerald-400 to-yellow-300 rounded-[3rem] blur-xl opacity-20 -z-10 animate-pulse"></div>
        
        <div class="glass-panel p-6 sm:p-8 md:p-12 rounded-[2rem] md:rounded-[2.5rem]">
            <form action="/generate" method="post" enctype="multipart/form-data" id="creator-form" class="space-y-8 md:space-y-10">
                
                <!-- Audio Upload -->
                <div class="group">
                    <label class="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest mb-4">
                        <span class="text-emerald-500 text-base">01.</span> Upload Audio
                    </label>
                    <div class="relative">
                        <input type="file" name="audio" accept="audio/*,video/*" required class="w-full p-4 glass-input rounded-2xl outline-none z-10 relative">
                        <div class="absolute inset-0 border-2 border-transparent group-hover:border-emerald-200/50 rounded-2xl pointer-events-none transition-colors duration-300"></div>
                    </div>
                </div>

                <div class="relative py-6">
                    <div class="absolute inset-0 flex items-center"><div class="w-full border-t border-slate-200/60"></div></div>
                    <div class="relative flex justify-center"><span class="bg-[#f0fdf4] px-6 text-[10px] font-black text-emerald-600 uppercase tracking-[0.3em] rounded-full border border-emerald-100/50 py-1 shadow-sm">Visual Engine</span></div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-10">
                    <!-- AI Image Prompt -->
                    <div class="group">
                        <label class="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest mb-4">
                            <span class="text-emerald-500 text-base">02.</span> Prompt AI Visual
                        </label>
                        <input type="text" name="image_prompt" placeholder="E.g., Cinematic cyberpunk city at night..." class="w-full p-5 glass-input rounded-2xl outline-none font-medium placeholder:text-slate-300">
                    </div>

                    <!-- Model Selection -->
                    <div class="group">
                        <label class="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest mb-4">
                            <span class="text-emerald-500 text-base">03.</span> Pilih Model
                        </label>
                        <div class="relative">
                            <select name="ai_model" class="w-full p-5 glass-input rounded-2xl outline-none font-extrabold text-slate-700 appearance-none cursor-pointer">
                                <option value="flux">⚡ FLUX (Ultra Realistic)</option>
                                <option value="zimage">🎬 ZIMAGE (Cinematic)</option>
                            </select>
                            <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-6 text-slate-400">
                                <svg class="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/></svg>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Manual Photos Area -->
                <div class="group">
                    <label class="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest mb-4">
                        <span class="text-slate-300 text-base">OR</span> Upload Manual (Hindari jika pakai AI)
                    </label>
                    <div class="relative">
                        <input type="file" name="images" multiple accept="image/*" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10">
                        <div class="border-2 border-dashed border-slate-300/50 rounded-[2rem] p-10 text-center bg-white/40 backdrop-blur-sm transition-all duration-300 group-hover:bg-emerald-50/50 group-hover:border-emerald-300/80 group-hover:shadow-inner">
                            <div class="w-16 h-16 bg-white rounded-2xl flex items-center justify-center text-2xl mx-auto mb-4 shadow-sm group-hover:scale-110 transition-transform duration-300">📸</div>
                            <h4 class="text-base font-extrabold text-slate-600">Drag & Drop atau Klik Memilih Foto</h4>
                            <p class="text-slate-400 text-xs mt-2 font-medium">Resolusi disarankan: 9:16 (Vertikal)</p>
                        </div>
                    </div>
                </div>
                
                <button type="submit" id="submit-btn" class="relative overflow-hidden w-full py-6 group rounded-2xl shadow-xl shadow-emerald-200/50 hover:shadow-emerald-300/60 transform active:scale-[0.98] transition-all duration-300">
                    <div class="absolute inset-0 bg-gradient-to-r from-emerald-500 via-emerald-400 to-yellow-400 bg-[length:200%_auto] hover:bg-[100%_auto] transition-all duration-500"></div>
                    <span class="relative z-10 text-white font-black text-xl tracking-wide flex items-center justify-center gap-3">
                        <span class="text-2xl group-hover:animate-bounce">🚀</span> GENERATE MUSIC VIDEO
                    </span>
                </button>

                <!-- Inline Loading Status -->
                <div id="loading-status" class="hidden animate-in fade-in slide-in-from-top-4 duration-500">
                    <div class="glass-panel rounded-[2rem] p-8 border border-emerald-200/50 relative overflow-hidden">
                        <div class="absolute inset-0 bg-gradient-to-r from-emerald-500/5 to-yellow-500/5 animate-pulse"></div>
                        <div class="relative z-10">
                            <div class="flex items-center justify-between mb-4">
                                <span id="status-text" class="text-emerald-700 font-extrabold text-sm uppercase tracking-widest flex items-center gap-3">
                                    <span class="animate-spin text-xl block">⏳</span> Sedang menginisialisasi...
                                </span>
                                <span id="progress-percent" class="text-emerald-500 font-black text-sm px-3 py-1 bg-white rounded-full shadow-sm">0%</span>
                            </div>
                            <div class="w-full h-3 bg-slate-100 rounded-full overflow-hidden p-[2px]">
                                <div id="progress-bar" class="w-0 h-full bg-gradient-to-r from-emerald-500 to-yellow-400 rounded-full transition-all duration-700 ease-out shadow-[0_0_10px_rgba(16,185,129,0.5)]"></div>
                            </div>
                            <p class="text-xs text-slate-500 mt-5 font-medium text-center bg-white/50 py-2 rounded-xl backdrop-blur-sm">Mesin AI Pro sedang membuat mahakarya untuk Anda. Jangan tutup layar ini. ✨</p>
                        </div>
                    </div>
                </div>
            </form>
        </div>

        {% if result_video %}
        <div class="mt-12 bg-white p-10 rounded-[2.5rem] border-4 border-emerald-400 shadow-2xl animate-in slide-in-from-bottom-10">
            <div class="flex items-center gap-4 mb-8">
                <div class="w-14 h-14 bg-emerald-500 rounded-2xl flex items-center justify-center text-2xl shadow-lg shadow-emerald-200">🎸</div>
                <div>
                    <h3 class="text-2xl font-black text-slate-800">Music Video Berhasil Dibuat!</h3>
                    <p class="text-emerald-600 font-bold">Visual dan musik telah digabungkan sempurna.</p>
                </div>
            </div>
            <div class="aspect-video bg-black rounded-2xl overflow-hidden mb-8 shadow-inner">
                <video class="w-full h-full" controls>
                    <source src="/download/{{ result_video }}" type="video/mp4">
                </video>
            </div>
            <a href="/download/{{ result_video }}" class="block w-full py-5 bg-emerald-500 text-white font-black rounded-2xl text-center hover:bg-emerald-600 transition-all shadow-lg">
                📥 DOWNLOAD HASIL AKHIR
            </a>
        </div>
        {% endif %}

        <script>
            document.getElementById('creator-form').onsubmit = function() {
                // Hide button and show status
                document.getElementById('submit-btn').classList.add('hidden');
                const statusArea = document.getElementById('loading-status');
                statusArea.classList.remove('hidden');
                
                const statusText = document.getElementById('status-text');
                const progressBar = document.getElementById('progress-bar');
                const progressPercent = document.getElementById('progress-percent');
                
                const steps = [
                    { text: "🧠 Memanggil AI Engine...", p: 15 },
                    { text: "🎨 Mengunduh Aset Visual...", p: 35 },
                    { text: "🎵 Sinkronisasi Audio...", p: 55 },
                    { text: "🎞️ Menjahit Frame Musik...", p: 75 },
                    { text: "⚡ Final Rendering...", p: 92 }
                ];
                
                let currentStep = 0;
                const interval = setInterval(() => {
                    if(currentStep < steps.length) {
                        const step = steps[currentStep];
                        statusText.innerHTML = `<span class="animate-spin text-xl">⏳</span> ${step.text}`;
                        progressBar.style.width = `${step.p}%`;
                        progressPercent.innerText = `${step.p}%`;
                        currentStep++;
                    } else {
                        clearInterval(interval);
                    }
                }, 4000);
            };
        </script>
    </div>
"""

GALLERY_CONTENT = """
    <header class="mb-12">
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-100/50 text-emerald-600 text-xs font-bold mb-4 border border-emerald-200/50">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span> Koleksi Karya
        </div>
        <h2 class="text-4xl md:text-5xl font-black text-slate-800 tracking-tight leading-tight">Galeri <span class="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 to-yellow-400">Musik.</span></h2>
        <p class="text-slate-500 mt-2 text-lg font-medium max-w-2xl">Koleksi mahakarya video musik yang telah dihasilkan oleh AI Engine Anda.</p>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-2 xxl:grid-cols-3 gap-8">
        {% for video in videos %}
        <div class="glass-panel rounded-[2rem] overflow-hidden group hover:scale-[1.02] hover:-translate-y-2 transition-all duration-300">
            <div class="relative aspect-[9/16] bg-slate-900 overflow-hidden">
                <video class="w-full h-full object-cover" controls preload="metadata">
                    <source src="/download/{{ video.path }}" type="video/mp4">
                </video>
                <!-- Subtle overlay vignette -->
                <div class="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-transparent to-transparent pointer-events-none"></div>
                <div class="absolute top-4 left-4">
                    <span class="px-3 py-1 bg-black/40 backdrop-blur-md rounded-full text-white text-[10px] font-black uppercase tracking-widest border border-white/20">AI Visual</span>
                </div>
            </div>
            <div class="p-6 bg-white/40 backdrop-blur-md border-t border-white/50">
                <h4 class="font-black text-slate-800 text-lg mb-4 line-clamp-1 group-hover:text-emerald-600 transition-colors" title="{{ video.name }}">{{ video.name }}</h4>
                <div class="flex items-center justify-between">
                    <span class="text-[10px] font-extrabold text-slate-400 uppercase tracking-[0.2em] bg-white/60 px-3 py-1.5 rounded-xl">{{ video.date }}</span>
                    <form action="/delete_video" method="post" class="relative z-10">
                        <input type="hidden" name="path" value="{{ video.path }}">
                        <button type="submit" class="p-2.5 bg-rose-50 text-rose-500 border border-rose-100 rounded-xl hover:bg-rose-500 hover:text-white transition-all duration-300 shadow-sm hover:shadow-rose-300 group/btn" onclick="return confirm('Apakah Anda yakin ingin menghapus mahakarya ini secara permanen?')">
                            <span class="group-hover/btn:hidden block text-lg">🗑️</span>
                            <span class="hidden group-hover/btn:block text-lg">⚠️</span>
                        </button>
                    </form>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>

    {% if not videos %}
    <div class="text-center py-32 glass-panel rounded-[3rem] border border-dashed border-emerald-200/50">
        <div class="text-8xl mb-8 animate-bounce-short">✨</div>
        <h3 class="text-3xl font-black text-slate-800 mb-4">Galeri Masih Kosong</h3>
        <p class="text-slate-500 font-medium mb-10 max-w-md mx-auto">Mulailah menciptakan mahakarya video musik pertama Anda menggunakan keajaiban AI.</p>
        <a href="/" class="inline-flex py-4 px-10 group rounded-2xl shadow-lg shadow-emerald-200/50 hover:shadow-emerald-300/60 transform hover:scale-[1.02] active:scale-[0.98] transition-all duration-300 bg-gradient-to-r from-emerald-500 to-emerald-400">
            <span class="text-white font-black text-lg tracking-wide flex items-center justify-center gap-3">
                <span class="text-xl group-hover:rotate-12 transition-transform">🚀</span> BUAT SEKARANG
            </span>
        </a>
    </div>
    {% endif %}
"""

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("index"))
    if request.method == "POST":
        if request.form.get("auth_key") == DASHBOARD_AUTH_KEY:
            session["authenticated"] = True
            return redirect(url_for("index"))
        else:
            flash("Kunci Akses Salah.")
    return render_template_string("""
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
    <!-- Background Decor -->
    <div class="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-300 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse"></div>
    <div class="absolute bottom-1/4 right-1/4 w-96 h-96 bg-yellow-300 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse" style="animation-delay: 2s;"></div>
    
    <div class="w-full max-w-md glass-panel p-12 rounded-[3rem] text-center relative z-10">
        <div class="w-24 h-24 bg-gradient-to-br from-emerald-400 via-emerald-500 to-yellow-400 rounded-3xl flex items-center justify-center text-white text-5xl mx-auto mb-10 shadow-xl shadow-emerald-200/50 hover:scale-110 hover:rotate-6 transition-all duration-500">🎵</div>
        <h1 class="text-4xl font-black text-slate-800 tracking-tight mb-2">MUSIC<span class="text-emerald-500">PRO</span></h1>
        <p class="text-slate-500 font-medium mb-12">Portal Akses Keamanan Sistem</p>
        <form method="POST" class="space-y-8">
            <div class="relative group">
                <input type="password" name="auth_key" placeholder="Masukkan Kunci Akses" required 
                       class="w-full p-6 bg-white/60 backdrop-blur-sm border-2 border-transparent border-b-slate-200 rounded-2xl text-center text-xl font-bold tracking-widest outline-none focus:bg-white focus:border-emerald-400 shadow-sm transition-all duration-300 placeholder:tracking-normal placeholder:font-medium placeholder:text-sm">
            </div>
            <button type="submit" class="w-full py-6 group rounded-2xl shadow-xl shadow-emerald-200/50 hover:shadow-emerald-300/60 transform active:scale-[0.98] transition-all duration-300 relative overflow-hidden bg-gradient-to-r from-emerald-500 to-emerald-400">
                <span class="relative z-10 text-white font-black tracking-widest text-lg flex items-center justify-center gap-3">
                    BUKA AKSES <span class="group-hover:translate-x-2 transition-transform">✨</span>
                </span>
            </button>
        </form>
    </div>
</body>
</html>
""")

@app.route("/logout")
def logout():
    session.pop("authenticated", None)
    return redirect(url_for("login"))

@app.route("/")
@require_auth
def index():
    return render_template_string(LAYOUT_START + MUSIC_CREATE_CONTENT + LAYOUT_END, 
                                 title="Music Video Creator", active="dashboard")

@app.route("/gallery")
@require_auth
def gallery():
    videos = []
    if os.path.exists(UPLOAD_FOLDER):
        files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".mp4")]
        # Sort by latest
        files.sort(key=lambda x: os.path.getmtime(os.path.join(UPLOAD_FOLDER, x)), reverse=True)
        for f in files:
            mtime = os.path.getmtime(os.path.join(UPLOAD_FOLDER, f))
            date_str = datetime.fromtimestamp(mtime).strftime("%d %b %Y, %H:%M")
            videos.append({
                "name": f,
                "path": f,
                "date": date_str
            })
    return render_template_string(LAYOUT_START + GALLERY_CONTENT + LAYOUT_END, 
                                 title="Galeri Music", active="gallery", videos=videos)

@app.route("/delete_video", methods=["POST"])
@require_auth
def delete_video():
    video_path = request.form.get("path")
    if video_path:
        full_path = os.path.join(UPLOAD_FOLDER, video_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            # Also try to delete accompanying text/script file if exists
            base = os.path.splitext(full_path)[0]
            if os.path.exists(base + ".txt"):
                os.remove(base + ".txt")
            flash("Video berhasil dihapus!")
    return redirect(url_for("gallery"))

@app.route("/generate", methods=["POST"])
@require_auth
def generate():
    audio_file = request.files.get("audio")
    image_prompt = request.form.get("image_prompt")
    ai_model = request.form.get("ai_model", "flux") # Get selected model
    manual_images = request.files.getlist("images")
    
    if not audio_file:
        flash("File audio wajib diunggah!")
        return redirect(url_for("index"))

    # Save audio
    audio_path = os.path.join("temp", audio_file.filename)
    os.makedirs("temp", exist_ok=True)
    audio_file.save(audio_path)

    try:
        image_paths = []
        if image_prompt and (not manual_images or not manual_images[0].filename):
            # Use AI Generator with selected model
            image_paths = ai_handler.generate_images_from_prompt(image_prompt, count=5, model=ai_model)
        elif manual_images and manual_images[0].filename:
            # Save manual images
            for img in manual_images:
                path = os.path.join("temp", img.filename)
                img.save(path)
                image_paths.append(path)
        
        if not image_paths:
            flash("Gagal mendapatkan gambar (AI atau Manual)!")
            return redirect(url_for("index"))

        # Create video
        output_filename = f"music_video_{int(time.time())}.mp4"
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        success = video_processor.create_video_from_images_and_audio(
            image_paths, audio_path, output_path
        )

        if success:
            return render_template_string(LAYOUT_START + MUSIC_CREATE_CONTENT + LAYOUT_END, 
                                         title="Video Selesai", active="dashboard", result_video=output_filename)
        else:
            flash("Gagal membuat video. Cek log server.")
            return redirect(url_for("index"))

    except Exception as e:
        logger.error(f"Generate Error: {e}")
        flash(f"Error: {e}")
        return redirect(url_for("index"))

@app.route("/download/<path:filename>")
@require_auth
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
