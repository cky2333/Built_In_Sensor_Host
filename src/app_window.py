import logging

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QStatusBar, QMessageBox,
)

from .serial_config import SerialConfigBar
from .serial_worker import SerialWorker
from .waveform_panel import WaveformPanel

_logger = logging.getLogger("app_window")


class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("机载传感器上位机")
        self.setMinimumSize(900, 700)
        self.resize(1200, 800)

        self._worker = SerialWorker()
        self._worker.data_ready.connect(self._on_data)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.port_opened.connect(self._on_port_opened)
        self._worker.port_closed.connect(self._on_port_closed)

        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self._serial_bar = SerialConfigBar()
        self._serial_bar.connect_btn.clicked.connect(self._toggle_connect)
        self._serial_bar.stroke_command.connect(self._on_stroke_command)
        layout.addWidget(self._serial_bar)

        self._waveform = WaveformPanel()
        layout.addWidget(self._waveform)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("就绪 - 请选择串口并连接")

    def _toggle_connect(self):
        if self._worker.isRunning():
            _logger.info("断开连接")
            self._worker.stop()
        else:
            port = self._serial_bar.get_port()
            baud = self._serial_bar.get_baud()
            if not port:
                QMessageBox.warning(self, "提示", "请选择串口")
                return
            _logger.info(f"连接 {port} @ {baud}")
            self._waveform.clear()
            self._worker.open(port, baud)

    def _on_port_opened(self):
        _logger.info("串口已打开")
        self._serial_bar.set_connected(True)
        self.statusBar().showMessage("已连接 - 正在接收数据...")

    def _on_port_closed(self):
        _logger.info("串口已关闭")
        self._serial_bar.set_connected(False)
        self.statusBar().showMessage("已断开")

    @Slot(float, float, float, float)
    def _on_data(self, ch1: float, ch2: float, ch3: float, ch4: float):
        # 协议 CH4 为温度(°C)；协议 CH2 指示行程（非0正行程，0负行程）
        self._serial_bar.set_temperature(ch4)
        self._serial_bar.set_stroke_from_ch2(ch2)
        self._waveform.append(ch1, ch2, ch3, ch4, temperature_c=ch4)

    @Slot(bool)
    def _on_stroke_command(self, forward: bool):
        name = "正行程" if forward else "负行程"
        if not self._worker.isRunning():
            QMessageBox.warning(self, "提示", "请先连接串口")
            return
        ok = self._worker.send_stroke(forward)
        if ok:
            self.statusBar().showMessage(f"已切换到{name}")
            _logger.info(f"已发送{name}指令")
        else:
            QMessageBox.warning(self, "提示", f"发送{name}指令失败")

    @Slot(str)
    def _on_error(self, msg: str):
        _logger.error(msg)
        QMessageBox.critical(self, "错误", msg)

    def closeEvent(self, event):
        _logger.info("关闭窗口")
        self._worker.stop()
        super().closeEvent(event)
