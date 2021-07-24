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
        return {
            0: self.Ranked,
            2: self.Pending,
            3: self.Qualified,
            5: self.Pending,
            7: self.Ranked,
            8: self.Loved
        }.get(status)

def apiStatuses(status: int) -> int:
    if status in (-2, -1, 0):
        return 0

    if status in (1, 2, 3, 4):
        return status + 1

def apiFromDirect(d_status: int) -> int:
    status = mapStatuses.from_direct(d_status)

    return {
        mapStatuses.Pending: 0,
        mapStatuses.Ranked: 1,
        mapStatuses.Approved: 2,
        mapStatuses.Qualified: 3,
        mapStatuses.Loved: 4
    }.get(status)

class scoreStatuses(Enum):
    Failed = 0
    Submitted = 1
    Best = 2
