"""
Config Manager - 설정 관리자
애플리케이션 설정을 로드, 저장, 관리하는 모듈
"""

import json
import os
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from ..core.stt_processor import STTConfig, STTModelType

@dataclass
class AppConfig:
    """애플리케이션 설정"""
    # GUI 설정
    window_width: int = 1200
    window_height: int = 800
    theme: str = "dark"
    language: str = "ko"
    
    # 파일 설정
    output_directory: str = "./output"
    auto_save: bool = True
    save_format: str = "txt"
    
    # 로깅 설정
    log_level: str = "INFO"
    log_file: str = "stt_demo.log"

class ConfigManager:
    """설정 관리자 클래스"""
    
    DEFAULT_CONFIG_FILE = "config.json"
    
    def __init__(self, config_file: Optional[str] = None):
        """
        ConfigManager 초기화
        
        Args:
            config_file: 설정 파일 경로 (기본값: config.json)
        """
        self.config_file = config_file or self.DEFAULT_CONFIG_FILE
        self.app_config = AppConfig()
        self.stt_config = STTConfig()
        self.custom_settings: Dict[str, Any] = {}
        
        self.load_config()
    
    def load_config(self) -> bool:
        """
        설정 파일에서 설정을 로드
        
        Returns:
            bool: 로드 성공 여부
        """
        try:
            if not os.path.exists(self.config_file):
                # 기본 설정으로 새 파일 생성
                self.save_config()
                return True
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 앱 설정 로드
            if 'app_config' in data:
                app_data = data['app_config']
                self.app_config = AppConfig(**app_data)
            
            # STT 설정 로드
            if 'stt_config' in data:
                stt_data = data['stt_config']
                
                # Enum 타입 변환
                if 'model_type' in stt_data:
                    model_type_str = stt_data['model_type']
                    if isinstance(model_type_str, str):
                        try:
                            stt_data['model_type'] = STTModelType(model_type_str)
                        except ValueError:
                            stt_data['model_type'] = STTModelType.WHISPER
                
                self.stt_config = STTConfig(**stt_data)
            
            # 사용자 정의 설정 로드
            if 'custom_settings' in data:
                self.custom_settings = data['custom_settings']
            
            return True
            
        except Exception as e:
            print(f"설정 로드 실패: {e}")
            # 기본 설정으로 복원
            self.app_config = AppConfig()
            self.stt_config = STTConfig()
            self.custom_settings = {}
            return False
    
    def save_config(self) -> bool:
        """
        현재 설정을 파일에 저장
        
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 설정 딕셔너리 구성
            config_data = {
                'app_config': asdict(self.app_config),
                'stt_config': self._stt_config_to_dict(),
                'custom_settings': self.custom_settings,
                'last_updated': time.time()
            }
            
            # 파일에 저장
            os.makedirs(os.path.dirname(os.path.abspath(self.config_file)), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"설정 저장 실패: {e}")
            return False
    
    def _stt_config_to_dict(self) -> Dict[str, Any]:
        """STTConfig를 딕셔너리로 변환"""
        config_dict = asdict(self.stt_config)
        
        # Enum을 문자열로 변환
        if 'model_type' in config_dict:
            config_dict['model_type'] = config_dict['model_type'].value
        
        return config_dict
    
    def get_app_config(self) -> AppConfig:
        """앱 설정 반환"""
        return self.app_config
    
    def set_app_config(self, config: AppConfig):
        """앱 설정 설정"""
        self.app_config = config
    
    def get_stt_config(self) -> STTConfig:
        """STT 설정 반환"""
        return self.stt_config
    
    def set_stt_config(self, config: STTConfig):
        """STT 설정 설정"""
        self.stt_config = config
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        사용자 정의 설정 값 반환
        
        Args:
            key: 설정 키
            default: 기본값
            
        Returns:
            설정 값
        """
        return self.custom_settings.get(key, default)
    
    def set_setting(self, key: str, value: Any):
        """
        사용자 정의 설정 값 설정
        
        Args:
            key: 설정 키
            value: 설정 값
        """
        self.custom_settings[key] = value
    
    def get_output_directory(self) -> str:
        """출력 디렉토리 경로 반환"""
        return os.path.abspath(self.app_config.output_directory)
    
    def ensure_output_directory(self) -> bool:
        """출력 디렉토리 생성 (없는 경우)"""
        try:
            output_dir = self.get_output_directory()
            os.makedirs(output_dir, exist_ok=True)
            return True
        except Exception as e:
            print(f"출력 디렉토리 생성 실패: {e}")
            return False
    
    def reset_to_defaults(self):
        """기본 설정으로 리셋"""
        self.app_config = AppConfig()
        self.stt_config = STTConfig()
        self.custom_settings = {}
    
    def export_config(self, file_path: str) -> bool:
        """
        설정을 지정된 파일로 내보내기
        
        Args:
            file_path: 내보낼 파일 경로
            
        Returns:
            bool: 성공 여부
        """
        try:
            config_data = {
                'app_config': asdict(self.app_config),
                'stt_config': self._stt_config_to_dict(),
                'custom_settings': self.custom_settings,
                'exported_at': time.time()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"설정 내보내기 실패: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """
        지정된 파일에서 설정 가져오기
        
        Args:
            file_path: 가져올 파일 경로
            
        Returns:
            bool: 성공 여부
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 임시로 현재 설정 백업
            backup_app = self.app_config
            backup_stt = self.stt_config
            backup_custom = self.custom_settings.copy()
            
            try:
                # 새 설정 적용
                if 'app_config' in data:
                    self.app_config = AppConfig(**data['app_config'])
                
                if 'stt_config' in data:
                    stt_data = data['stt_config']
                    if 'model_type' in stt_data and isinstance(stt_data['model_type'], str):
                        stt_data['model_type'] = STTModelType(stt_data['model_type'])
                    self.stt_config = STTConfig(**stt_data)
                
                if 'custom_settings' in data:
                    self.custom_settings = data['custom_settings']
                
                return True
                
            except Exception:
                # 오류 시 백업으로 복원
                self.app_config = backup_app
                self.stt_config = backup_stt
                self.custom_settings = backup_custom
                raise
                
        except Exception as e:
            print(f"설정 가져오기 실패: {e}")
            return False