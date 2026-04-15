from ..models.connection import Connection
from ..models.drone import Drone, DroneStatus
from ..models.graph import Graph
from ..models.zone import HubType, Zone, ZoneType


class Simulator:

    _MAX_TURNS: int = 10_000

    def __init__(self, graph: Graph) -> None:
        self._graph = graph

    def run(self, drones: list[Drone]) -> list[str]:
        all_moves: list[str] = []
        for _ in range(self._MAX_TURNS):
            done, moves = self.step(drones)
            all_moves.append(" ".join(moves))
            if done:
                break
        return all_moves

    def step(self, drones: list[Drone]) -> tuple[bool, list[str]]:
        active = [d for d in drones if d.status != DroneStatus.ARRIVED]
        if not active:
            return True, []

        pre_waiting = [d for d in active if d.status == DroneStatus.WAITING]

        moves: list[str] = []
        moves += self._land_transit(active)
        moves += self._move_waiting(pre_waiting)

        all_done = all(d.status == DroneStatus.ARRIVED for d in drones)
        return all_done, moves

    def _land_transit(self, active: list[Drone]) -> list[str]:
        moves: list[str] = []
        for drone in active:
            if drone.status != DroneStatus.IN_TRANSIT:
                continue
            drone.transit_turns_left -= 1
            if drone.transit_turns_left > 0:
                continue

            nxt: Zone = drone.path[drone.path_index + 1]
            conn: Connection | None = drone.transit_connection

            nxt.drones.append(drone)
            drone.advance()

            if conn is not None:
                conn.remove_drone()
                drone.transit_connection = None

            drone.status = (
                DroneStatus.ARRIVED
                if drone.has_arrived()
                else DroneStatus.WAITING
            )
            moves.append(f"D{drone.id}-{nxt.name}")

        return moves

    def _move_waiting(self, pre_waiting: list[Drone]) -> list[str]:
        conn_extra: dict[str, int] = {}
        zone_in: dict[str, int] = {}
        zone_out: dict[str, int] = {}

        candidates = self._build_candidates(pre_waiting)
        moves: list[str] = []

        for drone, curr, nxt, conn in sorted(
                candidates, key=lambda x: x[0].id):

            conn_key = f"{conn.from_zone}-{conn.to_zone}"

            if (
                conn.current_link_usage + conn_extra.get(conn_key, 0)
                >= conn.max_link_capacity
            ):
                continue

            eff_occ = (
                len(nxt.drones)
                - zone_out.get(nxt.name, 0)
                + zone_in.get(nxt.name, 0)
            )
            if nxt.type != HubType.END and eff_occ >= nxt.max_drone:
                continue

            conn_extra[conn_key] = conn_extra.get(conn_key, 0) + 1
            zone_in[nxt.name] = zone_in.get(nxt.name, 0) + 1
            zone_out[curr.name] = zone_out.get(curr.name, 0) + 1

            curr.drones.remove(drone)
            cost = int(nxt.movement_cost())

            if cost == 1:
                nxt.drones.append(drone)
                conn.add_drone()
                conn.remove_drone()
                drone.advance()
                drone.status = (
                    DroneStatus.ARRIVED
                    if drone.has_arrived()
                    else DroneStatus.WAITING
                )
                moves.append(f"D{drone.id}-{nxt.name}")
            else:
                conn.add_drone()
                drone.status = DroneStatus.IN_TRANSIT
                drone.transit_turns_left = 1
                drone.transit_connection = conn
                moves.append(f"D{drone.id}-{curr.name}-{nxt.name}")

        return moves

    def _build_candidates(
        self,
        pre_waiting: list[Drone],
    ) -> list[tuple[Drone, Zone, Zone, Connection]]:
        candidates: list[tuple[Drone, Zone, Zone, Connection]] = []
        for drone in pre_waiting:
            if drone.path and drone.has_arrived():
                drone.status = DroneStatus.ARRIVED
                continue

            nxt = drone.next_zone()
            if nxt is None:
                continue
            if nxt.zone == ZoneType.BLOCKED:
                continue

            curr = drone.path[drone.path_index]
            conn = self._graph.get_connection(curr.name, nxt.name)
            if conn is None:
                continue

            candidates.append((drone, curr, nxt, conn))

        return candidates
