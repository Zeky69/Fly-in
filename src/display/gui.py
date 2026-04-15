from __future__ import annotations
import math
from typing import Optional
import pygame
from ..models.zone import HubType, Zone, ZoneType
from ..models.graph import Graph
from ..models.drone import Drone, DroneStatus


class _Palette:

    BG = (18, 22, 42)
    SIDEBAR_BG = (28, 33, 55)
    DIVIDER = (55, 60, 90)

    ZONE_NORMAL = (70, 100, 160)
    ZONE_RESTRICT = (180, 65, 65)
    ZONE_PRIORITY = (190, 140, 30)
    ZONE_BLOCKED = (45, 45, 50)
    ZONE_START = (60, 200, 90)
    ZONE_END = (220, 190, 50)

    BORDER_START = (80, 255, 110)
    BORDER_END = (255, 225, 60)
    BORDER_RESTRICT = (240, 100, 100)
    BORDER_PRIORITY = (255, 200, 60)
    BORDER_BLOCKED = (80, 80, 90)
    BORDER_NORMAL = (130, 160, 220)

    CONN_NORMAL = (100, 105, 130)
    CONN_MULTI = (200, 160, 50)

    TEXT_PRIMARY = (230, 235, 255)
    TEXT_MUTED = (140, 145, 170)
    TEXT_GOOD = (80, 210, 120)
    TEXT_WARN = (220, 170, 60)

    _DRONES: tuple[tuple[int, int, int], ...] = (
        (255, 220, 50), (255, 120, 50), (50, 200, 255),
        (200, 80, 255), (255, 80, 130), (80, 255, 180),
        (255, 255, 255), (255, 160, 80), (100, 255, 100),
        (80, 130, 255), (255, 80, 80), (160, 255, 80),
        (255, 80, 210), (50, 220, 220), (180, 180, 180),
    )

    @classmethod
    def drone(cls, drone_id: int) -> tuple[int, int, int]:
        return cls._DRONES[(drone_id - 1) % len(cls._DRONES)]


class _Config:

    SCREEN_RATIO = 0.90
    SIDEBAR_W = 300
    PADDING = 80

    ZONE_R = 26
    DRONE_R = 11
    RING_R = 18

    CONN_W = 2
    BORDER_W = 3

    FONT_LARGE = 22
    FONT_NORMAL = 17
    FONT_SMALL = 14

    FPS = 60
    TITLE = "Fly-In — Drone Simulation"

    @classmethod
    def screen_size(cls) -> tuple[int, int]:
        info = pygame.display.Info()
        w = max(1024, int(info.current_w * cls.SCREEN_RATIO))
        h = max(640, int(info.current_h * cls.SCREEN_RATIO))
        return w, h


class _Projection:

    def __init__(
        self,
        zones: list[Zone],
        viewport: pygame.Rect,
        padding: int,
    ) -> None:
        xs = [z.x for z in zones]
        ys = [z.y for z in zones]
        self._x0 = float(min(xs))
        self._y0 = float(min(ys))
        self._dx = float(max(xs) - min(xs))
        self._dy = float(max(ys) - min(ys))
        self._vp = viewport
        self._pad = padding

    def to_screen(self, x: float, y: float) -> tuple[int, int]:
        w = self._vp.width - 2 * self._pad
        h = self._vp.height - 2 * self._pad
        ox = self._vp.left + self._pad
        oy = self._vp.top + self._pad

        sx = (
            int(ox + (x - self._x0) / self._dx * w)
            if self._dx else ox + w // 2
        )
        sy = (
            int(oy + (1.0 - (y - self._y0) / self._dy) * h)
            if self._dy else oy + h // 2
        )
        return sx, sy


def _zone_fill(zone: Zone) -> tuple[int, int, int]:
    if zone.type == HubType.START:
        return _Palette.ZONE_START
    if zone.type == HubType.END:
        return _Palette.ZONE_END
    match zone.zone:
        case ZoneType.RESTRICTED:
            return _Palette.ZONE_RESTRICT
        case ZoneType.PRIORITY:
            return _Palette.ZONE_PRIORITY
        case ZoneType.BLOCKED:
            return _Palette.ZONE_BLOCKED
        case _:
            return _Palette.ZONE_NORMAL


def _zone_border(zone: Zone) -> tuple[int, int, int]:
    if zone.type == HubType.START:
        return _Palette.BORDER_START
    if zone.type == HubType.END:
        return _Palette.BORDER_END
    match zone.zone:
        case ZoneType.RESTRICTED:
            return _Palette.BORDER_RESTRICT
        case ZoneType.PRIORITY:
            return _Palette.BORDER_PRIORITY
        case ZoneType.BLOCKED:
            return _Palette.BORDER_BLOCKED
        case _:
            return _Palette.BORDER_NORMAL


def _parse_map_color(
    color_str: Optional[str],
) -> Optional[tuple[int, int, int]]:
    if not color_str:
        return None
    try:
        c = pygame.Color(color_str)
        return (c.r, c.g, c.b)
    except ValueError:
        return None


def _ring_offsets(count: int, ring_r: int) -> list[tuple[int, int]]:
    if count == 1:
        return [(0, 0)]
    return [
        (
            int(ring_r * math.cos(2 * math.pi * i / count)),
            int(ring_r * math.sin(2 * math.pi * i / count)),
        )
        for i in range(count)
    ]


class GuiDisplay:

    def __init__(self, graph: Optional[Graph] = None) -> None:
        pygame.init()
        width, height = _Config.screen_size()
        self._screen = pygame.display.set_mode(
            (width, height), pygame.RESIZABLE
        )
        pygame.display.set_caption(_Config.TITLE)
        self._clock = pygame.time.Clock()

        self._font_l = pygame.font.SysFont(
            "monospace", _Config.FONT_LARGE, bold=True
        )
        self._font_n = pygame.font.SysFont("monospace", _Config.FONT_NORMAL)
        self._font_s = pygame.font.SysFont("monospace", _Config.FONT_SMALL)

        self._has_graph: bool = graph is not None
        self._graph: Graph = graph  # type: ignore[assignment]
        self._total: int = graph.nb_drones if graph is not None else 0

        self._speeds: list[int] = [1200, 800, 500, 300, 150, 50]
        self._speed_idx: int = 1

        self._selected_drone: int = 0

        self._sidebar_drone_rows: dict[int, pygame.Rect] = {}

        self._map_rows: list[tuple[pygame.Rect, str]] = []

        self._total_turns: int = 0

        self._resize(width, height)

    def _resize(self, width: int, height: int) -> None:
        self._sidebar = pygame.Rect(
            width - _Config.SIDEBAR_W, 0, _Config.SIDEBAR_W, height
        )
        self._viewport = pygame.Rect(
            0, 0, width - _Config.SIDEBAR_W, height
        )
        if self._has_graph:
            self._proj = _Projection(
                list(self._graph.zones.values()),
                self._viewport,
                _Config.PADDING,
            )
        if not hasattr(self, "_last_turn"):
            self._last_turn: int = 0
            self._last_drones: list[Drone] = []
            self._last_moves: list[str] = []
            self._prev_pixel_pos: dict[int, tuple[int, int]] = {}
        else:
            if self._has_graph:
                self._prev_pixel_pos = self._compute_drone_positions(
                    self._last_drones
                )

    def set_total_turns(self, total: int) -> None:
        self._total_turns = total

    @property
    def anim_delay(self) -> int:
        return self._speeds[self._speed_idx]

    def render_frame(
        self,
        turn: int,
        drones: Optional[list[Drone]] = None,
        moves: Optional[list[str]] = None,
    ) -> None:
        self._last_turn = turn
        self._last_drones = drones if drones is not None else []
        self._last_moves = moves or []

        self._screen.fill(_Palette.BG)
        self._draw_connections()
        self._draw_paths(
            self._last_drones, self._selected_drone
        )
        self._draw_zones()
        self._draw_drones(self._last_drones)
        self._draw_sidebar(
            turn, self._last_drones, self._last_moves
        )
        pygame.display.flip()
        self._prev_pixel_pos = self._compute_drone_positions(
            self._last_drones
        )

    def animate_turn(
        self,
        turn: int,
        drones: Optional[list[Drone]] = None,
        moves: Optional[list[str]] = None,
        delay_ms: int = -1,
    ) -> bool:
        if delay_ms < 0:
            delay_ms = self.anim_delay
        drone_list = drones if drones is not None else []
        move_list = moves or []

        from_pos = dict(self._prev_pixel_pos)
        to_pos = self._compute_drone_positions(drone_list)
        for d_id, pos in to_pos.items():
            from_pos.setdefault(d_id, pos)

        alive = True
        start_t = pygame.time.get_ticks()
        while True:
            if not self._handle_events():
                alive = False
                break
            elapsed = pygame.time.get_ticks() - start_t
            raw = min(elapsed / delay_ms, 1.0) if delay_ms > 0 else 1.0
            t = raw * raw * (3.0 - 2.0 * raw)
            self._screen.fill(_Palette.BG)
            self._draw_connections()
            self._draw_paths(drone_list, self._selected_drone)
            self._draw_zones()
            self._draw_drones_lerp(drone_list, from_pos, to_pos, t)
            self._draw_sidebar(turn, drone_list, move_list)
            pygame.display.flip()
            self._clock.tick(_Config.FPS)
            if elapsed >= delay_ms:
                break

        self._last_turn = turn
        self._last_drones = drone_list
        self._last_moves = move_list
        self._prev_pixel_pos = to_pos
        return alive

    def wait_next_turn(self, delay_ms: int = 600) -> bool:
        end = pygame.time.get_ticks() + delay_ms
        while pygame.time.get_ticks() < end:
            if not self._handle_events():
                return False
            self._clock.tick(_Config.FPS)
        return True

    def wait_for_close(self) -> None:
        while self._handle_events():
            self._clock.tick(_Config.FPS)

    def wait_for_key_or_close(
        self, allow_map: bool = False
    ) -> str:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "quit"
                    if event.key == pygame.K_r:
                        return "replay"
                    if allow_map and event.key == pygame.K_m:
                        return "map"
                    if event.key in (
                        pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS
                    ):
                        self._speed_idx = min(
                            self._speed_idx + 1,
                            len(self._speeds) - 1,
                        )
                    elif event.key in (
                        pygame.K_MINUS, pygame.K_KP_MINUS
                    ):
                        self._speed_idx = max(self._speed_idx - 1, 0)
                if (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                    and allow_map
                ):
                    for rect, _ in self._map_rows:
                        if rect.collidepoint(event.pos):
                            return "map"
            self._clock.tick(_Config.FPS)

    def pick_map(
        self, candidates: list[tuple[str, str]]
    ) -> Optional[str]:
        selected: int = 0
        font_title = self._font_l
        font_item = self._font_n
        font_hint = self._font_s
        pad = 60
        item_h = 40

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    if event.key == pygame.K_UP:
                        selected = (selected - 1) % len(candidates)
                    if event.key == pygame.K_DOWN:
                        selected = (selected + 1) % len(candidates)
                    if event.key == pygame.K_RETURN:
                        return candidates[selected][1]
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, (r, _path) in enumerate(self._map_rows):
                        if r.collidepoint(event.pos):
                            return candidates[i][1]
                if event.type == pygame.VIDEORESIZE:
                    w, h = event.w, event.h
                    self._screen = pygame.display.set_mode(
                        (w, h), pygame.RESIZABLE
                    )

            self._screen.fill(_Palette.BG)
            sw = self._screen.get_width()
            title = font_title.render(
                "Select a map", True, _Palette.TEXT_PRIMARY
            )
            self._screen.blit(title, (pad, pad))
            hint_surf = font_hint.render(
                "\u2191\u2193 navigate    Enter / click to select"
                "    ESC cancel",
                True, _Palette.TEXT_MUTED,
            )
            self._screen.blit(
                hint_surf, (pad, pad + title.get_height() + 6)
            )

            self._map_rows = []
            start_y = (
                pad + title.get_height() + hint_surf.get_height() + 28
            )
            for i, (label, _path) in enumerate(candidates):
                is_sel = i == selected
                row_rect = pygame.Rect(
                    pad - 8, start_y + i * item_h,
                    sw - pad * 2 + 16, item_h - 4,
                )
                if is_sel:
                    pygame.draw.rect(
                        self._screen, _Palette.SIDEBAR_BG, row_rect,
                        border_radius=6
                    )
                    pygame.draw.rect(
                        self._screen, _Palette.BORDER_NORMAL, row_rect,
                        1, border_radius=6
                    )
                color = (
                    _Palette.TEXT_PRIMARY if is_sel
                    else _Palette.TEXT_MUTED
                )
                surf = font_item.render(label, True, color)
                self._screen.blit(surf, (pad, start_y + i * item_h + 8))
                self._map_rows.append((row_rect, _path))

            pygame.display.flip()
            self._clock.tick(_Config.FPS)

    def load_graph(self, graph: Graph) -> None:
        self._graph = graph
        self._has_graph = True
        self._total = graph.nb_drones
        self._selected_drone = 0
        self._total_turns = 0
        self._last_turn = 0
        self._last_drones = []
        self._last_moves = []
        self._prev_pixel_pos = {}
        self._sidebar_drone_rows = {}
        self._map_rows = []
        w = self._screen.get_width()
        h = self._screen.get_height()
        self._resize(w, h)

    def close(self) -> None:
        pygame.quit()

    def _handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key in (pygame.K_PLUS, pygame.K_EQUALS,
                                 pygame.K_KP_PLUS):
                    self._speed_idx = min(
                        self._speed_idx + 1, len(self._speeds) - 1
                    )
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self._speed_idx = max(self._speed_idx - 1, 0)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_drone_click(event.pos)
            if event.type == pygame.VIDEORESIZE:
                w, h = event.w, event.h
                self._screen = pygame.display.set_mode(
                    (w, h), pygame.RESIZABLE
                )
                self._resize(w, h)
                self._screen.fill(_Palette.BG)
                self._draw_connections()
                self._draw_paths(self._last_drones, self._selected_drone)
                self._draw_zones()
                self._draw_drones(self._last_drones)
                self._draw_sidebar(
                    self._last_turn,
                    self._last_drones,
                    self._last_moves,
                )
                pygame.display.flip()
        return True

    def _handle_drone_click(self, mouse_pos: tuple[int, int]) -> None:
        for drone_id, rect in self._sidebar_drone_rows.items():
            if rect.collidepoint(mouse_pos):
                self._selected_drone = (
                    0 if drone_id == self._selected_drone else drone_id
                )
                return

        r_sq = (_Config.DRONE_R + 6) ** 2
        best_id = 0
        best_dist = r_sq
        pos_map = self._compute_drone_positions(self._last_drones)
        for drone_id, pos in pos_map.items():
            dx = mouse_pos[0] - pos[0]
            dy = mouse_pos[1] - pos[1]
            d = dx * dx + dy * dy
            if d < best_dist:
                best_dist = d
                best_id = drone_id
        self._selected_drone = (
            0 if best_id == self._selected_drone else best_id
        )

    def _compute_drone_positions(
        self, drones: list[Drone]
    ) -> dict[int, tuple[int, int]]:
        at_zone: dict[str, list[Drone]] = {}
        in_transit: list[Drone] = []

        for drone in drones:
            if drone.status == DroneStatus.ARRIVED:
                end = self._graph.get_end()
                if end:
                    at_zone.setdefault(end.name, []).append(drone)
            elif (
                drone.status == DroneStatus.IN_TRANSIT
                and drone.transit_connection is not None
            ):
                in_transit.append(drone)
            else:
                if drone.path and drone.path_index < len(drone.path):
                    name = drone.path[drone.path_index].name
                    at_zone.setdefault(name, []).append(drone)
                else:
                    start = self._graph.get_start()
                    if start:
                        at_zone.setdefault(start.name, []).append(drone)

        positions: dict[int, tuple[int, int]] = {}
        for zone_name, group in at_zone.items():
            zone = self._graph.zones[zone_name]
            center = self._proj.to_screen(zone.x, zone.y)
            offsets = _ring_offsets(len(group), _Config.RING_R)
            for drone, (ox, oy) in zip(group, offsets):
                positions[drone.id] = (center[0] + ox, center[1] + oy)

        for drone in in_transit:
            conn = drone.transit_connection
            if conn is None:
                continue
            z1 = self._graph.zones.get(conn.from_zone)
            z2 = self._graph.zones.get(conn.to_zone)
            if z1 is None or z2 is None:
                continue
            p1 = self._proj.to_screen(z1.x, z1.y)
            p2 = self._proj.to_screen(z2.x, z2.y)
            positions[drone.id] = (
                (p1[0] + p2[0]) // 2,
                (p1[1] + p2[1]) // 2,
            )
        return positions

    def _draw_drones_lerp(
        self,
        drones: list[Drone],
        from_pos: dict[int, tuple[int, int]],
        to_pos: dict[int, tuple[int, int]],
        t: float,
    ) -> None:
        for drone in drones:
            p0 = from_pos.get(drone.id)
            p1 = to_pos.get(drone.id)
            if p0 is None or p1 is None:
                continue
            x = int(p0[0] + (p1[0] - p0[0]) * t)
            y = int(p0[1] + (p1[1] - p0[1]) * t)
            self._draw_drone_dot(drone, (x, y))

    def _draw_paths(
        self, drones: list[Drone], selected_drone: int = 0
    ) -> None:
        conn_entries: dict[
            frozenset[str], list[tuple[int, tuple[int, int, int]]]
        ] = {}
        for drone in drones:
            if drone.status == DroneStatus.ARRIVED:
                continue
            for i in range(drone.path_index, len(drone.path) - 1):
                a = drone.path[i].name
                b = drone.path[i + 1].name
                key: frozenset[str] = frozenset({a, b})
                conn_entries.setdefault(key, []).append(
                    (drone.id, _Palette.drone(drone.id))
                )

        gap = 4
        for key, entries in conn_entries.items():
            names = sorted(key)
            if len(names) != 2:
                continue
            za = self._graph.zones.get(names[0])
            zb = self._graph.zones.get(names[1])
            if za is None or zb is None:
                continue
            p1 = self._proj.to_screen(za.x, za.y)
            p2 = self._proj.to_screen(zb.x, zb.y)
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = math.sqrt(dx * dx + dy * dy)
            if length < 1:
                continue
            px = -dy / length
            py = dx / length
            n = len(entries)
            for idx, (d_id, color) in enumerate(sorted(entries)):
                is_sel = selected_drone != 0 and d_id == selected_drone
                bright = 0.90 if is_sel else 0.40
                width = 3 if is_sel else 2
                offset = (idx - (n - 1) / 2.0) * gap
                ox = int(px * offset)
                oy = int(py * offset)
                muted = (
                    int(color[0] * bright),
                    int(color[1] * bright),
                    int(color[2] * bright),
                )
                q1 = (p1[0] + ox, p1[1] + oy)
                q2 = (p2[0] + ox, p2[1] + oy)
                pygame.draw.line(self._screen, muted, q1, q2, width)

    def _draw_connections(self) -> None:
        for conn in self._graph.connections:
            z_from = self._graph.zones[conn.from_zone]
            z_to = self._graph.zones[conn.to_zone]
            p1 = self._proj.to_screen(z_from.x, z_from.y)
            p2 = self._proj.to_screen(z_to.x, z_to.y)

            color = (
                _Palette.CONN_MULTI
                if conn.max_link_capacity > 1
                else _Palette.CONN_NORMAL
            )
            pygame.draw.line(self._screen, color, p1, p2, _Config.CONN_W)

            if conn.max_link_capacity > 1:
                mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
                badge = self._font_s.render(
                    f"×{conn.max_link_capacity}", True, _Palette.CONN_MULTI
                )
                self._screen.blit(badge, (mid[0] + 4, mid[1] - 8))

    def _draw_zones(self) -> None:
        for zone in self._graph.zones.values():
            pos = self._proj.to_screen(zone.x, zone.y)
            fill = _parse_map_color(zone.color) or _zone_fill(zone)
            border = _zone_border(zone)
            r = _Config.ZONE_R

            pygame.draw.circle(self._screen, fill, pos, r)

            pygame.draw.circle(self._screen, border, pos, r, _Config.BORDER_W)

            name_surf = self._font_s.render(
                zone.name, True, _Palette.TEXT_PRIMARY
            )
            self._screen.blit(
                name_surf,
                (pos[0] - name_surf.get_width() // 2, pos[1] + r + 4),
            )

            if zone.max_drone > 1:
                badge = self._font_s.render(
                    f"/{zone.max_drone}", True, _Palette.TEXT_MUTED
                )
                self._screen.blit(badge, (pos[0] + r - 2, pos[1] - r - 2))

    def _draw_drones(self, drones: list[Drone]) -> None:
        at_zone: dict[str, list[Drone]] = {}
        in_transit: list[Drone] = []

        for drone in drones:
            if drone.status == DroneStatus.ARRIVED:
                end = self._graph.get_end()
                if end:
                    at_zone.setdefault(end.name, []).append(drone)
            elif (
                drone.status == DroneStatus.IN_TRANSIT
                and drone.transit_connection is not None
            ):
                in_transit.append(drone)
            else:
                if drone.path and drone.path_index < len(drone.path):
                    name = drone.path[drone.path_index].name
                    at_zone.setdefault(name, []).append(drone)
                else:
                    start = self._graph.get_start()
                    if start:
                        at_zone.setdefault(start.name, []).append(drone)

        for zone_name, group in at_zone.items():
            zone = self._graph.zones[zone_name]
            center = self._proj.to_screen(zone.x, zone.y)
            offsets = _ring_offsets(len(group), _Config.RING_R)
            for drone, (ox, oy) in zip(group, offsets):
                self._draw_drone_dot(
                    drone, (center[0] + ox, center[1] + oy)
                )

        for drone in in_transit:
            conn = drone.transit_connection
            if conn is None:
                continue
            if conn.from_zone not in self._graph.zones:
                continue
            if conn.to_zone not in self._graph.zones:
                continue
            z1 = self._graph.zones[conn.from_zone]
            z2 = self._graph.zones[conn.to_zone]
            p1 = self._proj.to_screen(z1.x, z1.y)
            p2 = self._proj.to_screen(z2.x, z2.y)
            mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
            self._draw_drone_dot(drone, mid)

    def _draw_drone_dot(
        self, drone: Drone, pos: tuple[int, int]
    ) -> None:
        color = _Palette.drone(drone.id)
        r = _Config.DRONE_R
        pygame.draw.circle(self._screen, (10, 10, 15), pos, r + 2)
        pygame.draw.circle(self._screen, color, pos, r)

    def _draw_sidebar(
        self,
        turn: int,
        drones: list[Drone],
        moves: list[str],
    ) -> None:
        pygame.draw.rect(self._screen, _Palette.SIDEBAR_BG, self._sidebar)
        pygame.draw.line(
            self._screen, _Palette.DIVIDER,
            (self._sidebar.left, 0),
            (self._sidebar.left, self._sidebar.height),
            2,
        )

        x = self._sidebar.left + 18
        y = 18

        def text(
            msg: str,
            color: tuple[int, int, int] = _Palette.TEXT_PRIMARY,
            font: Optional[pygame.font.Font] = None,
        ) -> None:
            nonlocal y
            f = font or self._font_n
            surf = f.render(msg, True, color)
            self._screen.blit(surf, (x, y))
            y += surf.get_height() + 4

        def sep(gap: int = 8) -> None:
            nonlocal y
            y += gap
            pygame.draw.line(
                self._screen, _Palette.DIVIDER,
                (x, y), (self._sidebar.right - 18, y), 1
            )
            y += gap

        text("FLY-IN", _Palette.TEXT_PRIMARY, self._font_l)
        sep()

        text(f"Turn   {turn}", _Palette.TEXT_GOOD, self._font_l)
        if self._total_turns > 0 and turn < self._total_turns:
            eta = self._total_turns - turn
            text(f"ETA  ~{eta} turn(s)", _Palette.TEXT_WARN)
        elif self._total_turns > 0 and turn >= self._total_turns:
            text("Finished!", _Palette.TEXT_GOOD)
        sep(6)

        bars = len(self._speeds)
        bar_w = (self._sidebar.width - 36) // bars
        for i in range(bars):
            color = _Palette.TEXT_GOOD if i <= self._speed_idx \
                else _Palette.DIVIDER
            rect = pygame.Rect(x + i * bar_w, y, bar_w - 2, 10)
            pygame.draw.rect(self._screen, color, rect)
        y += 14
        text(
            f"Speed  {self._speed_idx + 1}/{bars}  (+/-)",
            _Palette.TEXT_MUTED, self._font_s,
        )
        sep(6)

        arrived = sum(
            1 for d in drones if d.status == DroneStatus.ARRIVED
        )
        in_transit = sum(
            1 for d in drones if d.status == DroneStatus.IN_TRANSIT
        )
        waiting = sum(
            1 for d in drones if d.status == DroneStatus.WAITING
        )
        text(f"Arrived  {arrived} / {self._total}", _Palette.TEXT_WARN)
        text(f"Transit  {in_transit}", _Palette.TEXT_MUTED)
        text(f"Waiting  {waiting}", _Palette.TEXT_MUTED)
        sep()

        text("Legend", _Palette.TEXT_MUTED)
        sep(4)
        legend: list[tuple[tuple[int, int, int], str]] = [
            (_Palette.ZONE_START, "start"),
            (_Palette.ZONE_END, "end"),
            (_Palette.ZONE_NORMAL, "normal"),
            (_Palette.ZONE_RESTRICT, "restricted  x2"),
            (_Palette.ZONE_PRIORITY, "priority"),
            (_Palette.ZONE_BLOCKED, "blocked"),
        ]
        for color, label in legend:
            pygame.draw.circle(self._screen, color, (x + 8, y + 8), 8)
            surf = self._font_s.render(
                f"  {label}", True, _Palette.TEXT_MUTED
            )
            self._screen.blit(surf, (x + 20, y + 1))
            y += 22
        sep()

        text("Drones  (click to select)", _Palette.TEXT_MUTED)
        sep(4)
        self._sidebar_drone_rows = {}
        for drone_id in range(1, self._total + 1):
            if y > self._sidebar.height - 100:
                text("...", _Palette.TEXT_MUTED, self._font_s)
                break
            self._sidebar_drone_rows[drone_id] = pygame.Rect(
                self._sidebar.left, y, self._sidebar.width, 22
            )
            is_sel = drone_id == self._selected_drone
            clr = _Palette.drone(drone_id)
            pygame.draw.circle(
                self._screen,
                clr,
                (x + 8, y + 8),
                9 if is_sel else 8,
            )
            label = f"  D{drone_id}"
            if is_sel:
                label += "  ◀"
            id_surf = self._font_s.render(
                label,
                True,
                _Palette.TEXT_PRIMARY if is_sel else _Palette.TEXT_MUTED,
            )
            self._screen.blit(id_surf, (x + 20, y + 1))
            y += 22
        sep()

        if self._selected_drone != 0:
            sel = next(
                (d for d in drones if d.id == self._selected_drone), None
            )
            if sel is not None:
                text(
                    f"D{sel.id} path ({sel.path_index}→"
                    f"{len(sel.path) - 1})",
                    _Palette.drone(sel.id), self._font_s,
                )
                for i, zone in enumerate(sel.path):
                    if y > self._sidebar.height - 24:
                        text("...", _Palette.TEXT_MUTED, self._font_s)
                        break
                    marker = "> " if i == sel.path_index else "  "
                    clr = (
                        _Palette.TEXT_GOOD
                        if i == sel.path_index
                        else _Palette.TEXT_MUTED
                    )
                    text(f"{marker}{zone.name}", clr, self._font_s)
                sep()

        text("Moves this turn", _Palette.TEXT_MUTED)
        sep(4)
        if moves:
            for move in moves:
                if y > self._sidebar.height - 40:
                    break
                text(move, _Palette.TEXT_PRIMARY, self._font_s)
        else:
            text("—", _Palette.TEXT_MUTED, self._font_s)

        if self._map_rows:
            sep(6)
            text("M — change map", _Palette.TEXT_MUTED, self._font_s)
