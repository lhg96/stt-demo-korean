"""
Main Window - 메인 윈도우 클래스
전체 애플리케이션의 GUI를 관리하고 컴포넌트들을 통합
"""

import sys
import os
from typing import Optional
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QMenuBar, QStatusBar, QAction, QMessageBox,
    QApplication, QProgressDialog,QLabel
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QIcon, QFont

from ..core.audio_recorder import AudioRecorder
from ..core.stt_processor import STTProcessor, STTConfig, STTModelType, STTResult
from ..utils.config_manager import ConfigManager
from ..utils.audio_utils import AudioUtils
from .control_panel import ControlPanelWidget
from .audio_visualizer import AudioVisualizerWidget


class STTMainWindow(QMainWindow):
    """메인 윈도우 클래스"""
    
    def __init__(self):
        """STTMainWindow 초기화"""
        super().__init__()
        
        # 컴포넌트 초기화
        self.config_manager = ConfigManager()
        self.audio_recorder: Optional[AudioRecorder] = None
        self.stt_processor: Optional[STTProcessor] = None
        self.audio_utils = AudioUtils()
        
        # UI 상태
        self.is_recording = False
        self.current_model_loading = False
        
        # UI 컴포넌트
        self.control_panel: Optional[ControlPanelWidget] = None
        self.visualizer: Optional[AudioVisualizerWidget] = None
        self.progress_dialog: Optional[QProgressDialog] = None
        
        self.setup_window()
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        self.setup_connections()
        self.load_initial_config()

    def setup_window(self):
        """윈도우 기본 설정"""
        self.setWindowTitle("STT Demo - 고급 음성 인식 데모 애플리케이션")
        self.setGeometry(100, 100, 1400, 900)
        
        # 아이콘 설정 (있는 경우)
        try:
            self.setWindowIcon(QIcon("icon.png"))
        except:
            pass
        
        # 폰트 설정
        font = QFont("Malgun Gothic", 9)
        self.setFont(font)
        
        # 스타일 설정
        self.setStyleSheet(self.get_application_stylesheet())

    def get_application_stylesheet(self) -> str:
        """애플리케이션 스타일시트 반환"""
        return """
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #555;
            border-radius: 8px;
            margin: 10px 0;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            background-color: #2b2b2b;
        }
        
        QPushButton {
            padding: 8px 16px;
            border-radius: 6px;
            border: 1px solid #555;
            font-weight: bold;
        }
        
        QPushButton:hover {
            border: 1px solid #777;
            background-color: #3c3c3c;
        }
        
        QPushButton:pressed {
            background-color: #1e1e1e;
        }
        
        QPushButton:disabled {
            background-color: #3c3c3c;
            color: #666;
            border: 1px solid #444;
        }
        
        QComboBox {
            padding: 6px;
            border: 1px solid #555;
            border-radius: 4px;
            background-color: #3c3c3c;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        
        QComboBox::down-arrow {
            width: 12px;
            height: 12px;
        }
        
        QTextEdit {
            border: 1px solid #555;
            border-radius: 4px;
            background-color: #1e1e1e;
            selection-background-color: #4a4a4a;
        }
        
        QLabel {
            color: #ffffff;
        }
        
        QCheckBox {
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #555;
            border-radius: 3px;
            background-color: #3c3c3c;
        }
        
        QCheckBox::indicator:checked {
            background-color: #4CAF50;
            border: 1px solid #4CAF50;
        }
        
        QSlider::groove:horizontal {
            border: 1px solid #555;
            height: 8px;
            background: #3c3c3c;
            border-radius: 4px;
        }
        
        QSlider::handle:horizontal {
            background: #4CAF50;
            border: 1px solid #4CAF50;
            width: 18px;
            border-radius: 9px;
            margin: -5px 0;
        }
        
        QProgressBar {
            border: 1px solid #555;
            border-radius: 4px;
            text-align: center;
            background-color: #3c3c3c;
        }
        
        QProgressBar::chunk {
            background-color: #4CAF50;
            border-radius: 3px;
        }
        
        QTabWidget::pane {
            border: 1px solid #555;
            border-radius: 4px;
            background-color: #2b2b2b;
        }
        
        QTabBar::tab {
            background-color: #3c3c3c;
            padding: 8px 16px;
            border: 1px solid #555;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #4CAF50;
        }
        
        QTabBar::tab:hover {
            background-color: #4a4a4a;
        }
        
        QMenuBar {
            background-color: #3c3c3c;
            border-bottom: 1px solid #555;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 4px 8px;
        }
        
        QMenuBar::item:selected {
            background-color: #4CAF50;
        }
        
        QMenu {
            background-color: #3c3c3c;
            border: 1px solid #555;
        }
        
        QMenu::item {
            padding: 4px 16px;
        }
        
        QMenu::item:selected {
            background-color: #4CAF50;
        }
        
        QStatusBar {
            background-color: #3c3c3c;
            border-top: 1px solid #555;
        }
        
        QSplitter::handle {
            background-color: #555;
        }
        
        QSplitter::handle:horizontal {
            width: 2px;
        }
        
        QSplitter::handle:vertical {
            height: 2px;
        }
        """

    def setup_ui(self):
        """UI 구성 요소 설정"""
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 스플리터
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 왼쪽 패널 (컨트롤)
        self.control_panel = ControlPanelWidget(self.config_manager)
        main_splitter.addWidget(self.control_panel)
        
        # 오른쪽 패널 (시각화)
        self.visualizer = AudioVisualizerWidget()
        main_splitter.addWidget(self.visualizer)
        
        # 스플리터 비율 설정 (1:2)
        main_splitter.setSizes([400, 800])
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 2)
        
        # 레이아웃
        layout = QVBoxLayout()
        layout.addWidget(main_splitter)
        layout.setContentsMargins(5, 5, 5, 5)
        central_widget.setLayout(layout)

    def setup_menu(self):
        """메뉴바 설정"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일(&F)")
        
        # 설정 불러오기
        load_config_action = QAction("설정 불러오기(&L)", self)
        load_config_action.setShortcut("Ctrl+O")
        load_config_action.triggered.connect(self.load_config_file)
        file_menu.addAction(load_config_action)
        
        # 설정 저장하기
        save_config_action = QAction("설정 저장하기(&S)", self)
        save_config_action.setShortcut("Ctrl+S")
        save_config_action.triggered.connect(self.save_config_file)
        file_menu.addAction(save_config_action)
        
        file_menu.addSeparator()
        
        # 종료
        exit_action = QAction("종료(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 도구 메뉴
        tools_menu = menubar.addMenu("도구(&T)")
        
        # 오디오 테스트
        audio_test_action = QAction("오디오 테스트(&A)", self)
        audio_test_action.triggered.connect(self.test_audio_device)
        tools_menu.addAction(audio_test_action)
        
        # 모델 관리
        model_manager_action = QAction("모델 관리(&M)", self)
        model_manager_action.triggered.connect(self.open_model_manager)
        tools_menu.addAction(model_manager_action)
        
        tools_menu.addSeparator()
        
        # 설정 초기화
        reset_config_action = QAction("설정 초기화(&R)", self)
        reset_config_action.triggered.connect(self.reset_config)
        tools_menu.addAction(reset_config_action)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말(&H)")
        
        # 정보
        about_action = QAction("정보(&A)", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def setup_status_bar(self):
        """상태바 설정"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 기본 상태 메시지
        self.status_bar.showMessage("준비 완료")
        
        # 상태바에 추가 정보 표시
        self.model_status_label = QLabel("모델: 미로드")
        self.status_bar.addPermanentWidget(self.model_status_label)

    def setup_connections(self):
        """시그널-슬롯 연결"""
        # 컨트롤 패널 연결
        self.control_panel.start_recording_requested.connect(self.start_recording)
        self.control_panel.stop_recording_requested.connect(self.stop_recording)
        self.control_panel.pause_recording_requested.connect(self.pause_recording)
        self.control_panel.resume_recording_requested.connect(self.resume_recording)
        self.control_panel.config_changed.connect(self.on_config_changed)
        self.control_panel.save_results_requested.connect(self.save_results_to_file)
        self.control_panel.clear_results_requested.connect(self.on_clear_results)

    def load_initial_config(self):
        """초기 설정 로드"""
        try:
            # 설정 로드
            self.config_manager.load_config()
            
            # STT 프로세서 초기화
            config = self.config_manager.get_stt_config()
            self.stt_processor = STTProcessor(config)
            
            # 시그널 연결
            self.stt_processor.result_ready.connect(self.on_stt_result)
            self.stt_processor.model_loaded.connect(self.on_model_loaded)
            self.stt_processor.model_load_failed.connect(self.on_model_load_failed)
            self.stt_processor.error_occurred.connect(self.on_stt_error)
            
            # 초기 모델 로드 시도
            self.load_model_async()
            
        except Exception as e:
            QMessageBox.critical(self, "초기화 오류", f"초기 설정 로드 중 오류가 발생했습니다:\\n{str(e)}")

    def load_model_async(self):
        """비동기로 모델 로드"""
        if self.current_model_loading:
            return
        
        config = self.config_manager.get_stt_config()
        
        # 프로그레스 다이얼로그 표시
        self.progress_dialog = QProgressDialog("모델을 로드하는 중...", "취소", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()
        
        self.current_model_loading = True
        self.status_bar.showMessage("모델 로드 중...")
        
        # 별도 스레드에서 모델 로드
        QTimer.singleShot(100, lambda: self._load_model_worker(config))

    def _load_model_worker(self, config: STTConfig):
        """모델 로드 워커"""
        try:
            success = self.stt_processor.load_model(config.model_type, config.model_name)
            if not success:
                raise Exception("모델 로드 실패")
        except Exception as e:
            self.on_model_load_failed(config.model_name, str(e))
        finally:
            self.current_model_loading = False
            if self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None

    @pyqtSlot()
    def start_recording(self):
        """녹음 시작"""
        if self.is_recording:
            return
        
        try:
            # 오디오 레코더 초기화
            config = self.config_manager.get_stt_config()
            self.audio_recorder = AudioRecorder(
                sample_rate=config.sample_rate,
                chunk_size=1024
            )
            
            # 시그널 연결
            self.audio_recorder.audio_data_ready.connect(self.on_audio_data)
            self.audio_recorder.volume_level_changed.connect(self.control_panel.update_volume_level)
            self.audio_recorder.error_occurred.connect(self.on_audio_error)
            
            # 녹음 시작
            self.audio_recorder.start_recording()
            self.is_recording = True
            
            self.status_bar.showMessage("녹음 중...")
            
        except Exception as e:
            QMessageBox.critical(self, "녹음 오류", f"녹음을 시작할 수 없습니다:\\n{str(e)}")

    @pyqtSlot()
    def stop_recording(self):
        """녹음 중지"""
        if not self.is_recording:
            return
        
        try:
            if self.audio_recorder:
                self.audio_recorder.stop_recording()
                self.audio_recorder = None
            
            self.is_recording = False
            self.status_bar.showMessage("녹음 중지됨")
            
        except Exception as e:
            QMessageBox.warning(self, "중지 오류", f"녹음 중지 중 오류가 발생했습니다:\\n{str(e)}")

    @pyqtSlot()
    def pause_recording(self):
        """녹음 일시정지"""
        if self.audio_recorder:
            self.audio_recorder.pause_recording()
            self.status_bar.showMessage("녹음 일시정지됨")

    @pyqtSlot()
    def resume_recording(self):
        """녹음 재개"""
        if self.audio_recorder:
            self.audio_recorder.resume_recording()
            self.status_bar.showMessage("녹음 재개됨")

    @pyqtSlot(STTConfig)
    def on_config_changed(self, config: STTConfig):
        """설정 변경 시"""
        # STT 프로세서 설정 업데이트
        if self.stt_processor:
            self.stt_processor.set_config(config)
            
            # 모델이 변경된 경우 재로드
            current_model_type = getattr(self.stt_processor.current_model, 'model_type', None)
            if current_model_type != config.model_type:
                self.load_model_async()

    @pyqtSlot(object)  # np.ndarray
    def on_audio_data(self, audio_data):
        """오디오 데이터 수신"""
        # 시각화 업데이트
        self.visualizer.update_visualization(audio_data)
        
        # STT 처리
        if self.stt_processor:
            self.stt_processor.process_audio(audio_data)

    @pyqtSlot(STTResult)
    def on_stt_result(self, result: STTResult):
        """STT 결과 수신"""
        self.control_panel.add_result(result)
        self.status_bar.showMessage(f"인식 완료: {result.text[:30]}...")

    @pyqtSlot(str, STTModelType)
    def on_model_loaded(self, model_name: str, model_type: STTModelType):
        """모델 로드 완료"""
        status_text = f"모델: {model_type.value.upper()} ({model_name})"
        self.model_status_label.setText(status_text)
        self.control_panel.update_model_status(f"{model_type.value.upper()} {model_name} 로드됨")
        self.status_bar.showMessage(f"모델 로드 완료: {model_name}")

    @pyqtSlot(str, str)
    def on_model_load_failed(self, model_name: str, error_message: str):
        """모델 로드 실패"""
        self.model_status_label.setText("모델: 로드 실패")
        self.control_panel.update_model_status("모델 로드 실패")
        self.status_bar.showMessage(f"모델 로드 실패: {error_message}")
        QMessageBox.warning(self, "모델 로드 오류", f"모델 '{model_name}' 로드에 실패했습니다:\\n{error_message}")

    @pyqtSlot(str)
    def on_stt_error(self, error_message: str):
        """STT 오류"""
        self.status_bar.showMessage(f"STT 오류: {error_message}")

    @pyqtSlot(str)
    def on_audio_error(self, error_message: str):
        """오디오 오류"""
        self.status_bar.showMessage(f"오디오 오류: {error_message}")
        QMessageBox.warning(self, "오디오 오류", error_message)

    @pyqtSlot(str)
    def save_results_to_file(self, file_path: str):
        """파일에 결과 저장"""
        try:
            text_content = self.control_panel.result_text.toPlainText()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            QMessageBox.information(self, "저장 완료", f"결과가 저장되었습니다:\\n{file_path}")
            self.status_bar.showMessage(f"결과 저장됨: {os.path.basename(file_path)}")
            
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"파일 저장 중 오류가 발생했습니다:\\n{str(e)}")

    @pyqtSlot()
    def on_clear_results(self):
        """결과 지우기"""
        self.control_panel.reset_stats()
        self.status_bar.showMessage("결과가 지워졌습니다.")

    def load_config_file(self):
        """설정 파일 불러오기"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "설정 파일 불러오기", "", "JSON files (*.json);;All files (*)"
        )
        
        if file_path:
            try:
                self.config_manager.load_config(file_path)
                self.control_panel.load_config()
                QMessageBox.information(self, "성공", "설정이 불러와졌습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"설정 불러오기 실패:\\n{str(e)}")

    def save_config_file(self):
        """설정 파일 저장하기"""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "설정 파일 저장하기", "stt_config.json", "JSON files (*.json);;All files (*)"
        )
        
        if file_path:
            try:
                self.config_manager.save_config(file_path)
                QMessageBox.information(self, "성공", "설정이 저장되었습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"설정 저장 실패:\\n{str(e)}")

    def test_audio_device(self):
        """오디오 장치 테스트"""
        try:
            device_info = self.audio_utils.get_audio_device_info()
            
            message = "오디오 장치 정보:\\n\\n"
            message += f"입력 장치: {device_info.get('input_device', 'N/A')}\\n"
            message += f"출력 장치: {device_info.get('output_device', 'N/A')}\\n"
            message += f"샘플링 레이트: {device_info.get('sample_rate', 'N/A')}\\n"
            message += f"채널 수: {device_info.get('channels', 'N/A')}"
            
            QMessageBox.information(self, "오디오 장치 테스트", message)
            
        except Exception as e:
            QMessageBox.critical(self, "테스트 오류", f"오디오 장치 테스트 실패:\\n{str(e)}")

    def open_model_manager(self):
        """모델 관리자 열기"""
        # 향후 구현 예정
        QMessageBox.information(self, "준비 중", "모델 관리 기능은 향후 버전에서 제공될 예정입니다.")

    def reset_config(self):
        """설정 초기화"""
        reply = QMessageBox.question(
            self, "설정 초기화", 
            "모든 설정을 초기화하시겠습니까?\\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.config_manager.reset_to_defaults()
                self.control_panel.load_config()
                QMessageBox.information(self, "완료", "설정이 초기화되었습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"설정 초기화 실패:\\n{str(e)}")

    def show_about_dialog(self):
        """정보 다이얼로그 표시"""
        about_text = f"""
        <h2>STT Demo</h2>
        <p><b>버전:</b> 1.0.0</p>
        <p><b>설명:</b> 고급 음성 인식 데모 애플리케이션</p>
        
        <h3>주요 기능</h3>
        <ul>
        <li>실시간 음성 인식 (Whisper, Vosk 지원)</li>
        <li>오디오 시각화 (파형, 스펙트럼, 스펙트로그램)</li>
        <li>다양한 모델 및 언어 지원</li>
        <li>설정 저장 및 불러오기</li>
        <li>결과 내보내기</li>
        </ul>
        
        <h3>지원 모델</h3>
        <ul>
        <li>OpenAI Whisper (tiny, base, small, medium, large)</li>
        <li>Vosk (다국어 지원)</li>
        </ul>
        
        <p><b>개발:</b> STT Demo Team</p>
        <p><b>라이센스:</b> MIT License</p>
        """
        
        QMessageBox.about(self, "STT Demo 정보", about_text)

    def closeEvent(self, event):
        """애플리케이션 종료 시"""
        try:
            # 녹음 중지
            if self.is_recording:
                self.stop_recording()
            
            # 리소스 정리
            if self.stt_processor:
                self.stt_processor.cleanup()
            
            if self.visualizer:
                self.visualizer.stop_updates()
            
            # 설정 저장
            self.config_manager.save_config()
            
        except Exception as e:
            print(f"종료 중 오류: {e}")
        
        event.accept()


def main():
    """메인 함수"""
    # QApplication 생성
    app = QApplication(sys.argv)
    app.setApplicationName("STT Demo")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("STT Demo Team")
    
    # 사용 가능한 모델 확인
    available_models = []
    try:
        import whisper
        available_models.append("Whisper")
    except ImportError:
        pass
    
    try:
        from vosk import Model
        available_models.append("Vosk")
    except ImportError:
        pass
    
    if not available_models:
        QMessageBox.critical(
            None, "오류", 
            "사용 가능한 STT 모델이 없습니다.\\n\\n"
            "다음 중 하나 이상을 설치하세요:\\n"
            "• pip install openai-whisper\\n"
            "• pip install vosk"
        )
        sys.exit(1)
    
    # 메인 윈도우 생성 및 표시
    window = STTMainWindow()
    window.show()
    
    # 애플리케이션 실행
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()