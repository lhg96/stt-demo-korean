#!/usr/bin/env python3
"""
STT Demo - 통합된 음성 인식 데모 애플리케이션
Whisper와 Vosk 모델을 지원하는 GUI 애플리케이션

Usage:
  python stt_demo.py           # GUI 실행 (기본값)
  python stt_demo.py gui       # GUI 실행
  python stt_demo.py check     # 패키지 확인
  python stt_demo.py install   # 패키지 설치
  python stt_demo.py help      # 도움말
"""

import sys
import os
import json
import time
import threading
import queue
import subprocess
from typing import Optional
from pathlib import Path

import numpy as np
import pyaudio
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QLabel, QPushButton, QComboBox, QTextEdit, QProgressBar, 
    QGroupBox, QCheckBox, QSlider, QTabWidget, QStatusBar,
    QMessageBox, QFileDialog
)
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QFont, QIcon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.style as mplstyle

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False




def check_requirements():
    """필수 패키지 설치 확인"""
    required_packages = {
        'PyQt5': ('PyQt5.QtCore', 'pip install PyQt5'),
        'numpy': ('numpy', 'pip install numpy'),
        'pyaudio': ('pyaudio', 'pip install pyaudio'),
        'matplotlib': ('matplotlib', 'pip install matplotlib')
    }
    
    missing_packages = []
    
    for package_name, (import_name, install_cmd) in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append((package_name, install_cmd))
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package, cmd in missing_packages:
            print(f"   - {package}: {cmd}")
        return False
    
    return True


def check_optional_packages():
    """선택적 패키지 확인"""
    available = {}
    
    if WHISPER_AVAILABLE:
        available['whisper'] = True
        print("✅ Whisper available")
    else:
        print("⚠️  Whisper not installed: pip install openai-whisper")
    
    if VOSK_AVAILABLE:
        available['vosk'] = True
        print("✅ Vosk available")
    else:
        print("⚠️  Vosk not installed: pip install vosk")
    
    return available


def install_packages():
    """패키지 자동 설치"""
    packages = [
        "PyQt5", "numpy", "pyaudio", "matplotlib",
        "openai-whisper", "vosk"
    ]
    
    python_path = get_venv_python()
    
    for package in packages:
        print(f"📦 Installing {package}...")
        try:
            subprocess.run([python_path, "-m", "pip", "install", package], 
                         check=True, capture_output=True)
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")


def get_venv_python():
    """가상환경 Python 경로 반환"""
    venv_python = os.path.join(os.path.dirname(__file__), "venv", "bin", "python")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable


def show_help():
    """도움말 표시"""
    help_text = """
STT Demo - Speech-to-Text Demo Application

Commands:
  gui      Start GUI application (default)
  check    Check installed packages
  install  Install required packages
  help     Show this help

Examples:
  python stt_demo.py           # Run GUI
  python stt_demo.py gui       # Run GUI
  python stt_demo.py check     # Check packages
  python stt_demo.py install   # Install packages

Features:
  - Real-time speech recognition
  - Support for Whisper and Vosk models
  - Audio visualization (waveform, spectrum)
  - Korean and English support
  - Export results to text files
"""
    print(help_text)


class AudioRecorderThread(QThread):
    """오디오 녹음 전용 스레드 - 콜백 방식 사용"""
    audio_data = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)
    recording_finished = pyqtSignal(np.ndarray)  # 전체 녹음 데이터 시그널
    
    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.terminate_flag = False  # 안전한 종료 플래그
        self.recorded_data = []  # 전체 녹음 데이터 저장
        self.audio_queue = queue.Queue()
        
        # PyAudio 설정
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        
        self.p = None
        self.stream = None
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio 스트리밍 콜백"""
        if self.is_recording:
            self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)
        
    def start_recording(self):
        """녹음 시작"""
        try:
            self.recorded_data = []  # 녹음 데이터 초기화
            self.terminate_flag = False
            self.is_recording = True
            
            self.p = pyaudio.PyAudio()
            
            # 콜백 방식으로 스트림 생성
            self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
                stream_callback=self.audio_callback
            )
            
            self.stream.start_stream()
            self.start()  # 스레드 시작
            
        except Exception as e:
            self.error_occurred.emit(f"Recording start error: {str(e)}")
    
    def stop_recording(self):
        """녹음 중지 - test_pyqt5_gui.py의 안전한 종료 방식"""
        self.terminate_flag = True
        self.is_recording = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()
        
        # 전체 녹음 데이터를 하나로 결합
        if self.recorded_data:
            combined_audio = np.concatenate(self.recorded_data)
            self.recording_finished.emit(combined_audio)
            print(f"🎤 Recording finished. Total length: {len(combined_audio)} samples")
        
        self.quit()
        self.wait()
    
    def run(self):
        """녹음 루프 - 콜백에서 받은 데이터 처리"""
        try:
            while not self.terminate_flag:
                try:
                    # 콜백에서 데이터 받기 (1초 타임아웃)
                    data = self.audio_queue.get(timeout=1)
                    audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                    
                    # 전체 녹음 데이터에 추가
                    self.recorded_data.append(audio_np)
                    
                    # 실시간 시각화만 전송
                    self.audio_data.emit(audio_np)
                    
                except queue.Empty:
                    continue  # 타임아웃 시 계속
                    
        except Exception as e:
            self.error_occurred.emit(f"Recording error: {str(e)}")


class STTThread(QThread):
    """일회성 STT 처리 전용 스레드"""
    result_ready = pyqtSignal(str, float)
    
    def __init__(self, model_type="whisper", audio_data=None):
        super().__init__()
        self.model_type = model_type
        self.audio_data = audio_data
        self.model = None
        self.recognizer = None
        
        # 모델 초기화
        self.init_model()
    
    def init_model(self):
        """모델 초기화"""
        try:
            if self.model_type == "whisper" and WHISPER_AVAILABLE:
                print("🔄 Loading Whisper model...")
                self.model = whisper.load_model("base")
                print("✅ Whisper model loaded")
            elif self.model_type == "vosk" and VOSK_AVAILABLE:
                model_path = "./vosk-model-small-ko-0.22"
                print(f"🔄 Loading Vosk model from {model_path}...")
                if os.path.exists(model_path):
                    vosk_model = Model(model_path)
                    self.recognizer = KaldiRecognizer(vosk_model, 16000)
                    # JSON 출력 활성화
                    self.recognizer.SetWords(True)
                    print("✅ Vosk Korean model loaded")
                else:
                    print(f"❌ Vosk model not found: {model_path}")
                    print("   Download: wget https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip")
            else:
                print(f"❌ Model {self.model_type} not available")
        except Exception as e:
            print(f"Model initialization error: {e}")
            self.model = None
            self.recognizer = None

    
    def run(self):
        """오디오 STT 처리"""
        try:
            if self.audio_data is not None and len(self.audio_data) > 0:
                print(f"🔎 Processing audio for STT (length: {len(self.audio_data)} samples)...")
                
                # 너무 조용한 경우 건너뛰기
                if np.max(np.abs(self.audio_data)) < 0.01:
                    print("🔇 Audio too quiet, skipping...")
                    return
                
                # STT 처리
                text = self.process_audio(self.audio_data)
                
                if text and text.strip() and len(text.strip()) > 1:
                    confidence = 0.85
                    self.result_ready.emit(text.strip(), confidence)
                    print(f"✅ STT Result: {text.strip()}")
                else:
                    print("❌ No speech detected or text too short")
                    
        except Exception as e:
            print(f"STT processing error: {e}")
    
    def process_audio(self, audio_data):
        """오디오 STT 처리 - test_pyqt5_gui.py와 동일한 방식"""
        try:
            # 최소 3초 이상의 데이터가 있는지 확인
            min_samples = 16000 * 3  # 3초
            if len(audio_data) < min_samples:
                print(f"🔇 Audio too short ({len(audio_data)} samples), minimum {min_samples} required")
                return ""
            
            if self.model_type == "whisper" and self.model:
                print(f"🎤 Processing audio with Whisper ({len(audio_data)} samples)...")
                # Whisper 한국어 처리 - numpy 배열 직접 전달
                result = self.model.transcribe(audio_data, language="ko")
                text = result["text"].strip()
                if text:
                    print(f"🎤 Whisper result: {text}")
                    return text
                else:
                    print("🎤 Whisper: No speech detected")
                    return ""
                
            elif self.model_type == "vosk" and self.recognizer:
                print(f"🎤 Processing audio with Vosk ({len(audio_data)} samples)...")
                # Vosk 한국어 처리
                audio_int16 = (audio_data * 32768).astype(np.int16)
                audio_bytes = audio_int16.tobytes()
                
                # 전체 오디오를 한 번에 처리
                if self.recognizer.AcceptWaveform(audio_bytes):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        print(f"🎤 Vosk result: {text}")
                        return text
                    else:
                        print("🎤 Vosk: No speech detected")
                        return ""
                else:
                    print("🎤 Vosk: Processing incomplete")
                    return ""
                    
            else:
                print(f"❌ No valid STT model available: {self.model_type}")
                return ""
                
        except Exception as e:
            print(f"Audio processing error: {e}")
            return ""


class AudioVisualizerWidget(QWidget):
    """오디오 시각화 위젯"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
        # 데이터 버퍼
        self.waveform_data = np.zeros(1024)
        self.spectrum_data = np.zeros(512)
        
        # 업데이트 타이머
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(50)  # 50ms 간격
    
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout()
        
        # Matplotlib Figure
        self.figure, (self.waveform_ax, self.spectrum_ax) = plt.subplots(2, 1, figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # 초기 플롯 설정
        self.waveform_line, = self.waveform_ax.plot([], [], 'g-')
        self.waveform_ax.set_title('Waveform')
        self.waveform_ax.set_ylim(-1, 1)
        self.waveform_ax.set_xlim(0, 1024)
        self.waveform_ax.grid(True)
        
        self.spectrum_line, = self.spectrum_ax.plot([], [], 'b-')
        self.spectrum_ax.set_title('Frequency Spectrum')
        self.spectrum_ax.set_xlim(0, 8000)
        self.spectrum_ax.set_ylim(-80, 0)
        self.spectrum_ax.grid(True)
        
        plt.tight_layout(pad=2.0)
        self.setLayout(layout)
    
    def update_audio_data(self, audio_data):
        """오디오 데이터 업데이트"""
        self.waveform_data = audio_data[:1024] if len(audio_data) >= 1024 else np.zeros(1024)
        
        # FFT 계산
        if len(audio_data) > 0:
            fft_data = np.abs(np.fft.fft(audio_data[:1024]))
            self.spectrum_data = 20 * np.log10(fft_data[:512] + 1e-6)
    
    def update_plots(self):
        """플롯 업데이트"""
        # 파형 업데이트
        self.waveform_line.set_data(range(len(self.waveform_data)), self.waveform_data)
        
        # 스펙트럼 업데이트
        freqs = np.linspace(0, 8000, len(self.spectrum_data))
        self.spectrum_line.set_data(freqs, self.spectrum_data)
        
        self.canvas.draw_idle()


class STTDemoMainWindow(QMainWindow):
    """메인 GUI 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.recorder_thread = None
        self.stt_thread = None
        self.is_recording = False
        self.selected_model = "whisper"
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("STT Demo - Speech Recognition")
        self.setGeometry(100, 100, 1200, 800)
        
        # 전체 앱 폰트 크기 설정
        font = QFont()
        font.setPointSize(9)  # 폰트 크기를 9로 설정
        self.setFont(font)
        QApplication.instance().setFont(font)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout()
        
        # 왼쪽 패널 (컨트롤)
        left_panel = self.create_control_panel()
        main_layout.addWidget(left_panel, 1)
        
        # 오른쪽 패널 (시각화)
        right_panel = self.create_visualization_panel()
        main_layout.addWidget(right_panel, 2)
        
        central_widget.setLayout(main_layout)
        
        # 상태바
        self.statusBar().showMessage("Ready")
    
    def create_control_panel(self):
        """컨트롤 패널 생성"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # 모델 선택
        model_group = QGroupBox("Model Settings")
        model_layout = QVBoxLayout()
        
        self.model_combo = QComboBox()
        available_models = []
        if WHISPER_AVAILABLE:
            self.model_combo.addItem("Whisper")
            available_models.append("Whisper")
        if VOSK_AVAILABLE:
            self.model_combo.addItem("Vosk")
            available_models.append("Vosk")
        
        # 모델이 없으면 기본값 추가
        if not available_models:
            self.model_combo.addItem("No STT Model Available")
            
        model_layout.addWidget(QLabel("Model:"))
        model_layout.addWidget(self.model_combo)
        
        # 상태 라벨 추가
        self.model_status_label = QLabel()
        self.update_model_status()
        model_layout.addWidget(self.model_status_label)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # 녹음 컨트롤
        record_group = QGroupBox("Recording Control")
        record_layout = QVBoxLayout()
        
        self.record_btn = QPushButton("Start Recording")
        self.record_btn.setStyleSheet("QPushButton { background-color: #4CAF50; }")
        record_layout.addWidget(self.record_btn)
        
        self.stop_btn = QPushButton("Stop Recording")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("QPushButton { background-color: #f44336; }")
        record_layout.addWidget(self.stop_btn)
        
        record_group.setLayout(record_layout)
        layout.addWidget(record_group)
        
        # 결과 표시
        result_group = QGroupBox("Recognition Results")
        result_layout = QVBoxLayout()
        
        self.result_text = QTextEdit()
        self.result_text.setStyleSheet("QTextEdit { font-size: 10px; }")
        self.result_text.setPlaceholderText("Recognition results will appear here...")
        result_layout.addWidget(self.result_text)
        
        # 버튼들
        button_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("Clear")
        self.save_btn = QPushButton("Save")
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.save_btn)
        
        result_layout.addLayout(button_layout)
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        layout.addStretch()
        panel.setLayout(layout)
        return panel
    
    def create_visualization_panel(self):
        """시각화 패널 생성"""
        self.visualizer = AudioVisualizerWidget()
        return self.visualizer
    
    def setup_connections(self):
        """시그널-슬롯 연결"""
        self.record_btn.clicked.connect(self.start_recording)
        self.stop_btn.clicked.connect(self.stop_recording)
        self.clear_btn.clicked.connect(self.clear_results)
        self.save_btn.clicked.connect(self.save_results)
        self.model_combo.currentTextChanged.connect(self.change_model)
    
    def update_model_status(self):
        """모델 상태 업데이트"""
        status_text = "Available models: "
        if WHISPER_AVAILABLE:
            status_text += "Whisper ✅ "
        else:
            status_text += "Whisper ❌ "
        if VOSK_AVAILABLE:
            status_text += "Vosk ✅"
        else:
            status_text += "Vosk ❌"
        self.model_status_label.setText(status_text)
        self.model_status_label.setStyleSheet("color: #888888; font-size: 8px;")
    
    def start_recording(self):
        """녹음 시작"""
        if self.is_recording:
            return
        
        # 모델 선택 확인
        selected_model = self.model_combo.currentText().lower()
        if selected_model == "no stt model available":
            QMessageBox.warning(self, "Warning", "No STT model available. Please install Whisper or Vosk.")
            return
            
        try:
            # 오디오 레코더 시작
            self.recorder_thread = AudioRecorderThread()
            self.recorder_thread.audio_data.connect(self.on_audio_data)
            self.recorder_thread.recording_finished.connect(self.on_recording_finished)
            self.recorder_thread.error_occurred.connect(self.on_error)
            self.recorder_thread.start_recording()
            
            self.is_recording = True
            self.selected_model = selected_model
            self.record_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.statusBar().showMessage(f"Recording with {selected_model.title()} model...")
            
            # 결과 영역에 시작 메시지 추가
            timestamp = time.strftime("%H:%M:%S")
            start_msg = f"[{timestamp}] === Recording started with {selected_model.title()} model ===\n"
            self.result_text.append(start_msg)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start recording: {str(e)}")
    
    def stop_recording(self):
        """녹음 중지"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        if self.recorder_thread:
            self.statusBar().showMessage("Stopping recording and processing...")
            self.recorder_thread.stop_recording()
            self.recorder_thread = None
        
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def on_audio_data(self, audio_data):
        """오디오 데이터 수신 (실시간 시각화용)"""
        # 실시간 시각화 업데이트
        self.visualizer.update_audio_data(audio_data)
        
        # 오디오 레벨 체크 (디버깅용)
        audio_level = np.max(np.abs(audio_data))
        if audio_level > 0.1:  # 충분한 음성이 감지되면
            self.statusBar().showMessage(f"🎤 Audio level: {audio_level:.3f} - Speaking detected")
    
    def on_stt_result(self, text, confidence):
        """STT 결과 수신 및 표시"""
        if text and text.strip():
            timestamp = time.strftime("%H:%M:%S")
            current_model = self.selected_model.title() if hasattr(self, 'selected_model') else "Unknown"
            result_line = f"[{timestamp}] [{current_model}] {text.strip()} (confidence: {confidence:.2f})\n"
            self.result_text.append(result_line)
            self.statusBar().showMessage(f"Recognized ({current_model}): {text.strip()[:50]}...")
            
            # 커서를 마지막으로 이동
            cursor = self.result_text.textCursor()
            cursor.movePosition(cursor.End)
            self.result_text.setTextCursor(cursor)
    
    def on_recording_finished(self, audio_data):
        """녹음 완료 시 STT 처리 시작"""
        print(f"🎤 Recording finished, starting STT processing...")
        
        # STT 처리를 위한 스레드 생성 및 시작
        selected_model = getattr(self, 'selected_model', 'whisper')
        self.stt_thread = STTThread(selected_model, audio_data)
        self.stt_thread.result_ready.connect(self.on_stt_result)
        self.stt_thread.finished.connect(self.on_stt_finished)
        self.stt_thread.start()
    
    def on_stt_finished(self):
        """실시간 STT 처리 완료"""
        self.statusBar().showMessage("Ready")
        if self.stt_thread:
            self.stt_thread = None
    
    def on_error(self, error_msg):
        """오류 처리"""
        QMessageBox.warning(self, "Warning", error_msg)
        self.stop_recording()
    
    def clear_results(self):
        """결과 지우기"""
        self.result_text.clear()
    
    def save_results(self):
        """결과 저장"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Results", "stt_results.txt", "Text Files (*.txt)")
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.result_text.toPlainText())
                QMessageBox.information(self, "Success", f"Results saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
    
    def change_model(self, model_name):
        """모델 변경"""
        if self.is_recording:
            reply = QMessageBox.question(self, "Model Change", 
                                       "Recording is in progress. Stop recording to change model?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.stop_recording()
            else:
                return
                
        # 모델 상태 업데이트
        self.statusBar().showMessage(f"Selected model: {model_name}")
        
        # Vosk 모델 사용 시 안내 메시지
        if model_name.lower() == "vosk":
            model_path = "./vosk-model-small-ko-0.22"
            if not os.path.exists(model_path):
                QMessageBox.information(self, "Vosk Model Info", 
                                       f"Vosk Korean model not found at: {model_path}\n\n"
                                       "To download:\n"
                                       "wget https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip\n"
                                       "unzip vosk-model-small-ko-0.22.zip")
    
    def closeEvent(self, event):
        """창 닫기 이벤트 - test_pyqt5_gui.py의 안전한 종료 방식"""
        if self.is_recording:
            self.stop_recording()
        
        # 스레드들 안전하게 종료
        if self.recorder_thread and self.recorder_thread.isRunning():
            self.recorder_thread.stop_recording()
        if self.stt_thread and self.stt_thread.isRunning():
            self.stt_thread.quit()
            self.stt_thread.wait()
            
        event.accept()


def run_gui():
    """GUI 실행"""
    app = QApplication(sys.argv)
    app.setApplicationName("STT Demo")
    
    # 다크 테마 설정
    app.setStyleSheet("""
        QMainWindow { background-color: #2b2b2b; color: #ffffff; }
        QWidget { background-color: #2b2b2b; color: #ffffff; }
        QGroupBox { 
            font-weight: bold; 
            border: 1px solid #555; 
            margin: 5px; 
            padding: 5px;
            border-radius: 4px;
        }
        QGroupBox::title { 
            subcontrol-origin: margin; 
            left: 10px; 
            padding: 0 5px 0 5px; 
        }
        QPushButton { 
            padding: 8px; 
            border-radius: 4px; 
            border: 1px solid #555;
            font-weight: bold;
        }
        QPushButton:hover {
            border: 1px solid #777;
            background-color: #3c3c3c;
        }
        QComboBox { 
            padding: 5px; 
            border: 1px solid #555; 
            border-radius: 4px;
            background-color: #3c3c3c;
        }
        QTextEdit { 
            border: 1px solid #555; 
            background-color: #1e1e1e;
            border-radius: 4px;
        }
        QLabel { color: #ffffff; }
    """)
    
    # 사용 가능한 모델 확인
    if not WHISPER_AVAILABLE and not VOSK_AVAILABLE:
        QMessageBox.critical(None, "Error", 
                           "No STT models available.\n"
                           "Please install: pip install openai-whisper OR pip install vosk")
        sys.exit(1)
    
    window = STTDemoMainWindow()
    window.show()
    
    sys.exit(app.exec_())


def main():
    """메인 함수"""
    # 명령어 파싱
    if len(sys.argv) < 2:
        command = "gui"  # 기본값
    else:
        command = sys.argv[1].lower()
    
    if command == "help":
        show_help()
    elif command == "check":
        print("📋 Checking packages...")
        if check_requirements():
            print("✅ All required packages installed")
            check_optional_packages()
        else:
            print("❌ Missing required packages")
    elif command == "install":
        print("📦 Installing packages...")
        install_packages()
    elif command == "gui" or command not in ["help", "check", "install"]:
        print("🎤 STT Demo Starting...")
        print("=" * 50)
        
        if not check_requirements():
            print("❌ Missing required packages. Run: python stt_demo.py install")
            return
        
        available = check_optional_packages()
        if not (available.get('whisper') or available.get('vosk')):
            print("⚠️  Please install at least one STT model:")
            print("   pip install openai-whisper  # For Whisper")
            print("   pip install vosk           # For Vosk")
            return
        
        run_gui()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()


if __name__ == "__main__":
    main()