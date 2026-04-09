from ..models.graph import Graph
import re


class MapParser:

    ZONE_PATTERN = re.compile(
        r'^(start_hub|end_hub|hub):\s+(\S+)\s+(-?\d+)\s+(-?\d+)(?:\s+\[(.*)\])?$'
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
        with open(self.file_path, 'r') as f:
            lines = f.readlines()
        graph = Graph()
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            zone_match = self.ZONE_PATTERN.match(line)
            if zone_match:
                hub_type, name, x, y, metadata_str = zone_match.groups()
                metadata = self.parse_metadata(metadata_str)
                graph.add_zone(Zone(
                    name=name,
                    x=int(x),
                    y=int(y),
                    type=HubType(hub_type),
                    color=metadata.get('color'),
                    max_drone=int(metadata.get('max_drone', 1)),
                    zone=ZoneType(metadata.get('zone', 'normal'))
                ))
                continue

            connection_match = self.CONNECTION_PATTERN.match(line)
            if connection_match:
                from_zone, to_zone, metadata_str = connection_match.groups()
                metadata = self.parse_metadata(metadata_str)
                graph.add_connection(Connection(
                    from_zone=from_zone,
                    to_zone=to_zone,
                    distance=float(metadata.get('distance', 1))
                ))
                continue
