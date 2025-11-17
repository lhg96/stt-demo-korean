"""
Whisper STT Model Implementation - OpenAI Whisper 모델 구현
"""

from typing import List, Optional
import time
import numpy as np

try:
    import whisper
    import torch
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

from ..core.stt_processor import STTModelInterface, STTResult, STTModelType


class WhisperSTTModel(STTModelInterface):
    """OpenAI Whisper 모델 구현"""
    
    # 지원하는 모델 크기
    SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
    
    # 지원하는 언어
    SUPPORTED_LANGUAGES = [
        "ko", "en", "ja", "zh", "es", "fr", "de", "ru", "pt", "it",
        "nl", "pl", "tr", "ar", "sv", "da", "no", "fi", "hu", "cs"
    ]
    
    def __init__(self, device: str = "auto"):
        """
        WhisperSTTModel 초기화
        
        Args:
            device: 사용할 디바이스 ("auto", "cpu", "cuda")
        """
        self.device = self._determine_device(device)
        self.model: Optional[whisper.Whisper] = None
        self.model_name: Optional[str] = None
        self.is_loaded = False
        
        # 모델별 최적 설정
        self.model_configs = {
            "tiny": {"fp16": False, "temperature": 0.0},
            "base": {"fp16": False, "temperature": 0.0}, 
            "small": {"fp16": True if self.device != "cpu" else False, "temperature": 0.0},
            "medium": {"fp16": True if self.device != "cpu" else False, "temperature": 0.0},
            "large": {"fp16": True if self.device != "cpu" else False, "temperature": 0.0},
            "large-v2": {"fp16": True if self.device != "cpu" else False, "temperature": 0.0},
            "large-v3": {"fp16": True if self.device != "cpu" else False, "temperature": 0.0}
        }

    def _determine_device(self, device: str) -> str:
        """디바이스 결정"""
        if not WHISPER_AVAILABLE:
            return "cpu"
            
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        return device

    def load_model(self, model_name: str) -> bool:
        """
        Whisper 모델 로드
        
        Args:
            model_name: 로드할 모델 이름
            
        Returns:
            bool: 로드 성공 여부
        """
        if not WHISPER_AVAILABLE:
            raise Exception("Whisper가 설치되지 않았습니다. 'pip install openai-whisper' 명령으로 설치하세요.")
        
        if model_name not in self.SUPPORTED_MODELS:
            raise Exception(f"지원되지 않는 모델: {model_name}. 지원 모델: {self.SUPPORTED_MODELS}")
        
        try:
            # 기존 모델 정리
            if self.model is not None:
                del self.model
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            
            # 새 모델 로드
            self.model = whisper.load_model(model_name, device=self.device)
            self.model_name = model_name
            self.is_loaded = True
            
            return True
            
        except Exception as e:
            self.is_loaded = False
            raise Exception(f"Whisper 모델 로드 실패: {str(e)}")

    def transcribe(self, audio_data: np.ndarray, language: str = "ko") -> STTResult:
        """
        음성 인식 수행
        
        Args:
            audio_data: 입력 오디오 데이터
            language: 언어 코드
            
        Returns:
            STTResult: 인식 결과
        """
        if not self.is_loaded or self.model is None:
            raise Exception("모델이 로드되지 않았습니다.")
        
        if language not in self.SUPPORTED_LANGUAGES:
            language = "ko"  # 기본값으로 한국어 사용
        
        start_time = time.time()
        
        try:
            # 모델 설정 가져오기
            config = self.model_configs.get(self.model_name, {})
            
            # Whisper 옵션 설정
            options = {
                "language": language,
                "task": "transcribe",
                "fp16": config.get("fp16", False),
                "temperature": config.get("temperature", 0.0),
                "beam_size": 5,
                "best_of": 5,
                "patience": 1.0,
                "length_penalty": 1.0,
                "suppress_tokens": [-1],
                "initial_prompt": None,
                "condition_on_previous_text": True,
                "verbose": False
            }
            
            # 음성 인식 수행
            result = self.model.transcribe(audio_data, **options)
            
            # 결과 추출
            text = result.get("text", "").strip()
            segments = result.get("segments", [])
            
            # 신뢰도 계산 (세그먼트별 평균)
            if segments:
                confidence_scores = []
                for segment in segments:
                    # Whisper는 기본적으로 신뢰도를 제공하지 않으므로
                    # no_speech_prob를 이용해 근사치 계산
                    no_speech_prob = segment.get("no_speech_prob", 0.5)
                    confidence = max(0.0, 1.0 - no_speech_prob)
                    confidence_scores.append(confidence)
                
                avg_confidence = sum(confidence_scores) / len(confidence_scores)
            else:
                # 텍스트가 있으면 기본 신뢰도, 없으면 0
                avg_confidence = 0.7 if text else 0.0
            
            processing_time = time.time() - start_time
            
            return STTResult(
                text=text,
                confidence=avg_confidence,
                processing_time=processing_time,
                language=language,
                model_type=STTModelType.WHISPER,
                timestamp=time.time(),
                audio_duration=len(audio_data) / 16000  # 16kHz 가정
            )
            
        except Exception as e:
            raise Exception(f"Whisper 인식 오류: {str(e)}")

    def is_model_loaded(self) -> bool:
        """모델 로드 상태 확인"""
        return self.is_loaded and self.model is not None

    def get_supported_languages(self) -> List[str]:
        """지원되는 언어 목록 반환"""
        return self.SUPPORTED_LANGUAGES.copy()

    def get_model_info(self) -> dict:
        """모델 정보 반환"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "is_loaded": self.is_loaded,
            "supported_models": self.SUPPORTED_MODELS,
            "supported_languages": self.SUPPORTED_LANGUAGES,
            "whisper_available": WHISPER_AVAILABLE
        }

    def get_device_info(self) -> dict:
        """디바이스 정보 반환"""
        info = {
            "current_device": self.device,
            "cuda_available": False,
            "mps_available": False,
            "cpu_count": 1
        }
        
        if WHISPER_AVAILABLE:
            info.update({
                "cuda_available": torch.cuda.is_available(),
                "mps_available": hasattr(torch.backends, 'mps') and torch.backends.mps.is_available(),
                "cpu_count": torch.get_num_threads()
            })
            
            if torch.cuda.is_available():
                info["cuda_device_count"] = torch.cuda.device_count()
                info["cuda_device_name"] = torch.cuda.get_device_name(0)
                info["cuda_memory_total"] = torch.cuda.get_device_properties(0).total_memory
        
        return info

    def set_device(self, device: str) -> bool:
        """디바이스 변경"""
        new_device = self._determine_device(device)
        
        if new_device != self.device:
            old_model_name = self.model_name
            self.cleanup()
            self.device = new_device
            
            # 모델이 로드되어 있었다면 새 디바이스로 다시 로드
            if old_model_name:
                return self.load_model(old_model_name)
        
        return True

    def optimize_for_realtime(self) -> bool:
        """실시간 처리 최적화"""
        if self.model_name in ["large", "large-v2", "large-v3"]:
            # 큰 모델의 경우 실시간에는 부적절할 수 있음
            return False
        
        # 실시간 최적화 설정 (메모리 사용량 감소)
        if self.model is not None and hasattr(self.model, 'eval'):
            self.model.eval()
            
        return True

    def cleanup(self):
        """리소스 정리"""
        if self.model is not None:
            del self.model
            self.model = None
            
        if WHISPER_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        self.is_loaded = False
        self.model_name = None

    def __del__(self):
        """소멸자"""
        self.cleanup()