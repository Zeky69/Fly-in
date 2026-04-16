from typing import Optional
import re

try:
    from ..models.connection import Connection
    from ..models.drone import Drone
    from ..models.zone import HubType, Zone, ZoneType
    from ..models.graph import Graph
    from ..utils.logger import logger
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.models.connection import Connection
    from src.models.drone import Drone
    from src.models.zone import HubType, Zone, ZoneType
    from src.models.graph import Graph
    from src.utils.logger import logger


class MapParser:
    """Parse a .txt map file into a Graph with zones and connections."""

    NB_DRONE_PATTERN = re.compile(r'nb_drones:\s+(\d+)')

    ZONE_PATTERN = re.compile(
        r'^(\S+):\s+(\S+)\s+(-?\d+)\s+(-?\d+)(?:\s+\[(.*)\])?$'
    )

    CONNECTION_PATTERN = re.compile(
        r'^connection:\s+(\S+)-(\S+)(?:\s+\[(.*)\])?$'
    )

    METADATA_PATTERN = re.compile(
        r'(\w+)=(\S+?)(?=\s+\w+=|$)'
    )

    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self) -> Graph:
        logger.debug(f"Opening map file: '{self.file_path}'")
        with open(self.file_path, 'r') as f:
            lines = f.readlines()
        logger.debug(f"Read {len(lines)} lines from '{self.file_path}'")
        graph = Graph()
        first_line = True
        seen_connections: set[frozenset[str]] = set()
        try:
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if first_line:
                    nb_drones = self._parse_nb_drone(line)
                    graph.nb_drones = nb_drones
                    first_line = False
                    continue
                if line.startswith("connection:"):
                    connection = self._parse_connection(line)
                    key = frozenset([connection.from_zone, connection.to_zone])
                    if key in seen_connections:
                        logger.error(
                            f"In '{self.file_path}': duplicate connection "
                            f"'{connection.from_zone}-{connection.to_zone}'"
                        )
                    seen_connections.add(key)
                    graph.add_connection(connection)
                    continue
                zone = self._parse_zone(line)
                graph.add_zone(zone)
        except ValueError as e:
            logger.error(str(e))

        logger.debug(
            f"Parsed {len(graph.zones)} zones and "
            f"{len(graph.connections)} connections"
        )
        self._check_validity(graph)
        self._create_drones(graph)
        return graph

    def _check_validity(self, graph: Graph) -> None:
        logger.debug("Checking graph validity...")
        if graph.name_start is None:
            logger.error(
                f"In '{self.file_path}': no start hub found in zones"
            )
        if graph.name_end is None:
            logger.error(
                f"In '{self.file_path}': no end hub found in zones"
            )
        logger.debug(
            f"Graph valid: start='{graph.name_start}' end='{graph.name_end}'"
        )

    def _create_drones(self, graph: Graph) -> None:
        logger.debug(f"Creating {graph.nb_drones} drone(s)...")
        start_zone: Optional[Zone] = graph.get_start()
        for i in range(1, graph.nb_drones + 1):
            drone = Drone(id=i)
            logger.debug(f"Created drone #{i}")
            if start_zone is not None:
                start_zone.drones.append(drone)
                logger.debug(f"Drone #{i} placed at start zone"
                             f" '{start_zone.name}'")

    def _parse_zone(self, line: str) -> Zone:
        match = self.ZONE_PATTERN.match(line)
        if not match:
            logger.error(
                f"In '{self.file_path}': cannot parse zone line: '{line}'\n"
                f"  Expected format: <type>: <name> <x> <y> [key=value ...]"
            )
        hub_type_str, name, x_str, y_str, metadata_str = match.groups()
        if not HubType.is_hub(hub_type_str):
            logger.error(
                f"In '{self.file_path}': unknown hub type '{hub_type_str}' "
                f"in line: '{line}'\n"
                f"  Valid types: {', '.join(h.value for h in HubType)}"
            )
        hub_type = HubType(hub_type_str)
        x = int(x_str)
        y = int(y_str)
        metadata = self._line_parse_metadata(metadata_str or "")
        logger.debug(f"Zone '{name}' metadata: {metadata}")
        known_zone_keys = {"color", "max_drones", "zone"}
        for key in metadata:
            if key not in known_zone_keys:
                logger.warning(
                    f"In '{self.file_path}': unknown metadata key '{key}' "
                    f"for zone '{name}'. "
                    f"Known keys: {', '.join(known_zone_keys)}"
                )
        raw_zone = metadata.get("zone", "normal")
        if not ZoneType.is_zone(raw_zone):
            logger.error(
                f"In '{self.file_path}': unknown zone type '{raw_zone}' "
                f"for hub '{name}' in line: '{line}'\n"
                f"  Valid types: {', '.join(ZoneType.get_set())}"
            )
        zone_type = ZoneType(raw_zone)
        color = metadata.get("color")
        max_drone = int(metadata.get("max_drones", 1))
        zone = Zone(
            name=name,
            x=x,
            y=y,
            type=hub_type,
            color=color,
            max_drone=max_drone,
            zone=zone_type
        )
        logger.debug(
            f"Parsed zone '{name}' at ({x}, {y}) | "
            f"type={hub_type_str} zone={raw_zone} max_drones={max_drone}"
        )
        return zone

    def _parse_nb_drone(self, line: str) -> int:
        match = self.NB_DRONE_PATTERN.match(line)
        if not match:
            logger.error(
                f"In '{self.file_path}': cannot parse nb_drones line:"
                f" '{line}'\n  Expected format: nb_drones: <integer>"
            )
        count = int(match.group(1))
        logger.debug(f"Max drones set to {count}")
        return count

    def _parse_connection(self, line: str) -> Connection:
        match = self.CONNECTION_PATTERN.match(line)
        if not match:
            logger.error(
                f"In '{self.file_path}': cannot parse connection line: "
                f"'{line}'\n  Expected format: connection: "
                f"<zone1>-<zone2> [key=value ...]"
            )
        zone1, zone2, metadata_str = match.groups()
        metadata = self._line_parse_metadata(metadata_str or "")
        logger.debug(f"Connection '{zone1}-{zone2}' metadata: {metadata}")
        known_connection_keys = {"max_link_capacity"}
        for key in metadata:
            if key not in known_connection_keys:
                logger.warning(
                    f"In '{self.file_path}': unknown metadata key '{key}' "
                    f"for connection '{zone1}-{zone2}'. "
                    f"Known keys: {', '.join(known_connection_keys)}"
                )
        max_link_capacity = int(metadata.get("max_link_capacity", 1))
        connection = Connection(
            from_zone=zone1,
            to_zone=zone2,
            max_link_capacity=max_link_capacity
        )
        logger.debug(
            f"Parsed connection between '{zone1}' and '{zone2}' "
            f"with max_link_capacity={max_link_capacity}"
        )
        return connection

    def _line_parse_metadata(self, metadata_str: str) -> dict[str, str]:
        metadata = {}
        for match in self.METADATA_PATTERN.finditer(metadata_str):
            key, value = match.groups()
            metadata[key] = value
        return metadata


if __name__ == "__main__":
    logger.set_level("DEBUG")

    map_files = [
        "maps/easy/01_linear_path.txt",
        "maps/easy/02_simple_fork.txt",
        "maps/challenger/01_the_impossible_dream.txt",
    ]

    for path in map_files:
        print(f"\n{'=' * 50}")
        print(f"Parsing: {path}")
        print('=' * 50)
        parser = MapParser(path)
        graph = parser.parse()
        print(graph)
