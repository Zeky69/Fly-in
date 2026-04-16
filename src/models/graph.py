"""Graph model holding zones and their connections."""
from typing import Optional

from .zone import HubType, Zone
from .connection import Connection


class Graph:
    """Weighted undirected graph of zones linked by connections."""
    def __init__(self) -> None:
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []
        self.adjacency_list: dict[str, list[tuple[Zone, Connection]]] = {}
        self.nb_drones: int = 0
        self.name_start: Optional[str] = None
        self.name_end: Optional[str] = None

    def add_zone(self, zone: Zone) -> None:
        if zone.name in self.zones:
            raise ValueError(f"Zone '{zone.name}' already exists in graph")
        if zone.type == HubType.START:
            if self.name_start is not None:
                raise ValueError(
                    f"Multiple start hubs found: '{self.name_start}' and "
                    f"'{zone.name}'"
                )
            self.name_start = zone.name
        elif zone.type == HubType.END:
            if self.name_end is not None:
                raise ValueError(
                    f"Multiple end hubs found: '{self.name_end}' and "
                    f"'{zone.name}'"
                )
            self.name_end = zone.name
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

    def create_connection(self, from_zone: str,
                          to_zone: str, **kwargs: int) -> None:
        if from_zone not in self.zones:
            raise ValueError(f"Zone '{from_zone}' not found in graph")
        if to_zone not in self.zones:
            raise ValueError(f"Zone '{to_zone}' not found in graph")
        connection = Connection(from_zone=from_zone, to_zone=to_zone, **kwargs)
        self.add_connection(connection)

    def get_neighbors(self, zone: Zone) -> list[tuple[Zone, Connection]]:
        return self.adjacency_list.get(zone.name, [])

    def get_start(self) -> Optional[Zone]:
        if self.name_start is not None:
            return self.zones.get(self.name_start)
        return None

    def get_end(self) -> Optional[Zone]:
        if self.name_end is not None:
            return self.zones.get(self.name_end)
        return None

    def get_connection(self, zone1: str, zone2: str) -> Optional[Connection]:
        for connection in self.connections:
            if connection.connects(zone1, zone2):
                return connection
        return None

    def __str__(self) -> str:
        lines = []
        lines.append(f"Graph  nb_drones={self.nb_drones}  "
                     f"start='{self.name_start}'  end='{self.name_end}'")
        lines.append(f"  Zones ({len(self.zones)}):")
        for zone in self.zones.values():
            tag = ""
            if zone.type == HubType.START:
                tag = " [START]"
            elif zone.type == HubType.END:
                tag = " [END]"
            drones_str = (
                f"  drones=[{', '.join(str(d.id) for d in zone.drones)}]"
                if zone.drones else ""
            )
            lines.append(
                f"    {zone.name}{tag}  pos=({zone.x},{zone.y})"
                f"  type={zone.type.value}  zone={zone.zone.value}"
                f"  max_drones={zone.max_drone}"
                f"  color={zone.color}{drones_str}"
            )
        lines.append(f"  Connections ({len(self.connections)}):")
        for conn in self.connections:
            lines.append(
                f"    {conn.from_zone} <-> {conn.to_zone}"
                f"  capacity={conn.max_link_capacity}"
                f"  usage={conn.current_link_usage}"
            )
        lines.append("  Adjacency list:")
        for zone_name, neighbors in self.adjacency_list.items():
            neighbor_str = ", ".join(
                f"{z.name}(cap={c.max_link_capacity})" for z, c in neighbors
            )
            lines.append(f"    {zone_name} -> [{neighbor_str}]")
        return "\n".join(lines)
