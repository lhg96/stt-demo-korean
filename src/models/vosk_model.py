"""
Vosk STT Model Implementation - Vosk 모델 구현
"""

import json
import os
import time
from typing import List, Optional
import numpy as np

try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

from ..core.stt_processor import STTModelInterface, STTResult, STTModelType


class VoskSTTModel(STTModelInterface):
    """Vosk 모델 구현"""
    
    # 기본 모델 경로들
    DEFAULT_MODEL_PATHS = [
        "./vosk-model-small-ko-0.22",
        "./models/vosk-model-small-ko-0.22", 
        "./vosk-model-ko",
        "./models/vosk-model-ko"
    ]
    
    # 지원하는 언어 (모델 기준)
    SUPPORTED_LANGUAGES = ["ko", "en", "ru", "fr", "de", "es", "pt", "cn", "jp"]
    
    def __init__(self, sample_rate: int = 16000):
        """
        VoskSTTModel 초기화
        
        Args:
            sample_rate: 샘플링 레이트
        """
        self.sample_rate = sample_rate
        self.model: Optional[Model] = None
        self.recognizer: Optional[KaldiRecognizer] = None
        self.model_path: Optional[str] = None
        self.is_loaded = False
        
        # 모델별 설정
        self.model_language = "ko"
        self.confidence_threshold = 0.5

    def load_model(self, model_path: str = None) -> bool:
        """
        Vosk 모델 로드
        
        Args:
            model_path: 모델 경로 (None인 경우 기본 경로에서 검색)
            
        Returns:
            bool: 로드 성공 여부
        """
        if not VOSK_AVAILABLE:
            raise Exception("Vosk가 설치되지 않았습니다. 'pip install vosk' 명령으로 설치하세요.")
        
        # 모델 경로 결정
        if model_path is None:
            model_path = self._find_model_path()
            if model_path is None:
                raise Exception("Vosk 모델을 찾을 수 없습니다. 모델을 다운로드하고 경로를 확인하세요.")
        
        if not os.path.exists(model_path):
            raise Exception(f"모델 경로가 존재하지 않습니다: {model_path}")
        
        try:
            # 기존 모델 정리
            if self.model is not None:
                del self.model
                del self.recognizer
                self.model = None
                self.recognizer = None
            
            # 새 모델 로드
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.model_path = model_path
            self.is_loaded = True
            
            # 모델 언어 감지
            self._detect_model_language(model_path)
            
            return True
            
        except Exception as e:
            self.is_loaded = False
            raise Exception(f"Vosk 모델 로드 실패: {str(e)}")

    def _find_model_path(self) -> Optional[str]:
        """기본 모델 경로 검색"""
        for path in self.DEFAULT_MODEL_PATHS:
            if os.path.exists(path) and os.path.isdir(path):
                # 모델 디렉토리 내 필수 파일 확인
                required_files = ["conf/model.conf", "am/final.mdl", "graph/HCLr.fst"]
                if all(os.path.exists(os.path.join(path, f)) for f in required_files):
                    return path
        return None

    def _detect_model_language(self, model_path: str):
        """모델 언어 감지"""
        # 경로에서 언어 추정
        path_lower = model_path.lower()
        if "ko" in path_lower or "korean" in path_lower:
            self.model_language = "ko"
        elif "en" in path_lower or "english" in path_lower:
            self.model_language = "en"
        elif "ru" in path_lower or "russian" in path_lower:
            self.model_language = "ru"
        elif "fr" in path_lower or "french" in path_lower:
            self.model_language = "fr"
        elif "de" in path_lower or "german" in path_lower:
            self.model_language = "de"
        elif "es" in path_lower or "spanish" in path_lower:
            self.model_language = "es"
        elif "pt" in path_lower or "portuguese" in path_lower:
            self.model_language = "pt"
        elif "cn" in path_lower or "chinese" in path_lower:
            self.model_language = "cn"
        elif "jp" in path_lower or "japanese" in path_lower:
            self.model_language = "jp"
        else:
            self.model_language = "ko"  # 기본값

    def transcribe(self, audio_data: np.ndarray, language: str = "ko") -> STTResult:
        """
        음성 인식 수행
        
        Args:
            audio_data: 입력 오디오 데이터
            language: 언어 코드 (Vosk는 모델에 의해 결정되므로 참고용)
            
        Returns:
            STTResult: 인식 결과
        """
        if not self.is_loaded or self.recognizer is None:
            raise Exception("모델이 로드되지 않았습니다.")
        
        start_time = time.time()
        
        try:
            # numpy 배열을 16비트 PCM으로 변환
            audio_int16 = (audio_data * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            
            # Vosk 인식 수행
            if self.recognizer.AcceptWaveform(audio_bytes):
                # 완전한 인식 결과
                result_json = self.recognizer.Result()
                result_data = json.loads(result_json)
                text = result_data.get("text", "").strip()
                confidence = result_data.get("confidence", 0.5)
            else:
                # 부분 인식 결과
                partial_json = self.recognizer.PartialResult()
                partial_data = json.loads(partial_json)
                text = partial_data.get("partial", "").strip()
                confidence = 0.3  # 부분 결과의 경우 낮은 신뢰도
            
            processing_time = time.time() - start_time
            
            return STTResult(
                text=text,
                confidence=confidence,
                processing_time=processing_time,
                language=self.model_language,
                model_type=STTModelType.VOSK,
                timestamp=time.time(),
                audio_duration=len(audio_data) / self.sample_rate
            )
            
        except Exception as e:
            raise Exception(f"Vosk 인식 오류: {str(e)}")

    def transcribe_streaming(self, audio_data: np.ndarray) -> tuple[str, float]:
        """
        스트리밍 인식 (부분 결과 포함)
        
        Args:
            audio_data: 입력 오디오 데이터
            
        Returns:
            tuple: (텍스트, 신뢰도)
        """
        if not self.is_loaded or self.recognizer is None:
            return "", 0.0
        
        try:
            # numpy 배열을 16비트 PCM으로 변환
            audio_int16 = (audio_data * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            
            # 스트리밍 인식
            if self.recognizer.AcceptWaveform(audio_bytes):
                # 완전한 결과
                result_json = self.recognizer.Result()
                result_data = json.loads(result_json)
                return result_data.get("text", "").strip(), result_data.get("confidence", 0.5)
            else:
                # 부분 결과
                partial_json = self.recognizer.PartialResult()
                partial_data = json.loads(partial_json)
                return partial_data.get("partial", "").strip(), 0.3
                
        except Exception as e:
            return "", 0.0

    def get_final_result(self) -> tuple[str, float]:
        """최종 인식 결과 반환"""
        if not self.is_loaded or self.recognizer is None:
            return "", 0.0
        
        try:
            final_json = self.recognizer.FinalResult()
            final_data = json.loads(final_json)
            return final_data.get("text", "").strip(), final_data.get("confidence", 0.5)
        except Exception as e:
            return "", 0.0

    def reset_recognizer(self):
        """인식기 리셋"""
        if self.is_loaded and self.model is not None:
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)

    def is_model_loaded(self) -> bool:
        """모델 로드 상태 확인"""
        return self.is_loaded and self.model is not None and self.recognizer is not None

    def get_supported_languages(self) -> List[str]:
        """지원되는 언어 목록 반환"""
        return self.SUPPORTED_LANGUAGES.copy()

    def get_model_info(self) -> dict:
        """모델 정보 반환"""
        return {
            "model_path": self.model_path,
            "model_language": self.model_language,
            "sample_rate": self.sample_rate,
            "is_loaded": self.is_loaded,
            "supported_languages": self.SUPPORTED_LANGUAGES,
            "vosk_available": VOSK_AVAILABLE,
            "confidence_threshold": self.confidence_threshold
        }

    def set_sample_rate(self, sample_rate: int) -> bool:
        """샘플링 레이트 변경"""
        if sample_rate != self.sample_rate:
            self.sample_rate = sample_rate
            # 인식기 재생성 필요
            if self.is_loaded and self.model is not None:
                try:
                    self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
                    return True
                except Exception as e:
                    return False
        return True

    def set_confidence_threshold(self, threshold: float):
        """신뢰도 임계값 설정"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))

    def list_available_models(self) -> List[dict]:
        """사용 가능한 모델 목록 반환"""
        models = []
        for path in self.DEFAULT_MODEL_PATHS:
            if os.path.exists(path) and os.path.isdir(path):
                # 모델 정보 수집
                model_info = {
                    "path": path,
                    "name": os.path.basename(path),
                    "size": self._get_directory_size(path),
                    "language": "ko" if "ko" in path.lower() else "unknown",
                    "valid": self._validate_model_directory(path)
                }
                models.append(model_info)
        return models

    def _get_directory_size(self, path: str) -> int:
        """디렉토리 크기 계산"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(filepath)
        except OSError:
            pass
        return total_size

    def _validate_model_directory(self, path: str) -> bool:
        """모델 디렉토리 유효성 검사"""
        required_files = [
            "conf/model.conf",
            "am/final.mdl", 
            "graph/HCLr.fst",
            "graph/phones.txt"
        ]
        
        return all(os.path.exists(os.path.join(path, f)) for f in required_files)

    def cleanup(self):
        """리소스 정리"""
        if self.recognizer is not None:
            del self.recognizer
            self.recognizer = None
            
        if self.model is not None:
            del self.model
            self.model = None
            
        self.is_loaded = False
        self.model_path = None

    def __del__(self):
        """소멸자"""
        self.cleanup()