#!/usr/bin/env python3
"""
Vosk 한국어 모델 테스트
경량화된 Vosk 한국어 모델을 사용한 실시간 음성 인식 테스트입니다.

실행 방법:
  python tests/test_vosk_korean.py

주의: vosk 패키지와 vosk-model-small-ko-0.22 모델이 필요합니다.
"""

from vosk import Model, KaldiRecognizer
import pyaudio
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import QThread, pyqtSignal
import json
import sys

# 음성 인식 스레드
class AudioThread(QThread):
    text_update = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        MODEL_PATH = "./vosk-model-small-ko-0.22"
        self.model = Model(MODEL_PATH)
        self.rec = KaldiRecognizer(self.model, 16000)
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
        self.stream.start_stream()

    def run(self):
        print("실시간 STT 시작...")
        try:
            while True:
                data = self.stream.read(4096, exception_on_overflow=False)
                if self.rec.AcceptWaveform(data):
                    result = json.loads(self.rec.Result())
                    text = result.get("text", "")
                    if text:
                        self.text_update.emit(f"인식된 텍스트: {text}")
        except Exception as e:
            print(f"오류 발생: {e}")
        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()

def main():
    """Vosk 한국어 모델 테스트 실행"""
    print("🎤 Vosk 한국어 모델 테스트 시작")
    print("경량 한국어 모델로 실시간 음성 인식을 테스트합니다.")
    print("창을 닫으면 종료됩니다.")
    print("=" * 50)
    
    try:
        # GUI 설정
        app = QApplication(sys.argv)
        window = QWidget()
        window.setWindowTitle("실시간 한국어 STT")
        window.setGeometry(100, 100, 500, 200)

        layout = QVBoxLayout()
        label = QLabel("한국어로 말해주세요...")
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 14pt;")
        layout.addWidget(label)
        window.setLayout(layout)

        # 스레드 연결
        audio_thread = AudioThread()
        audio_thread.text_update.connect(label.setText)
        audio_thread.start()

        # 애플리케이션 종료 시 스레드 정리
        def on_exit():
            audio_thread.terminate()
            audio_thread.wait()

        app.aboutToQuit.connect(on_exit)

        window.show()
        return app.exec_()
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())