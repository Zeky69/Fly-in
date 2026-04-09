from enum import Enum
from dataclasses import dataclass
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
    drone_id: int
    current_zone: Zone
    path: list[Zone]
    path_index: int = 0
    status: DroneStatus = DroneStatus.WAITING
    transit_turns_left: int = 0
    transit_connection: Optional[Connection] = None

    def identifier(self) -> str:
        return f"D{self.drone_id}"

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
        self.current_zone = self.path[self.path_index]
        return True
