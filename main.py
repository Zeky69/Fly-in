import os
import sys
import copy

from src.parser.map_parser import MapParser
from src.pathfinding.djikstra import Dijkstra
from src.pathfinding.flow_router import FlowRouter
from src.simulation.simulator import Simulator
from src.display.gui import GuiDisplay
from src.display.terminal import TerminalDisplay
from src.models.drone import Drone
from src.models.graph import Graph
from src.utils.logger import logger

_MAX_TURNS = 10_000


def _find_best_k(
    graph: Graph,
    dijkstra: Dijkstra,
) -> int:
    from src.simulation.simulator import Simulator as _Sim

    start = graph.get_start()
    end = graph.get_end()
    if start is None or end is None:
        return 1

    logger.info("[Optimisation] Testing k=1..10 path configurations...")
    best_k = 1
    best_turns = float("inf")

    for k in range(1, 11):
        graph_copy = copy.deepcopy(graph)
        start_copy = graph_copy.get_start()
        end_copy = graph_copy.get_end()
        if start_copy is None or end_copy is None:
            continue

        drones_copy = list(start_copy.drones)
        paths = dijkstra.find_k_paths(graph_copy, start_copy, end_copy, k=k)
        if not paths:
            logger.info(f"  k={k:2d}: no path found")
            continue

        for i, drone in enumerate(drones_copy):
            drone.path = list(paths[i % len(paths)])

        sim = _Sim(graph_copy)
        all_moves = sim.run(drones_copy)
        turns = len(all_moves)
        logger.info(f"[Optimisation]  k={k:2d}: {turns} turn(s)")

        if turns < best_turns:
            best_turns = turns
            best_k = k

    logger.info(f"[Optimisation] Best k={best_k} → {best_turns} turn(s).")
    return best_k


def _run_simulation(
    graph: Graph,
    drones: list[Drone],
    gui: GuiDisplay,
    term: TerminalDisplay | None = None,
) -> list[tuple[int, list[Drone], list[str]]]:
    simulator = Simulator(graph)
    frames: list[tuple[int, list[Drone], list[str]]] = []

    frames.append((0, copy.deepcopy(drones), []))
    gui.render_frame(turn=0, drones=drones)
    if not gui.wait_next_turn(gui.anim_delay):
        return frames

    turn = 0
    for _ in range(_MAX_TURNS):
        done, moves = simulator.step(drones)
        turn += 1

        move_str = " ".join(moves)
        if move_str:
            if term is None:
                print(move_str)
            else:
                term.render_turn(turn, drones, moves)

        frames.append((turn, copy.deepcopy(drones), list(moves)))
        if not gui.animate_turn(turn=turn, drones=drones, moves=moves):
            return frames

        if done:
            break

    logger.info(f"Simulation finished in {turn} turn(s).")
    gui.set_total_turns(turn)
    return frames


def _replay(
    gui: GuiDisplay,
    frames: list[tuple[int, list[Drone], list[str]]],
) -> bool:
    for i, (turn, drone_snap, moves) in enumerate(frames):
        if i == 0:
            gui.render_frame(turn=turn, drones=drone_snap, moves=moves)
            if not gui.wait_next_turn(gui.anim_delay):
                return False
        else:
            if not gui.animate_turn(turn=turn, drones=drone_snap, moves=moves):
                return False
    return True


def _pick_map_from_dir(directory: str) -> list[tuple[str, str]]:
    base = os.path.abspath(directory)
    results: list[tuple[str, str]] = []
    for root, dirs, files in os.walk(base):
        dirs.sort()
        for fname in sorted(files):
            if fname.endswith(".txt"):
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, base)
                results.append((rel, full))
    if not results:
        sys.stderr.write(
            f"Error: no .txt map files found in '{directory}'.\n"
        )
        sys.exit(1)
    return results


def _load_and_route(
    map_file: str,
) -> tuple[Graph, list[Drone]] | None:
    graph = MapParser(map_file).parse()
    start = graph.get_start()
    end = graph.get_end()
    if start is None or end is None:
        sys.stderr.write(
            "Error: map must have exactly one start and one end zone.\n"
        )
        return None

    drones = list(start.drones)
    dijkstra = Dijkstra()
    router = FlowRouter()
    try:
        best_k = _find_best_k(graph, dijkstra)
        drones = router.assign_paths(graph, drones, dijkstra, k=best_k)
    except NotImplementedError:
        logger.warning(
            "Flow-based pathfinding not implemented;"
            " using single shortest path."
        )
        return None
    return graph, drones


def main() -> None:
    logger.set_level(os.environ.get("LOG_LEVEL", "ERROR"))
    args = sys.argv[1:]
    if not args:
        sys.stderr.write(
            "Usage: python main.py <map_file|directory>\n"
            "Example: python main.py maps/\n"
        )
        sys.exit(1)

    path = args[0]
    if os.path.isdir(path):
        candidates = _pick_map_from_dir(path)
        is_dir = True
    elif os.path.isfile(path):
        candidates = [(os.path.basename(path), os.path.abspath(path))]
        is_dir = False
    else:
        sys.stderr.write(
            f"Error: '{path}' is not a valid file or directory.\n"
        )
        sys.exit(1)

    gui = GuiDisplay()

    while True:
        if is_dir:
            chosen = gui.pick_map(candidates)
            if chosen is None:
                gui.close()
                return
        else:
            chosen = candidates[0][1]

        result = _load_and_route(chosen)
        if result is None:
            if not is_dir:
                gui.close()
                sys.exit(1)
            continue

        graph, drones = result
        gui.load_graph(graph)

        term = TerminalDisplay(graph)
        frames = _run_simulation(graph, drones, gui, term)

        hint = "R replay"
        if is_dir:
            hint += "  M change map"
        hint += "  ESC quit"
        logger.info(hint)

        while True:
            action = gui.wait_for_key_or_close(allow_map=is_dir)
            if action == "quit":
                gui.close()
                return
            if action == "replay":
                if not _replay(gui, frames):
                    gui.close()
                    return
            if action == "map":
                break


if __name__ == "__main__":
    main()
