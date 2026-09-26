import logging

import serial.tools.list_ports
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDoubleSpinBox, QHBoxLayout,
    QLabel, QPushButton, QWidget,
)

_logger = logging.getLogger("serial_config")


class SerialConfigBar(QWidget):
    """串口配置栏；行程切换由用户点击触发 stroke_command。"""

    stroke_command = Signal(bool)  # True=正行程, False=负行程

    def __init__(self, parent=None):
        super().__init__(parent)
        self._syncing_stroke = False
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("COM口:"))

        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(150)
        self._port_combo.setEditable(True)
        self._refresh_ports()
        layout.addWidget(self._port_combo)

        layout.addWidget(QLabel("波特率:"))

        self._baud_combo = QComboBox()
        self._baud_combo.setEditable(True)
        self._baud_combo.addItems([
            "9600", "19200", "38400", "57600", "115200",
            "230400", "460800", "921600", "1000000", "2000000",
        ])
        self._baud_combo.setCurrentText("115200")
        layout.addWidget(self._baud_combo)

        self._refresh_btn = QPushButton("刷新")
        self._refresh_btn.clicked.connect(self._refresh_ports)
        layout.addWidget(self._refresh_btn)

        self._connect_btn = QPushButton("连接")
        layout.addWidget(self._connect_btn)

        self._status_label = QLabel("● 未连接")
        layout.addWidget(self._status_label)

        layout.addWidget(QLabel("温度(°C):"))
        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(-100.0, 200.0)
        self._temp_spin.setDecimals(2)
        self._temp_spin.setValue(25.0)
        self._temp_spin.setMinimumWidth(90)
        self._temp_spin.setReadOnly(True)
        self._temp_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self._temp_spin.setToolTip("温度来自下位机上传的 CH4，不可手动修改")
        layout.addWidget(self._temp_spin)

        layout.addWidget(QLabel("行程:"))
        self._stroke_forward_btn = QPushButton("正行程")
        self._stroke_forward_btn.setCheckable(True)
        self._stroke_forward_btn.setEnabled(False)
        self._stroke_forward_btn.setToolTip("切换正行程，发送 AA 01 01 5A")
        layout.addWidget(self._stroke_forward_btn)

        self._stroke_reverse_btn = QPushButton("负行程")
        self._stroke_reverse_btn.setCheckable(True)
        self._stroke_reverse_btn.setChecked(True)
        self._stroke_reverse_btn.setEnabled(False)
        self._stroke_reverse_btn.setToolTip("切换负行程，发送 AA 01 00 5A")
        layout.addWidget(self._stroke_reverse_btn)

        self._stroke_group = QButtonGroup(self)
        self._stroke_group.setExclusive(True)
        self._stroke_group.addButton(self._stroke_forward_btn, 1)
        self._stroke_group.addButton(self._stroke_reverse_btn, 0)
        self._stroke_group.idClicked.connect(self._on_stroke_id_clicked)

        layout.addStretch()

    def _refresh_ports(self):
        self._port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self._port_combo.addItem(f"{p.device} - {p.description}", p.device)

    def _on_stroke_id_clicked(self, button_id: int):
        if self._syncing_stroke:
            return
        forward = button_id == 1
        _logger.info(f"用户切换行程: {'正行程' if forward else '负行程'}")
        self.stroke_command.emit(forward)

    @property
    def connect_btn(self) -> QPushButton:
        return self._connect_btn

    @property
    def refresh_btn(self) -> QPushButton:
        return self._refresh_btn

    @property
    def port_combo(self) -> QComboBox:
        return self._port_combo

    @property
    def baud_combo(self) -> QComboBox:
        return self._baud_combo

    @property
    def status_label(self) -> QLabel:
        return self._status_label

    def get_port(self) -> str:
        return self._port_combo.currentData() or self._port_combo.currentText()

    def get_baud(self) -> int:
        return int(self._baud_combo.currentText())

    def get_temperature(self) -> float:
        return float(self._temp_spin.value())

    def set_temperature(self, temperature_c: float):
        """由下位机 CH4 刷新只读温度显示。"""
        self._temp_spin.setValue(float(temperature_c))

    def set_stroke_from_ch2(self, ch2: float):
        """上传 CH2≠0 显示正行程，CH2=0 显示负行程（不触发下发）。"""
        forward = abs(float(ch2)) > 1e-12
        target = self._stroke_forward_btn if forward else self._stroke_reverse_btn
        if target.isChecked():
            return
        self._syncing_stroke = True
        try:
            target.setChecked(True)
        finally:
            self._syncing_stroke = False

    def is_stroke_forward(self) -> bool:
        return self._stroke_forward_btn.isChecked()

    @property
    def temp_spin(self) -> QDoubleSpinBox:
        return self._temp_spin

    def set_connected(self, connected: bool):
        self._port_combo.setEnabled(not connected)
        self._baud_combo.setEnabled(not connected)
        self._stroke_forward_btn.setEnabled(connected)
        self._stroke_reverse_btn.setEnabled(connected)
        if connected:
            self._connect_btn.setText("断开")
            self._status_label.setText("● 已连接")
            self._status_label.setStyleSheet("color: green;")
        else:
            self._connect_btn.setText("连接")
            self._status_label.setText("● 未连接")
            self._status_label.setStyleSheet("color: gray;")
