"""Storage failures that can be reported without exposing connection credentials."""


class DatabaseUnavailable(RuntimeError):
    def __init__(self, reason="connection"):
        super().__init__("database unavailable")
        self.reason = reason
