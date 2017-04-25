# -*- coding: utf-8 -*-


class FelisError(BaseException):
    pass


class FSMError(FelisError):
    pass

class FilesystemError(FelisError):
    pass


class SnapshotError(FelisError):
    pass


class CloneError(FelisError):
    pass


class WorldError(FelisError):
    pass


class SkelError(FelisError):
    pass


class JailError(FelisError):
    pass


class ShellCmdExecFailed(FelisError):
    pass


class TaskFailed(FelisError):
    pass


class RctlUpdateFailed(FelisError):
    pass


class ZfsStatUpdateFailed(FelisError):
    pass
