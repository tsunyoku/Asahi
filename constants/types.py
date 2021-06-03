from enum import IntEnum, unique

@unique
class osuTypes(IntEnum):
    # integral
    i8  = 0
    u8  = 1
    i16 = 2
    u16 = 3
    i32 = 4
    u32 = 5
    f32 = 6
    i64 = 7
    u64 = 8
    f64 = 9

    # osu
    message = 11
    channel = 12
    match = 13

    # misc
    i32_list   = 17 # 2 bytes len
    i32_list4l = 18 # 4 bytes len
    string     = 19
    raw        = 20

@unique
class teamTypes(IntEnum):
    head = 0
    tag = 1
    team = 2
    tag_team = 3

@unique
class winConditions(IntEnum):
    score = 0
    acc = 1
    combo = 2
    scorev2 = 3