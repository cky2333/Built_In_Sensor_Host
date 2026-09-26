import struct
from enum import Enum, auto

FRAME_HEADER = bytes([0xAA, 0x55])
FRAME_TAIL = 0x5A


class _ParseState(Enum):
    IDLE = auto()
    GOT_AA = auto()
    GOT_HEADER = auto()
    GOT_DATA = auto()


class FrameParser:
    def __init__(self):
        self._state = _ParseState.IDLE
        self._buffer = bytearray()

    def feed(self, data: bytes):
        self._buffer.extend(data)
        frames = []
        while True:
            if self._state == _ParseState.IDLE:
                idx = self._buffer.find(0xAA)
                if idx < 0:
                    self._buffer.clear()
                    break
                self._buffer = self._buffer[idx:]
                self._state = _ParseState.GOT_AA
            elif self._state == _ParseState.GOT_AA:
                if len(self._buffer) < 2:
                    break
                if self._buffer[1] == 0x55:
                    self._buffer = self._buffer[2:]
                    self._state = _ParseState.GOT_HEADER
                else:
                    self._buffer = self._buffer[1:]
                    self._state = _ParseState.IDLE
            elif self._state == _ParseState.GOT_HEADER:
                if len(self._buffer) < 16:
                    break
                ch1 = struct.unpack('<f', self._buffer[0:4])[0]
                ch2 = struct.unpack('<f', self._buffer[4:8])[0]
                ch3 = struct.unpack('<f', self._buffer[8:12])[0]
                ch4 = struct.unpack('<f', self._buffer[12:16])[0]
                self._buffer = self._buffer[16:]
                self._pending = (ch1, ch2, ch3, ch4)
                self._state = _ParseState.GOT_DATA
            elif self._state == _ParseState.GOT_DATA:
                if len(self._buffer) < 1:
                    break
                if self._buffer[0] == FRAME_TAIL:
                    frames.append(self._pending)
                    self._buffer = self._buffer[1:]
                    self._state = _ParseState.IDLE
                else:
                    self._buffer = self._buffer[1:]
                    self._state = _ParseState.IDLE
        return frames
