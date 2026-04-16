"""Zone model with hub and terrain type enumerations."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .drone import Drone


class HubType(str, Enum):
    """Role of a zone in the network (normal hub, start, or end)."""
    NORMAL = "hub"
    END = "end_hub"
    START = "start_hub"

    @staticmethod
    def is_hub(value: str) -> bool:
        return value in HubType._value2member_map_


class ZoneType(str, Enum):
    """Terrain type affecting movement cost and drone capacity."""
    NORMAL = "normal"
    RESTRICTED = "restricted"
    PRIORITY = "priority"
    BLOCKED = "blocked"

    @staticmethod
    def is_zone(value: str) -> bool:
        return value in ZoneType._value2member_map_

    @staticmethod
    def get_set() -> set[str]:
        return {z.value for z in ZoneType}


@dataclass
class Zone:
    """A node in the routing graph with position, capacity and state."""
    name: str
    x: int
    y: int
    type: HubType
    color: Optional[str] = None
    max_drone: int = 1
    zone: ZoneType = ZoneType.NORMAL
    drones: list[Drone] = field(default_factory=list)

    def __str__(self) -> str:
        s = f"Zone {self.name} ({self.x}, {self.y})\n"
        if self.color:
            s += f" - color {self.color}\n"
        s += f" - max drone {self.max_drone}\n"
        s += f" - zone type {self.zone}\n"
        s += " - drones:\n"
        for drone in self.drones:
            s += f"  - {drone}\n"
        return s

    def movement_cost(self) -> float:
        if self.zone == ZoneType.NORMAL:
            return 1
        elif self.zone == ZoneType.RESTRICTED:
            return 2
        elif self.zone == ZoneType.PRIORITY:
            return 1
        elif self.zone == ZoneType.BLOCKED:
            return float('inf')
        return float('inf')

    def can_accept_drone(self) -> bool:
        if self.zone == ZoneType.BLOCKED:
            return False
        if self.type == HubType.END:
            return True
        return len(self.drones) < self.max_drone

    def add_drone(self, drone: Drone) -> bool:
        if self.can_accept_drone():
            self.drones.append(drone)
            return True
        return False

    def remove_drone(self, drone: Drone) -> bool:
        if drone in self.drones:
            self.drones.remove(drone)
            return True
        return False
