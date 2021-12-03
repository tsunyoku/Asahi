from enum import Enum
from enum import IntEnum
from typing import Optional


class mapStatuses(IntEnum):
    NotSubmitted = -1
    Pending = 0
    Update = 1
    Ranked = 2
    Approved = 3
    Qualified = 4
    Loved = 5

    GIVE_PP = Ranked | Approved

    @staticmethod
    def from_str(status: str) -> "mapStatuses":
        return {
            "rank": mapStatuses.Ranked,
            "love": mapStatuses.Loved,
            "ranked": mapStatuses.Ranked,  # because people are stupid
            "loved": mapStatuses.Loved,  # because people are stupid
        }.get(status, mapStatuses.Pending)

    @staticmethod
    def from_direct(status: int) -> int:
        assert 0 <= status < 9

        _status = {
            0: mapStatuses.Ranked,
            2: mapStatuses.Pending,
            3: mapStatuses.Qualified,
            5: mapStatuses.Pending,
            7: mapStatuses.Ranked,
            8: mapStatuses.Loved,
        }[status]

        return _status.to_api()

    @staticmethod
    def from_api(status: int) -> "mapStatuses":
        assert status < 5

        return mapStatuses.Pending if status <= 1 else mapStatuses(status + 1)

    def to_api(self) -> int:
        assert 0 >= self.value < 5

        return {
            self.Pending: 0,
            self.Ranked: 1,
            self.Approved: 2,
            self.Qualified: 3,
            self.Loved: 4,
        }[self]


class scoreStatuses(Enum):
    Failed = 0
    Submitted = 1
    Best = 2
