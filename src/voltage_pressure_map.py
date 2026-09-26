"""CH2 电压 → CH4 压力 标定换算。

三组截图表定数据（理论电压 V ↔ 实际压力 bar），对每组做线性插值后取平均。
"""

from __future__ import annotations

import numpy as np

# 三组标定：(电压 V, 压力 bar)，电压已按升序排列
_CALIBRATION_TABLES: tuple[tuple[np.ndarray, np.ndarray], ...] = (
    (
        np.array(
            [0.5180, 0.9965, 1.4750, 1.9524, 2.4318, 2.9103, 3.3897, 3.8673, 4.3471, 4.5071],
            dtype=np.float64,
        ),
        np.array(
            [1.0000, 30.9000, 60.8000, 90.6253, 120.5813, 150.4813, 180.4374, 210.2813, 240.2561, 250.2539],
            dtype=np.float64,
        ),
    ),
    (
        np.array(
            [0.5189, 0.9971, 1.4762, 1.9548, 2.4339, 2.9130, 3.3918, 3.8706, 4.3497, 4.5092],
            dtype=np.float64,
        ),
        np.array(
            [1.0561, 30.9374, 60.8748, 90.7748, 120.7121, 150.6495, 180.5682, 210.4869, 240.4243, 250.3847],
            dtype=np.float64,
        ),
    ),
    (
        np.array(
            [0.5189, 0.9971, 1.4759, 1.9548, 2.4342, 2.9127, 3.3915, 3.8706, 4.3497, 4.5092],
            dtype=np.float64,
        ),
        np.array(
            [1.0561, 30.9374, 60.8561, 90.7748, 120.7308, 150.6308, 180.5495, 210.4869, 240.4243, 250.3847],
            dtype=np.float64,
        ),
    ),
)


def voltage_to_pressure(voltage_v: float) -> float:
    """根据 CH2 电压，用三组标定曲线插值后取平均，得到修正后压力 (bar)。"""
    v = float(voltage_v)
    pressures = [
        float(np.interp(v, volts, bars))
        for volts, bars in _CALIBRATION_TABLES
    ]
    return float(np.mean(pressures))
