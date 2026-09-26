"""温度补偿：由当前温度下测得电压反解常温等效电压 V25。

物理模型（与原先正向公式一致）：
    VT = V25 + (T - 25) / 1000 * (0.035664*V25^2 - 0.156065*V25 + 0.349390)

上位机中：
    CH3 = 当前温度 T 下测得电压（视为 VT）
    CH2 = 温度补偿后的常温等效电压 V25（应与温度无关，落在验收上下限内）
"""

from __future__ import annotations

import math

_A = 0.035664
_B = -0.156065
_C = 0.349390

# 验收点：25 / 80 / 120°C 下 CH2 目标相同（温度补偿后应落在此带内）
_CH2_TARGETS = (
    0.5180040,
    1.4782440,
    2.4384840,
    3.3987240,
    4.3589640,
)
_CH2_LOWER = (
    0.5160035,
    1.4762435,
    2.4364835,
    3.3967235,
    4.3569635,
)
_CH2_UPPER = (
    0.5200045,
    1.4802445,
    2.4404845,
    3.4007245,
    4.3609645,
)


def measured_to_compensated(v_measured: float, temperature_c: float) -> float:
    """
    由温度 T 下测得电压 VT（CH3）反解常温等效电压 V25（CH2）。

    当 T=25 时返回 VT 本身；其余温度解二次方程，取更接近 VT 的实根。
    """
    vt = float(v_measured)
    delta = (float(temperature_c) - 25.0) / 1000.0
    if abs(delta) < 1e-15:
        return vt

    # a*δ*V^2 + (1 + b*δ)*V + (c*δ - VT) = 0
    qa = _A * delta
    qb = 1.0 + _B * delta
    qc = _C * delta - vt

    if abs(qa) < 1e-18:
        return (-qc / qb) if abs(qb) > 1e-18 else vt

    disc = qb * qb - 4.0 * qa * qc
    if disc < 0.0:
        disc = 0.0
    root = math.sqrt(disc)
    v1 = (-qb + root) / (2.0 * qa)
    v2 = (-qb - root) / (2.0 * qa)
    return v1 if abs(v1 - vt) <= abs(v2 - vt) else v2


# 兼容旧函数名：语义已改为「测得电压 + 温度 → 补偿后 CH2」
def room_voltage_to_temp_voltage(v25: float, temperature_c: float) -> float:
    return measured_to_compensated(v25, temperature_c)


def ch2_limit_band(voltage: float) -> tuple[float, float] | None:
    """按标定电压插值得到该点允许下限/上限；超出标定范围返回 None。"""
    v = float(voltage)
    xs = _CH2_TARGETS
    eps = 1e-9
    if v < xs[0] - eps or v > xs[-1] + eps:
        return None
    v = min(max(v, xs[0]), xs[-1])
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        if x0 <= v <= x1:
            t = 0.0 if x1 == x0 else (v - x0) / (x1 - x0)
            lo = _CH2_LOWER[i] + t * (_CH2_LOWER[i + 1] - _CH2_LOWER[i])
            hi = _CH2_UPPER[i] + t * (_CH2_UPPER[i + 1] - _CH2_UPPER[i])
            return lo, hi
    return _CH2_LOWER[-1], _CH2_UPPER[-1]


def ch2_within_limits(voltage: float) -> bool | None:
    """
    检查补偿后 CH2 是否落在验收上下限内。
    优先对照最近标定点（与截图 5 点一致）；不在标定跨度内返回 None。
    """
    v = float(voltage)
    best_i = min(range(len(_CH2_TARGETS)), key=lambda i: abs(_CH2_TARGETS[i] - v))
    # 靠近某个验收点时，用该点的固定上下限判定
    if abs(_CH2_TARGETS[best_i] - v) <= 0.01:
        return _CH2_LOWER[best_i] <= v <= _CH2_UPPER[best_i]
    band = ch2_limit_band(v)
    if band is None:
        return None
    lo, hi = band
    return lo <= v <= hi
