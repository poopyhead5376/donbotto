from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class ModFeature:
    feature: str
    confidence: float


@dataclass(slots=True)
class ModInfo:
    mod_id: str
    name: str
    version: str
    description: str
    features: list[ModFeature] = field(default_factory=list)


FEATURE_PATTERNS: dict[str, str] = {
    "machines": r"\b(machine|automation|generator|factory|energy|power)\b",
    "magic": r"\b(magic|mana|spell|arcane|ritual)\b",
    "storage": r"\b(storage|chest|inventory|warehouse|drawer)\b",
    "farming": r"\b(farm|crop|seed|harvest|agriculture)\b",
    "building": r"\b(build|block|architecture|structure|decorate)\b",
    "combat": r"\b(weapon|combat|battle|armor|boss)\b",
    "exploration": r"\b(biome|dimension|explore|adventure|worldgen)\b",
}


def _extract_mod_metadata(jar_path: Path) -> dict:
    with zipfile.ZipFile(jar_path) as zf:
        for candidate in ("fabric.mod.json", "META-INF/mods.toml", "mcmod.info"):
            if candidate in zf.namelist():
                raw = zf.read(candidate).decode("utf-8", errors="ignore")
                if candidate.endswith(".json"):
                    data = json.loads(raw)
                    if isinstance(data, list):
                        data = data[0]
                    return {
                        "mod_id": data.get("id") or data.get("modid", jar_path.stem),
                        "name": data.get("name", jar_path.stem),
                        "version": data.get("version", "unknown"),
                        "description": data.get("description", ""),
                    }

                # Minimal TOML-ish parsing for mods.toml without extra deps.
                mod_id_match = re.search(r"modId\s*=\s*\"([^\"]+)\"", raw)
                name_match = re.search(r"displayName\s*=\s*\"([^\"]+)\"", raw)
                ver_match = re.search(r"version\s*=\s*\"([^\"]+)\"", raw)
                desc_match = re.search(r"description\s*=\s*'''(.*?)'''", raw, re.DOTALL)
                return {
                    "mod_id": mod_id_match.group(1) if mod_id_match else jar_path.stem,
                    "name": name_match.group(1) if name_match else jar_path.stem,
                    "version": ver_match.group(1) if ver_match else "unknown",
                    "description": (desc_match.group(1).strip() if desc_match else ""),
                }
    return {"mod_id": jar_path.stem, "name": jar_path.stem, "version": "unknown", "description": ""}


def infer_features(text: str) -> list[ModFeature]:
    lowered = text.lower()
    features: list[ModFeature] = []
    for feature_name, pattern in FEATURE_PATTERNS.items():
        hits = len(re.findall(pattern, lowered))
        if hits:
            confidence = min(1.0, 0.25 + hits * 0.2)
            features.append(ModFeature(feature=feature_name, confidence=confidence))
    return sorted(features, key=lambda f: f.confidence, reverse=True)


def scan_mods(mods_dir: Path) -> list[ModInfo]:
    mods: list[ModInfo] = []
    for jar_path in sorted(mods_dir.glob("*.jar")):
        meta = _extract_mod_metadata(jar_path)
        joined = " ".join(str(v) for v in meta.values())
        features = infer_features(joined)
        mods.append(
            ModInfo(
                mod_id=meta["mod_id"],
                name=meta["name"],
                version=meta["version"],
                description=meta["description"],
                features=features,
            )
        )
    return mods


def summarize_features(mods: Iterable[ModInfo]) -> dict[str, float]:
    aggregate: dict[str, float] = {}
    for mod in mods:
        for feature in mod.features:
            aggregate[feature.feature] = max(aggregate.get(feature.feature, 0.0), feature.confidence)
    return aggregate
