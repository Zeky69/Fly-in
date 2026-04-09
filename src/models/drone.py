from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from .zone import Zone
from .connection import Connection


class DroneStatus(Enum):
    WAITING = "waiting"
    IN_TRANSIT = "in_transit"
    MOVING = "moving"
    ARRIVED = "arrived"


@dataclass
class Drone:
    id: int
    path: list[Zone] = field(default_factory=list)
    path_index: int = 0
    status: DroneStatus = DroneStatus.WAITING
    transit_turns_left: int = 0
    transit_connection: Optional[Connection] = None

    def identifier(self) -> str:
        return f"D{self.id}"

    def __str__(self) -> str:
        return self.identifier()

    def has_arrived(self) -> bool:
        return self.path_index >= len(self.path) - 1

    def next_zone(self) -> Optional[Zone]:
        next_index = self.path_index + 1
        if next_index < len(self.path):
            return self.path[next_index]
        return None

    def advance(self) -> bool:
        if self.has_arrived():
            return False
        self.path_index += 1
        return True
