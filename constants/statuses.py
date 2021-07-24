from enum import IntEnum, Enum

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
    def from_str(self, status: str):
        return {
            'rank': self.Ranked,
            'love': self.Loved,
            'ranked': self.Ranked, # because people are stupid
            'loved': self.Loved # because people are stupid
        }.get(status, self.Pending)

    @classmethod
    def from_direct(self, status: int):
        _status = {
            0: self.Ranked,
            2: self.Pending,
            3: self.Qualified,
            5: self.Pending,
            7: self.Ranked,
            8: self.Loved
        }.get(status)

        return self.to_api(_status)

    @classmethod
    def from_api(self, status: int):
        if status in (-2, -1, 0):
            return self.Pending

        if status in (1, 2, 3, 4):
            return self(status + 1)

    def to_api(self) -> int:
        return {
            self.Pending: 0,
            self.Ranked: 1,
            self.Approved: 2,
            self.Qualified: 3,
            self.Loved: 4
        }.get(self)

class scoreStatuses(Enum):
    Failed = 0
    Submitted = 1
    Best = 2
