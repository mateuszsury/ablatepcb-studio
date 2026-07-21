from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


LayerKind = Literal[
    "top_copper",
    "bottom_copper",
    "outline",
    "top_silk",
    "bottom_silk",
    "top_mask",
    "bottom_mask",
    "drill_via",
    "drill_pth",
    "drill_npth",
    "other",
]


@dataclass(slots=True)
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    def to_dict(self) -> dict[str, float]:
        return {
            "minX": round(self.min_x, 5),
            "minY": round(self.min_y, 5),
            "maxX": round(self.max_x, 5),
            "maxY": round(self.max_y, 5),
            "width": round(self.width, 5),
            "height": round(self.height, 5),
        }


@dataclass(slots=True)
class LayerFile:
    path: Path
    relative_name: str
    kind: LayerKind
    confidence: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.relative_name,
            "kind": self.kind,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass(slots=True)
class DrillHit:
    x: float
    y: float
    diameter: float
    category: Literal["via", "pth", "npth"]
    source: str

    def key(self) -> tuple[int, int]:
        return (round(self.x * 10000), round(self.y * 10000))


@dataclass(slots=True)
class DrillSlot:
    x1: float
    y1: float
    x2: float
    y2: float
    diameter: float
    category: Literal["via", "pth", "npth"]
    source: str


@dataclass(slots=True)
class Check:
    level: Literal["ok", "warning", "error"]
    title: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class Analysis:
    source: Path
    work_root: Path
    layers: list[LayerFile]
    board_bounds: Bounds
    copper_bounds: dict[str, Bounds]
    drills: list[DrillHit] = field(default_factory=list)
    slots: list[DrillSlot] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    min_feature_mm: float | None = None
    preview_data: dict[str, str] = field(default_factory=dict)

    def selected(self, kind: LayerKind) -> LayerFile | None:
        matches = [item for item in self.layers if item.kind == kind]
        return max(matches, key=lambda item: item.confidence, default=None)

    @property
    def can_generate(self) -> bool:
        return not any(check.level == "error" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        counts = {
            "vias": sum(d.category == "via" for d in self.drills),
            "pth": sum(d.category == "pth" for d in self.drills),
            "npth": sum(d.category == "npth" for d in self.drills),
            "slots": len(self.slots),
        }
        return {
            "source": str(self.source),
            "board": self.board_bounds.to_dict(),
            "layers": [layer.to_dict() for layer in self.layers],
            "drills": counts,
            "minFeatureMm": self.min_feature_mm,
            "checks": [check.to_dict() for check in self.checks],
            "canGenerate": self.can_generate,
            "previews": self.preview_data,
        }


@dataclass(slots=True)
class GenerationOptions:
    dpmm: int = 50
    blank_width: float = 0.0
    blank_height: float = 0.0
    origin_x: float = 10.0
    origin_y: float = 10.0
    flip: Literal["left_right", "top_bottom"] = "left_right"
    speed: float = 3000.0
    power: float = 50.0
    interval: float = 0.05
    passes: int = 2
    overscan: float = 2.5

    @classmethod
    def from_dict(cls, value: dict[str, Any], board: Bounds) -> "GenerationOptions":
        def number(key: str, default: float) -> float:
            try:
                return float(value.get(key, default))
            except (TypeError, ValueError):
                return default

        flip = value.get("flip", "left_right")
        if flip not in ("left_right", "top_bottom"):
            flip = "left_right"
        return cls(
            dpmm=max(10, min(100, int(number("dpmm", 50)))),
            blank_width=max(board.width, number("blankWidth", board.width)),
            blank_height=max(board.height, number("blankHeight", board.height)),
            origin_x=number("originX", 10.0),
            origin_y=number("originY", 10.0),
            flip=flip,
            speed=max(1.0, number("speed", 3000.0)),
            power=max(0.1, min(100.0, number("power", 50.0))),
            interval=max(0.01, min(1.0, number("interval", 0.05))),
            passes=max(1, min(20, int(number("passes", 2)))),
            overscan=max(0.0, min(20.0, number("overscan", 2.5))),
        )
