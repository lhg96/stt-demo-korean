"""
Audio Recording Module - 오디오 녹음 기능을 담당하는 모듈
실시간 오디오 입력을 처리하고 STT 프로세서에 데이터를 전달
"""

import queue
import threading
from typing import Optional, Callable
import numpy as np
import pyaudio
from PyQt5.QtCore import QThread, pyqtSignal


class AudioRecorder(QThread):
    """
    실시간 오디오 녹음을 처리하는 클래스
    PyQt5 QThread를 상속받아 GUI와의 비동기 처리를 지원
    """
    
    # 시그널 정의
    audio_data_ready = pyqtSignal(np.ndarray)  # 오디오 데이터가 준비되었을 때
    recording_started = pyqtSignal()           # 녹음이 시작되었을 때
    recording_stopped = pyqtSignal()           # 녹음이 중지되었을 때
    error_occurred = pyqtSignal(str)           # 오류가 발생했을 때
    volume_level_changed = pyqtSignal(float)   # 음량 레벨이 변경되었을 때

    def __init__(self, 
                 sample_rate: int = 16000,
                 channels: int = 1,
                 chunk_size: int = 1024,
                 audio_format: int = pyaudio.paInt16):
        """
        AudioRecorder 초기화
        
        Args:
            sample_rate: 샘플링 레이트 (Hz)
            channels: 오디오 채널 수
            chunk_size: 오디오 청크 크기
            audio_format: 오디오 포맷
        """
        super().__init__()
        
        # 오디오 설정
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.audio_format = audio_format
        
        # 녹음 상태
        self.is_recording = False
        self.is_paused = False
        
        # PyAudio 관련 객체
        self.pyaudio_instance: Optional[pyaudio.PyAudio] = None
        self.audio_stream: Optional[pyaudio.Stream] = None
        self.audio_queue = queue.Queue()
        
        # 콜백 함수
        self.audio_callback: Optional[Callable[[np.ndarray], None]] = None
        
        # 음량 모니터링
        self.volume_threshold = 0.01  # 음성 감지 임계값
        self.silence_duration = 0.0   # 무음 지속 시간
        self.max_silence_duration = 3.0  # 최대 무음 지속 시간 (초)

    def set_audio_callback(self, callback: Callable[[np.ndarray], None]):
        """오디오 데이터 콜백 함수 설정"""
        self.audio_callback = callback

    def start_recording(self):
        """녹음 시작"""
        if self.is_recording:
            return
        
        try:
            self._initialize_audio_stream()
            self.is_recording = True
            self.start()  # QThread 시작
            self.recording_started.emit()
            
        except Exception as e:
            self.error_occurred.emit(f"녹음 시작 오류: {str(e)}")

    def stop_recording(self):
        """녹음 중지"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        self.wait()  # 스레드 종료 대기
        self._cleanup_audio_stream()
        self.recording_stopped.emit()

    def pause_recording(self):
        """녹음 일시 정지"""
        self.is_paused = True

    def resume_recording(self):
        """녹음 재개"""
        self.is_paused = False

    def _initialize_audio_stream(self):
        """오디오 스트림 초기화"""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            self.audio_stream = self.pyaudio_instance.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._pyaudio_callback,
                start=True
            )
            
        except Exception as e:
            self._cleanup_audio_stream()
            raise Exception(f"오디오 스트림 초기화 실패: {str(e)}")

    def _cleanup_audio_stream(self):
        """오디오 스트림 정리"""
        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except:
                pass
            self.audio_stream = None
            
        if self.pyaudio_instance:
            try:
                self.pyaudio_instance.terminate()
            except:
                pass
            self.pyaudio_instance = None

    def _pyaudio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio 콜백 함수"""
        if status:
            self.error_occurred.emit(f"오디오 스트림 상태 오류: {status}")
            
        if not self.is_paused:
            self.audio_queue.put(in_data)
            
        return (None, pyaudio.paContinue)

    def run(self):
        """스레드 메인 루프"""
        while self.is_recording:
            try:
                # 큐에서 오디오 데이터 가져오기 (100ms 타임아웃)
                raw_data = self.audio_queue.get(timeout=0.1)
                
                # numpy 배열로 변환
                audio_data = self._convert_to_numpy(raw_data)
                
                # 음량 레벨 계산 및 무음 감지
                volume_level = self._calculate_volume_level(audio_data)
                self.volume_level_changed.emit(volume_level)
                
                # 무음 감지
                if volume_level < self.volume_threshold:
                    self.silence_duration += (self.chunk_size / self.sample_rate)
                else:
                    self.silence_duration = 0.0
                
                # 데이터 방출
                self.audio_data_ready.emit(audio_data)
                
                # 콜백 함수 호출
                if self.audio_callback:
                    self.audio_callback(audio_data)
                    
            except queue.Empty:
                continue
            except Exception as e:
                self.error_occurred.emit(f"오디오 처리 오류: {str(e)}")

    def _convert_to_numpy(self, raw_data: bytes) -> np.ndarray:
        """원시 오디오 데이터를 numpy 배열로 변환"""
        audio_data = np.frombuffer(raw_data, dtype=np.int16)
        
        # 정규화 (-1.0 ~ 1.0)
        normalized_data = audio_data.astype(np.float32) / 32768.0
        
        return normalized_data

    def _calculate_volume_level(self, audio_data: np.ndarray) -> float:
        """음량 레벨 계산 (RMS)"""
        rms = np.sqrt(np.mean(np.square(audio_data)))
        return float(rms)

    def get_audio_info(self) -> dict:
        """현재 오디오 설정 정보 반환"""
        return {
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "chunk_size": self.chunk_size,
            "is_recording": self.is_recording,
            "is_paused": self.is_paused,
            "silence_duration": self.silence_duration
        }

    def set_volume_threshold(self, threshold: float):
        """음성 감지 임계값 설정"""
        self.volume_threshold = max(0.0, min(1.0, threshold))

    def set_max_silence_duration(self, duration: float):
        """최대 무음 지속 시간 설정"""
        self.max_silence_duration = max(0.5, duration)

    def is_voice_detected(self) -> bool:
        """현재 음성이 감지되는지 확인"""
        return self.silence_duration < self.max_silence_duration

    def __del__(self):
        """소멸자 - 리소스 정리"""
        if self.is_recording:
            self.stop_recording()
        self._cleanup_audio_stream()