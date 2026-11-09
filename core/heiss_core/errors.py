class HeissError(Exception):
    """Base class for expected, user-presentable errors."""


class ValidationError(HeissError):
    pass
