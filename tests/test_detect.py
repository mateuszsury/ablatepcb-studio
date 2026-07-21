from pathlib import Path

from ablatepcb.detect import classify, coordinate_bounds


OUTLINE = """%FSLAX45Y45*%
%MOMM*%
X100000Y200000D02*
X3100000Y200000D01*
X3100000Y2200000D01*
X100000Y2200000D01*
X100000Y200000D01*
M02*
"""


def test_coordinate_bounds_uses_outline_centerline(tmp_path: Path) -> None:
    path = tmp_path / "board.gko"
    path.write_text(OUTLINE, encoding="utf-8")
    bounds = coordinate_bounds(path)
    assert bounds.min_x == 1.0
    assert bounds.min_y == 2.0
    assert bounds.width == 30.0
    assert bounds.height == 20.0


def test_common_layer_names_are_classified(tmp_path: Path) -> None:
    expected = {
        "board-F_Cu.gbr": "top_copper",
        "board-B_Cu.gbr": "bottom_copper",
        "board-Edge_Cuts.gbr": "outline",
        "Gerber_TopLayer.GTL": "top_copper",
        "Drill_NPTH_Through.DRL": "drill_npth",
    }
    for filename, kind in expected.items():
        path = tmp_path / filename
        path.write_text("M48\n" if path.suffix.lower() == ".drl" else "%MOMM*%\n", encoding="utf-8")
        assert classify(path, tmp_path).kind == kind
