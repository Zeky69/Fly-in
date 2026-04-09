

from typing import Optional

from .zone import HubType, Zone
from .connection import Connection


class Graph:
    def __init__(self) -> None:
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []
        self.adjacency_list: dict[str, list[tuple[Zone, Connection]]] = {}

    def add_zone(self, zone: Zone) -> None:
        self.zones[zone.name] = zone
        self.adjacency_list[zone.name] = []

    def add_connection(self, connection: Connection) -> None:
        if connection.from_zone not in self.zones:
            raise ValueError(
                f"Zone '{connection.from_zone}' "
                f"not found in graph")
        if connection.to_zone not in self.zones:
            raise ValueError(f"Zone '{connection.to_zone}' not found in graph")

        self.connections.append(connection)

        self.adjacency_list[connection.from_zone].append(
            (self.zones[connection.to_zone], connection))

        self.adjacency_list[connection.to_zone].append(
            (self.zones[connection.from_zone], connection))

    def get_neighbors(self, zone: Zone) -> list[tuple[Zone, Connection]]:
        return self.adjacency_list.get(zone.name, [])

    def get_start(self) -> Optional[Zone]:
        for zone in self.zones.values():
            if zone.type == HubType.START:
                return zone
        return None

    def get_end(self) -> Optional[Zone]:
        for zone in self.zones.values():
            if zone.type == HubType.END:
                return zone
        return None

    def get_connection(self, zone1: str, zone2: str) -> Optional[Connection]:
        for connection in self.connections:
            if connection.connects(zone1, zone2):
                return connection
        return None
