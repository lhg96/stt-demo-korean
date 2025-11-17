"""
Audio Visualizer Widget - 오디오 시각화 위젯
실시간 파형과 주파수 스펙트럼을 표시
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.style as mplstyle
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QSlider, QLabel
from PyQt5.QtCore import QTimer, Qt

# Matplotlib 다크 테마 설정
mplstyle.use('dark_background')


class AudioVisualizerWidget(QWidget):
    """오디오 시각화 위젯 클래스"""
    
    def __init__(self, parent=None):
        """
        AudioVisualizerWidget 초기화
        
        Args:
            parent: 부모 위젯
        """
        super().__init__(parent)
        
        # 데이터 저장
        self.audio_data = np.zeros(1024)
        self.audio_history = []
        self.max_history_length = 100
        
        # 시각화 옵션
        self.show_waveform = True
        self.show_spectrum = True
        self.show_spectrogram = False
        self.auto_scale = True
        self.update_rate = 30  # FPS
        
        # 색상 설정
        self.waveform_color = 'cyan'
        self.spectrum_color = 'yellow'
        self.spectrogram_colormap = 'viridis'
        
        self.setup_ui()
        self.setup_plots()
        self.setup_timer()

    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout()
        
        # 컨트롤 패널
        control_layout = QHBoxLayout()
        
        # 체크박스들
        self.waveform_check = QCheckBox("파형 표시")
        self.waveform_check.setChecked(True)
        self.waveform_check.stateChanged.connect(self.on_waveform_toggle)
        
        self.spectrum_check = QCheckBox("스펙트럼 표시") 
        self.spectrum_check.setChecked(True)
        self.spectrum_check.stateChanged.connect(self.on_spectrum_toggle)
        
        self.spectrogram_check = QCheckBox("스펙트로그램")
        self.spectrogram_check.stateChanged.connect(self.on_spectrogram_toggle)
        
        self.autoscale_check = QCheckBox("자동 스케일")
        self.autoscale_check.setChecked(True)
        self.autoscale_check.stateChanged.connect(self.on_autoscale_toggle)
        
        # 업데이트 레이트 슬라이더
        self.update_rate_label = QLabel(f"업데이트: {self.update_rate}FPS")
        self.update_rate_slider = QSlider(Qt.Horizontal)
        self.update_rate_slider.setRange(10, 60)
        self.update_rate_slider.setValue(self.update_rate)
        self.update_rate_slider.valueChanged.connect(self.on_update_rate_changed)
        
        # 클리어 버튼
        self.clear_button = QPushButton("화면 지우기")
        self.clear_button.clicked.connect(self.clear_plots)
        
        # 레이아웃에 추가
        control_layout.addWidget(self.waveform_check)
        control_layout.addWidget(self.spectrum_check)
        control_layout.addWidget(self.spectrogram_check)
        control_layout.addWidget(self.autoscale_check)
        control_layout.addStretch()
        control_layout.addWidget(self.update_rate_label)
        control_layout.addWidget(self.update_rate_slider)
        control_layout.addWidget(self.clear_button)
        
        # matplotlib 캔버스
        self.setup_canvas()
        
        layout.addLayout(control_layout)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def setup_canvas(self):
        """matplotlib 캔버스 설정"""
        # 서브플롯 개수 결정
        subplot_count = sum([self.show_waveform, self.show_spectrum, self.show_spectrogram])
        subplot_count = max(1, subplot_count)
        
        self.figure, self.axes = plt.subplots(subplot_count, 1, figsize=(10, 6))
        
        # 단일 서브플롯인 경우 리스트로 변환
        if not isinstance(self.axes, np.ndarray):
            self.axes = [self.axes]
        
        self.canvas = FigureCanvas(self.figure)
        
        # 여백 조정
        self.figure.tight_layout(pad=2.0)

    def setup_plots(self):
        """플롯 초기 설정"""
        self.update_plot_layout()

    def setup_timer(self):
        """업데이트 타이머 설정"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plots)
        self.start_updates()

    def start_updates(self):
        """업데이트 시작"""
        interval = int(1000 / self.update_rate)  # ms
        self.update_timer.start(interval)

    def stop_updates(self):
        """업데이트 중지"""
        self.update_timer.stop()

    def update_plot_layout(self):
        """플롯 레이아웃 업데이트"""
        # 기존 캔버스 제거
        if hasattr(self, 'canvas'):
            self.layout().removeWidget(self.canvas)
            self.canvas.deleteLater()
        
        # 새 캔버스 생성
        self.setup_canvas()
        self.layout().addWidget(self.canvas)
        
        # 플롯 초기화
        for ax in self.axes:
            ax.clear()
            ax.set_facecolor('black')

    def update_visualization(self, audio_data: np.ndarray):
        """
        오디오 시각화 업데이트
        
        Args:
            audio_data: 입력 오디오 데이터
        """
        # 데이터 저장
        self.audio_data = audio_data.copy()
        
        # 히스토리 업데이트
        self.audio_history.append(audio_data.copy())
        if len(self.audio_history) > self.max_history_length:
            self.audio_history.pop(0)

    def update_plots(self):
        """플롯 업데이트 (타이머에 의해 호출)"""
        if len(self.audio_data) == 0:
            return
        
        ax_index = 0
        
        try:
            # 파형 그래프
            if self.show_waveform and ax_index < len(self.axes):
                self.update_waveform_plot(self.axes[ax_index])
                ax_index += 1
            
            # 주파수 스펙트럼
            if self.show_spectrum and ax_index < len(self.axes):
                self.update_spectrum_plot(self.axes[ax_index])
                ax_index += 1
            
            # 스펙트로그램
            if self.show_spectrogram and ax_index < len(self.axes):
                self.update_spectrogram_plot(self.axes[ax_index])
                ax_index += 1
            
            # 캔버스 업데이트
            self.canvas.draw()
            
        except Exception as e:
            print(f"플롯 업데이트 오류: {str(e)}")

    def update_waveform_plot(self, ax):
        """파형 플롯 업데이트"""
        ax.clear()
        
        # 시간 축 생성
        time_axis = np.linspace(0, len(self.audio_data) / 16000, len(self.audio_data))
        
        # 파형 플롯
        ax.plot(time_axis, self.audio_data, color=self.waveform_color, linewidth=1)
        
        # 축 설정
        if self.auto_scale:
            ax.set_ylim([-1.1, 1.1])
        else:
            data_min, data_max = np.min(self.audio_data), np.max(self.audio_data)
            margin = 0.1 * (data_max - data_min)
            ax.set_ylim([data_min - margin, data_max + margin])
        
        ax.set_xlim([0, max(0.1, time_axis[-1])])
        ax.set_xlabel('시간 (초)', color='white')
        ax.set_ylabel('진폭', color='white')
        ax.set_title('실시간 파형', color='white')
        ax.set_facecolor('black')
        ax.grid(True, alpha=0.3)

    def update_spectrum_plot(self, ax):
        """스펙트럼 플롯 업데이트"""
        ax.clear()
        
        # FFT 계산
        fft = np.fft.fft(self.audio_data)
        freqs = np.fft.fftfreq(len(fft), 1/16000)
        magnitude = np.abs(fft)
        
        # 양의 주파수만 표시
        positive_freqs = freqs[:len(freqs)//2]
        positive_magnitude = magnitude[:len(magnitude)//2]
        
        # 로그 스케일 적용 (dB)
        magnitude_db = 20 * np.log10(positive_magnitude + 1e-10)
        
        # 스펙트럼 플롯
        ax.plot(positive_freqs, magnitude_db, color=self.spectrum_color, linewidth=1)
        
        # 축 설정
        ax.set_xlim([0, 8000])  # 8kHz까지 표시
        if self.auto_scale:
            ax.set_ylim([np.max(magnitude_db) - 60, np.max(magnitude_db) + 5])
        
        ax.set_xlabel('주파수 (Hz)', color='white')
        ax.set_ylabel('크기 (dB)', color='white')
        ax.set_title('주파수 스펙트럼', color='white')
        ax.set_facecolor('black')
        ax.grid(True, alpha=0.3)

    def update_spectrogram_plot(self, ax):
        """스펙트로그램 플롯 업데이트"""
        if len(self.audio_history) < 10:
            return
        
        ax.clear()
        
        # 스펙트로그램 데이터 준비
        spectrogram_data = []
        for audio_chunk in self.audio_history[-50:]:  # 최근 50개 청크
            fft = np.fft.fft(audio_chunk)
            magnitude = np.abs(fft[:len(fft)//2])
            magnitude_db = 20 * np.log10(magnitude + 1e-10)
            spectrogram_data.append(magnitude_db)
        
        if len(spectrogram_data) > 0:
            spectrogram_array = np.array(spectrogram_data).T
            
            # 스펙트로그램 표시
            im = ax.imshow(
                spectrogram_array, 
                aspect='auto',
                origin='lower',
                cmap=self.spectrogram_colormap,
                interpolation='nearest'
            )
            
            # 축 설정
            ax.set_xlabel('시간', color='white')
            ax.set_ylabel('주파수 빈', color='white')
            ax.set_title('스펙트로그램', color='white')
            ax.set_facecolor('black')

    def clear_plots(self):
        """플롯 지우기"""
        self.audio_history.clear()
        for ax in self.axes:
            ax.clear()
            ax.set_facecolor('black')
        self.canvas.draw()

    def on_waveform_toggle(self, state):
        """파형 표시 토글"""
        self.show_waveform = bool(state)
        self.update_plot_layout()

    def on_spectrum_toggle(self, state):
        """스펙트럼 표시 토글"""
        self.show_spectrum = bool(state)
        self.update_plot_layout()

    def on_spectrogram_toggle(self, state):
        """스펙트로그램 표시 토글"""
        self.show_spectrogram = bool(state)
        self.update_plot_layout()

    def on_autoscale_toggle(self, state):
        """자동 스케일 토글"""
        self.auto_scale = bool(state)

    def on_update_rate_changed(self, value):
        """업데이트 레이트 변경"""
        self.update_rate = value
        self.update_rate_label.setText(f"업데이트: {value}FPS")
        
        # 타이머 재시작
        self.stop_updates()
        self.start_updates()

    def set_colors(self, waveform_color='cyan', spectrum_color='yellow'):
        """색상 설정"""
        self.waveform_color = waveform_color
        self.spectrum_color = spectrum_color

    def get_visualization_info(self) -> dict:
        """시각화 정보 반환"""
        return {
            "show_waveform": self.show_waveform,
            "show_spectrum": self.show_spectrum,
            "show_spectrogram": self.show_spectrogram,
            "auto_scale": self.auto_scale,
            "update_rate": self.update_rate,
            "history_length": len(self.audio_history),
            "max_history_length": self.max_history_length
        }

    def closeEvent(self, event):
        """위젯 종료 시"""
        self.stop_updates()
        event.accept()