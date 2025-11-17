# STT Demo Tests

이 폴더에는 다양한 음성 인식(STT) 방법들을 테스트하는 예제 파일들이 있습니다.

## 📁 테스트 파일들

### 1. Whisper 모델 테스트
- **`test_whisper_basic.py`** - 기본 Whisper 모델 (5초 단위 샘플링)
- **`test_whisper_large.py`** - Whisper large-v3 모델 (고성능)
- **`test_whisper_mic.py`** - whisper-mic 라이브러리 테스트

### 2. GUI 테스트
- **`test_pyqt5_gui.py`** - PyQt5 GUI + 실시간 오디오 시각화

### 3. Vosk 모델 테스트  
- **`test_vosk_korean.py`** - 경량 한국어 Vosk 모델

## 🚀 실행 방법

```bash
# 가상환경 활성화 (프로젝트 루트에서)
cd /Users/hyun/workspace/stt_demo
source venv/bin/activate

# 또는 직접 가상환경 Python 사용
./venv/bin/python tests/test_whisper_basic.py
./venv/bin/python tests/test_whisper_large.py
./venv/bin/python tests/test_whisper_mic.py
./venv/bin/python tests/test_pyqt5_gui.py
./venv/bin/python tests/test_vosk_korean.py
```

## 📋 필수 조건

- 마이크가 연결되어 있어야 함
- PyAudio, Whisper, Vosk 등 관련 패키지 설치 필요
- GUI 테스트의 경우 PyQt5 설치 필요

## 💡 참고사항

- **Whisper 모델**: 첫 실행 시 모델 다운로드로 시간이 걸릴 수 있음
- **Vosk 모델**: `vosk-model-small-ko-0.22` 폴더가 프로젝트 루트에 있어야 함
- **GUI 테스트**: 한글 폰트 경고가 나타날 수 있지만 정상 동작함

각 테스트는 독립적으로 실행할 수 있으며, 다양한 STT 접근 방법을 비교해볼 수 있습니다.