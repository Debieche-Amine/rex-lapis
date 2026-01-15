from enum import Enum

class ExecutorState(str, Enum):
    """Enumeration of possible trade lifecycle states."""
    PENDING_ENTRY = "PENDING_ENTRY"
    PLACED_ENTRY = "PLACED_ENTRY"
    FILLED_WAIT = "FILLED_WAIT"
    PLACED_EXIT = "PLACED_EXIT"
    COMPLETED = "COMPLETED"