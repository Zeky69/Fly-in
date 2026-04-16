"""Connection model between two zones."""
from dataclasses import dataclass


@dataclass
class Connection:
    """Directional link between two zones with capacity tracking."""
    from_zone: str
    to_zone: str
    max_link_capacity: int = 1
    current_link_usage: int = 0

    def __str__(self) -> str:
        return f"{self.from_zone}-{self.to_zone}"

    def connects(self, zone1: str, zone2: str) -> bool:
        return (self.from_zone == zone1 and self.to_zone == zone2) \
            or (self.from_zone == zone2 and self.to_zone == zone1)

    def can_accept_drone(self) -> bool:
        return self.current_link_usage < self.max_link_capacity

    def add_drone(self) -> bool:
        if self.can_accept_drone():
            self.current_link_usage += 1
            return True
        return False

    def remove_drone(self) -> bool:
        if self.current_link_usage > 0:
            self.current_link_usage -= 1
            return True
        return False
