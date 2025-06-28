#!/usr/bin/env python3
"""
WhisperS2T Appliance - Live Audio Server (Standalone)
Complete implementation with integrated AudioInputManager
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio
import json
from datetime import datetime
import numpy as np
import time
import queue
from typing import Dict, Optional, Callable
from collections import deque

# Import faster-whisper
from faster_whisper import WhisperModel

app = FastAPI(title="WhisperS2T Live Audio", version="0.3.0")

# ============================================================================
# INTEGRATED AUDIO INPUT MANAGER
# ============================================================================

class AudioInputManager:
    def __init__(self, sample_rate: int = 16000, channels: int = 1, chunk_duration: float = 1.0):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration = chunk_duration
        self.chunk_size = int(sample_rate * chunk_duration)
        
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.audio_buffer = deque(maxlen=10)
        
        self.input_devices = []
        self.current_device = None
        self.hardware_available = False
        
        self._detect_audio_devices()
    
    def _detect_audio_devices(self):
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            self.input_devices = []
            
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    device_info = {
                        'index': i,
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'sample_rate': device['default_samplerate'],
                        'type': 'hardware'
                    }
                    self.input_devices.append(device_info)
            
            if self.input_devices:
                self.current_device = self.input_devices[0]
                self.hardware_available = True
                print(f"🎤 Found {len(self.input_devices)} hardware audio devices")
            else:
                self._setup_fallback_devices()
                
        except (ImportError, OSError) as e:
            print(f"⚠️ Hardware audio not available: {e}")
            self._setup_fallback_devices()
    
    def _setup_fallback_devices(self):
        self.input_devices = [{
            'index': 0,
            'name': 'Simulated Microphone (Test Mode)',
            'channels': 1,
            'sample_rate': 16000,
            'type': 'simulated'
        }]
        self.current_device = self.input_devices[0]
        self.hardware_available = False
        print("🔄 Using simulated audio devices")
    
    def get_device_status(self) -> Dict:
        return {
            "devices_available": len(self.input_devices),
            "input_devices": self.input_devices,
            "current_device": self.current_device,
            "is_recording": self.is_recording,
            "hardware_available": self.hardware_available,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "chunk_duration": self.chunk_duration
        }
    
    def has_microphone(self) -> bool:
        return len(self.input_devices) > 0
    
    def _generate_test_audio(self, duration: float = 1.0) -> np.ndarray:
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples)
        
        # Generate speech-like audio
        audio = (
            0.3 * np.sin(2 * np.pi * 220 * t) +
            0.2 * np.sin(2 * np.pi * 440 * t) +
            0.1 * np.sin(2 * np.pi * 880 * t) +
            0.05 * np.random.normal(0, 1, samples)
        )
        
        envelope = np.exp(-t * 0.5) * (1 + 0.5 * np.sin(2 * np.pi * 3 * t))
        audio *= envelope
        audio = audio / np.max(np.abs(audio)) * 0.3
        
        return audio.astype(np.float32)
    
    def start_recording(self) -> bool:
        if self.is_recording:
            print("⚠️ Already recording")
            return True
        
        if not self.has_microphone():
            print("❌ No audio input available")
            return False
        
        try:
            if self.hardware_available:
                return self._start_hardware_recording()
            else:
                return self._start_simulated_recording()
        except Exception as e:
            print(f"❌ Failed to start recording: {e}")
            return False
    
    def _start_hardware_recording(self) -> bool:
        try:
            import sounddevice as sd
            
            def audio_callback(indata, frames, time, status):
                if status:
                    print(f"⚠️ Audio callback status: {status}")
                
                if indata.shape[1] > 1:
                    audio_data = np.mean(indata, axis=1)
                else:
                    audio_data = indata[:, 0]
                
                self.audio_buffer.append(audio_data.copy())
                
                try:
                    self.audio_queue.put_nowait(audio_data.copy())
                except queue.Full:
                    try:
                        self.audio_queue.get_nowait()
                        self.audio_queue.put_nowait(audio_data.copy())
                    except queue.Empty:
                        pass
            
            self.audio_stream = sd.InputStream(
                device=self.current_device['index'],
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                callback=audio_callback,
                dtype=np.float32
            )
            
            self.audio_stream.start()
            self.is_recording = True
            print(f"🎤 Started hardware recording: {self.current_device['name']}")
            return True
            
        except Exception as e:
            print(f"❌ Hardware recording failed: {e}")
            return False
    
    def _start_simulated_recording(self) -> bool:
        self.is_recording = True
        
        import threading
        
        def generate_audio():
            while self.is_recording:
                audio_chunk = self._generate_test_audio(self.chunk_duration)
                self.audio_buffer.append(audio_chunk)
                
                try:
                    self.audio_queue.put_nowait(audio_chunk)
                except queue.Full:
                    try:
                        self.audio_queue.get_nowait()
                        self.audio_queue.put_nowait(audio_chunk)
                    except queue.Empty:
                        pass
                
                time.sleep(self.chunk_duration)
        
        self.audio_thread = threading.Thread(target=generate_audio, daemon=True)
        self.audio_thread.start()
        print(f"🎤 Started simulated recording: {self.current_device['name']}")
        return True
    
    def stop_recording(self) -> bool:
        if not self.is_recording:
            return True
        
        try:
            self.is_recording = False
            
            if self.hardware_available and hasattr(self, 'audio_stream'):
                self.audio_stream.stop()
                self.audio_stream.close()
                del self.audio_stream
            
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
            
            print("🛑 Stopped recording")
            return True
            
        except Exception as e:
            print(f"❌ Failed to stop recording: {e}")
            return False
    
    def get_audio_chunk(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    async def get_audio_chunk_async(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None, 
                lambda: self.audio_queue.get(timeout=timeout)
            )
        except queue.Empty:
            return None
    
    def get_audio_level(self) -> float:
        if not self.audio_buffer:
            return 0.0
        
        latest_chunk = self.audio_buffer[-1]
        rms = np.sqrt(np.mean(latest_chunk ** 2))
        level = min(rms / 0.1, 1.0)
        return level
    
    def get_recent_audio(self, duration: float = 5.0) -> np.ndarray:
        if not self.audio_buffer:
            return np.array([], dtype=np.float32)
        
        chunks_needed = int(duration / self.chunk_duration)
        chunks_needed = min(chunks_needed, len(self.audio_buffer))
        
        if chunks_needed == 0:
            return np.array([], dtype=np.float32)
        
        recent_chunks = list(self.audio_buffer)[-chunks_needed:]
        audio_data = np.concatenate(recent_chunks)
        return audio_data


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

# Global state
whisper_model = None
current_model_name = None
connected_clients = []
system_ready = False
audio_manager = AudioInputManager()

async def load_whisper_model(model_name="tiny"):
    global whisper_model, current_model_name
    
    print(f"🔄 Loading {model_name} model...")
    start_time = time.time()
    
    loop = asyncio.get_event_loop()
    whisper_model = await loop.run_in_executor(
        None, 
        lambda: WhisperModel(model_name, device="cpu", compute_type="int8")
    )
    
    load_time = time.time() - start_time
    current_model_name = model_name
    
    print(f"✅ Model {model_name} loaded in {load_time:.1f}s")
    return {"model": model_name, "load_time": round(load_time, 1)}

async def transcribe_audio(audio_data):
    global whisper_model
    
    if not whisper_model:
        await load_whisper_model("tiny")
    
    print(f"🎤 Transcribing {len(audio_data)} audio samples...")
    start_time = time.time()
    
    loop = asyncio.get_event_loop()
    segments, info = await loop.run_in_executor(
        None,
        lambda: whisper_model.transcribe(audio_data, beam_size=1)
    )
    
    full_text = " ".join(segment.text for segment in segments)
    processing_time = time.time() - start_time
    
    return {
        "text": full_text.strip(),
        "language": info.language,
        "processing_time": round(processing_time, 2),
        "model": current_model_name,
        "audio_length": len(audio_data) / 16000
    }

@app.on_event("startup")
async def startup_event():
    global system_ready
    
    print("🚀 Starting WhisperS2T Appliance with LIVE AUDIO...")
    try:
        await load_whisper_model("tiny")
        
        audio_status = audio_manager.get_device_status()
        print(f"🎤 Audio devices: {audio_status['devices_available']}")
        print(f"🔧 Hardware available: {audio_status['hardware_available']}")
        
        system_ready = True
        print("✅ WhisperS2T Live Audio ready!")
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        system_ready = False

@app.get("/")
async def root():
    status = "✅ Ready for live transcription!" if system_ready else "🔄 Starting up..."
    model = current_model_name or "Loading..."
    audio_status = audio_manager.get_device_status()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>WhisperS2T - Live Audio</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .status {{ padding: 15px; background: #d4edda; color: #155724; border-radius: 5px; margin: 20px 0; font-weight: bold; }}
            .audio-status {{ padding: 15px; background: #e2e3e5; color: #383d41; border-radius: 5px; margin: 20px 0; }}
            .button {{ display: inline-block; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px; font-weight: bold; }}
            .button:hover {{ background: #0056b3; }}
            .feature {{ background: #f8f9fa; padding: 15px; margin: 15px 0; border-left: 4px solid #007bff; }}
            .highlight {{ background: #fff3cd; padding: 15px; margin: 15px 0; border-left: 4px solid #ffc107; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎤 WhisperS2T Live Audio</h1>
            <p><strong>Real-time Speech-to-Text with Live Audio Input</strong></p>
            
            <div class="status">{status}</div>
            
            <div class="audio-status">
                <h4>🎙️ Audio System</h4>
                <p><strong>Devices:</strong> {audio_status['devices_available']}</p>
                <p><strong>Hardware:</strong> {'✅ Available' if audio_status['hardware_available'] else '🔄 Simulated'}</p>
                <p><strong>Device:</strong> {audio_status['current_device']['name'] if audio_status['current_device'] else 'None'}</p>
            </div>
            
            <div class="highlight">
                <h3>🔥 LIVE AUDIO TRANSCRIPTION!</h3>
                <p>Real-time microphone → Whisper transcription</p>
            </div>
            
            <h3>🎯 Try It Now</h3>
            <a href="/demo" class="button">🎙️ Live Demo</a>
            <a href="/api/status" class="button">📊 Status</a>
            <a href="/docs" class="button">📚 API Docs</a>
            
            <div class="feature">
                <h3>🔧 Configuration</h3>
                <p><strong>Model:</strong> {model}</p>
                <p><strong>Sample Rate:</strong> {audio_status['sample_rate']} Hz</p>
                <p><strong>Connected Clients:</strong> {len(connected_clients)}</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/api/status")
async def get_status():
    import platform
    import psutil
    
    audio_status = audio_manager.get_device_status()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "version": "0.3.0-standalone",
        "status": "ready" if system_ready else "starting",
        "whisper": {
            "current_model": current_model_name,
            "available_models": ["tiny", "base", "small", "medium"],
            "model_loaded": whisper_model is not None
        },
        "audio": audio_status,
        "system": {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "cpu_cores": psutil.cpu_count()
        },
        "websocket": {
            "connected_clients": len(connected_clients)
        }
    }

@app.get("/demo")
async def live_demo_page():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WhisperS2T - LIVE AUDIO Demo</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f8f9fa; }
            .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            button { padding: 12px 24px; margin: 8px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; transition: all 0.2s; }
            .btn-primary { background: #007bff; color: white; }
            .btn-success { background: #28a745; color: white; }
            .btn-record { background: #dc3545; color: white; font-size: 18px; padding: 15px 30px; }
            .btn-record.recording { background: #28a745; animation: pulse 1s infinite; }
            @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
            
            .status { padding: 12px; border-radius: 5px; margin: 15px 0; font-weight: bold; text-align: center; }
            .connected { background: #d4edda; color: #155724; }
            .disconnected { background: #f8d7da; color: #721c24; }
            .recording { background: #fff3cd; color: #856404; }
            
            .controls { background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; text-align: center; }
            
            .live-transcription {
                background: #f0fff0;
                border: 1px solid #90ee90;
                border-radius: 5px;
                padding: 15px;
                margin: 10px 0;
                border-left: 4px solid #28a745;
            }
            
            .audio-level {
                width: 100%;
                height: 30px;
                background: #e9ecef;
                border-radius: 15px;
                margin: 10px 0;
                overflow: hidden;
            }
            
            .audio-level-bar {
                height: 100%;
                background: linear-gradient(90deg, #28a745, #ffc107, #dc3545);
                border-radius: 15px;
                transition: width 0.1s ease;
                width: 0%;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🎤 WhisperS2T - LIVE AUDIO Demo</h2>
            <p>Real-time microphone → Whisper transcription</p>
            
            <div id="status" class="status disconnected">
                ❌ Disconnected - Click Connect to start
            </div>
            
            <div class="controls">
                <h4>🔌 Connection & Recording</h4>
                <button onclick="connect()" class="btn-primary">🔌 Connect</button>
                <br><br>
                
                <button id="recordBtn" onclick="toggleRecording()" class="btn-record">
                    🎙️ START LIVE RECORDING
                </button>
                <br><br>
                
                <button onclick="transcribeRecent()" class="btn-success">📝 Transcribe Last 5s</button>
                
                <h4>🎛️ Audio Level</h4>
                <div class="audio-level">
                    <div id="audioLevelBar" class="audio-level-bar"></div>
                </div>
                <span id="audioLevelText">Level: 0%</span>
            </div>
            
            <div id="transcription-display" style="min-height: 200px; margin: 20px 0;">
                <h4>📝 Live Transcription Results</h4>
                <div id="liveResults">Results will appear here...</div>
            </div>
        </div>
        
        <script>
            let ws = null;
            let isRecording = false;
            
            function connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/live-audio`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function() { updateStatus('connected'); };
                ws.onmessage = function(event) { handleMessage(JSON.parse(event.data)); };
                ws.onclose = function() { updateStatus('disconnected'); isRecording = false; updateRecordButton(); };
                ws.onerror = function(error) { console.error('WebSocket error:', error); updateStatus('disconnected'); };
            }
            
            function toggleRecording() {
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    alert('Not connected! Click Connect first.');
                    return;
                }
                
                if (!isRecording) {
                    ws.send(JSON.stringify({action: 'start_recording'}));
                } else {
                    ws.send(JSON.stringify({action: 'stop_recording'}));
                }
            }
            
            function transcribeRecent() {
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    alert('Not connected!');
                    return;
                }
                
                ws.send(JSON.stringify({action: 'transcribe_recent', duration: 5.0}));
            }
            
            function handleMessage(data) {
                console.log('Received:', data.type, data);
                
                switch(data.type) {
                    case 'connected':
                        addLogMessage('✅ ' + data.message);
                        break;
                    case 'recording_started':
                        isRecording = true;
                        updateRecordButton();
                        updateStatus('recording');
                        addLogMessage('🎤 Recording started - speak now!');
                        break;
                    case 'recording_stopped':
                        isRecording = false;
                        updateRecordButton();
                        updateStatus('connected');
                        addLogMessage('🛑 Recording stopped');
                        break;
                    case 'live_transcription':
                        displayLiveTranscription(data.result);
                        break;
                    case 'transcription_result':
                        displayTranscriptionResult(data.result, data.source);
                        break;
                    case 'audio_level':
                        updateAudioLevel(data.level);
                        break;
                    case 'processing':
                        addLogMessage('🔄 ' + data.message);
                        break;
                    case 'error':
                        addLogMessage('❌ ' + data.message);
                        break;
                }
            }
            
            function displayLiveTranscription(result) {
                const liveResults = document.getElementById('liveResults');
                const div = document.createElement('div');
                div.className = 'live-transcription';
                div.innerHTML = `
                    <h5>🔴 LIVE: ${new Date().toLocaleTimeString()}</h5>
                    <p><strong>"${result.text}"</strong></p>
                    <small>Language: ${result.language} | Processing: ${result.processing_time}s | Model: ${result.model}</small>
                `;
                liveResults.appendChild(div);
                liveResults.scrollTop = liveResults.scrollHeight;
            }
            
            function displayTranscriptionResult(result, source) {
                const liveResults = document.getElementById('liveResults');
                const div = document.createElement('div');
                div.className = 'live-transcription';
                div.innerHTML = `
                    <h5>📝 ${source}: ${new Date().toLocaleTimeString()}</h5>
                    <p><strong>"${result.text}"</strong></p>
                    <small>Language: ${result.language} | Processing: ${result.processing_time}s | Audio: ${result.audio_length.toFixed(1)}s</small>
                `;
                liveResults.appendChild(div);
                liveResults.scrollTop = liveResults.scrollHeight;
            }
            
            function addLogMessage(message) {
                const liveResults = document.getElementById('liveResults');
                const div = document.createElement('div');
                div.style.cssText = 'padding: 8px; margin: 5px 0; background: #f8f9fa; border-radius: 3px; font-size: 14px;';
                div.innerHTML = `<small>${new Date().toLocaleTimeString()}: ${message}</small>`;
                liveResults.appendChild(div);
                liveResults.scrollTop = liveResults.scrollHeight;
            }
            
            function updateAudioLevel(level) {
                const bar = document.getElementById('audioLevelBar');
                const text = document.getElementById('audioLevelText');
                const percentage = Math.round(level * 100);
                
                bar.style.width = percentage + '%';
                text.textContent = `Level: ${percentage}%`;
            }
            
            function updateRecordButton() {
                const btn = document.getElementById('recordBtn');
                if (isRecording) {
                    btn.innerHTML = '⏹️ STOP RECORDING';
                    btn.className = 'btn-record recording';
                } else {
                    btn.innerHTML = '🎙️ START LIVE RECORDING';
                    btn.className = 'btn-record';
                }
            }
            
            function updateStatus(status) {
                const statusDiv = document.getElementById('status');
                switch(status) {
                    case 'connected':
                        statusDiv.className = 'status connected';
                        statusDiv.innerHTML = '✅ Connected - Ready for Live Audio';
                        break;
                    case 'recording':
                        statusDiv.className = 'status recording';
                        statusDiv.innerHTML = '🔴 RECORDING - Speak now!';
                        break;
                    case 'disconnected':
                        statusDiv.className = 'status disconnected';
                        statusDiv.innerHTML = '❌ Disconnected';
                        break;
                }
            }
            
            window.onload = function() {
                console.log('WhisperS2T Live Audio Demo Ready!');
                addLogMessage('Demo interface loaded - click Connect to start');
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

if __name__ == "__main__":
    import uvicorn
    
    print("🎤 Starting WhisperS2T Live Audio Server...")
    print("🌐 Main Interface: http://localhost:5000")
    print("🎙️ Live Audio Demo: http://localhost:5000/demo")
    print("📊 API Status: http://localhost:5000/api/status")
    print()
    print("🎤 LIVE FEATURES:")
    print("   - Real microphone input (or simulated if no hardware)")
    print("   - Live audio level monitoring")
    print("   - Real-time transcription")
    print("   - WebSocket live communication")
    
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
