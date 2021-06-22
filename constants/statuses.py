from enum import IntEnum, Enum

class mapStatuses(IntEnum):
    NotSubmitted = -1
    Pending = 0
    Update = 1
    Ranked = 2
    Approved = 3
    Qualified = 4
    Loved = 5

def strStatuses(status: str):
    if status == 'rank':
        return mapStatuses.Ranked
    elif status == 'love':
        return mapStatuses.Loved
    else:
        return mapStatuses.Pending

def apiStatuses(status: int):
    if status in [-2, -1, 0]:
        ns = 0
    elif status == 1:
        ns = 2
    elif status == 2:
        ns = 3
    elif status == 3:
        ns = 4
    elif status == 4:
        ns = 5

    return ns

class scoreStatuses(Enum):
    Failed = 0
    Submitted = 1
    Best = 2