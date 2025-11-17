#!/usr/bin/env python3
"""
PyQt5 GUI 테스트
PyQt5를 사용한 실시간 오디오 시각화와 음성 인식 GUI 테스트입니다.

실행 방법:
  python tests/test_pyqt5_gui.py

주의: PyQt5, matplotlib, whisper 패키지가 설치되어 있어야 합니다.
"""

from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QHBoxLayout
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import sys
import whisper
import pyaudio
import numpy as np
import queue
import torch
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# 음성 인식 스레드
class AudioThread(QThread):
    text_update = pyqtSignal(str)
    audio_data_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.terminate_flag = False  # 안전한 종료 플래그
        
        # Whisper 모델 로드
        self.model = whisper.load_model("medium")  # "small", "medium", "large" 선택 가능
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"

        # PyAudio 설정
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000

        self.p = pyaudio.PyAudio()
        self.audio_queue = queue.Queue()

        # 오디오 스트리밍 (콜백 방식 사용)
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
            stream_callback=self.callback
        )
        self.stream.start_stream()

    def callback(self, in_data, frame_count, time_info, status):
        """PyAudio 스트리밍 콜백"""
        self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def run(self):
        print("실시간 STT 시작...")
        buffer = []
        
        while not self.terminate_flag:
            try:
                data = self.audio_queue.get(timeout=1)  # 1초 대기 (종료 처리)
            except queue.Empty:
                continue

            audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            buffer.append(audio_np)
            self.audio_data_signal.emit(audio_np)  # 오디오 시각화 업데이트
            
            # 3초 분량(48000 샘플) 처리
            if len(buffer) * self.CHUNK >= self.RATE * 3:
                audio_input = np.concatenate(buffer)
                buffer = []

                # Whisper로 음성 변환 (numpy 배열 전달)
                result = self.model.transcribe(audio_input, language="ko")
                transcription = result["text"]

                if transcription:
                    self.text_update.emit(transcription)  # 실시간으로 새로운 텍스트 반영

    def stop(self):
        """안전한 스레드 종료"""
        self.terminate_flag = True
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        self.quit()
        self.wait()


# GUI 설정
class STTApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("실시간 한국어 STT (Whisper + 시각화)")
        self.setGeometry(100, 100, 800, 500)

        # 전체 레이아웃 (세로 정렬)
        layout = QVBoxLayout()

        # 텍스트 출력 레이아웃
        text_layout = QVBoxLayout()
        self.label = QLabel("한국어로 말해주세요...")
        self.label.setWordWrap(True)
        self.label.setStyleSheet("font-size: 16pt; color: blue;")
        text_layout.addWidget(self.label)

        # 오디오 시각화 레이아웃
        self.figure, self.ax = plt.subplots(2, 1, figsize=(6, 3))
        self.canvas = FigureCanvas(self.figure)
        self.ax[0].set_title("Waveform")
        self.ax[1].set_title("Spectrogram")
        audio_layout = QVBoxLayout()
        audio_layout.addWidget(self.canvas)

        # 레이아웃 통합
        layout.addLayout(text_layout)
        layout.addLayout(audio_layout)
        self.setLayout(layout)

        # 오디오 스레드 실행
        self.audio_thread = AudioThread()
        self.audio_thread.text_update.connect(self.label.setText)
        self.audio_thread.audio_data_signal.connect(self.update_plot)
        self.audio_thread.start()

        # 타이머 설정 (0.1초마다 시각화 업데이트)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.canvas.draw)
        self.timer.start(100)

    def update_plot(self, audio_data):
        """실시간 오디오 데이터 시각화"""
        self.ax[0].cla()  # 파형 그래프 업데이트
        self.ax[0].plot(audio_data, color="blue")
        self.ax[0].set_ylim([-1, 1])
        self.ax[0].set_title("Waveform")

        # 스펙트로그램 생성
        self.ax[1].cla()
        self.ax[1].specgram(audio_data, Fs=16000, cmap="inferno")
        self.ax[1].set_title("Spectrogram")

        self.canvas.draw()

    def closeEvent(self, event):
        """창 닫을 때 스레드 정리"""
        self.audio_thread.stop()
        event.accept()

def main():
    """PyQt5 GUI 테스트 실행"""
    print("🎤 PyQt5 GUI 테스트 시작")
    print("실시간 오디오 시각화와 음성 인식을 테스트합니다.")
    print("창을 닫으면 종료됩니다.")
    print("=" * 50)
    
    try:
        app = QApplication(sys.argv)
        main_window = STTApp()
        main_window.show()
        return app.exec_()
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
