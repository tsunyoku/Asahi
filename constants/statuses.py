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

def strStatuses(status: str) -> mapStatuses:
    return {
        'rank': mapStatuses.Ranked,
        'love': mapStatuses.Loved,
        'ranked': mapStatuses.Ranked, # because people are stupid
        'loved': mapStatuses.Loved # because people are stupid
    }.get(status, mapStatuses.Pending)

def directStatuses(status: int) -> mapStatuses:
    return {
        0: mapStatuses.Ranked,
        2: mapStatuses.Pending,
        3: mapStatuses.Qualified,
        5: mapStatuses.Pending,
        7: mapStatuses.Ranked,
        8: mapStatuses.Loved
    }.get(status)

def apiStatuses(status: int) -> int:
    if status in (-2, -1, 0):
        return 0

    if status in (1, 2, 3, 4):
        return status + 1

def apiFromDirect(d_status: int) -> int:
    status = directStatuses(d_status)

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
