#!/usr/bin/env python3
"""
Merge two PDFs so every output page has the same dimensions.

Source pages are scaled uniformly to fit inside the target rectangle (letterboxing),
centered, so aspect ratio is preserved.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import fitz


# Point sizes (72 dpi), width x height
PRESETS: dict[str, tuple[float, float]] = {
    "a4": (595.0, 842.0),
    "a4landscape": (842.0, 595.0),
    "a3": (842.0, 1191.0),
    "letter": (612.0, 792.0),
}


def parse_size(s: str) -> tuple[float, float]:
    s = s.strip().lower()
    if s in PRESETS:
        return PRESETS[s]
    if "x" in s:
        a, b = s.split("x", 1)
        return float(a.strip()), float(b.strip())
    raise argparse.ArgumentTypeError(
        f"Unknown size {s!r}. Use a4, a3, letter, a4landscape, or WIDTHxHEIGHT (points)."
    )


def rect_from_page(page: fitz.Page) -> fitz.Rect:
    return page.rect


def merge_normalized(
    paths: list[Path],
    out_path: Path,
    target_w: float,
    target_h: float,
) -> int:
    target = fitz.Rect(0, 0, target_w, target_h)
    out = fitz.open()
    total_pages = 0

    for p in paths:
        src = fitz.open(p)
        try:
            # show_pdf_page only embeds the page stream; annotations and form
            # widgets would otherwise be dropped, so merge them into content
            # first to preserve their visual appearance after merging.
            src.bake(annots=True, widgets=True)
            for i in range(src.page_count):
                out.new_page(width=target_w, height=target_h)
                # Scale source page to fit inside target; keep aspect ratio, centered
                out[-1].show_pdf_page(target, src, i)
                total_pages += 1
        finally:
            src.close()

    out.save(out_path)
    out.close()
    return total_pages


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge PDFs with all pages normalized to the same size."
    )
    parser.add_argument("pdf_a", type=Path, help="First PDF")
    parser.add_argument("pdf_b", type=Path, help="Second PDF")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("merged.pdf"),
        help="Output path (default: merged.pdf)",
    )
    g = parser.add_mutually_exclusive_group()
    g.add_argument(
        "--size",
        type=parse_size,
        default=PRESETS["a4"],
        metavar="SPEC",
        help="Target page size: a4 (default), a3, letter, a4landscape, or WIDTHxHEIGHT in points",
    )
    g.add_argument(
        "--match",
        choices=("first", "second"),
        help="Use page size of first or second PDF as target (from page 0)",
    )
    args = parser.parse_args()

    for path in (args.pdf_a, args.pdf_b):
        if not path.is_file():
            print(f"error: not a file: {path}", file=sys.stderr)
            return 1

    if args.match == "first":
        doc = fitz.open(args.pdf_a)
        try:
            r = rect_from_page(doc.load_page(0))
            tw, th = r.width, r.height
        finally:
            doc.close()
    elif args.match == "second":
        doc = fitz.open(args.pdf_b)
        try:
            r = rect_from_page(doc.load_page(0))
            tw, th = r.width, r.height
        finally:
            doc.close()
    else:
        tw, th = args.size

    n = merge_normalized([args.pdf_a, args.pdf_b], args.output, tw, th)
    print(f"Wrote {args.output}: {n} pages at {tw:.0f}x{th:.0f} pt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
