#!/usr/bin/env bash

# WhisperS2T Proxmox Standalone Installer
# Self-contained installation without GitHub dependency
# Usage: Copy this script to Proxmox and run as root

set -e

# Colors
BL='\033[36m'
RD='\033[0;31m'
GN='\033[1;92m'
YW='\033[33m'
CL='\033[m'

function msg_info() { echo -e "${BL}[INFO]${CL} $1"; }
function msg_ok() { echo -e "${GN}[OK]${CL} $1"; }
function msg_error() { echo -e "${RD}[ERROR]${CL} $1"; }
function msg_warn() { echo -e "${YW}[WARN]${CL} $1"; }

clear
cat <<"EOF"

 __    __ _     _                      _               _ _                      
/ / /\ \ \ |__ (_)___ _ __   ___ _ __ /_\  _ __  _ __ | (_) __ _ _ __   ___ ___ 
\ \/  \/ / '_ \| / __| '_ \ / _ \ '__//_\\| '_ \| '_ \| | |/ _` | '_ \ / __/ _ \
 \  /\  /| | | | \__ \ |_) |  __/ | /  _  \ |_) | |_) | | | (_| | | | | (_|  __/
  \/  \/ |_| |_|_|___/ .__/ \___|_| \_/ \_/ .__/| .__/|_|_|\__,_|_| |_|\___\___|
                     |_|                  |_|   |_|                             


WhisperS2T Proxmox LXC Container Creator (Standalone)
===================================================
EOF

# Check if running on Proxmox
if ! command -v pct >/dev/null 2>&1; then
    msg_error "This script must be run on Proxmox VE"
    exit 1
fi

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    msg_error "This script must be run as root"
    exit 1
fi

# Get next available container ID
CTID=$(pvesh get /cluster/nextid)
msg_info "Using Container ID: $CTID"

# Configuration
HOSTNAME="whisper-appliance"
CORES="2"
MEMORY="4096"
DISK_SIZE="20"
TEMPLATE="ubuntu-22.04-standard_22.04-1_amd64.tar.zst"

msg_info "Creating WhisperS2T LXC Container"
msg_info "  ID: $CTID"
msg_info "  Hostname: $HOSTNAME"
msg_info "  CPU: $CORES cores"
msg_info "  RAM: $MEMORY MB"
msg_info "  Disk: $DISK_SIZE GB"

# Download template if needed
TEMPLATE_PATH="/var/lib/vz/template/cache/$TEMPLATE"
if [[ ! -f "$TEMPLATE_PATH" ]]; then
    msg_info "Downloading Ubuntu 22.04 template (this may take a while)..."
    pveam download local $TEMPLATE
    msg_ok "Template downloaded"
fi

# Create container
msg_info "Creating LXC container..."
pct create $CTID $TEMPLATE_PATH \
    --hostname $HOSTNAME \
    --cores $CORES \
    --memory $MEMORY \
    --rootfs local-lvm:$DISK_SIZE \
    --net0 name=eth0,bridge=vmbr0,ip=dhcp \
    --features nesting=1,keyctl=1 \
    --unprivileged 1 \
    --onboot 1 \
    --tags "ai,speech,transcription,whisper"

msg_ok "Container created"

# Start container
msg_info "Starting container..."
pct start $CTID
sleep 10
msg_ok "Container started"

# Install WhisperS2T
msg_info "Installing WhisperS2T (this will take 10-15 minutes)..."

# Create installation script inside container
cat > /tmp/install-whisper.sh << 'INSTALL_EOF'
#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

export DEBIAN_FRONTEND=noninteractive

print_status "Updating system packages..."
apt-get update >/dev/null 2>&1
apt-get upgrade -y >/dev/null 2>&1

print_status "Installing system dependencies..."
apt-get install -y \
    build-essential \
    cmake \
    git \
    curl \
    wget \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release >/dev/null 2>&1

print_status "Installing Python development environment..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-setuptools \
    python3-wheel >/dev/null 2>&1

print_status "Installing multimedia libraries..."
apt-get install -y \
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libasound2-dev \
    libpulse-dev \
    libsndfile1-dev \
    libffi-dev \
    libssl-dev >/dev/null 2>&1

print_status "Installing web server and SSL support..."
apt-get install -y nginx openssl >/dev/null 2>&1

print_status "Creating application user..."
if ! id "whisper" &>/dev/null; then
    useradd -m -s /bin/bash whisper
    usermod -aG audio whisper
fi

print_status "Cloning WhisperS2T repository..."
cd /opt
# Clone the repository
if ! git clone https://github.com/GaboCapo/whisper-appliance.git; then
    print_error "Failed to clone repository"
    exit 1
fi
chown -R whisper:whisper /opt/whisper-appliance

print_status "Installing Python dependencies..."
sudo -u whisper python3 -m pip install --user --upgrade pip >/dev/null 2>&1

# Install production requirements from downloaded file
if [ -f "/opt/whisper-appliance/requirements.txt" ]; then
    print_status "Installing from requirements.txt..."
    sudo -u whisper python3 -m pip install --user -r /opt/whisper-appliance/requirements.txt >/dev/null 2>&1
else
    print_warning "Requirements file not found, installing manually..."
    # Fallback manual installation
    sudo -u whisper python3 -m pip install --user \
        torch torchaudio --index-url https://download.pytorch.org/whl/cpu >/dev/null 2>&1
    sudo -u whisper python3 -m pip install --user \
        openai-whisper \
        flask \
        flask-cors \
        flask-socketio \
        flask-swagger-ui \
        python-socketio \
        python-engineio \
        gunicorn \
        librosa \
        soundfile \
        pydub \
        requests \
        werkzeug \
        psutil \
        numpy >/dev/null 2>&1
fi

# Function to create fallback app if GitHub download fails
create_fallback_app() {
    print_warning "Creating basic fallback application..."
    cat > /opt/whisper-appliance/src/main.py << 'FALLBACK_APP_EOF'
#!/usr/bin/env python3
"""
WhisperS2T Fallback Application
Basic transcription service when GitHub download fails
"""

import os
import tempfile
import threading
import logging
from flask import Flask, render_template_string, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import whisper

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Whisper model
model = None

def load_model():
    global model
    try:
        model = whisper.load_model("base")
        logger.info("Whisper model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")

# Load model in background
threading.Thread(target=load_model, daemon=True).start()

UPLOAD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>WhisperS2T - Speech to Text</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; margin-bottom: 30px; }
        .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; border-radius: 10px; margin: 20px 0; }
        .upload-area:hover { border-color: #007bff; }
        .btn { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        .btn:hover { background: #0056b3; }
        .result { margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 5px; }
        .status { margin: 10px 0; font-weight: bold; }
        .error { color: #dc3545; }
        .success { color: #28a745; }
        .warning { color: #ffc107; background: #fff3cd; padding: 10px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ WhisperS2T - Speech to Text</h1>
        
        <div class="warning">
            <strong>⚠️ Fallback Mode:</strong> This is a basic version. GitHub download failed during installation.
        </div>
        
        <form id="uploadForm" enctype="multipart/form-data">
            <div class="upload-area">
                <p>📁 Drag & drop audio files here or click to select</p>
                <input type="file" id="audioFile" name="audio" accept="audio/*" style="display: none;">
                <button type="button" class="btn" onclick="document.getElementById('audioFile').click()">Select Audio File</button>
            </div>
            <button type="submit" class="btn">🚀 Transcribe</button>
        </form>
        
        <div id="status" class="status"></div>
        <div id="result" class="result" style="display: none;"></div>
    </div>

    <script>
        const form = document.getElementById('uploadForm');
        const fileInput = document.getElementById('audioFile');
        const status = document.getElementById('status');
        const result = document.getElementById('result');

        fileInput.addEventListener('change', function(e) {
            const fileName = e.target.files[0]?.name;
            if (fileName) {
                document.querySelector('.upload-area p').textContent = `Selected: ${fileName}`;
            }
        });

        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!fileInput.files[0]) {
                status.innerHTML = '<span class="error">Please select an audio file</span>';
                return;
            }

            const formData = new FormData();
            formData.append('audio', fileInput.files[0]);

            status.innerHTML = '<span class="success">Transcribing... This may take a moment.</span>';
            result.style.display = 'none';

            try {
                const response = await fetch('/transcribe', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                
                if (data.success) {
                    status.innerHTML = '<span class="success">✅ Transcription completed!</span>';
                    result.innerHTML = `<h3>Transcription Result:</h3><p>${data.transcription}</p>`;
                    result.style.display = 'block';
                } else {
                    status.innerHTML = `<span class="error">❌ Error: ${data.error}</span>`;
                }
            } catch (error) {
                status.innerHTML = `<span class="error">❌ Error: ${error.message}</span>`;
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(UPLOAD_TEMPLATE)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'success': False, 'error': 'No audio file provided'})
    
    if model is None:
        return jsonify({'success': False, 'error': 'Whisper model not loaded yet. Please wait and try again.'})
    
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            file.save(tmp_file.name)
            
            # Transcribe
            result = model.transcribe(tmp_file.name)
            transcription = result['text'].strip()
            
            # Clean up
            os.unlink(tmp_file.name)
            
            return jsonify({
                'success': True,
                'transcription': transcription
            })
            
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'version': 'fallback-1.0'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
FALLBACK_APP_EOF
}

# Function to create fallback audio manager
create_fallback_audio_manager() {
    print_warning "Creating basic fallback audio input manager..."
    cat > /opt/whisper-appliance/src/whisper-service/audio_input_manager.py << 'FALLBACK_AUDIO_EOF'
#!/usr/bin/env python3
"""
Basic Audio Input Manager Fallback
Placeholder when GitHub download fails
"""

import logging

logger = logging.getLogger(__name__)

class AudioInputManager:
    """Basic fallback audio input manager"""
    
    def __init__(self):
        logger.warning("Using fallback AudioInputManager - Live speech feature not available")
        self.recording = False
    
    def start_recording(self):
        logger.warning("Live recording not available in fallback mode")
        return False
    
    def stop_recording(self):
        logger.warning("Live recording not available in fallback mode")
        return None
    
    def is_recording(self):
        return False
FALLBACK_AUDIO_EOF
}

print_status "Creating WhisperS2T application..."

# Function to download file with fallback mechanisms
download_file() {
    local url="$1"
    local output_file="$2"
    local description="$3"
    
    print_status "Downloading $description..."
    
    # Method 1: Try wget first (more reliable for file downloads)
    if wget -q --timeout=30 --tries=3 "$url" -O "$output_file.tmp"; then
        print_success "Downloaded $description using wget"
    # Method 2: Try curl as fallback
    elif curl -s --max-time 30 --retry 3 "$url" -o "$output_file.tmp"; then
        print_success "Downloaded $description using curl"
    else
        print_error "Failed to download $description from GitHub"
        return 1
    fi
    
    # Verify file is not empty and contains expected content
    if [[ ! -s "$output_file.tmp" ]]; then
        print_error "Downloaded file is empty: $description"
        rm -f "$output_file.tmp"
        return 1
    fi
    
    # For Python files, verify they contain basic Python syntax
    if [[ "$output_file" == *.py ]]; then
        if ! grep -q "import\|def\|class" "$output_file.tmp"; then
            print_error "Downloaded Python file appears corrupted: $description"
            rm -f "$output_file.tmp"
            return 1
        fi
    fi
    
    # Move to final location
    mv "$output_file.tmp" "$output_file"
    print_success "Successfully downloaded and verified: $description"
    return 0
}

# Create whisper-service directory
mkdir -p /opt/whisper-appliance/src/whisper-service

# Download the modular main app from GitHub
if ! download_file "https://raw.githubusercontent.com/GaboCapo/whisper-appliance/main/src/main.py" \
                  "/opt/whisper-appliance/src/main.py" \
                  "Enhanced WhisperS2T Main App"; then
    print_warning "GitHub download failed, creating basic fallback app..."
    create_fallback_app
fi

# Create modules directory and download modular components
mkdir -p /opt/whisper-appliance/src/modules
mkdir -p /opt/whisper-appliance/src/templates

print_status "Downloading modular components..."

# Download modules
download_file "https://raw.githubusercontent.com/GaboCapo/whisper-appliance/main/src/modules/__init__.py" \
              "/opt/whisper-appliance/src/modules/__init__.py" \
              "Modules Init"

download_file "https://raw.githubusercontent.com/GaboCapo/whisper-appliance/main/src/modules/live_speech.py" \
              "/opt/whisper-appliance/src/modules/live_speech.py" \
              "Live Speech Module"

download_file "https://raw.githubusercontent.com/GaboCapo/whisper-appliance/main/src/modules/upload_handler.py" \
              "/opt/whisper-appliance/src/modules/upload_handler.py" \
              "Upload Handler Module"

download_file "https://raw.githubusercontent.com/GaboCapo/whisper-appliance/main/src/modules/admin_panel.py" \
              "/opt/whisper-appliance/src/modules/admin_panel.py" \
              "Admin Panel Module"

download_file "https://raw.githubusercontent.com/GaboCapo/whisper-appliance/main/src/modules/api_docs.py" \
              "/opt/whisper-appliance/src/modules/api_docs.py" \
              "API Documentation Module"

download_file "https://raw.githubusercontent.com/GaboCapo/whisper-appliance/main/src/modules/chat_history.py" \
              "/opt/whisper-appliance/src/modules/chat_history.py" \
              "Chat History Module"

download_file "https://raw.githubusercontent.com/GaboCapo/whisper-appliance/main/src/modules/model_manager.py" \
              "/opt/whisper-appliance/src/modules/model_manager.py" \
              "Model Manager Module"

# Download templates
download_file "https://raw.githubusercontent.com/GaboCapo/whisper-appliance/main/src/templates/main_interface.html" \
              "/opt/whisper-appliance/src/templates/main_interface.html" \
              "Main Interface Template"

# Download requirements from project root (not src/)
download_file "https://raw.githubusercontent.com/GaboCapo/whisper-appliance/main/requirements.txt" \
              "/opt/whisper-appliance/requirements.txt" \
              "Production Requirements File"

# Download audio input manager
if ! download_file "https://raw.githubusercontent.com/GaboCapo/whisper-appliance/main/src/whisper-service/audio_input_manager.py" \
                  "/opt/whisper-appliance/src/whisper-service/audio_input_manager.py" \
                  "Audio Input Manager"; then
    print_warning "GitHub download failed, creating basic fallback audio manager..."
    create_fallback_audio_manager
fi

chown -R whisper:whisper /opt/whisper-appliance/src

print_status "Setting up intelligent SSL certificates for network HTTPS access..."

# Auto-detect IP addresses for SAN
LOCAL_IPS=$(hostname -I | tr ' ' '\n' | grep -v '^127\.' | grep -v '^::1' | head -5)
PRIMARY_IP=$(echo "$LOCAL_IPS" | head -1)

# Build SAN list
SAN_LIST="DNS:localhost,DNS:$(hostname)"
for ip in $LOCAL_IPS; do
    if [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        SAN_LIST="${SAN_LIST},IP:${ip}"
        print_status "📍 Adding IP to SSL certificate: $ip"
    fi
done

# Create SSL directory and certificates
mkdir -p /opt/whisper-appliance/ssl
cd /opt/whisper-appliance/ssl || exit 1

# Use primary IP as CN if available
CN_VALUE="${PRIMARY_IP:-localhost}"
print_status "🎯 Certificate CN: $CN_VALUE"
print_status "🌐 SAN Configuration: $SAN_LIST"

# Generate private key
openssl genrsa -out whisper-appliance.key 2048

# Generate certificate with SAN (try modern method first)
if openssl req -help 2>&1 | grep -q "addext"; then
    print_status "✅ Using modern OpenSSL with SAN support"
    openssl req -x509 -new -key whisper-appliance.key -sha256 -days 365 -out whisper-appliance.crt \
        -subj "/C=DE/ST=NRW/L=Container/O=WhisperS2T/OU=Production/CN=${CN_VALUE}/emailAddress=admin@whisper-appliance.local" \
        -addext "subjectAltName=${SAN_LIST}"
else
    # Fallback for older OpenSSL
    print_status "🔄 Using legacy OpenSSL config method"
    cat > ssl.conf << EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
C = DE
ST = NRW
L = Container
O = WhisperS2T
OU = Production
CN = ${CN_VALUE}
emailAddress = admin@whisper-appliance.local

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = ${SAN_LIST}
EOF
    openssl req -x509 -new -key whisper-appliance.key -sha256 -days 365 -out whisper-appliance.crt -config ssl.conf
    rm ssl.conf
fi

# Set permissions and ownership
chmod 600 whisper-appliance.key
chmod 644 whisper-appliance.crt
chown -R whisper:whisper /opt/whisper-appliance/ssl

print_success "✅ SSL certificates with SAN generated for network access"
print_status "🎙️ Microphone access enabled for ALL detected network IPs"

cd /opt/whisper-appliance || exit 1

print_status "Creating systemd service..."
cat > /etc/systemd/system/whisper-appliance.service << "SERVICE_EOF"
[Unit]
Description=WhisperS2T Appliance
After=network.target

[Service]
Type=simple
User=whisper
Group=whisper
WorkingDirectory=/opt/whisper-appliance/src
Environment=PATH=/home/whisper/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/opt/whisper-appliance
ExecStart=/usr/bin/python3 /opt/whisper-appliance/src/main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE_EOF

print_status "Configuring Nginx for HTTPS pass-through..."
cat > /etc/nginx/sites-available/whisper-appliance << "NGINX_EOF"
server {
    listen 5000;
    server_name _;

    client_max_body_size 100M;
    
    # HTTP to HTTPS redirect for production access
    return 301 https://$host:5001$request_uri;
}

server {
    listen 5001 ssl http2;
    server_name _;

    # SSL Configuration
    ssl_certificate /opt/whisper-appliance/ssl/whisper-appliance.crt;
    ssl_certificate_key /opt/whisper-appliance/ssl/whisper-appliance.key;
    
    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass https://127.0.0.1:5001;
        proxy_ssl_verify off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}
NGINX_EOF

print_status "Configuring firewall for HTTPS access..."
# Remove Nginx proxy since Flask app handles HTTPS directly
rm -f /etc/nginx/sites-enabled/whisper-appliance /etc/nginx/sites-available/whisper-appliance
systemctl disable nginx
systemctl stop nginx

if command -v ufw >/dev/null 2>&1; then
    ufw --force enable
    ufw allow 5001/tcp comment "WhisperS2T HTTPS"
    ufw allow ssh
    print_status "✅ Firewall configured for port 5001 (HTTPS)"
fi

print_status "Starting services..."
systemctl daemon-reload
systemctl enable whisper-appliance

# Start whisper service with retry mechanism
for i in {1..3}; do
    print_status "Starting WhisperS2T HTTPS service (attempt $i/3)..."
    if systemctl start whisper-appliance; then
        sleep 5
        if systemctl is-active --quiet whisper-appliance; then
            print_success "WhisperS2T HTTPS service started successfully"
            
            # Quick connectivity test to ensure HTTPS service is actually working
            sleep 3
            if curl -k -s -o /dev/null -w "%{http_code}" https://localhost:5001/ | grep -q "200\|404\|500"; then
                print_success "HTTPS app responding on port 5001"
            else
                print_warning "HTTPS app not responding, attempting fix..."
                systemctl stop whisper-appliance
                sleep 2
                systemctl start whisper-appliance
                sleep 5
                if curl -k -s -o /dev/null -w "%{http_code}" https://localhost:5001/ | grep -q "200\|404\|500"; then
                    print_success "HTTPS app fixed and responding"
                else
                    print_warning "HTTPS app still not responding - check logs"
                fi
            fi
            break
        else
            print_warning "Service started but not active, checking logs..."
            systemctl status whisper-appliance --no-pager -l
        fi
    else
        print_error "Failed to start WhisperS2T service on attempt $i"
        if [[ $i -eq 3 ]]; then
            print_error "Service failed to start after 3 attempts. Check logs with: journalctl -u whisper-appliance"
        else
            sleep 3
        fi
    fi
done

print_success "WhisperS2T installation completed!"
INSTALL_EOF

# Copy script to container and make executable
pct push $CTID /tmp/install-whisper.sh /root/install-whisper.sh
pct exec $CTID -- chmod +x /root/install-whisper.sh

# Run installation
msg_info "Executing installation inside container..."
pct exec $CTID -- /root/install-whisper.sh

# Get container IP
msg_info "Getting container IP address..."
sleep 5
CONTAINER_IP=$(pct exec $CTID -- hostname -I | awk '{print $1}')

# Verify installation
msg_info "Verifying HTTPS installation..."
pct exec $CTID -- systemctl is-active whisper-appliance >/dev/null 2>&1
if [[ $? -eq 0 ]]; then
    msg_ok "WhisperS2T HTTPS service is running"
else
    msg_warn "WhisperS2T service may not be fully started yet"
fi

# Test HTTPS web interface accessibility with retry
web_accessible=false
for i in {1..3}; do
    if timeout 10 pct exec $CTID -- curl -k -s "https://localhost:5001" >/dev/null 2>&1; then
        msg_ok "HTTPS web interface is accessible"
        web_accessible=true
        break
    else
        if [[ $i -lt 3 ]]; then
            msg_warn "HTTPS web interface not ready, retrying in 5 seconds... (attempt $i/3)"
            sleep 5
        fi
    fi
done

if [[ "$web_accessible" == "false" ]]; then
    msg_warn "HTTPS web interface not immediately accessible - applying automated fix..."
    pct exec $CTID -- bash -c "
        systemctl stop whisper-appliance
        sleep 3
        systemctl start whisper-appliance
        sleep 8
    "
    
    # Final test
    if timeout 10 pct exec $CTID -- curl -k -s "https://localhost:5001" >/dev/null 2>&1; then
        msg_ok "HTTPS web interface fixed and accessible"
    else
        msg_warn "HTTPS web interface requires manual troubleshooting"
    fi
fi

# Success message
clear
cat <<"EOF"
 __        ___     _                  ____ ____  _____ 
 \ \      / / |__ (_)___ _ __   ___ _ / ___|___ \|_   _|
  \ \ /\ / /| '_ \| / __| '_ \ / _ \ '_\___ \ __) | | |  
   \ V  V / | | | | \__ \ |_) |  __/ |  ___) / __/  | |  
    \_/\_/  |_| |_|_|___/ .__/ \___|_| |____/_____| |_|  
                        |_|                              

🎉 INSTALLATION SUCCESSFUL! 🎉
EOF

echo
msg_ok "WhisperS2T LXC Container created successfully!"
msg_ok "Container ID: $CTID"
msg_ok "IP Address: $CONTAINER_IP"
echo
msg_ok "🌐 HTTPS Web Interface: https://$CONTAINER_IP:5001"
msg_ok "🔧 SSH Access: ssh root@$CONTAINER_IP"
echo
msg_info "Features available:"
msg_info "  🎙️ Live speech recognition with microphone access"
msg_info "  📁 Upload and transcribe audio files"
msg_info "  🔒 Full HTTPS with SSL certificates for network access"
msg_info "  🏥 Health monitoring: https://$CONTAINER_IP:5001/health"
msg_info "  ⚙️ Admin panel: https://$CONTAINER_IP:5001/admin"
msg_info "  📚 API documentation: https://$CONTAINER_IP:5001/docs"
echo
msg_warn "🔒 Browser Security: Click 'Advanced' → 'Continue to site' (self-signed cert)"
msg_warn "📝 Note: First transcription may take longer as Whisper downloads models"
echo
msg_info "Troubleshooting commands:"
msg_info "  pct exec $CTID -- systemctl status whisper-appliance"
msg_info "  pct exec $CTID -- journalctl -u whisper-appliance -f"
msg_info "  pct exec $CTID -- openssl x509 -in /opt/whisper-appliance/ssl/whisper-appliance.crt -text -noout | grep -A5 'Subject Alternative Name'"
echo
msg_info "Container management commands:"
msg_info "  pct start $CTID    # Start container"
msg_info "  pct stop $CTID     # Stop container"
msg_info "  pct enter $CTID    # Enter container console"
echo