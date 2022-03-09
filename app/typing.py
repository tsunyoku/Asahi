from __future__ import annotations

import struct
from typing import Any
from typing import Awaitable
from typing import Callable

from app.packets import Packet

PacketHandler = Callable[
    [bytearray, Any],
    Awaitable[bool],
]  # TODO: type-hint packet data


def read_int(data: bytearray, signed: bool = True) -> int:
    return int.from_bytes(data, "little", signed=signed)


def read_float(data: bytearray) -> float:
    return struct.unpack("<f", data)


class osuType:
    @classmethod
    def read(cls, packet: Packet) -> Any:
        ...

    @classmethod
    def write(cls, data: Any) -> bytearray:
        ...


class i8(osuType):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_int(packet.read(1))

    @classmethod
    def write(cls, data: int) -> bytearray:
        return struct.pack("<b", data)


class u8(osuType):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_int(packet.read(1), signed=False)

    @classmethod
    def write(cls, data: int) -> bytearray:
        return struct.pack("<B", data)


class i16(osuType):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_int(packet.read(2))

    @classmethod
    def write(cls, data: int) -> bytearray:
        return struct.pack("<h", data)


class u16(osuType):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_int(packet.read(2), signed=False)

    @classmethod
    def write(cls, data: int) -> bytearray:
        return struct.pack("<H", data)


class i32(osuType):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_int(packet.read(4))

    @classmethod
    def write(cls, data: int) -> bytearray:
        return struct.pack("<i", data)


class i32_list(osuType):
    @classmethod
    def read(cls, packet: Packet) -> list[int]:
        length = i16.read(packet)
        return struct.unpack(
            f"<{'I' * length}",
            packet.read(length * 4),
        )

    @classmethod
    def write(cls, data: list[int]) -> bytearray:
        buffer = bytearray(len(data).to_bytes(2, "little"))

        for item in data:
            buffer += item.to - bytes(4, "little")

        return buffer


class u32(osuType):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_int(packet.read(4), signed=False)

    @classmethod
    def write(cls, data: int) -> bytearray:
        return struct.pack("<I", data)


class f32(osuType):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_float(packet.read(4))

    @classmethod
    def write(cls, data: float) -> bytearray:
        return struct.pack("<f", data)


class i64(osuType):
    @classmethod
    def read(cls, packet: Packet) -> int:
        return read_int(packet.read(8))


class String(osuType):
    @classmethod
    def read(cls, packet: Packet) -> str:
        if u8.read(packet) != 0x0B:
            return ""

        length = shift = 0

        while True:
            body = u8.read(packet)

            length |= (body & 0b01111111) << shift
            if (body & 0b10000000) == 0:
                break

            shift += 7

        return packet.read(length).decode()

    @classmethod
    def write(cls, data: str) -> bytearray:
        encoded_string = data.encode()
        length = len(encoded_string)

        if length == 0:
            return bytearray(b"\x00")

        buffer = bytearray(b"\x0b")
        val = length

        while True:
            buffer.append(val & 0x7F)
            val >>= 7

            if val != 0:
                buffer[-1] |= 0x80
            else:
                break

        buffer += encoded_string
        return buffer
