#!/usr/bin/env python3
"""
Whisper Large-v3 모델 테스트
고성능 Whisper large-v3 모델을 사용한 실시간 음성 인식 테스트입니다.

실행 방법:
  python tests/test_whisper_large.py
"""

import whisper
import pyaudio
import numpy as np
import torch
import time
import queue
import threading

# CPU 강제 사용
device = "cpu"
print(f"Using device: {device}")
model = whisper.load_model("large-v3", device=device)
print("Model loaded with large-v3")

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
q = queue.Queue()

def record_audio():
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        q.put(data)

threading.Thread(target=record_audio, daemon=True).start()

print("한국어로 말해주세요... (Ctrl+C로 종료)")

try:
    while True:
        start_time = time.time()
        audio_buffer = []
        for _ in range(10):  # 0.25초 분량
            audio_buffer.append(q.get())
        audio_data = b''.join(audio_buffer)
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        result = model.transcribe(audio_np, language="ko")
        text = result["text"].strip()
        if text:
            print(f"인식된 텍스트: {text} (처리 시간: {time.time() - start_time:.2f}s)")

if __name__ == "__main__":
    print("🎤 Whisper Large-v3 테스트 시작")
    print("고성능 모델로 빠른 처리를 테스트합니다.")
    print("Ctrl+C로 종료할 수 있습니다.")
    print("=" * 50)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n프로그램을 종료합니다.")
    except Exception as e:
        print(f"\n오류가 발생했습니다: {e}")
    finally:
        try:
            stream.stop_stream()
            stream.close()
            audio.terminate()
        except:
            pass

stream.stop_stream()
stream.close()
p.terminate()