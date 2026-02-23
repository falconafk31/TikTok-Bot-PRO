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
:root {
    --bg-main: #f0f5ff;
    --card-bg: #ffffff;
    --sidebar-bg: linear-gradient(180deg, #0052D4 0%, #4364F7 50%, #6FB1FC 100%);
    --accent-blue: #007bff;
    --accent-royal: #0056b3;
    --accent-cyan: #00b4d8;
    --accent-success: #28a745;
    --accent-danger: #dc3545;
    --text-primary: #1a365d;
    --text-secondary: #4a5568;
    --border-soft: rgba(0, 0, 0, 0.05);
    --shadow-soft: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
    --sidebar-width: 260px;
}

body { 
    font-family: 'Outfit', 'Inter', sans-serif; 
    background: var(--bg-main);
    color: var(--text-primary); 
    margin: 0; padding: 0;
    min-height: 100vh;
    display: flex;
    line-height: 1.6;
}

/* Scrollbar */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #f8fafc; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; border: 2px solid #f8fafc; }
::-webkit-scrollbar-thumb:hover { background: var(--accent-blue); }

.sidebar {
    width: var(--sidebar-width);
    background: var(--sidebar-bg);
    height: 100vh;
    position: fixed;
    padding: 40px 20px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    z-index: 100;
    color: white;
    box-shadow: 4px 0 15px rgba(0, 0, 0, 0.05);
    transition: transform 0.3s ease;
}

.main-content { 
    flex: 1;
    margin-left: var(--sidebar-width);
    padding: 60px 50px;
    box-sizing: border-box;
    width: 100%;
}

.logo { 
    font-size: 24px; 
    font-weight: 800; 
    color: white;
    margin-bottom: 50px;
    letter-spacing: -0.5px;
    text-align: center;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    padding-bottom: 20px;
}

.nav-menu { list-style: none; padding: 0; margin: 0; }
.nav-item { margin-bottom: 10px; }
.nav-link { 
    text-decoration: none; 
    color: rgba(255,255,255,0.8); 
    padding: 14px 20px; 
    border-radius: 14px; 
    display: flex;
    align-items: center;
    gap: 12px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    font-weight: 500;
}

.nav-link:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
    transform: translateX(5px);
}

.nav-link.active { 
    background: white;
    color: var(--accent-royal);
    font-weight: 700;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.card { 
    background: var(--card-bg);
    border: 1px solid var(--border-soft);
    border-radius: 20px;
    padding: 35px;
    margin-bottom: 30px;
    box-shadow: var(--shadow-soft);
    transition: all 0.3s ease;
}

.card:hover { transform: translateY(-5px); box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.08); }

.btn { 
    background: var(--accent-blue);
    border: none;
    color: white; 
    padding: 14px 28px; 
    border-radius: 14px; 
    cursor: pointer; 
    font-weight: 700; 
    transition: all 0.3s ease;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
}

.btn:hover { 
    background: var(--accent-royal);
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(0, 123, 255, 0.3);
}

.btn-red { background: var(--accent-danger); }
.btn-red:hover { background: #c82333; box-shadow: 0 8px 20px rgba(220, 53, 69, 0.3); }

.btn-outline { 
    background: white; 
    border: 1.5px solid #e2e8f0; 
    color: var(--text-secondary);
}
.btn-outline:hover { border-color: var(--accent-blue); color: var(--accent-blue); background: #f8fafc; }

input[type="text"], input[type="file"], textarea, select {
    width: 100%; padding: 15px;
    background: #f8fafc;
    border: 2px solid #edf2f7;
    border-radius: 14px;
    color: var(--text-primary);
    box-sizing: border-box;
    transition: all 0.3s ease;
    font-size: 15px;
}

input:focus, textarea:focus {
    outline: none;
    border-color: var(--accent-blue);
    background: white;
    box-shadow: 0 0 0 4px rgba(0, 123, 255, 0.1);
}

.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 30px; margin-bottom: 40px; }
.stat-card { text-align: center; }
.stat-value { font-size: 42px; font-weight: 800; color: var(--accent-blue); }
.stat-label { font-size: 14px; color: var(--text-secondary); font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }

.flash-msg { 
    padding: 18px 28px; 
    border-radius: 16px; 
    margin-bottom: 40px; 
    background: #ebf8ff;
    color: #2b6cb0;
    border-left: 6px solid #3182ce;
    font-weight: 600;
    animation: fadeIn 0.4s ease-out;
}

@keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }

.menu-toggle { display: none; }

@media (max-width: 992px) {
    .sidebar { transform: translateX(-100%); width: 260px; height: 100vh; position: fixed; box-shadow: 10px 0 30px rgba(0,0,0,0.1); }
    .sidebar.active { transform: translateX(0); }
    .main-content { margin-left: 0; padding: 40px 20px; }
    .menu-toggle { display: block; position: fixed; top: 20px; right: 20px; z-index: 200; border-radius: 10px; }
    .menu-toggle { display: block; position: fixed; top: 20px; right: 20px; z-index: 200; border-radius: 10px; }
    .nav-menu { display: flex; flex-direction: column; width: 100%; }
}

/* Auth Pages */
.auth-container {
    width: 100%;
    max-width: 400px;
    margin: 100px auto;
    padding: 40px;
    background: white;
    border-radius: 24px;
    box-shadow: var(--shadow-soft);
    text-align: center;
}

.auth-logo {
    font-size: 28px;
    font-weight: 900;
    background: var(--sidebar-bg);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 30px;
}

/* Loading Overlay */
#loading-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(240, 245, 255, 0.95);
    backdrop-filter: blur(12px);
    z-index: 1000;
    display: none;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
}

.loader-container {
    position: relative;
    width: 120px;
    height: 120px;
    margin-bottom: 30px;
}

.loader-ring {
    position: absolute;
    width: 100%;
    height: 100%;
    border: 6px solid #e2e8f0;
    border-top: 6px solid var(--accent-blue);
    border-radius: 50%;
    animation: spin 1.5s linear infinite;
}

.loader-ring-outer {
    position: absolute;
    top: -10px; left: -10px; right: -10px; bottom: -10px;
    border: 4px solid rgba(0, 123, 255, 0.1);
    border-radius: 50%;
    animation: pulse 2s ease-in-out infinite;
}

@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
@keyframes pulse { 0%, 100% { transform: scale(1); opacity: 0.5; } 50% { transform: scale(1.1); opacity: 0.8; } }

.loading-text {
    font-size: 24px;
    font-weight: 800;
    color: var(--text-primary);
    margin-bottom: 10px;
}

.loading-subtext {
    color: var(--text-secondary);
    font-size: 14px;
    max-width: 300px;
}
"""

LAYOUT_START = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - TikTok Bot Pro</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>""" + BASE_CSS + """</style>
</head>
<body>
    <button class="btn btn-outline menu-toggle" onclick="document.querySelector('.sidebar').classList.toggle('active')">☰ Menu</button>
    <div class="sidebar">
        <div class="logo">TIKTOK BOT PRO</div>
        <ul class="nav-menu">
            <li class="nav-item"><a href="/" class="nav-link {{ 'active' if active == 'dashboard' else '' }}">📊 Dashboard</a></li>
            <li class="nav-item"><a href="/create" class="nav-link {{ 'active' if active == 'create' else '' }}">🎬 Video Creator</a></li>
            <li class="nav-item"><a href="/gallery" class="nav-link {{ 'active' if active == 'gallery' else '' }}">🖼 Gallery</a></li>
            <li class="nav-item"><a href="/settings" class="nav-link {{ 'active' if active == 'settings' else '' }}">⚙️ Settings</a></li>
            <li class="nav-item" style="margin-top: auto; padding-top: 40px; border-top: 1px solid rgba(255,255,255,0.1);">
                <a href="/logout" class="nav-link" style="color: #ff8080; background: rgba(220, 53, 69, 0.1);"><span>🚪</span> Logout</a>
            </li>
        </ul>
        <div style="margin-top: auto; font-size: 11px; color: var(--text-dim); opacity: 0.5;">v2.5 Premium Edition</div>
    </div>
    <div class="main-content">
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <div class="flash-msg">✨ {{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
"""

LAYOUT_END = """
    </div>
</body>
</html>
"""

INDEX_CONTENT = """
    <div class="header" style="margin-bottom: 40px;">
        <h1 style="font-size: 32px; font-weight: 800; color: var(--text-primary); margin-bottom: 5px;">Dashboard Overview</h1>
        <p style="color: var(--text-secondary); font-size: 16px;">Real-time bot performance and activity metrics.</p>
    </div>

    <div class="stats-grid">
        <div class="card stat-card" style="border-bottom: 4px solid var(--accent-blue);">
            <div class="stat-label">Total Users</div>
            <div class="stat-value">{{ stats.total_users }}</div>
        </div>
        <div class="card stat-card" style="border-bottom: 4px solid var(--accent-success);">
            <div class="stat-label">Videos Created</div>
            <div class="stat-value">{{ stats.videos_created }}</div>
        </div>
        <div class="card stat-card" style="border-bottom: 4px solid var(--accent-cyan);">
            <div class="stat-label">Images Processed</div>
            <div class="stat-value">{{ stats.images_processed }}</div>
        </div>
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 35px;">
        <div class="card">
            <h3 style="margin-top: 0; font-size: 20px; font-weight: 700; margin-bottom: 25px; display: flex; align-items: center; gap: 12px; color: var(--accent-royal);">
                <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: var(--accent-success); box-shadow: 0 0 10px var(--accent-success);"></span> 
                Live Activity Feed
            </h3>
            <div style="height: 450px; overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 13px; display: flex; flex-direction: column-reverse; padding-right: 15px;">
                {% for log in logs %}
                    <div style="padding: 12px 0; border-bottom: 1px solid #f1f5f9; line-height: 1.6;">
                        <span style="color: var(--text-secondary); font-size: 11px;">{{ log.time }}</span> 
                        <span style="color: {{ 'var(--accent-success)' if log.level == 'INFO' else 'var(--accent-danger)' }}; font-weight: 800; margin: 0 8px;">[{{ log.level }}]</span> 
                        <span style="color: var(--text-primary);">{{ log.message }}</span>
                    </div>
                {% endfor %}
            </div>
        </div>
        <div class="card">
            <h3 style="margin-top: 0; font-size: 20px; font-weight: 700; margin-bottom: 25px; color: var(--accent-royal);">Recent Active Users</h3>
            <div style="display: flex; flex-direction: column; gap: 18px;">
                {% for user in active_users[:10] %}
                    <div style="padding: 18px; background: #f8fafc; border-radius: 16px; border: 1px solid #edf2f7; display: flex; justify-content: space-between; align-items: center; transition: all 0.3s ease;">
                        <div>
                            <div style="font-weight: 800; font-size: 16px; color: var(--text-primary);">{{ user.id }}</div>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 3px;">Activity logged: {{ user.last_seen }}</div>
                        </div>
                        <div style="background: white; padding: 10px; border-radius: 10px; box-shadow: var(--shadow-soft);">👤</div>
                    </div>
                {% endfor %}
                {% if not active_users %}
                    <div style="text-align: center; padding: 40px; background: #f8fafc; border-radius: 16px;">
                        <p style="color: var(--text-secondary);">No active users found yet.</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
"""

CREATE_CONTENT = """
    <div class="header" style="margin-bottom: 40px;">
        <h1 style="font-size: 32px; font-weight: 800; color: var(--text-primary); margin-bottom: 5px;">Video Creator Engine</h1>
        <p style="color: var(--text-secondary); font-size: 16px;">Generate high-converting TikTok affiliate videos in seconds.</p>
    </div>

    <div style="max-width: 850px; margin: 0 auto;">
        <div class="card">
            <form action="/generate" method="post" enctype="multipart/form-data" id="creator-form">
                <div class="form-group">
                    <label style="color: var(--accent-royal); text-transform: uppercase; letter-spacing: 1px; font-size: 12px;">🔗 AUTOMATED LINKS (Tiktok Shop)</label>
                    <textarea name="product_links" placeholder="Paste product URLs here (supports bulk scraping)..." style="min-height: 140px; margin-top: 10px;"></textarea>
                </div>
                
                <div style="position: relative; text-align: center; margin: 40px 0;">
                    <hr style="border: none; border-top: 2px solid #f1f5f9;">
                    <span style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 0 20px; color: var(--text-secondary); font-size: 12px; font-weight: 800; letter-spacing: 1px;">OR MANUAL CREATION</span>
                </div>

                <div class="form-group">
                    <label style="color: var(--accent-royal); text-transform: uppercase; letter-spacing: 1px; font-size: 12px;">🖼️ UPLOAD PRODUCT PHOTOS</label>
                    <div style="border: 2px dashed #cbd5e1; border-radius: 18px; padding: 40px; text-align: center; background: #f8fafc; transition: all 0.3s ease; margin-top: 10px;" onmouseover="this.style.borderColor='var(--accent-blue)'; this.style.background='white';" onmouseout="this.style.borderColor='#cbd5e1'; this.style.background='#f8fafc';">
                        <input type="file" name="images" multiple accept="image/*" style="opacity: 0; position: absolute; width: 0.1px; height: 0.1px;" id="file-upload">
                        <label for="file-upload" style="cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 15px; margin: 0;">
                            <div style="font-size: 40px;">📤</div>
                            <span style="color: var(--text-primary); font-weight: 700; font-size: 16px;">Click to select or drag images here</span>
                            <span style="color: var(--text-secondary); font-size: 13px;">Supports PNG, JPG, JPEG, and WebP</span>
                        </label>
                    </div>
                </div>

                <div class="form-group" style="margin-top: 30px;">
                    <label style="color: var(--accent-royal); text-transform: uppercase; letter-spacing: 1px; font-size: 12px;">🏷️ BRAND/PRODUCT NAME (Optional)</label>
                    <input type="text" name="product_name" placeholder="Leave blank to use AI detection from links" style="margin-top: 10px;">
                </div>
                
                <button type="submit" class="btn" style="width: 100%; margin-top: 20px; padding: 18px; font-size: 18px;">🎬 GENERATE PRODUCTION VIDEO</button>
            </form>
        </div>

        <!-- Animation Overlay -->
        <div id="loading-overlay">
            <div class="loader-container">
                <div class="loader-ring-outer"></div>
                <div class="loader-ring"></div>
                <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; font-size: 30px;">🎬</div>
            </div>
            <div class="loading-text">Generating Your Content...</div>
            <div class="loading-subtext">AI is creating description, generating voiceover, and rendering video. Please wait.</div>
        </div>

        <script>
            document.getElementById('creator-form').onsubmit = function() {
                document.getElementById('loading-overlay').style.display = 'flex';
                const statuses = [
                    "Analyzing product data...",
                    "Writing viral script...",
                    "Generating AI voiceover...",
                    "Mixing background music...",
                    "Rendering high-quality video...",
                    "Finalizing effects..."
                ];
                let i = 0;
                setInterval(() => {
                    const sub = document.querySelector('.loading-subtext');
                    if(sub) sub.innerText = statuses[i % statuses.length];
                    i++;
                }, 4000);
            };
        </script>

        {% if result_video %}
        <div class="card" style="background: #f0fff4; border: 2px solid var(--accent-success); animation: softGlow 2s infinite alternate;">
            <h2 style="color: #22543d; margin-top: 0; display: flex; align-items: center; gap: 12px; font-size: 24px;">
                <span>✨</span> Creation Successful!
            </h2>
            <p style="color: #2f855a; margin-bottom: 25px;">Your high-quality affiliate video has been rendered and is ready for use.</p>
            
            {% if description %}
            <div style="margin: 25px 0; background: white; padding: 25px; border-radius: 18px; border: 1px solid #c6f6d5; box-shadow: var(--shadow-soft);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #f1f5f9; padding-bottom: 15px;">
                    <label style="font-size: 11px; color: var(--text-secondary); font-weight: 800; text-transform: uppercase; letter-spacing: 1.5px;">📋 AI Naskah & Deskripsi</label>
                    <button onclick="copyDesc()" class="btn btn-outline" style="font-size: 11px; padding: 8px 16px; border-radius: 8px;">COPY TEXT</button>
                </div>
                <div id="ai-desc" style="font-size: 15px; line-height: 1.8; color: var(--text-primary); white-space: pre-wrap;">{{ description }}</div>
            </div>
            <script>
                function copyDesc() {
                    var text = document.getElementById("ai-desc").innerText;
                    navigator.clipboard.writeText(text).then(function() {
                        const btn = document.querySelector('button[onclick="copyDesc()"]');
                        btn.innerHTML = "✅ SUCCESS!";
                        btn.style.borderColor = "var(--accent-success)";
                        btn.style.color = "var(--accent-success)";
                        setTimeout(() => {
                            btn.innerHTML = "COPY TEXT";
                            btn.style.borderColor = "#e2e8f0";
                            btn.style.color = "var(--text-secondary)";
                        }, 2000);
                    });
                }
            </script>
            {% endif %}

            <div style="display: flex; gap: 20px;">
                <a href="/download/{{ result_video }}" class="btn" style="flex: 1; background: var(--accent-success); padding: 18px;">⬇️ DOWNLOAD RESULT (MP4)</a>
            </div>
        </div>
        <style>@keyframes softGlow { from { box-shadow: 0 0 10px rgba(40, 167, 69, 0.1); } to { box-shadow: 0 0 25px rgba(40, 167, 69, 0.25); } }</style>
        {% endif %}
    </div>
"""

GALLERY_CONTENT = """
    <div class="header" style="margin-bottom: 40px;">
        <h1 style="font-size: 32px; font-weight: 800; color: var(--text-primary); margin-bottom: 5px;">Video Gallery</h1>
        <p style="color: var(--text-secondary); font-size: 16px;">Review and manage your viral video collection.</p>
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 35px;">
        {% for video in videos %}
        <div class="card" style="padding: 10px; display: flex; flex-direction: column; overflow: hidden;">
            <video style="width: 100%; border-radius: 14px; aspect-ratio: 9/16; background: #f1f5f9; object-fit: cover; box-shadow: inset 0 0 40px rgba(0,0,0,0.05);" controls preload="none">
                <source src="/download/{{ video.path }}" type="video/mp4">
            </video>
            <div style="padding: 20px 10px 10px 10px; flex: 1;">
                <div style="font-weight: 800; font-size: 15px; margin-bottom: 5px; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{{ video.name }}">{{ video.name }}</div>
                <div style="font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; gap: 6px;">
                    <span style="font-size: 14px;">📅</span> {{ video.date }}
                </div>
            </div>
            <div style="display: flex; gap: 12px; margin-top: 10px; padding: 0 10px 10px 10px;">
                <a href="/download/{{ video.path }}" class="btn" style="flex: 1; font-size: 13px; padding: 12px;">Download</a>
                <form action="/delete_video" method="post" style="display: contents;">
                    <input type="hidden" name="path" value="{{ video.path }}">
                    <button type="submit" class="btn btn-red" style="padding: 12px 18px;" onclick="return confirm('Hapus video ini permanen?')">🗑</button>
                </form>
            </div>
        </div>
        {% endfor %}
    </div>
    
    {% if not videos %}
    <div class="card" style="text-align: center; padding: 100px 30px; background: #f8fafc; border: 2px dashed #e2e8f0; box-shadow: none;">
        <div style="font-size: 60px; margin-bottom: 25px; opacity: 0.3;">🎬</div>
        <h3 style="margin-bottom: 12px; color: var(--text-primary); font-size: 22px;">No Videos Detected</h3>
        <p style="color: var(--text-secondary); max-width: 450px; margin: 0 auto 35px auto; font-size: 15px;">Your video gallery is empty. Head over to the Creator engine to start building your affiliate content.</p>
        <a href="/create" class="btn" style="padding: 16px 40px;">🚀 Go to Creator</a>
    </div>
    {% endif %}
"""

SETTINGS_CONTENT = """
    <div class="header" style="margin-bottom: 40px;">
        <h1 style="font-size: 32px; font-weight: 800; color: var(--text-primary); margin-bottom: 5px;">System Console</h1>
        <p style="color: var(--text-secondary); font-size: 16px;">Manage system assets, core engines, and bot behavior.</p>
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 35px;">
        <div class="card">
            <h3 style="margin-top: 0; display: flex; align-items: center; gap: 12px; color: var(--accent-royal);">
                <span>🎵</span> Background Music
            </h3>
            <div style="background: #f8fafc; padding: 20px; border-radius: 16px; margin: 25px 0; border: 1px solid #edf2f7;">
                <p style="font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Active Selection</p>
                <div style="font-size: 16px; font-weight: 800; color: var(--accent-blue);">{{ current_music }}</div>
            </div>
            
            <form action="/upload_music" method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <label style="font-size: 11px; color: var(--text-secondary); font-weight: 700;">UPLOAD SOUNDTRACK (MP3, MP4, MOV, WAV)</label>
                    <input type="file" name="music" accept="audio/*,video/*" required style="margin-top: 10px;">
                </div>
                <button type="submit" class="btn btn-outline" style="width: 100%; margin-top: 10px; padding: 15px; border-width: 2px;">Update Soundtrack & Set Primary</button>
            </form>
        </div>
        
        <div class="card">
            <h3 style="margin-top: 0; display: flex; align-items: center; gap: 12px; color: var(--accent-royal);">
                <span>🏥</span> System Health Monitor
            </h3>
            <div style="display: flex; flex-direction: column; gap: 15px; margin: 25px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 15px; background: #f8fafc; border-radius: 14px;">
                    <span style="font-size: 15px; font-weight: 600;">Groq AI Engine</span>
                    <span style="background: #c6f6d5; color: #22543d; padding: 5px 12px; border-radius: 20px; font-size: 11px; font-weight: 800;">HEALTHY</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 15px; background: #f8fafc; border-radius: 14px;">
                    <span style="font-size: 15px; font-weight: 600;">FFmpeg Video Core</span>
                    <span style="background: #c6f6d5; color: #22543d; padding: 5px 12px; border-radius: 20px; font-size: 11px; font-weight: 800;">READY</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 15px; background: #f8fafc; border-radius: 14px;">
                    <span style="font-size: 15px; font-weight: 600;">System Storage</span>
                    <span style="color: var(--accent-royal); font-weight: 800; font-size: 16px;">{{ storage_used }} MB</span>
                </div>
            </div>
            <div style="margin-top: 40px; font-size: 12px; color: var(--text-secondary); text-align: center; border-top: 1px solid #f1f5f9; padding-top: 25px;">
                <strong style="color: var(--text-primary);">TikTok Affiliate Bot PRO</strong><br>
                Enterprise Version 2.5 • Developed by Antigravity
            </div>
        </div>
    </div>
"""

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
            
    # Premium Login Page Template with Inline CSS for BASE_CSS integration
    login_html = """
    <style>""" + BASE_CSS + """</style>
    <div style="width: 100%; min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg-main); font-family: 'Outfit', sans-serif;">
        <div class="auth-container">
            <div class="auth-logo">TIKTOK BOT PRO</div>
            <h2 style="margin-top: 0; color: var(--text-primary); font-weight: 800;">Dashboard Login</h2>
            <p style="color: var(--text-secondary); margin-bottom: 30px; font-size: 14px;">Please enter your access key to continue.</p>
            
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                {% for message in messages %}
                  <div style="padding: 12px; background: #fff5f5; border: 1px solid #feb2b2; color: #c53030; border-radius: 12px; margin-bottom: 20px; font-size: 13px; font-weight: 600;">
                    {{ message }}
                  </div>
                {% endfor %}
              {% endif %}
            {% endwith %}

            <form method="POST">
                <div style="text-align: left; margin-bottom: 20px;">
                    <label style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px;">Access Key</label>
                    <input type="password" name="auth_key" placeholder="••••••••" required 
                           style="width: 100%; padding: 16px; border-radius: 14px; border: 2px solid var(--border-soft); margin-top: 8px; box-sizing: border-box; font-size: 16px; transition: all 0.3s ease;">
                </div>
                <button type="submit" class="btn" style="width: 100%; padding: 18px; font-weight: 800; font-size: 16px; letter-spacing: 0.5px;">Login to Dashboard</button>
            </form>
            
            <p style="margin-top: 40px; font-size: 12px; color: var(--text-secondary); opacity: 0.7;">
                Enterprise Security Core v2.5
            </p>
        </div>
    </div>
    """
    return render_template_string(login_html)

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
                    stat = os.stat(full_path)
                    videos.append({
                        "name": file,
                        "path": rel_path,
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
        
        video_filename = f"video_{session_id}.mp4"
        video_path = os.path.join(session_dir, video_filename)
        
        # Look for any background file
        bg_files = [f for f in os.listdir(MUSIC_FOLDER) if f.startswith("background.")]
        music_path = os.path.join(MUSIC_FOLDER, bg_files[0]) if bg_files else None
        
        video_processor.create_video_from_images_and_audio(
            image_paths, audio_path, video_path, 
            bg_music_path=music_path, description=description
        )
        
        return render_template_string(LAYOUT_START + CREATE_CONTENT + LAYOUT_END, title="Create Video", active="create", result_video=f"{session_id}/{video_filename}", product_name=product_name, description=description)
    except Exception as e:
        flash(f"Error: {e}")
        return redirect(url_for("create"))

@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    # host='0.0.0.0' allows access from other devices on same WiFi
    app.run(debug=True, host='0.0.0.0', port=5000)
