"""ANSI terminal display for the drone simulation."""
from __future__ import annotations

from ..models.drone import Drone, DroneStatus
from ..models.graph import Graph
from ..models.zone import HubType, ZoneType, Zone

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_GREEN = "\033[92m"
_BLUE = "\033[94m"
_YELLOW = "\033[93m"
_ORANGE = "\033[33m"
_RED = "\033[91m"
_PURPLE = "\033[95m"
_CYAN = "\033[96m"
_WHITE = "\033[97m"

_COLOR_MAP: dict[str, str] = {
    "green": _GREEN,
    "blue": _BLUE,
    "yellow": _YELLOW,
    "orange": _ORANGE,
    "red": _RED,
    "purple": _PURPLE,
    "cyan": _CYAN,
    "white": _WHITE,
}


def _zone_color(zone: Zone, degree: int, bottleneck: bool = False) -> str:
    if zone.color:
        c = _COLOR_MAP.get(zone.color.lower())
        if c:
            return c
    if zone.type in (HubType.START, HubType.END):
        return _GREEN
    if zone.zone == ZoneType.RESTRICTED:
        return _PURPLE
    if zone.zone == ZoneType.PRIORITY:
        return _CYAN
    if zone.zone == ZoneType.BLOCKED:
        return _RED
    if degree <= 1:
        return _RED
    if degree >= 3:
        return _YELLOW
    if bottleneck:
        return _ORANGE
    return _BLUE


class TerminalDisplay:

    SHOW_CAPACITY: bool = False

    def __init__(self, graph: Graph) -> None:
        self._graph = graph
        self._degree: dict[str, int] = {name: 0 for name in graph.zones}
        for conn in graph.connections:
            self._degree[conn.from_zone] += 1
            self._degree[conn.to_zone] += 1
        self._bottleneck: dict[str, bool] = {}
        for name, zone in graph.zones.items():
            if self._degree[name] == 2:
                conns = [
                    c for c in graph.connections
                    if c.from_zone == name or c.to_zone == name
                ]
                self._bottleneck[name] = all(
                    c.max_link_capacity == 1 for c in conns
                )
            else:
                self._bottleneck[name] = False

    def render_map(self) -> None:
        sep = "─" * 56
        print(f"\n{_BOLD}Map zones{_RESET}  {_DIM}{sep}{_RESET}")
        for zone in self._graph.zones.values():
            deg = self._degree[zone.name]
            bot = self._bottleneck[zone.name]
            color = _zone_color(zone, deg, bot)
            tag = self._zone_tag(zone, deg, bot)
            cap = f"  cap={zone.max_drone}" if zone.max_drone > 1 else ""
            print(
                f"  {color}{zone.name:<20}{_RESET}"
                f"  {_DIM}{tag}{cap}{_RESET}"
            )
        print()

    def render_turn(
        self,
        turn: int,
        drones: list[Drone],
        moves: list[str],
    ) -> None:
        if moves:
            print(" ".join(self._color_move(m) for m in moves))

    def _colored_zone(self, zone_name: str) -> str:
        zone = self._graph.zones.get(zone_name)
        if zone is None:
            return zone_name
        deg = self._degree.get(zone_name, 0)
        bot = self._bottleneck.get(zone_name, False)
        color = _zone_color(zone, deg, bot)
        if self.SHOW_CAPACITY:
            current = len(zone.drones)
            cap = f"{_DIM}({current}/{zone.max_drone}){_RESET}"
            return f"{color}{zone_name}{_RESET}{cap}"
        return f"{color}{zone_name}{_RESET}"

    def _drone_zone_name(self, drone: Drone) -> str:
        if drone.status == DroneStatus.ARRIVED:
            end = self._graph.get_end()
            return end.name if end else "?"
        if (
            drone.status == DroneStatus.IN_TRANSIT
            and drone.transit_connection is not None
        ):
            return drone.transit_connection.to_zone
        if drone.path and drone.path_index < len(drone.path):
            return drone.path[drone.path_index].name
        start = self._graph.get_start()
        return start.name if start else "?"

    def _color_move(self, move: str) -> str:
        if "-" not in move:
            return move
        drone_part, zone_part = move.split("-", 1)
        return f"{drone_part}-{self._colored_zone(zone_part)}"

    @staticmethod
    def _zone_tag(zone: Zone, degree: int, bottleneck: bool) -> str:
        if zone.type == HubType.START:
            return "start"
        if zone.type == HubType.END:
            return "end"
        if zone.zone == ZoneType.RESTRICTED:
            return "restricted"
        if zone.zone == ZoneType.PRIORITY:
            return "priority"
        if zone.zone == ZoneType.BLOCKED:
            return "blocked"
        if degree <= 1:
            return "dead end"
        if degree >= 3:
            return "junction"
        if bottleneck:
            return "bottleneck"
        return "normal"
