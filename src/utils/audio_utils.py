"""
Audio Utilities - 오디오 유틸리티 함수들
오디오 장치 관리, 포맷 변환, 테스트 등을 담당
"""

import pyaudio
import numpy as np
import wave
import threading
import time
from typing import Dict, List, Optional, Tuple, Any


class AudioUtils:
    """오디오 유틸리티 클래스"""
    
    def __init__(self):
        """AudioUtils 초기화"""
        self.audio = None
        self._initialize_audio()
    
    def _initialize_audio(self):
        """PyAudio 초기화"""
        try:
            self.audio = pyaudio.PyAudio()
        except Exception as e:
            print(f"PyAudio 초기화 실패: {e}")
            self.audio = None
    
    def get_audio_device_info(self) -> Dict[str, Any]:
        """오디오 장치 정보 반환"""
        if not self.audio:
            return {
                'input_device': 'N/A',
                'output_device': 'N/A', 
                'sample_rate': 'N/A',
                'channels': 'N/A'
            }
        
        try:
            # 기본 입력/출력 장치 정보
            default_input = self.audio.get_default_input_device_info()
            default_output = self.audio.get_default_output_device_info()
            
            return {
                'input_device': default_input.get('name', 'Unknown'),
                'output_device': default_output.get('name', 'Unknown'),
                'sample_rate': default_input.get('defaultSampleRate', 44100),
                'channels': default_input.get('maxInputChannels', 1)
            }
        except Exception as e:
            print(f"오디오 장치 정보 조회 실패: {e}")
            return {
                'input_device': 'Error',
                'output_device': 'Error',
                'sample_rate': 44100,
                'channels': 1
            }
    
    def list_input_devices(self) -> List[Dict[str, Any]]:
        """사용 가능한 입력 장치 목록 반환"""
        if not self.audio:
            return []
        
        devices = []
        try:
            device_count = self.audio.get_device_count()
            for i in range(device_count):
                device_info = self.audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    devices.append({
                        'index': i,
                        'name': device_info['name'],
                        'channels': device_info['maxInputChannels'],
                        'sample_rate': device_info['defaultSampleRate']
                    })
        except Exception as e:
            print(f"입력 장치 목록 조회 실패: {e}")
        
        return devices
    
    def list_output_devices(self) -> List[Dict[str, Any]]:
        """사용 가능한 출력 장치 목록 반환"""
        if not self.audio:
            return []
        
        devices = []
        try:
            device_count = self.audio.get_device_count()
            for i in range(device_count):
                device_info = self.audio.get_device_info_by_index(i)
                if device_info['maxOutputChannels'] > 0:
                    devices.append({
                        'index': i,
                        'name': device_info['name'],
                        'channels': device_info['maxOutputChannels'],
                        'sample_rate': device_info['defaultSampleRate']
                    })
        except Exception as e:
            print(f"출력 장치 목록 조회 실패: {e}")
        
        return devices
    
    def test_audio_device(self, device_index: Optional[int] = None, 
                         duration: float = 1.0, sample_rate: int = 44100) -> bool:
        """오디오 장치 테스트"""
        if not self.audio:
            return False
        
        try:
            # 테스트 스트림 생성
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024
            )
            
            # 짧은 시간 동안 오디오 읽기
            data = []
            frames_to_read = int(sample_rate / 1024 * duration)
            
            for _ in range(frames_to_read):
                audio_data = stream.read(1024, exception_on_overflow=False)
                data.append(audio_data)
            
            stream.stop_stream()
            stream.close()
            
            # 데이터가 있는지 확인
            audio_array = np.frombuffer(b''.join(data), dtype=np.int16)
            max_amplitude = np.max(np.abs(audio_array))
            
            # 최소한의 신호가 있는지 확인 (완전한 무음이 아닌지)
            return max_amplitude > 10
            
        except Exception as e:
            print(f"오디오 장치 테스트 실패: {e}")
            return False
    
    def get_supported_sample_rates(self, device_index: Optional[int] = None) -> List[int]:
        """지원하는 샘플링 레이트 목록 반환"""
        if not self.audio:
            return [44100]  # 기본값
        
        standard_rates = [8000, 11025, 16000, 22050, 44100, 48000, 88200, 96000]
        supported_rates = []
        
        for rate in standard_rates:
            try:
                # 테스트 스트림 생성해보기
                stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=1024
                )
                stream.close()
                supported_rates.append(rate)
            except:
                continue
        
        return supported_rates if supported_rates else [44100]
    
    def convert_audio_format(self, audio_data: np.ndarray, 
                           from_rate: int, to_rate: int,
                           from_dtype: np.dtype = np.int16,
                           to_dtype: np.dtype = np.float32) -> np.ndarray:
        """오디오 포맷 변환"""
        try:
            # 데이터 타입 변환
            if from_dtype != to_dtype:
                if from_dtype == np.int16 and to_dtype == np.float32:
                    audio_data = audio_data.astype(np.float32) / 32768.0
                elif from_dtype == np.float32 and to_dtype == np.int16:
                    audio_data = (audio_data * 32768.0).astype(np.int16)
            
            # 샘플링 레이트 변환 (간단한 리샘플링)
            if from_rate != to_rate:
                # scipy가 있다면 더 정확한 리샘플링 가능
                try:
                    from scipy import signal
                    audio_data = signal.resample(
                        audio_data, int(len(audio_data) * to_rate / from_rate)
                    )
                except ImportError:
                    # scipy가 없다면 간단한 선형 보간
                    ratio = to_rate / from_rate
                    new_length = int(len(audio_data) * ratio)
                    old_indices = np.linspace(0, len(audio_data) - 1, new_length)
                    audio_data = np.interp(old_indices, np.arange(len(audio_data)), audio_data)
            
            return audio_data
            
        except Exception as e:
            print(f"오디오 포맷 변환 실패: {e}")
            return audio_data
    
    def calculate_rms(self, audio_data: np.ndarray) -> float:
        """RMS (Root Mean Square) 계산"""
        try:
            return float(np.sqrt(np.mean(audio_data ** 2)))
        except:
            return 0.0
    
    def calculate_volume_level(self, audio_data: np.ndarray, 
                              max_value: Optional[float] = None) -> float:
        """볼륨 레벨 계산 (0.0 ~ 1.0)"""
        try:
            if max_value is None:
                if audio_data.dtype == np.int16:
                    max_value = 32768.0
                else:
                    max_value = 1.0
            
            rms = self.calculate_rms(audio_data)
            return min(rms / max_value, 1.0)
            
        except:
            return 0.0
    
    def apply_noise_gate(self, audio_data: np.ndarray, 
                        threshold: float = 0.01, 
                        fade_samples: int = 100) -> np.ndarray:
        """노이즈 게이트 적용"""
        try:
            # RMS 기반 볼륨 계산
            volume = self.calculate_volume_level(audio_data)
            
            if volume < threshold:
                # 볼륨이 임계값 이하면 페이드아웃
                result = audio_data.copy()
                if len(result) > fade_samples:
                    fade = np.linspace(1, 0, fade_samples)
                    result[-fade_samples:] *= fade
                else:
                    fade = np.linspace(1, 0, len(result))
                    result *= fade
                return result
            else:
                return audio_data
                
        except:
            return audio_data
    
    def detect_silence(self, audio_data: np.ndarray, 
                      threshold: float = 0.01,
                      min_silence_duration: float = 0.5,
                      sample_rate: int = 16000) -> List[Tuple[int, int]]:
        """무음 구간 감지"""
        try:
            # 볼륨 계산
            volume = self.calculate_volume_level(audio_data)
            
            # 무음 임계값 이하인 구간 찾기
            is_silence = volume < threshold
            
            # 연속된 무음 구간 찾기
            min_silence_samples = int(min_silence_duration * sample_rate)
            silence_regions = []
            
            in_silence = False
            silence_start = 0
            
            for i, silent in enumerate([is_silence]):  # 전체가 무음인지만 확인
                if silent and not in_silence:
                    in_silence = True
                    silence_start = 0
                elif not silent and in_silence:
                    silence_length = len(audio_data) - silence_start
                    if silence_length >= min_silence_samples:
                        silence_regions.append((silence_start, len(audio_data)))
                    in_silence = False
            
            # 마지막 구간이 무음이면 추가
            if in_silence:
                silence_length = len(audio_data) - silence_start
                if silence_length >= min_silence_samples:
                    silence_regions.append((silence_start, len(audio_data)))
            
            return silence_regions
            
        except:
            return []
    
    def save_audio_to_wav(self, audio_data: np.ndarray, 
                         filename: str, 
                         sample_rate: int = 16000,
                         channels: int = 1) -> bool:
        """오디오 데이터를 WAV 파일로 저장"""
        try:
            # int16으로 변환
            if audio_data.dtype == np.float32:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data.tobytes())
            
            return True
            
        except Exception as e:
            print(f"WAV 파일 저장 실패: {e}")
            return False
    
    def load_audio_from_wav(self, filename: str) -> Tuple[Optional[np.ndarray], int]:
        """WAV 파일에서 오디오 데이터 로드"""
        try:
            with wave.open(filename, 'rb') as wav_file:
                frames = wav_file.readframes(-1)
                sample_rate = wav_file.getframerate()
                audio_data = np.frombuffer(frames, dtype=np.int16)
                
                # float32로 정규화
                audio_data = audio_data.astype(np.float32) / 32768.0
                
                return audio_data, sample_rate
                
        except Exception as e:
            print(f"WAV 파일 로드 실패: {e}")
            return None, 0
    
    def cleanup(self):
        """리소스 정리"""
        if self.audio:
            try:
                self.audio.terminate()
            except:
                pass
            self.audio = None


# 싱글톤 인스턴스
_audio_utils_instance = None

def get_audio_utils() -> AudioUtils:
    """AudioUtils 싱글톤 인스턴스 반환"""
    global _audio_utils_instance
    if _audio_utils_instance is None:
        _audio_utils_instance = AudioUtils()
    return _audio_utils_instance