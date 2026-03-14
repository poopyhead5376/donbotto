import json
import zipfile
from pathlib import Path

from sima2_bazzite.mod_scanner import scan_mods, summarize_features


def _write_fake_mod(path: Path, metadata: dict) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("fabric.mod.json", json.dumps(metadata))


def test_scan_mods_infers_features(tmp_path: Path) -> None:
    mods_dir = tmp_path / "mods"
    mods_dir.mkdir()
    _write_fake_mod(
        mods_dir / "techmagic.jar",
        {
            "id": "techmagic",
            "name": "Tech Magic",
            "version": "1.0.0",
            "description": "Adds machine automation with mana rituals and power generators",
        },
    )

    mods = scan_mods(mods_dir)
    summary = summarize_features(mods)

    assert len(mods) == 1
    assert mods[0].mod_id == "techmagic"
    assert "machines" in summary
    assert "magic" in summary
