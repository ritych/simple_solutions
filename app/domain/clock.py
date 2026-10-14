import time
from abc import ABC, abstractmethod


class Clock(ABC):
    """Source of the UNIX timestamp written next to a price."""

    @abstractmethod
    def unix_timestamp(self) -> int:
        """Current UTC time as UNIX seconds."""


class SystemClock(Clock):
    def unix_timestamp(self) -> int:
        return int(time.time())
