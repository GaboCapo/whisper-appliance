#!/usr/bin/env python3
"""
Enhanced WhisperS2T Appliance - Development Server
v0.5.0 - Lite Development Mode with proper UI structure
"""

import os
import sys
import logging
import socket
from pathlib import Path
from datetime import datetime

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Configure logging for development
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(backend_dir / 'dev-server.log')
    ]
)

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
    import uvicorn
    import psutil
    
    # Create FastAPI app
    app = FastAPI(
        title="Enhanced WhisperS2T Appliance",
        description="Development server for Enhanced WhisperS2T Appliance v0.5.0",
        version="0.5.0-dev"
    )
    
    # Navigation template
    def get_nav_html(current_page=""):
        nav_items = [
            ("Home", "/", "🏠"),
            ("Demo", "/demo", "🎤"),
            ("Admin", "/admin", "🔧"),
            ("API Docs", "/docs", "📚")
        ]
        
        nav_html = "<nav style='background: #343a40; padding: 15px; margin-bottom: 20px; border-radius: 5px;'>"
        nav_html += "<div style='display: flex; gap: 15px; align-items: center;'>"
        nav_html += "<h2 style='color: white; margin: 0; margin-right: 20px;'>🎤 WhisperS2T v0.5.0</h2>"
        
        for name, url, icon in nav_items:
            active = "background: #007bff;" if current_page == name.lower() else "background: #495057;"
            nav_html += f"""
                <a href="{url}" style="color: white; text-decoration: none; padding: 8px 16px; 
                   border-radius: 3px; {active} transition: all 0.3s;">
                    {icon} {name}
                </a>
            """
        
        nav_html += "</div></nav>"
        return nav_html
    
    def get_base_html(title, content, current_page=""):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0; padding: 20px; background: #f8f9fa; line-height: 1.6;
                }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .card {{ 
                    background: white; padding: 25px; border-radius: 8px; 
                    margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                .status-ok {{ color: #28a745; font-weight: bold; }}
                .status-warning {{ color: #ffc107; font-weight: bold; }}
                .status-error {{ color: #dc3545; font-weight: bold; }}
                .button {{ 
                    background: #007bff; color: white; padding: 10px 20px; 
                    text-decoration: none; border-radius: 5px; display: inline-block; 
                    margin: 5px; transition: all 0.3s; border: none; cursor: pointer;
                }}
                .button:hover {{ background: #0056b3; }}
                .button-success {{ background: #28a745; }}
                .button-warning {{ background: #ffc107; color: #212529; }}
                .button-danger {{ background: #dc3545; }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
                .demo-area {{
                    border: 2px dashed #dee2e6; padding: 30px; text-align: center;
                    border-radius: 8px; background: #f8f9fa;
                }}
                .info-box {{
                    background: #d1ecf1; padding: 15px; border-radius: 5px; 
                    border-left: 4px solid #17a2b8; margin: 15px 0;
                }}
                .warning-box {{
                    background: #fff3cd; padding: 15px; border-radius: 5px; 
                    border-left: 4px solid #ffc107; margin: 15px 0;
                }}
                code {{ 
                    background: #f8f9fa; padding: 2px 6px; border-radius: 3px; 
                    font-family: 'Courier New', monospace; 
                }}
                pre {{ 
                    background: #f8f9fa; padding: 15px; border-radius: 5px; 
                    overflow-x: auto; border-left: 4px solid #007bff;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                {get_nav_html(current_page)}
                {content}
            </div>
        </body>
        </html>
        """
    
    # Root/Home page - Overview and status
    @app.get("/", response_class=HTMLResponse)
    async def home():
        content = """
        <div class="card">
            <h1>🎤 Enhanced WhisperS2T Appliance v0.5.0</h1>
            <h2>Development Server - Overview</h2>
            
            <div class="grid">
                <div class="card">
                    <h3>🚀 Server Status</h3>
                    <p><span class="status-ok">✅ Development Server</span> - Running successfully</p>
                    <p><span class="status-warning">⚠️ ML Processing</span> - Limited (development mode)</p>
                    <p><span class="status-warning">⚠️ GPU Acceleration</span> - Not available</p>
                </div>
                
                <div class="card">
                    <h3>🎯 Quick Navigation</h3>
                    <a href="/demo" class="button">🎤 Try Speech Recognition</a>
                    <a href="/admin" class="button button-warning">🔧 System Administration</a>
                    <a href="/docs" class="button button-success">📚 API Documentation</a>
                </div>
            </div>
            
            <div class="warning-box">
                <strong>⚠️ Development Mode Active</strong><br>
                This is a lightweight development server without full ML capabilities. 
                Some features are limited to avoid Python 3.13 compatibility issues.
            </div>
            
            <div class="info-box">
                <strong>🚀 Full Features Available</strong><br>
                For complete ML functionality including GPU acceleration and all Whisper models:<br>
                <code>./dev.sh container start</code>
            </div>
        </div>
        
        <div class="card">
            <h3>📋 Available Features</h3>
            <div class="grid">
                <div>
                    <h4>🎤 Demo Interface</h4>
                    <ul>
                        <li>Audio file upload simulation</li>
                        <li>Real-time transcription demo</li>
                        <li>Language selection</li>
                        <li>Basic speech recognition testing</li>
                    </ul>
                </div>
                <div>
                    <h4>🔧 Admin Panel</h4>
                    <ul>
                        <li>System resource monitoring</li>
                        <li>Service status overview</li>
                        <li>Configuration management</li>
                        <li>Development tools</li>
                    </ul>
                </div>
            </div>
        </div>
        """
        
        return get_base_html("Enhanced WhisperS2T Appliance - Home", content, "home")
    
    # Demo page - Speech recognition interface
    @app.get("/demo", response_class=HTMLResponse)
    async def demo_page():
        content = """
        <div class="card">
            <h1>🎤 Speech Recognition Demo</h1>
            <p>Interactive demonstration of the Enhanced WhisperS2T Appliance capabilities</p>
            
            <div class="demo-area">
                <h3>🎙️ Audio Upload Demo</h3>
                <p>In full mode, you would drag & drop audio files here for transcription</p>
                <div style="margin: 20px 0;">
                    <input type="file" accept="audio/*" disabled style="margin: 10px;">
                    <button class="button" disabled>Upload Audio File</button>
                </div>
                <small>Feature disabled in development mode</small>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h3>🌍 Language Selection</h3>
                    <select class="button" style="width: 100%; padding: 10px;">
                        <option>Auto-detect</option>
                        <option>English</option>
                        <option>German</option>
                        <option>French</option>
                        <option>Spanish</option>
                        <option>Italian</option>
                        <option>Portuguese</option>
                    </select>
                </div>
                
                <div class="card">
                    <h3>🧠 Model Selection</h3>
                    <select class="button" style="width: 100%; padding: 10px;">
                        <option selected>Development Mode</option>
                        <option disabled>tiny (fast, lower quality)</option>
                        <option disabled>base (balanced)</option>
                        <option disabled>small (better quality)</option>
                        <option disabled>medium (high quality)</option>
                        <option disabled>large (best quality)</option>
                    </select>
                    <small>Full models available in container mode</small>
                </div>
            </div>
            
            <div class="card">
                <h3>📝 Transcription Result</h3>
                <textarea style="width: 100%; height: 150px; padding: 10px; border: 1px solid #ddd; border-radius: 5px;" 
                         placeholder="Transcribed text will appear here..." readonly></textarea>
                <div style="margin-top: 10px;">
                    <button class="button" disabled>🎤 Start Recording</button>
                    <button class="button button-success" disabled>▶️ Process Audio</button>
                    <button class="button button-warning" disabled>📋 Copy Text</button>
                </div>
            </div>
            
            <div class="warning-box">
                <strong>🔧 Development Mode Limitations</strong><br>
                • Audio processing disabled<br>
                • ML models not loaded<br>
                • Real-time transcription unavailable<br>
                • Use container mode for full functionality: <code>./dev.sh container start</code>
            </div>
            
            <div class="info-box">
                <strong>🔄 Test API Endpoints</strong><br>
                <a href="/health" class="button">Health Check</a>
                <a href="/admin/system/info" class="button">System Info</a>
            </div>
        </div>
        """
        
        return get_base_html("Speech Recognition Demo", content, "demo")
    
    # Admin page - System administration
    @app.get("/admin", response_class=HTMLResponse)
    async def admin_page():
        # Get system info
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            disk = psutil.disk_usage('/')
        except:
            memory = cpu_percent = disk = None
            
        content = f"""
        <div class="card">
            <h1>🔧 System Administration</h1>
            <p>Development server management and monitoring</p>
            
            <div class="grid">
                <div class="card">
                    <h3>🖥️ System Resources</h3>
                    {"<p><strong>CPU Usage:</strong> " + f"{cpu_percent:.1f}%" + "</p>" if cpu_percent else "<p>CPU: N/A</p>"}
                    {"<p><strong>Memory:</strong> " + f"{memory.percent:.1f}% ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)" + "</p>" if memory else "<p>Memory: N/A</p>"}
                    {"<p><strong>Disk:</strong> " + f"{disk.percent:.1f}% used" + "</p>" if disk else "<p>Disk: N/A</p>"}
                </div>
                
                <div class="card">
                    <h3>⚙️ Service Status</h3>
                    <p><span class="status-ok">✅ Web Server</span> - Running on port 5000</p>
                    <p><span class="status-warning">⚠️ Whisper Service</span> - Not loaded (dev mode)</p>
                    <p><span class="status-warning">⚠️ GPU Service</span> - Not available</p>
                    <p><span class="status-ok">✅ API Endpoints</span> - Active</p>
                </div>
            </div>
            
            <div class="card">
                <h3>🛠️ Management Actions</h3>
                <div class="grid">
                    <div>
                        <h4>Server Control</h4>
                        <button class="button button-warning" onclick="alert('Use: ./dev.sh dev stop')">🛑 Stop Server</button>
                        <button class="button" onclick="window.location.reload()">🔄 Refresh Status</button>
                        <a href="/health" class="button button-success">🏥 Health Check</a>
                    </div>
                    <div>
                        <h4>Development Tools</h4>
                        <button class="button" onclick="alert('Feature available in container mode')">📊 View Logs</button>
                        <button class="button" onclick="alert('Feature available in container mode')">⚙️ Configuration</button>
                        <a href="/docs" class="button">📚 API Documentation</a>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>🔄 Deployment Options</h3>
                <div class="info-box">
                    <strong>Current:</strong> Development Server (Lite Mode)<br>
                    <strong>Alternative:</strong> Full Container Deployment
                </div>
                <pre>
# Stop development server
./dev.sh dev stop

# Start full container with ML capabilities  
./dev.sh container start

# Container includes:
• GPU acceleration (if available)
• All Whisper models (tiny to large)
• Real-time audio processing
• Production-grade performance</pre>
            </div>
            
            <div class="card">
                <h3>📊 System Information</h3>
                <a href="/admin/system/info" class="button">📋 Detailed System Info (JSON)</a>
                <a href="/health" class="button button-success">💚 Health Endpoint</a>
                <a href="/docs" class="button button-warning">📖 OpenAPI Schema</a>
            </div>
        </div>
        """
        
        return get_base_html("System Administration", content, "admin")
    
    # API Endpoints
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "version": "0.5.0-dev",
            "mode": "development",
            "timestamp": datetime.now().isoformat(),
            "features": {
                "web_interface": True,
                "api_endpoints": True,
                "ml_processing": False,
                "gpu_acceleration": False,
                "real_time_audio": False
            }
        }
    
    @app.get("/admin/system/info")
    async def system_info():
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')
            
            return {
                "system": {
                    "cpu_usage": cpu_percent,
                    "cpu_count": psutil.cpu_count(),
                    "memory_total": memory.total,
                    "memory_available": memory.available,
                    "memory_percent": memory.percent,
                    "disk_total": disk.total,
                    "disk_used": disk.used,
                    "disk_percent": disk.percent
                },
                "application": {
                    "version": "0.5.0-dev",
                    "mode": "development",
                    "python_version": sys.version,
                    "features": {
                        "ml_processing": False,
                        "gpu_acceleration": False,
                        "whisper_models": [],
                        "real_time_audio": False,
                        "note": "Full ML features available in container mode"
                    }
                },
                "development": {
                    "server_type": "uvicorn",
                    "environment": "development",
                    "hot_reload": False,
                    "debug_mode": True
                }
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            raise HTTPException(status_code=500, detail="Could not retrieve system information")
    
    def find_available_port(start_port=5000, max_attempts=10):
        """Find an available port starting from start_port"""
        for port in range(start_port, start_port + max_attempts):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('localhost', port))
                sock.close()
                return port
            except OSError:
                continue
        return None

    if __name__ == "__main__":
        # Find available port
        port = find_available_port(5000)
        if port is None:
            logger.error("❌ No available ports found (tried 5000-5009)")
            sys.exit(1)
        
        if port != 5000:
            logger.warning(f"⚠️ Port 5000 in use, using port {port} instead")
        
        logger.info("🚀 Starting Enhanced WhisperS2T Appliance Development Server")
        logger.info("📍 Running in development mode")
        logger.info(f"🌐 Starting web server on http://localhost:{port}")
        logger.info(f"🏠 Home page: http://localhost:{port}/")
        logger.info(f"🎤 Demo interface: http://localhost:{port}/demo")
        logger.info(f"🔧 Admin panel: http://localhost:{port}/admin")
        logger.info(f"📚 API docs: http://localhost:{port}/docs")
        logger.info("🛑 Press Ctrl+C to stop")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True
        )

except ImportError as e:
    logger.error(f"❌ Missing dependencies: {e}")
    logger.error("💡 Try: ./dev.sh dev setup")
    sys.exit(1)
except Exception as e:
    logger.error(f"❌ Server error: {e}")
    sys.exit(1)
