from enum import Enum
from enum import IntEnum


class mapStatuses(IntEnum):
    NotSubmitted = -1
    Pending = 0
    Update = 1
    Ranked = 2
    Approved = 3
    Qualified = 4
    Loved = 5

    GIVE_PP = Ranked | Approved

    @classmethod
    def from_str(cls, status: str) -> "mapStatuses":
        return {
            "rank": cls.Ranked,
            "love": cls.Loved,
            "ranked": cls.Ranked,  # because people are stupid
            "loved": cls.Loved,  # because people are stupid
        }.get(status, cls.Pending)

    @classmethod
    def from_direct(cls, status: int) -> "mapStatuses":
        _status = {
            0: cls.Ranked,
            2: cls.Pending,
            3: cls.Qualified,
            5: cls.Pending,
            7: cls.Ranked,
            8: cls.Loved,
        }.get(status)

        return cls.to_api(_status)

    @classmethod
    def from_api(cls, status: int) -> "mapStatuses":
        if status in (-2, -1, 0):
            return cls.Pending

        if status in (1, 2, 3, 4):
            return cls(status + 1)

    def to_api(self) -> int:
        return {
            self.Pending: 0,
            self.Ranked: 1,
            self.Approved: 2,
            self.Qualified: 3,
            self.Loved: 4,
        }.get(self)


class scoreStatuses(Enum):
    Failed = 0
    Submitted = 1
    Best = 2
