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

def strStatuses(status: str):
    return {
        'rank': mapStatuses.Ranked,
        'love': mapStatuses.Loved,
        'ranked': mapStatuses.Ranked, # because people are stupid
        'loved': mapStatuses.Loved # because people are stupid
    }.get(status, mapStatuses.Pending)

def apiStatuses(status: int):
    if status in (-2, -1, 0):
        return 0

    if status in (1, 2, 3, 4):
        return status + 1

class scoreStatuses(Enum):
    Failed = 0
    Submitted = 1
    Best = 2
