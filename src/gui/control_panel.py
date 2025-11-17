"""
Control Panel Widget - 컨트롤 패널 위젯
STT 설정, 녹음 제어, 결과 표시 등을 담당
"""

import os
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QPushButton, QComboBox, QTextEdit, QCheckBox, QSlider,
    QProgressBar, QFileDialog, QMessageBox, QSpinBox,
    QDoubleSpinBox, QTabWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from ..core.stt_processor import STTModelType, STTConfig, STTResult
from ..utils.config_manager import ConfigManager


class ControlPanelWidget(QWidget):
    """컨트롤 패널 위젯 클래스"""
    
    # 시그널 정의
    start_recording_requested = pyqtSignal()
    stop_recording_requested = pyqtSignal()
    pause_recording_requested = pyqtSignal()
    resume_recording_requested = pyqtSignal()
    config_changed = pyqtSignal(STTConfig)
    save_results_requested = pyqtSignal(str)  # 파일 경로
    clear_results_requested = pyqtSignal()
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        ControlPanelWidget 초기화
        
        Args:
            config_manager: 설정 관리자
            parent: 부모 위젯
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.current_config = self.config_manager.get_stt_config()
        self.is_recording = False
        self.is_paused = False
        self.processing_stats = {
            "total_processed": 0,
            "avg_processing_time": 0.0,
            "total_confidence": 0.0
        }
        
        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout()
        
        # 탭 위젯 생성
        tab_widget = QTabWidget()
        
        # 모델 설정 탭
        model_tab = self.create_model_tab()
        tab_widget.addTab(model_tab, "🤖 모델 설정")
        
        # 오디오 설정 탭  
        audio_tab = self.create_audio_tab()
        tab_widget.addTab(audio_tab, "🎵 오디오 설정")
        
        # 처리 설정 탭
        processing_tab = self.create_processing_tab()
        tab_widget.addTab(processing_tab, "⚙️ 처리 설정")
        
        # 컨트롤 그룹
        control_group = self.create_control_group()
        
        # 결과 그룹
        result_group = self.create_result_group()
        
        # 통계 그룹
        stats_group = self.create_stats_group()
        
        # 레이아웃 구성
        layout.addWidget(tab_widget)
        layout.addWidget(control_group)
        layout.addWidget(result_group)
        layout.addWidget(stats_group)
        
        self.setLayout(layout)

    def create_model_tab(self) -> QWidget:
        """모델 설정 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 모델 타입 선택
        model_type_group = QGroupBox("모델 타입")
        model_type_layout = QVBoxLayout()
        
        self.model_type_combo = QComboBox()
        
        # 사용 가능한 모델 타입 추가
        try:
            import whisper
            self.model_type_combo.addItem("Whisper", STTModelType.WHISPER)
        except ImportError:
            pass
            
        try:
            from vosk import Model
            self.model_type_combo.addItem("Vosk", STTModelType.VOSK)
        except ImportError:
            pass
        
        if self.model_type_combo.count() == 0:
            self.model_type_combo.addItem("사용 가능한 모델 없음", None)
        
        self.model_type_combo.currentIndexChanged.connect(self.on_model_type_changed)
        
        model_type_layout.addWidget(QLabel("모델 타입:"))
        model_type_layout.addWidget(self.model_type_combo)
        model_type_group.setLayout(model_type_layout)
        
        # Whisper 모델 설정
        whisper_group = QGroupBox("Whisper 모델 설정")
        whisper_layout = QVBoxLayout()
        
        self.whisper_model_combo = QComboBox()
        whisper_models = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
        self.whisper_model_combo.addItems(whisper_models)
        self.whisper_model_combo.currentTextChanged.connect(self.on_config_changed)
        
        self.whisper_device_combo = QComboBox()
        self.whisper_device_combo.addItems(["auto", "cpu", "cuda", "mps"])
        self.whisper_device_combo.currentTextChanged.connect(self.on_config_changed)
        
        whisper_layout.addWidget(QLabel("모델 크기:"))
        whisper_layout.addWidget(self.whisper_model_combo)
        whisper_layout.addWidget(QLabel("처리 디바이스:"))
        whisper_layout.addWidget(self.whisper_device_combo)
        whisper_group.setLayout(whisper_layout)
        
        # Vosk 모델 설정
        vosk_group = QGroupBox("Vosk 모델 설정")
        vosk_layout = QVBoxLayout()
        
        self.vosk_model_path_label = QLabel("모델 경로: 자동 검색")
        self.vosk_browse_button = QPushButton("모델 경로 선택...")
        self.vosk_browse_button.clicked.connect(self.browse_vosk_model)
        
        vosk_layout.addWidget(self.vosk_model_path_label)
        vosk_layout.addWidget(self.vosk_browse_button)
        vosk_group.setLayout(vosk_layout)
        
        # 언어 설정
        language_group = QGroupBox("언어 설정")
        language_layout = QVBoxLayout()
        
        self.language_combo = QComboBox()
        languages = [
            ("한국어", "ko"),
            ("English", "en"),  
            ("日本語", "ja"),
            ("中文", "zh"),
            ("Español", "es"),
            ("Français", "fr"),
            ("Deutsch", "de"),
            ("Русский", "ru")
        ]
        
        for name, code in languages:
            self.language_combo.addItem(name, code)
        
        self.language_combo.currentIndexChanged.connect(self.on_config_changed)
        
        language_layout.addWidget(QLabel("인식 언어:"))
        language_layout.addWidget(self.language_combo)
        language_group.setLayout(language_layout)
        
        # 레이아웃 구성
        layout.addWidget(model_type_group)
        layout.addWidget(whisper_group)
        layout.addWidget(vosk_group)
        layout.addWidget(language_group)
        layout.addStretch()
        
        tab.setLayout(layout)
        return tab

    def create_audio_tab(self) -> QWidget:
        """오디오 설정 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 샘플링 레이트
        sample_rate_group = QGroupBox("샘플링 레이트")
        sample_rate_layout = QVBoxLayout()
        
        self.sample_rate_combo = QComboBox()
        sample_rates = ["8000", "16000", "22050", "44100", "48000"]
        self.sample_rate_combo.addItems(sample_rates)
        self.sample_rate_combo.setCurrentText("16000")
        self.sample_rate_combo.currentTextChanged.connect(self.on_config_changed)
        
        sample_rate_layout.addWidget(QLabel("샘플링 레이트 (Hz):"))
        sample_rate_layout.addWidget(self.sample_rate_combo)
        sample_rate_group.setLayout(sample_rate_layout)
        
        # 청크 설정
        chunk_group = QGroupBox("오디오 청크 설정")
        chunk_layout = QVBoxLayout()
        
        self.chunk_duration_spin = QDoubleSpinBox()
        self.chunk_duration_spin.setRange(0.5, 10.0)
        self.chunk_duration_spin.setValue(3.0)
        self.chunk_duration_spin.setSuffix(" 초")
        self.chunk_duration_spin.valueChanged.connect(self.on_config_changed)
        
        self.overlap_spin = QDoubleSpinBox()
        self.overlap_spin.setRange(0.0, 0.9)
        self.overlap_spin.setValue(0.5)
        self.overlap_spin.setSingleStep(0.1)
        self.overlap_spin.valueChanged.connect(self.on_config_changed)
        
        chunk_layout.addWidget(QLabel("청크 지속시간:"))
        chunk_layout.addWidget(self.chunk_duration_spin)
        chunk_layout.addWidget(QLabel("오버랩 비율:"))
        chunk_layout.addWidget(self.overlap_spin)
        chunk_group.setLayout(chunk_layout)
        
        # 음량 설정
        volume_group = QGroupBox("음량 설정")
        volume_layout = QVBoxLayout()
        
        self.volume_threshold_slider = QSlider(Qt.Horizontal)
        self.volume_threshold_slider.setRange(0, 100)
        self.volume_threshold_slider.setValue(10)
        self.volume_threshold_label = QLabel("음성 감지 임계값: 10%")
        self.volume_threshold_slider.valueChanged.connect(self.on_volume_threshold_changed)
        
        volume_layout.addWidget(self.volume_threshold_label)
        volume_layout.addWidget(self.volume_threshold_slider)
        volume_group.setLayout(volume_layout)
        
        # 레이아웃 구성
        layout.addWidget(sample_rate_group)
        layout.addWidget(chunk_group)
        layout.addWidget(volume_group)
        layout.addStretch()
        
        tab.setLayout(layout)
        return tab

    def create_processing_tab(self) -> QWidget:
        """처리 설정 탭 생성"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 신뢰도 설정
        confidence_group = QGroupBox("신뢰도 설정")
        confidence_layout = QVBoxLayout()
        
        self.confidence_threshold_spin = QDoubleSpinBox()
        self.confidence_threshold_spin.setRange(0.0, 1.0)
        self.confidence_threshold_spin.setValue(0.5)
        self.confidence_threshold_spin.setSingleStep(0.1)
        self.confidence_threshold_spin.valueChanged.connect(self.on_config_changed)
        
        confidence_layout.addWidget(QLabel("최소 신뢰도 임계값:"))
        confidence_layout.addWidget(self.confidence_threshold_spin)
        confidence_group.setLayout(confidence_layout)
        
        # 처리 옵션
        processing_group = QGroupBox("처리 옵션")
        processing_layout = QVBoxLayout()
        
        self.preprocessing_check = QCheckBox("오디오 전처리 활성화")
        self.preprocessing_check.setChecked(True)
        self.preprocessing_check.stateChanged.connect(self.on_config_changed)
        
        self.postprocessing_check = QCheckBox("텍스트 후처리 활성화")
        self.postprocessing_check.setChecked(True)
        self.postprocessing_check.stateChanged.connect(self.on_config_changed)
        
        self.realtime_check = QCheckBox("실시간 처리 모드")
        self.realtime_check.setChecked(True)
        self.realtime_check.stateChanged.connect(self.on_config_changed)
        
        processing_layout.addWidget(self.preprocessing_check)
        processing_layout.addWidget(self.postprocessing_check)
        processing_layout.addWidget(self.realtime_check)
        processing_group.setLayout(processing_layout)
        
        # 성능 설정
        performance_group = QGroupBox("성능 설정")
        performance_layout = QVBoxLayout()
        
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 8)
        self.max_workers_spin.setValue(2)
        self.max_workers_spin.valueChanged.connect(self.on_config_changed)
        
        self.buffer_size_spin = QSpinBox()
        self.buffer_size_spin.setRange(1024, 8192)
        self.buffer_size_spin.setValue(2048)
        self.buffer_size_spin.setSuffix(" 샘플")
        self.buffer_size_spin.valueChanged.connect(self.on_config_changed)
        
        performance_layout.addWidget(QLabel("최대 워커 스레드:"))
        performance_layout.addWidget(self.max_workers_spin)
        performance_layout.addWidget(QLabel("버퍼 크기:"))
        performance_layout.addWidget(self.buffer_size_spin)
        performance_group.setLayout(performance_layout)
        
        # 레이아웃 구성
        layout.addWidget(confidence_group)
        layout.addWidget(processing_group)
        layout.addWidget(performance_group)
        layout.addStretch()
        
        tab.setLayout(layout)
        return tab

    def create_control_group(self) -> QGroupBox:
        """컨트롤 그룹 생성"""
        group = QGroupBox("녹음 컨트롤")
        layout = QVBoxLayout()
        
        # 메인 컨트롤 버튼들
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("🎤 녹음 시작")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px;
                font-size: 14px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.start_button.clicked.connect(self.on_start_recording)
        
        self.pause_button = QPushButton("⏸️ 일시정지")
        self.pause_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 12px;
                font-size: 14px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.on_pause_resume_recording)
        
        self.stop_button = QPushButton("⏹️ 녹음 중지")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 12px;
                font-size: 14px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.on_stop_recording)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        
        # 상태 표시
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("상태: 대기 중")
        self.status_label.setStyleSheet("font-weight: bold; color: #666;")
        
        self.volume_label = QLabel("음량: -")
        self.volume_progress = QProgressBar()
        self.volume_progress.setRange(0, 100)
        self.volume_progress.setValue(0)
        
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.volume_label)
        status_layout.addWidget(self.volume_progress)
        
        layout.addLayout(button_layout)
        layout.addLayout(status_layout)
        group.setLayout(layout)
        
        return group

    def create_result_group(self) -> QGroupBox:
        """결과 그룹 생성"""
        group = QGroupBox("인식 결과")
        layout = QVBoxLayout()
        
        # 결과 텍스트
        self.result_text = QTextEdit()
        self.result_text.setMinimumHeight(150)
        self.result_text.setPlaceholderText("인식된 텍스트가 여기에 표시됩니다...")
        self.result_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Malgun Gothic', Arial, sans-serif;
                font-size: 12px;
                line-height: 1.4;
                border: 1px solid #555;
                background-color: #1e1e1e;
                color: #ffffff;
                padding: 8px;
            }
        """)
        
        # 결과 컨트롤 버튼들
        result_button_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("텍스트 지우기")
        self.clear_button.clicked.connect(self.on_clear_results)
        
        self.save_button = QPushButton("결과 저장")
        self.save_button.clicked.connect(self.on_save_results)
        
        self.copy_button = QPushButton("클립보드 복사")
        self.copy_button.clicked.connect(self.on_copy_results)
        
        result_button_layout.addWidget(self.clear_button)
        result_button_layout.addWidget(self.save_button)
        result_button_layout.addWidget(self.copy_button)
        result_button_layout.addStretch()
        
        layout.addWidget(self.result_text)
        layout.addLayout(result_button_layout)
        group.setLayout(layout)
        
        return group

    def create_stats_group(self) -> QGroupBox:
        """통계 그룹 생성"""
        group = QGroupBox("처리 통계")
        layout = QVBoxLayout()
        
        stats_layout = QHBoxLayout()
        
        # 처리 건수
        self.processed_count_label = QLabel("처리 건수: 0")
        
        # 평균 처리 시간
        self.avg_time_label = QLabel("평균 시간: -")
        
        # 평균 신뢰도
        self.avg_confidence_label = QLabel("평균 신뢰도: -")
        
        # 모델 상태
        self.model_status_label = QLabel("모델 상태: 미로드")
        
        stats_layout.addWidget(self.processed_count_label)
        stats_layout.addWidget(self.avg_time_label)
        stats_layout.addWidget(self.avg_confidence_label)
        stats_layout.addWidget(self.model_status_label)
        
        layout.addLayout(stats_layout)
        group.setLayout(layout)
        
        return group

    def load_config(self):
        """설정 로드"""
        config = self.current_config
        
        # 모델 타입 설정
        for i in range(self.model_type_combo.count()):
            if self.model_type_combo.itemData(i) == config.model_type:
                self.model_type_combo.setCurrentIndex(i)
                break
        
        # Whisper 설정
        self.whisper_model_combo.setCurrentText(config.model_name)
        
        # 언어 설정
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == config.language:
                self.language_combo.setCurrentIndex(i)
                break
        
        # 오디오 설정
        self.sample_rate_combo.setCurrentText(str(config.sample_rate))
        self.chunk_duration_spin.setValue(config.chunk_duration)
        self.overlap_spin.setValue(config.overlap_ratio)
        
        # 처리 설정
        self.confidence_threshold_spin.setValue(config.confidence_threshold)
        self.preprocessing_check.setChecked(config.enable_preprocessing)
        self.postprocessing_check.setChecked(config.enable_postprocessing)

    def on_model_type_changed(self):
        """모델 타입 변경 시"""
        self.on_config_changed()

    def on_volume_threshold_changed(self, value):
        """음량 임계값 변경 시"""
        self.volume_threshold_label.setText(f"음성 감지 임계값: {value}%")

    def on_config_changed(self):
        """설정 변경 시"""
        # 현재 UI 값들로 설정 업데이트
        model_type_data = self.model_type_combo.currentData()
        if model_type_data is None:
            return
        
        new_config = STTConfig(
            model_type=model_type_data,
            model_name=self.whisper_model_combo.currentText(),
            language=self.language_combo.currentData() or "ko",
            sample_rate=int(self.sample_rate_combo.currentText()),
            chunk_duration=self.chunk_duration_spin.value(),
            overlap_ratio=self.overlap_spin.value(),
            confidence_threshold=self.confidence_threshold_spin.value(),
            enable_preprocessing=self.preprocessing_check.isChecked(),
            enable_postprocessing=self.postprocessing_check.isChecked()
        )
        
        self.current_config = new_config
        self.config_changed.emit(new_config)
        
        # 설정 저장
        self.config_manager.set_stt_config(new_config)
        self.config_manager.save_config()

    def on_start_recording(self):
        """녹음 시작"""
        self.is_recording = True
        self.is_paused = False
        
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        
        self.pause_button.setText("⏸️ 일시정지")
        self.status_label.setText("상태: 녹음 중")
        self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        
        self.start_recording_requested.emit()

    def on_pause_resume_recording(self):
        """녹음 일시정지/재개"""
        if self.is_paused:
            # 재개
            self.is_paused = False
            self.pause_button.setText("⏸️ 일시정지")
            self.status_label.setText("상태: 녹음 중")
            self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
            self.resume_recording_requested.emit()
        else:
            # 일시정지
            self.is_paused = True
            self.pause_button.setText("▶️ 재개")
            self.status_label.setText("상태: 일시정지")
            self.status_label.setStyleSheet("font-weight: bold; color: #FF9800;")
            self.pause_recording_requested.emit()

    def on_stop_recording(self):
        """녹음 중지"""
        self.is_recording = False
        self.is_paused = False
        
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
        self.pause_button.setText("⏸️ 일시정지")
        self.status_label.setText("상태: 대기 중")
        self.status_label.setStyleSheet("font-weight: bold; color: #666;")
        
        self.stop_recording_requested.emit()

    def on_clear_results(self):
        """결과 지우기"""
        self.result_text.clear()
        self.clear_results_requested.emit()

    def on_save_results(self):
        """결과 저장"""
        text_content = self.result_text.toPlainText()
        if not text_content.strip():
            QMessageBox.information(self, "정보", "저장할 텍스트가 없습니다.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "결과 저장", 
            f"stt_result_{time.strftime('%Y%m%d_%H%M%S')}.txt", 
            "Text files (*.txt);;All files (*)"
        )
        
        if file_path:
            self.save_results_requested.emit(file_path)

    def on_copy_results(self):
        """클립보드에 복사"""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.result_text.toPlainText())
        
        QMessageBox.information(self, "성공", "텍스트가 클립보드에 복사되었습니다.")

    def browse_vosk_model(self):
        """Vosk 모델 경로 선택"""
        folder = QFileDialog.getExistingDirectory(
            self, "Vosk 모델 폴더 선택"
        )
        
        if folder:
            self.vosk_model_path_label.setText(f"모델 경로: {folder}")
            self.on_config_changed()

    def add_result(self, result: STTResult):
        """결과 추가"""
        if result.text.strip():
            timestamp = time.strftime("%H:%M:%S", time.localtime(result.timestamp))
            formatted_text = f"[{timestamp}] {result.text}\n"
            self.result_text.append(formatted_text)
            
            # 통계 업데이트
            self.processing_stats["total_processed"] += 1
            self.processing_stats["avg_processing_time"] = (
                (self.processing_stats["avg_processing_time"] * (self.processing_stats["total_processed"] - 1) +
                 result.processing_time) / self.processing_stats["total_processed"]
            )
            self.processing_stats["total_confidence"] += result.confidence
            
            # UI 업데이트
            self.update_stats_display()

    def update_volume_level(self, level: float):
        """음량 레벨 업데이트"""
        volume_percent = min(100, int(level * 100))
        self.volume_progress.setValue(volume_percent)
        self.volume_label.setText(f"음량: {volume_percent}%")

    def update_model_status(self, status: str):
        """모델 상태 업데이트"""
        self.model_status_label.setText(f"모델 상태: {status}")

    def update_stats_display(self):
        """통계 표시 업데이트"""
        count = self.processing_stats["total_processed"]
        avg_time = self.processing_stats["avg_processing_time"]
        avg_confidence = (
            self.processing_stats["total_confidence"] / count if count > 0 else 0.0
        )
        
        self.processed_count_label.setText(f"처리 건수: {count}")
        self.avg_time_label.setText(f"평균 시간: {avg_time:.2f}초")
        self.avg_confidence_label.setText(f"평균 신뢰도: {avg_confidence:.1%}")

    def get_current_config(self) -> STTConfig:
        """현재 설정 반환"""
        return self.current_config

    def reset_stats(self):
        """통계 리셋"""
        self.processing_stats = {
            "total_processed": 0,
            "avg_processing_time": 0.0,
            "total_confidence": 0.0
        }
        self.update_stats_display()