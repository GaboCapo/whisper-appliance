"""
Upload Handler Module
Handles file upload transcription functionality
Preserves all original upload features from enhanced_app.py
"""

import logging
import os
import tempfile
from datetime import datetime

from flask import jsonify, request
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


class UploadHandler:
    """Handles audio file upload and transcription"""

    def __init__(self, model_manager, whisper_available, system_stats, chat_history):
        self.model_manager = model_manager
        self.whisper_available = whisper_available
        self.system_stats = system_stats
        self.chat_history = chat_history

    def transcribe_upload(self):
        """Transcribe uploaded audio file - Original functionality preserved"""
        if not self.whisper_available:
            return jsonify({"error": "Whisper model not available"})

        try:
            if "audio" not in request.files:
                return jsonify({"error": "No audio file provided"})

            audio_file = request.files["audio"]
            if audio_file.filename == "":
                return jsonify({"error": "No audio file selected"})

            # Secure filename
            filename = secure_filename(audio_file.filename)

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                audio_file.save(tmp_file.name)

                # Transcribe audio using ModelManager
                current_model = self.model_manager.get_current_model_name()
                logger.info(f"Transcribing file: {filename} with model: {current_model}")
                result = self.model_manager.transcribe(tmp_file.name)

                # Clean up temp file
                os.unlink(tmp_file.name)

                # Update statistics
                self.system_stats["total_transcriptions"] += 1
                logger.info("Transcription completed successfully")

                if result:
                    # Save to chat history
                    try:
                        self.chat_history.add_transcription(
                            text=result["text"],
                            language=result.get("language", "unknown"),
                            model_used=current_model,
                            source_type="upload",
                            filename=filename,
                            metadata={"timestamp": datetime.now().isoformat()},
                        )
                    except Exception as e:
                        logger.warning(f"Failed to save transcription to history: {e}")

                    return jsonify(
                        {
                            "text": result["text"],
                            "language": result.get("language", "unknown"),
                            "model_used": current_model,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                else:
                    return jsonify({"error": "Transcription failed"})

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return jsonify({"error": str(e)})

    def transcribe_live_api(self):
        """Transcribe live audio recording - Enhanced API version"""
        if not self.whisper_available:
            return jsonify({"error": "Whisper model not available"})

        try:
            if "audio" not in request.files:
                return jsonify({"error": "No audio data provided"})

            audio_file = request.files["audio"]
            language = request.form.get("language", "auto")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                audio_file.save(tmp_file.name)

                logger.info(f"Live transcribing audio (lang: {language})")

                kwargs = {}
                if language != "auto":
                    kwargs["language"] = language

                result = self.model_manager.transcribe(tmp_file.name, **kwargs)
                os.unlink(tmp_file.name)

                self.system_stats["total_transcriptions"] += 1

                # Save to chat history
                try:
                    self.chat_history.add_transcription(
                        text=result["text"],
                        language=result.get("language", "unknown"),
                        model_used=self.model_manager.get_current_model_name(),
                        source_type="live_api",
                        metadata={"language_requested": language, "timestamp": datetime.now().isoformat()},
                    )
                except Exception as e:
                    logger.warning(f"Failed to save live transcription to history: {e}")

                return jsonify(
                    {
                        "text": result["text"],
                        "language": result.get("language", "unknown"),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        except Exception as e:
            logger.error(f"Live transcription error: {e}")
            return jsonify({"error": str(e)})
