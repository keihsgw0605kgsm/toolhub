from __future__ import annotations

import argparse
import os
from pathlib import Path


def _positive_int(value: str) -> int:
    iv = int(value)
    if iv <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return iv


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Convert PDF pages to images (high resolution).")
    p.add_argument("pdf", type=Path, help="Input PDF path")
    p.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: <pdf_stem>_images next to PDF)",
    )
    p.add_argument(
        "--format",
        choices=["png", "jpg", "jpeg"],
        default="png",
        help="Output image format",
    )
    p.add_argument(
        "--dpi",
        type=_positive_int,
        default=300,
        help="Render DPI (default: 300). Higher => larger images.",
    )
    p.add_argument(
        "--page",
        type=_positive_int,
        default=None,
        help="Convert only this 1-based page number",
    )
    p.add_argument(
        "--start",
        type=_positive_int,
        default=None,
        help="Start page (1-based, inclusive)",
    )
    p.add_argument(
        "--end",
        type=_positive_int,
        default=None,
        help="End page (1-based, inclusive)",
    )
    p.add_argument(
        "--prefix",
        default=None,
        help="Output filename prefix (default: PDF stem)",
    )
    p.add_argument(
        "--quality",
        type=int,
        default=95,
        help="JPEG quality (1-100). Only for jpg/jpeg. Default: 95",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    if not args.pdf.exists():
        raise FileNotFoundError(args.pdf)
    if args.pdf.suffix.lower() != ".pdf":
        raise ValueError("Input must be a .pdf file")

    out_dir = args.out
    if out_dir is None:
        out_dir = args.pdf.parent / f"{args.pdf.stem}_images"
    out_dir.mkdir(parents=True, exist_ok=True)

    prefix = args.prefix or args.pdf.stem
    img_format = "jpg" if args.format == "jpeg" else args.format

    # Render scale: PDF points assume 72 DPI. scale = dpi / 72.
    scale = args.dpi / 72.0

    try:
        import fitz  # PyMuPDF
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "PyMuPDF is required. Install with: pip install pymupdf"
        ) from e

    doc = fitz.open(os.fspath(args.pdf))

    if args.page is not None:
        start_page = args.page
        end_page = args.page
    else:
        start_page = args.start or 1
        end_page = args.end or doc.page_count

    if start_page < 1 or end_page < 1:
        raise ValueError("Pages are 1-based and must be >= 1")
    if start_page > end_page:
        raise ValueError("--start must be <= --end")
    if end_page > doc.page_count:
        raise ValueError(f"PDF has only {doc.page_count} pages (end={end_page})")

    matrix = fitz.Matrix(scale, scale)

    for page_no in range(start_page, end_page + 1):
        page = doc.load_page(page_no - 1)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        out_path = out_dir / f"{prefix}_p{page_no:04d}.{img_format}"
        if img_format == "png":
            pix.save(os.fspath(out_path))
        else:
            q = max(1, min(100, int(args.quality)))
            pix.save(os.fspath(out_path), jpg_quality=q)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
