from enum import IntEnum

class mapStatuses(IntEnum):
    NotSubmitted = -1
    Pending = 0
    Update = 1
    Ranked = 2
    Approved = 3
    Qualified = 4
    Loved = 5

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