from ..models.graph import Graph
from ..models.zone import Zone
import heapq


class Dijkstra:

    def find_path(self, graph: Graph, start: Zone, end: Zone) -> list[Zone]:

        heap = [(0.0, start.name)]
        dist = {start.name: 0.0}
        prev = {}

        while heap:
            cost, name = heapq.heappop(heap)
            if name == end.name:
                break
            if cost > dist.get(name, float("inf")):
                continue
            for neighbour, _conn in graph.get_neighbors(graph.zones[name]):
                edge_cost = neighbour.movement_cost()
                if edge_cost == float("inf"):
                    continue
                new_cost = cost + edge_cost
                if new_cost < dist.get(neighbour.name, float("inf")):
                    dist[neighbour.name] = new_cost
                    prev[neighbour.name] = name
                    heapq.heappush(heap, (new_cost, neighbour.name))

        path = []
        current_name = end.name
        while current_name in prev:
            path.append(graph.zones[current_name])
            current_name = prev[current_name]
        if current_name == start.name:
            path.append(graph.zones[current_name])
            path.reverse()
            return path
        else:
            return []

    def find_k_paths(
        self,
        graph: Graph,
        start: Zone,
        end: Zone,
        k: int = 5,
    ) -> list[list[Zone]]:
        heap: list[tuple[float, int, list[Zone]]] = [(0.0, 0, [start])]
        paths: list[list[Zone]] = []
        counter = 0
        while heap and len(paths) < k:
            cost, _, path = heapq.heappop(heap)
            last_zone = path[-1]
            if last_zone.name == end.name:
                paths.append(path)
                continue
            for neighbour, _conn in graph.get_neighbors(last_zone):
                if neighbour in path:
                    continue
                edge_cost = neighbour.movement_cost()
                if edge_cost == float("inf"):
                    continue
                new_cost = cost + edge_cost
                new_path = path + [neighbour]
                counter += 1
                heapq.heappush(heap, (new_cost, counter, new_path))
        return paths
