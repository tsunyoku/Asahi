# type: ignore
from __future__ import annotations

from . import cache
from . import services
from . import sessions
from app.typing import PacketHandler

PACKETS: dict[int, PacketHandler] = {}
RESTRICTED_PACKETS: dict[int, PacketHandler] = {}
