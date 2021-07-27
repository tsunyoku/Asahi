from enum import IntFlag

class osuFlags(IntFlag):
    SpeedHackDetected = 1 << 1
    IncorrectModValue = 1 << 2
    MultipleOsuClients = 1 << 3
    ChecksumFailure = 1 << 4
    FlashlightChecksumIncorrect = 1 << 5
    OsuExecutableChecksum = 1 << 6
    MissingProcessesInList = 1 << 7
    FlashLightImageHack = 1 << 8
    SpinnerHack = 1 << 9
    TransparentWindow = 1 << 10
    FastPress = 1 << 11

    RawMouseDiscrepancy = 1 << 12
    RawKeyboardDiscrepancy = 1 << 13

    RunWithLdFlag = 1 << 14
    ConsoleOpen = 1 << 15
    ExtraThreads = 1 << 16
    HQAssembly = 1 << 17
    HQFile = 1 << 18
    RegistryEdits = 1 << 19

    SQL2Library = 1 << 20
    libeay32Library = 1 << 21
    aqnMenuSample = 1 << 22

    HQ_RELATED = RunWithLdFlag | ConsoleOpen | ExtraThreads | HQAssembly | HQFile | RegistryEdits
    AQN_RELATED = SQL2Library | libeay32Library | aqnMenuSample
    AUTO_BOT = RawMouseDiscrepancy | RawKeyboardDiscrepancy
    FL_CHEAT = FlashlightChecksumIncorrect | FlashLightImageHack
