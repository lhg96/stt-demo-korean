"""
STT Processor Module - 음성 인식 처리를 담당하는 모듈
다양한 STT 모델들을 통합하여 관리하고 처리 결과를 제공
"""

import time
import threading
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass
from enum import Enum
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal


class STTModelType(Enum):
    """STT 모델 타입 열거형"""
    WHISPER = "whisper"
    VOSK = "vosk"
    GOOGLE_CLOUD = "google_cloud"
    AZURE = "azure"


@dataclass
class STTResult:
    """STT 처리 결과 데이터 클래스"""
    text: str
    confidence: float
    processing_time: float
    language: str
    model_type: STTModelType
    timestamp: float
    audio_duration: float
    
    def __post_init__(self):
        self.timestamp = time.time() if self.timestamp is None else self.timestamp


@dataclass
class STTConfig:
    """STT 설정 데이터 클래스"""
    model_type: STTModelType
    model_name: str = "base"
    language: str = "ko"
    sample_rate: int = 16000
    chunk_duration: float = 3.0
    overlap_ratio: float = 0.5
    confidence_threshold: float = 0.5
    enable_preprocessing: bool = True
    enable_postprocessing: bool = True


class STTModelInterface(ABC):
    """STT 모델 인터페이스"""
    
    @abstractmethod
    def load_model(self, model_name: str) -> bool:
        """모델 로드"""
        pass
    
    @abstractmethod
    def transcribe(self, audio_data: np.ndarray, language: str = "ko") -> STTResult:
        """음성 인식 수행"""
        pass
    
    @abstractmethod
    def is_model_loaded(self) -> bool:
        """모델 로드 상태 확인"""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """지원되는 언어 목록 반환"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """리소스 정리"""
        pass


class STTProcessor(QObject):
    """
    통합 STT 프로세서 클래스
    다양한 STT 모델을 관리하고 음성 인식을 처리
    """
    
    # 시그널 정의
    result_ready = pyqtSignal(STTResult)           # 결과가 준비되었을 때
    model_loaded = pyqtSignal(str, STTModelType)   # 모델이 로드되었을 때
    model_load_failed = pyqtSignal(str, str)       # 모델 로드 실패 시
    processing_started = pyqtSignal()              # 처리 시작 시
    processing_finished = pyqtSignal()             # 처리 완료 시
    error_occurred = pyqtSignal(str)               # 오류 발생 시

    def __init__(self, config: STTConfig):
        """
        STTProcessor 초기화
        
        Args:
            config: STT 설정
        """
        super().__init__()
        
        self.config = config
        self.current_model: Optional[STTModelInterface] = None
        self.is_processing = False
        self.audio_buffer = []
        self.buffer_lock = threading.Lock()
        
        # 처리 통계
        self.total_processed = 0
        self.total_processing_time = 0.0
        self.results_history: List[STTResult] = []
        
        # 콜백 함수들
        self.result_callbacks: List[Callable[[STTResult], None]] = []
        self.error_callbacks: List[Callable[[str], None]] = []
        
        # 버퍼 관리
        self.buffer_size = int(self.config.sample_rate * self.config.chunk_duration)
        self.overlap_size = int(self.buffer_size * self.config.overlap_ratio)

    def set_config(self, config: STTConfig):
        """설정 업데이트"""
        self.config = config
        self.buffer_size = int(self.config.sample_rate * self.config.chunk_duration)
        self.overlap_size = int(self.buffer_size * self.config.overlap_ratio)

    def load_model(self, model_type: STTModelType, model_name: str = None) -> bool:
        """
        STT 모델 로드
        
        Args:
            model_type: 모델 타입
            model_name: 모델 이름 (선택사항)
        
        Returns:
            bool: 로드 성공 여부
        """
        try:
            # 기존 모델 정리
            if self.current_model:
                self.current_model.cleanup()
                self.current_model = None
            
            # 새 모델 생성
            self.current_model = self._create_model_instance(model_type)
            if not self.current_model:
                raise Exception(f"지원되지 않는 모델 타입: {model_type}")
            
            # 모델 로드
            model_name = model_name or self.config.model_name
            if self.current_model.load_model(model_name):
                self.model_loaded.emit(model_name, model_type)
                return True
            else:
                raise Exception(f"모델 로드 실패: {model_name}")
                
        except Exception as e:
            error_msg = f"모델 로드 오류: {str(e)}"
            self.model_load_failed.emit(model_name or "unknown", error_msg)
            self.error_occurred.emit(error_msg)
            return False

    def _create_model_instance(self, model_type: STTModelType) -> Optional[STTModelInterface]:
        """모델 인스턴스 생성"""
        if model_type == STTModelType.WHISPER:
            from ..models.whisper_model import WhisperSTTModel
            return WhisperSTTModel()
        elif model_type == STTModelType.VOSK:
            from ..models.vosk_model import VoskSTTModel
            return VoskSTTModel()
        else:
            return None

    def process_audio(self, audio_data: np.ndarray):
        """
        오디오 데이터 처리
        
        Args:
            audio_data: 입력 오디오 데이터
        """
        if not self.current_model or not self.current_model.is_model_loaded():
            return
        
        with self.buffer_lock:
            self.audio_buffer.extend(audio_data.flatten())
            
            # 버퍼가 충분히 찬 경우 처리
            if len(self.audio_buffer) >= self.buffer_size:
                # 처리할 오디오 청크 추출
                audio_chunk = np.array(self.audio_buffer[:self.buffer_size])
                
                # 오버랩을 고려하여 버퍼 업데이트
                if self.overlap_size > 0:
                    self.audio_buffer = self.audio_buffer[self.buffer_size - self.overlap_size:]
                else:
                    self.audio_buffer = self.audio_buffer[self.buffer_size:]
                
                # 별도 스레드에서 처리
                threading.Thread(
                    target=self._process_audio_chunk,
                    args=(audio_chunk,),
                    daemon=True
                ).start()

    def _process_audio_chunk(self, audio_chunk: np.ndarray):
        """오디오 청크 처리"""
        if self.is_processing:
            return  # 이미 처리 중인 경우 건너뜀
        
        try:
            self.is_processing = True
            self.processing_started.emit()
            
            start_time = time.time()
            
            # 전처리
            if self.config.enable_preprocessing:
                audio_chunk = self._preprocess_audio(audio_chunk)
            
            # STT 처리
            result = self.current_model.transcribe(
                audio_chunk, 
                language=self.config.language
            )
            
            # 후처리
            if self.config.enable_postprocessing and result.text:
                result.text = self._postprocess_text(result.text)
            
            # 신뢰도 확인
            if result.confidence >= self.config.confidence_threshold and result.text.strip():
                # 처리 시간 업데이트
                result.processing_time = time.time() - start_time
                result.audio_duration = len(audio_chunk) / self.config.sample_rate
                
                # 통계 업데이트
                self.total_processed += 1
                self.total_processing_time += result.processing_time
                self.results_history.append(result)
                
                # 결과 방출
                self.result_ready.emit(result)
                
                # 콜백 호출
                for callback in self.result_callbacks:
                    try:
                        callback(result)
                    except Exception as e:
                        self.error_occurred.emit(f"콜백 오류: {str(e)}")
        
        except Exception as e:
            error_msg = f"음성 인식 처리 오류: {str(e)}"
            self.error_occurred.emit(error_msg)
            for callback in self.error_callbacks:
                try:
                    callback(error_msg)
                except:
                    pass
        
        finally:
            self.is_processing = False
            self.processing_finished.emit()

    def _preprocess_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """오디오 전처리"""
        # 노이즈 제거 (간단한 하이패스 필터)
        if len(audio_data) > 1:
            # 단순한 하이패스 필터
            filtered = np.diff(audio_data, prepend=audio_data[0])
            audio_data = filtered * 0.95 + audio_data * 0.05
        
        # 정규화
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            audio_data = audio_data / max_val * 0.8
        
        return audio_data

    def _postprocess_text(self, text: str) -> str:
        """텍스트 후처리"""
        # 기본적인 텍스트 정리
        text = text.strip()
        
        # 반복된 공백 제거
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # 기본적인 문장 정리
        text = text.replace(' .', '.')
        text = text.replace(' ,', ',')
        text = text.replace(' ?', '?')
        text = text.replace(' !', '!')
        
        return text

    def add_result_callback(self, callback: Callable[[STTResult], None]):
        """결과 콜백 추가"""
        self.result_callbacks.append(callback)

    def add_error_callback(self, callback: Callable[[str], None]):
        """에러 콜백 추가"""
        self.error_callbacks.append(callback)

    def remove_result_callback(self, callback: Callable[[STTResult], None]):
        """결과 콜백 제거"""
        if callback in self.result_callbacks:
            self.result_callbacks.remove(callback)

    def remove_error_callback(self, callback: Callable[[str], None]):
        """에러 콜백 제거"""
        if callback in self.error_callbacks:
            self.error_callbacks.remove(callback)

    def clear_buffer(self):
        """오디오 버퍼 초기화"""
        with self.buffer_lock:
            self.audio_buffer.clear()

    def get_statistics(self) -> Dict:
        """처리 통계 반환"""
        avg_processing_time = (
            self.total_processing_time / self.total_processed 
            if self.total_processed > 0 else 0.0
        )
        
        return {
            "total_processed": self.total_processed,
            "total_processing_time": self.total_processing_time,
            "average_processing_time": avg_processing_time,
            "current_model_type": self.config.model_type.value if self.current_model else None,
            "buffer_size": len(self.audio_buffer),
            "is_processing": self.is_processing,
            "results_count": len(self.results_history)
        }

    def get_recent_results(self, count: int = 10) -> List[STTResult]:
        """최근 결과 반환"""
        return self.results_history[-count:] if self.results_history else []

    def clear_history(self):
        """결과 히스토리 초기화"""
        self.results_history.clear()
        self.total_processed = 0
        self.total_processing_time = 0.0

    def is_ready(self) -> bool:
        """처리 준비 상태 확인"""
        return (self.current_model is not None and 
                self.current_model.is_model_loaded() and 
                not self.is_processing)

    def get_supported_languages(self) -> List[str]:
        """지원되는 언어 목록 반환"""
        if self.current_model:
            return self.current_model.get_supported_languages()
        return []

    def cleanup(self):
        """리소스 정리"""
        if self.current_model:
            self.current_model.cleanup()
            self.current_model = None
        self.clear_buffer()
        self.clear_history()

    def __del__(self):
        """소멸자"""
        self.cleanup()