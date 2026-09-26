import logging
import threading

import serial
from PySide6.QtCore import QThread, Signal

from .frame_parser import FrameParser

_logger = logging.getLogger("serial_worker")

CMD_STROKE_FORWARD = bytes([0xAA, 0x01, 0x01, 0x5A])  # 正行程
CMD_STROKE_REVERSE = bytes([0xAA, 0x01, 0x00, 0x5A])  # 负行程


class SerialWorker(QThread):
    data_ready = Signal(float, float, float, float)
    error_occurred = Signal(str)
    port_opened = Signal()
    port_closed = Signal()

    def __init__(self):
        super().__init__()
        self._serial: serial.Serial | None = None
        self._running = False
        self._parser = FrameParser()
        self._io_lock = threading.Lock()

    def open(self, port: str, baudrate: int):
        self._port = port
        self._baudrate = baudrate
        self._running = True
        self.start()

    def stop(self):
        self._running = False
        if self._serial and self._serial.is_open:
            try:
                self._serial.cancel_read()
            except Exception:
                pass
        self.wait(2000)

    def write(self, data: bytes) -> bool:
        with self._io_lock:
            if not self._serial or not self._serial.is_open:
                return False
            try:
                self._serial.write(data)
                _logger.info(f"串口发送: {data.hex(' ').upper()}")
                return True
            except Exception as e:
                _logger.error(f"串口发送失败: {e}")
                self.error_occurred.emit(f"串口发送失败: {e}")
                return False

    def send_stroke(self, forward: bool) -> bool:
        cmd = CMD_STROKE_FORWARD if forward else CMD_STROKE_REVERSE
        return self.write(cmd)

    def run(self):
        try:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1,
            )
            _logger.info(f"串口 {self._port} 已打开, 波特率 {self._baudrate}")
        except Exception as e:
            _logger.error(f"打开串口失败: {e}")
            self.error_occurred.emit(f"打开串口失败: {e}")
            return

        self.port_opened.emit()
        self._parser = FrameParser()

        try:
            while self._running:
                try:
                    with self._io_lock:
                        data = self._serial.read(1024) if self._serial else b""
                except serial.SerialException as e:
                    _logger.error(f"串口读取错误: {e}")
                    self.error_occurred.emit(f"串口读取错误: {e}")
                    break

                if data:
                    frames = self._parser.feed(data)
                    for ch1, ch2, ch3, ch4 in frames:
                        self.data_ready.emit(ch1, ch2, ch3, ch4)
        finally:
            with self._io_lock:
                if self._serial and self._serial.is_open:
                    try:
                        self._serial.close()
                        _logger.info(f"串口 {self._port} 已关闭")
                    except Exception:
                        pass
            self.port_closed.emit()
