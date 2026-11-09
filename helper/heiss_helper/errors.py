class HelperError(Exception):
    """Expected error with a stable D-Bus error name suffix."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code      # Invalid | NotAuthorized | Busy | Failed
        self.message = message


def invalid(msg):
    return HelperError("Invalid", msg)
