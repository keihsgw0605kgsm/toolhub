from __future__ import annotations

import argparse
from pathlib import Path


SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert images to a single PDF.")
    p.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Input image files and/or directories (directories are scanned non-recursively)",
    )
    p.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("output.pdf"),
        help="Output PDF path (default: output.pdf)",
    )
    p.add_argument(
        "--sort",
        choices=["name", "mtime", "none"],
        default="name",
        help="Ordering for directory inputs (default: name)",
    )
    p.add_argument(
        "--recursive",
        action="store_true",
        help="Scan directories recursively",
    )
    return p.parse_args()


def _iter_images_from_dir(d: Path, recursive: bool) -> list[Path]:
    if recursive:
        candidates = [p for p in d.rglob("*") if p.is_file()]
    else:
        candidates = [p for p in d.iterdir() if p.is_file()]
    return [p for p in candidates if p.suffix.lower() in SUPPORTED_EXTS]


def _collect_images(inputs: list[Path], recursive: bool, sort_mode: str) -> list[Path]:
    images: list[Path] = []
    for inp in inputs:
        if inp.is_dir():
            images.extend(_iter_images_from_dir(inp, recursive=recursive))
        else:
            images.append(inp)

    missing = [p for p in images if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing inputs:\n" + "\n".join(str(p) for p in missing))

    images = [p for p in images if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
    if not images:
        raise ValueError(f"No supported images found. Supported: {sorted(SUPPORTED_EXTS)}")

    if sort_mode == "name":
        images.sort(key=lambda p: str(p).lower())
    elif sort_mode == "mtime":
        images.sort(key=lambda p: p.stat().st_mtime)
    elif sort_mode == "none":
        pass
    else:
        raise ValueError("Invalid --sort")

    return images


def main() -> int:
    args = _parse_args()

    try:
        from PIL import Image
    except Exception as e:  # pragma: no cover
        raise RuntimeError("Pillow is required. Install with: pip install pillow") from e

    images = _collect_images(args.inputs, recursive=args.recursive, sort_mode=args.sort)

    opened: list[Image.Image] = []
    try:
        for p in images:
            im = Image.open(p)
            # PDF export expects RGB (no alpha). Convert if needed.
            if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                im = im.convert("RGB")
            elif im.mode != "RGB":
                im = im.convert("RGB")
            opened.append(im)

        out_path: Path = args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)

        first, rest = opened[0], opened[1:]
        first.save(out_path, "PDF", save_all=True, append_images=rest)
    finally:
        for im in opened:
            try:
                im.close()
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
