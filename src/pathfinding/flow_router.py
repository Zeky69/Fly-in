from ..models.drone import Drone
from ..models.graph import Graph
from .djikstra import Dijkstra


class FlowRouter:

    def assign_paths(
        self,
        graph: Graph,
        drones: list[Drone],
        dijkstra: Dijkstra,
        k: int = 4,
    ) -> list[Drone]:
        start = graph.get_start()
        end = graph.get_end()
        if start is None or end is None:
            return drones

        paths = dijkstra.find_k_paths(graph, start, end, k=k)
        if not paths:
            return drones
        for i, drone in enumerate(drones):
            drone.path = list(paths[i % len(paths)])

        return drones
