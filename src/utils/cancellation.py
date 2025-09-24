class CancellationRequested(Exception):
    """Raised to cooperatively abort long-running tasks on user request."""
    pass

__all__ = ["CancellationRequested"]

