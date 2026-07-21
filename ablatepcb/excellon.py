from __future__ import annotations

import re
from pathlib import Path

from .models import DrillHit, DrillSlot


def parse_excellon(path: Path, category: str) -> tuple[list[DrillHit], list[DrillSlot]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    metric = "INCH" not in text.upper()
    factor = 1.0 if metric else 25.4
    fmt = re.search(r"FILE_FORMAT\s*=\s*(\d+)\s*:\s*(\d+)", text, re.IGNORECASE)
    decimals = int(fmt.group(2)) if fmt else (3 if metric else 4)
    tools: dict[str, float] = {}
    for match in re.finditer(r"^T(\d+)C([\d.]+)", text, re.IGNORECASE | re.MULTILINE):
        tools[match.group(1)] = float(match.group(2)) * factor

    active = ""
    current_x = 0.0
    current_y = 0.0
    hits: list[DrillHit] = []
    slots: list[DrillSlot] = []

    def coord(raw: str | None, previous: float) -> float:
        if raw is None:
            return previous
        if "." in raw:
            return float(raw) * factor
        return int(raw) / (10**decimals) * factor

    tool_line = re.compile(r"^T(\d+)$", re.IGNORECASE)
    point = re.compile(r"X([+-]?[\d.]+)?Y([+-]?[\d.]+)?", re.IGNORECASE)
    for raw_line in text.splitlines():
        line = raw_line.strip().upper()
        selected = tool_line.fullmatch(line)
        if selected:
            active = selected.group(1)
            continue
        if not line.startswith(("X", "Y")):
            continue
        coordinates = list(point.finditer(line))
        if not coordinates:
            continue
        first = coordinates[0]
        x1 = coord(first.group(1), current_x)
        y1 = coord(first.group(2), current_y)
        diameter = tools.get(active, 0.0)
        if "G85" in line and len(coordinates) > 1:
            second = coordinates[1]
            x2 = coord(second.group(1), x1)
            y2 = coord(second.group(2), y1)
            slots.append(DrillSlot(x1, y1, x2, y2, diameter, category, path.name))
            current_x, current_y = x2, y2
        else:
            hits.append(DrillHit(x1, y1, diameter, category, path.name))
            current_x, current_y = x1, y1
    return hits, slots


def merge_drills(groups: list[tuple[list[DrillHit], list[DrillSlot]]]) -> tuple[list[DrillHit], list[DrillSlot]]:
    priority = {"pth": 1, "npth": 2, "via": 3}
    points: dict[tuple[int, int], DrillHit] = {}
    slots: list[DrillSlot] = []
    for hits, new_slots in groups:
        for hit in hits:
            old = points.get(hit.key())
            if old is None or priority[hit.category] > priority[old.category]:
                points[hit.key()] = hit
        slots.extend(new_slots)
    return sorted(points.values(), key=lambda h: (h.y, h.x)), slots

