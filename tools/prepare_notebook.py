import json
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[2] / "最終課題(Basic).ipynb"
OUTPUT = Path(__file__).resolve().parents[1] / "notebooks" / "smolvla_libero_final.ipynb"


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"Expected one match, got {text.count(old)}: {old[:60]}")
    return text.replace(old, new)


nb = json.loads(SOURCE.read_text(encoding="utf-8"))

replacements = {
    """        raise NotImplementedError(
            "TODO 1: SinusoidalTimeEmbedding.forward で args を計算せよ"
        )
        args = ...    # ← ここを書き換え. shape: (B, half)""":
    """        args = t[:, None] * freqs[None, :]  # (B, half)""",
    """        raise NotImplementedError(
            "TODO 2: 線形補間 x_t を実装せよ (SmolVLA.compute_loss)"
        )
        xt = ...    # ← ここを書き換え""":
    """        xt = (1.0 - tv) * noise + tv * actions""",
    """        raise NotImplementedError(
            "TODO 3: 真の速度 target_v を計算せよ (SmolVLA.compute_loss)"
        )
        target_v = ...    # ← ここを書き換え""":
    """        target_v = actions - noise""",
    """            raise NotImplementedError(
                "TODO 4: Euler の 1 歩を実装せよ (SmolVLA.sample_actions)"
            )
            x = ...    # ← ここを書き換え""":
    """            x = x + velocity * dt""",
}

for cell in nb["cells"]:
    if cell.get("cell_type") != "code":
        continue
    source = "".join(cell.get("source", []))
    for old, new in replacements.items():
        if old in source:
            source = replace_once(source, old, new)
    cell["source"] = source.splitlines(keepends=True)

remaining = sum(
    c.get("cell_type") == "code"
    and "raise NotImplementedError" in "".join(c.get("source", []))
    for c in nb["cells"]
)
if remaining:
    raise RuntimeError(f"{remaining} TODO implementation blocks remain")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(OUTPUT)
