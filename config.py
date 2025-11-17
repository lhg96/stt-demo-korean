"""
STT Demo 설정 관리
애플리케이션의 모든 설정을 중앙에서 관리
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

class STTConfig:
    """STT 애플리케이션 설정 관리 클래스"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.default_config = {
            # 오디오 설정
            "audio": {
                "sample_rate": 16000,
                "chunk_size": 1024,
                "channels": 1,
                "format": "int16",
                "buffer_seconds": 3.0,
                "overlap_ratio": 0.5
            },
            
            # Whisper 모델 설정
            "whisper": {
                "default_model": "base",
                "available_models": ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
                "language": "ko",
                "device": "auto",  # auto, cpu, cuda, mps
                "fp16": True
            },
            
            # Vosk 모델 설정
            "vosk": {
                "model_path": "./vosk-model-small-ko-0.22",
                "alternative_paths": [
                    "./models/vosk-model-small-ko-0.22",
                    "~/models/vosk-model-small-ko-0.22"
                ]
            },
            
            # GUI 설정
            "gui": {
                "window_width": 1000,
                "window_height": 700,
                "theme": "dark",
                "font_size": 14,
                "auto_save": True,
                "save_directory": "./results",
                "visualization_update_ms": 100
            },
            
            # 성능 설정
            "performance": {
                "max_audio_buffer_mb": 50,
                "processing_timeout_seconds": 10,
                "enable_gpu_acceleration": True,
                "thread_pool_size": 2
            },
            
            # 로깅 설정
            "logging": {
                "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
                "log_file": "stt_demo.log",
                "max_log_size_mb": 10,
                "backup_count": 5
            }
        }
        
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """설정 파일을 로드하거나 기본 설정 생성"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # 기본 설정과 병합 (새로운 설정 항목 추가)
                return self._merge_config(self.default_config, loaded_config)
            except Exception as e:
                print(f"설정 파일 로드 실패: {e}. 기본 설정을 사용합니다.")
                return self.default_config.copy()
        else:
            # 기본 설정 파일 생성
            self.save_config(self.default_config)
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any] = None):
        """설정을 파일에 저장"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"설정 파일 저장 실패: {e}")
    
    def get(self, key_path: str, default=None):
        """점 표기법으로 설정값 가져오기 (예: 'audio.sample_rate')"""
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except KeyError:
            return default
    
    def set(self, key_path: str, value: Any):
        """점 표기법으로 설정값 설정하기"""
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        self.save_config()
    
    def _merge_config(self, default: Dict, loaded: Dict) -> Dict:
        """기본 설정과 로드된 설정을 병합"""
        merged = default.copy()
        
        for key, value in loaded.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_config(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def get_whisper_models(self):
        """사용 가능한 Whisper 모델 목록 반환"""
        return self.get('whisper.available_models', [])
    
    def get_audio_config(self):
        """오디오 설정 반환"""
        return self.get('audio', {})
    
    def get_gui_config(self):
        """GUI 설정 반환"""
        return self.get('gui', {})
    
    def get_vosk_model_path(self):
        """Vosk 모델 경로 반환 (존재하는 경로 찾기)"""
        main_path = self.get('vosk.model_path')
        if os.path.exists(main_path):
            return main_path
        
        # 대안 경로들 확인
        alt_paths = self.get('vosk.alternative_paths', [])
        for path in alt_paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                return expanded_path
        
        return main_path  # 기본 경로 반환 (존재하지 않아도)
    
    def validate_config(self):
        """설정 유효성 검사"""
        errors = []
        
        # 오디오 설정 검사
        sample_rate = self.get('audio.sample_rate')
        if sample_rate not in [8000, 16000, 22050, 44100, 48000]:
            errors.append(f"지원되지 않는 샘플레이트: {sample_rate}")
        
        # Whisper 모델 검사
        default_model = self.get('whisper.default_model')
        available_models = self.get('whisper.available_models')
        if default_model not in available_models:
            errors.append(f"기본 Whisper 모델이 사용 가능한 모델 목록에 없음: {default_model}")
        
        # Vosk 모델 경로 검사
        vosk_path = self.get_vosk_model_path()
        if not os.path.exists(vosk_path):
            errors.append(f"Vosk 모델 경로가 존재하지 않음: {vosk_path}")
        
        return errors
    
    def reset_to_defaults(self):
        """설정을 기본값으로 초기화"""
        self.config = self.default_config.copy()
        self.save_config()


# 전역 설정 인스턴스
config = STTConfig()

def get_config() -> STTConfig:
    """전역 설정 인스턴스 반환"""
    return config