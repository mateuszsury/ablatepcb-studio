from pathlib import Path

from ablatepcb.excellon import merge_drills, parse_excellon


def test_excellon_points_slots_and_via_priority(tmp_path: Path) -> None:
    pth = tmp_path / "pth.drl"
    pth.write_text(
        "M48\nMETRIC,LZ,000.000\n;FILE_FORMAT=3:3\nT01C0.300\n%\nT01\nX010000Y020000\nX012000Y020000G85X013000Y020000\nM30\n",
        encoding="utf-8",
    )
    via = tmp_path / "via.drl"
    via.write_text(
        "M48\nMETRIC,LZ,000.000\n;FILE_FORMAT=3:3\nT01C0.300\n%\nT01\nX010000Y020000\nM30\n",
        encoding="utf-8",
    )
    pth_group = parse_excellon(pth, "pth")
    via_group = parse_excellon(via, "via")
    hits, slots = merge_drills([pth_group, via_group])
    assert len(hits) == 1
    assert hits[0].category == "via"
    assert hits[0].x == 10.0 and hits[0].y == 20.0
    assert len(slots) == 1
    assert slots[0].x2 == 13.0
