"""STT Demo Package - 음성 인식 데모 애플리케이션"""

__version__ = "1.0.0"
__author__ = "STT Demo Team"
__description__ = "Speech-to-Text demonstration application with GUI"

from .core.audio_recorder import AudioRecorder
from .core.stt_processor import STTProcessor
from .models.whisper_model import WhisperSTTModel
from .models.vosk_model import VoskSTTModel
from .gui.main_window import STTMainWindow
from .utils.config_manager import ConfigManager
from .utils.audio_utils import AudioUtils

__all__ = [
    "AudioRecorder",
    "STTProcessor", 
    "WhisperSTTModel",
    "VoskSTTModel",
    "STTMainWindow",
    "ConfigManager",
    "AudioUtils"
]
