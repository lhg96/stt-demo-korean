#!/usr/bin/env python3
"""
Whisper 기본 테스트
5초 단위 샘플링으로 음성 인식을 수행하는 기본적인 Whisper 테스트입니다.

실행 방법:
  python tests/test_whisper_basic.py
"""

import pyaudio
import whisper
import numpy as np
import queue
import time
import threading

def main():
    """Whisper 기본 테스트 메인 함수"""
    print("🎤 Whisper 기본 테스트 시작 (5초 단위 샘플링)")
    print("Ctrl+C로 종료할 수 있습니다.")
    print("=" * 50)
    
    # Whisper 모델 로드 (예: "base" 모델 사용, 더 높은 정확도를 원하면 "medium" 또는 "large"로 변경)
    print("Whisper 모델을 로드하는 중...")
    model = whisper.load_model("base")
    print("모델 로드 완료!")

    # PyAudio 설정
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1024
    RECORD_SECONDS = 5  # 5초 단위로 녹음 후 처리

    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)

    # 오디오 데이터를 저장할 큐
    q = queue.Queue()

    def record_audio():
        """오디오 녹음을 위한 스레드 함수"""
        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                q.put(data)
            except Exception as e:
                print(f"녹음 오류: {e}")
                break

    # 녹음 스레드 시작
    record_thread = threading.Thread(target=record_audio, daemon=True)
    record_thread.start()

    print("음성 인식을 시작합니다. 마이크에 대고 말씀하세요...")

    try:
        while True:
            # 5초간 데이터 수집
            audio_buffer = []
            for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                try:
                    audio_buffer.append(q.get(timeout=1))
                except queue.Empty:
                    continue

            if not audio_buffer:
                continue

            # numpy 배열로 변환
            audio_data = b''.join(audio_buffer)
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

            # Whisper로 한국어 텍스트 변환
            print("음성을 처리하는 중...")
            result = model.transcribe(audio_np, language="ko")
            text = result["text"].strip()
            
            if text:
                print(f"✅ 인식된 텍스트: {text}")
            else:
                print("❌ 음성이 인식되지 않았습니다.")
            print("-" * 50)

    except KeyboardInterrupt:
        print("\n\n프로그램을 종료합니다.")
    except Exception as e:
        print(f"\n오류가 발생했습니다: {e}")
    finally:
        try:
            stream.stop_stream()
            stream.close()
            audio.terminate()
            print("리소스 정리 완료.")
        except:
            pass

if __name__ == "__main__":
    main()