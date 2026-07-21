import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from gerber2lightburn.engine import Converter


ZIP = Path(os.environ.get("GERBER_GOLDEN_ZIP", "__missing_golden_zip__"))
REFERENCE = Path(os.environ.get("GERBER_GOLDEN_REFERENCE", "__missing_golden_reference__"))


@pytest.mark.golden
@pytest.mark.skipif(not ZIP.exists() or not REFERENCE.exists(), reason="external golden files are not configured")
def test_usb_switch_matches_verified_mask(tmp_path: Path) -> None:
    converter = Converter()
    analysis = converter.analyze(ZIP)
    assert analysis.board_bounds.width == pytest.approx(62.0, abs=0.001)
    assert sum(item.category == "via" for item in analysis.drills) == 12
    assert not any(check.level == "error" for check in analysis.checks)
    output = converter.generate(
        {"blankWidth": 70, "blankHeight": 50, "originX": 10, "originY": 10, "flip": "left_right"},
        tmp_path,
    )
    actual = np.asarray(Image.open(output / "01_TOP_ablation.png").convert("L"))
    reference = np.asarray(Image.open(REFERENCE).convert("L"))
    assert actual.shape == (1500, 3100)
    assert np.array_equal(actual, reference)
