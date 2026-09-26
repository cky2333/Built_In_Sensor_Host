from collections import deque

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from .temp_voltage import ch2_within_limits, measured_to_compensated
from .voltage_pressure_map import voltage_to_pressure

PLOT_HISTORY = 1000

# (显示名, 单位, 颜色, 协议通道下标 0=CH1 … 3=CH4)
# 界面顺序：CH1 → CH3 → CH2 → CH4（CH2/CH3 位置对调）
# CH2 = 温度补偿后的常温等效电压（由 CH3 + T 反解）；CH4 = f(CH2 标定)
_CHANNEL_CONFIG = (
    ("CH1 采集电压", "V", "y", 0),
    ("CH3 一次常温综合精度提升", "V", "m", 2),
    ("CH2 二次温度修正", "V", "c", 1),
    ("CH4 修正后压力值", "bar", "g", 3),
)

_VALUE_STYLE_OK = (
    "background-color: #1e1e1e; color: #00ff88;"
    "border: 1px solid #555; border-radius: 4px; padding: 4px 8px;"
)
_VALUE_STYLE_FAIL = (
    "background-color: #1e1e1e; color: #ff5555;"
    "border: 1px solid #aa3333; border-radius: 4px; padding: 4px 8px;"
)
_VALUE_STYLE_NEUTRAL = _VALUE_STYLE_OK



class WaveformPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = [deque(maxlen=PLOT_HISTORY) for _ in _CHANNEL_CONFIG]
        self._curves = []
        self._value_labels = []
        self._index = 0

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        reset_row = QHBoxLayout()
        reset_row.addStretch()
        self._reset_btn = QPushButton("重置波形")
        self._reset_btn.clicked.connect(self.clear)
        reset_row.addWidget(self._reset_btn)
        layout.addLayout(reset_row)

        value_font = QFont("Consolas", 14)
        value_font.setBold(True)

        for name, unit, color, _src in _CHANNEL_CONFIG:
            channel_box = QVBoxLayout()
            channel_box.setSpacing(4)

            header = QHBoxLayout()
            title = QLabel(f"{name} 波形")
            title.setStyleSheet("font-weight: bold;")
            header.addWidget(title)
            header.addStretch()

            value_label = QLabel(f"-- {unit}")
            value_label.setFont(value_font)
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value_label.setMinimumWidth(140)
            value_label.setStyleSheet(_VALUE_STYLE_NEUTRAL)
            header.addWidget(value_label)
            self._value_labels.append(value_label)
            channel_box.addLayout(header)

            plot = pg.PlotWidget()
            plot.setLabel("left", unit)
            plot.setLabel("bottom", "采样点")
            plot.showGrid(x=True, y=True)
            curve = plot.plot(pen=color)
            self._curves.append(curve)
            channel_box.addWidget(plot)

            layout.addLayout(channel_box)

    def clear(self):
        for data in self._data:
            data.clear()
        for curve in self._curves:
            curve.setData([], [])
        for (_, unit, _, _), label in zip(_CHANNEL_CONFIG, self._value_labels):
            label.setText(f"-- {unit}")
        self._index = 0

    def append(
        self,
        ch1: float,
        ch2: float,
        ch3: float,
        ch4: float = 0.0,
        temperature_c: float = 25.0,
    ):
        # 协议 CH4 为温度(°C)；CH3 为当前温度下测得电压 VT，反解得 CH2；
        # 界面 CH4 波形仍为压力，由补偿后 CH2 标定换算
        ch2_comp = measured_to_compensated(ch3, temperature_c)
        ch4_p = voltage_to_pressure(ch2_comp)
        proto = (ch1, ch2_comp, ch3, ch4_p)
        for data, (_, _, _, src) in zip(self._data, _CHANNEL_CONFIG):
            data.append(proto[src])
        self._index += 1

        x_min = max(0, self._index - PLOT_HISTORY)
        x = np.arange(x_min, x_min + len(self._data[0]))
        limit_ok = ch2_within_limits(ch2_comp)
        for idx, (data, curve, (_, unit, _, _), label) in enumerate(
            zip(self._data, self._curves, _CHANNEL_CONFIG, self._value_labels)
        ):
            curve.setData(x, list(data))
            label.setText(f"{data[-1]:.4f} {unit}")
            # CH2 数值框：落在验收带内绿色，超出红色
            if idx == 2 and limit_ok is False:
                label.setStyleSheet(_VALUE_STYLE_FAIL)
            elif idx == 2:
                label.setStyleSheet(_VALUE_STYLE_OK)
