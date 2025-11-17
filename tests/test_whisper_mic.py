#!/usr/bin/env python3
"""
whisper-mic 라이브러리 테스트
whisper-mic 라이브러리를 사용한 간단한 음성 인식 테스트입니다.

실행 방법:
  python tests/test_whisper_mic.py

주의: whisper-mic 패키지가 설치되어 있어야 합니다.
  pip install whisper-mic
"""

from whisper_mic import WhisperMic

def main():
    """whisper-mic를 사용한 음성 인식 테스트"""
    print("🎤 whisper-mic 테스트 시작")
    print("마이크에 대고 말씀하세요...")
    
    try:
        mic = WhisperMic()
        result = mic.listen()
        print(f"인식된 텍스트: {result}")
    except ImportError:
        print("❌ whisper-mic 패키지가 설치되지 않았습니다.")
        print("설치 명령: pip install whisper-mic")
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()