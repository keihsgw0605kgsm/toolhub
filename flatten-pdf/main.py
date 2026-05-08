#!/usr/bin/env python3
"""
Flatten a PDF so it is no longer editable.

- Bakes annotations (highlights, freetext memos, etc.) into page content.
- Bakes interactive form widgets (text fields, checkboxes, signatures' visual)
  into page content and removes the AcroForm catalog entry, so viewers no
  longer offer "fill & sign" UI.
- Optionally re-renders pages as raster images at a chosen DPI as a last
  resort (no text layer, but absolutely nothing remains editable/selectable).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import fitz


def _drop_acroform(doc: fitz.Document) -> None:
    """Remove /AcroForm entry from the PDF catalog if present."""
    try:
        catalog_xref = doc.pdf_catalog()
    except Exception:
        return
    try:
        if doc.xref_get_key(catalog_xref, "AcroForm")[0] != "null":
            doc.xref_set_key(catalog_xref, "AcroForm", "null")
    except Exception:
        # Best effort; some PDFs may not allow this. bake() already neutralized
        # the widgets visually, so this is just cleanup.
        pass


def flatten(
    in_path: Path,
    out_path: Path,
    *,
    annots: bool = True,
    widgets: bool = True,
    rasterize_dpi: int | None = None,
) -> None:
    doc = fitz.open(in_path)
    try:
        # Convert annotations and widgets to permanent page content.
        doc.bake(annots=annots, widgets=widgets)
        if widgets:
            _drop_acroform(doc)

        if rasterize_dpi:
            # Render every page to an image and rebuild the PDF from images.
            new_doc = fitz.open()
            for page in doc:
                pix = page.get_pixmap(dpi=rasterize_dpi, alpha=False)
                rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
                np = new_doc.new_page(width=rect.width, height=rect.height)
                np.insert_image(rect, pixmap=pix)
            new_doc.save(out_path, garbage=4, deflate=True, clean=True)
            new_doc.close()
        else:
            doc.save(out_path, garbage=4, deflate=True, clean=True)
    finally:
        doc.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Flatten a PDF: bake annotations/forms so the result is not editable."
    )
    parser.add_argument("pdf", type=Path, help="Input PDF")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (default: <input>.flat.pdf next to the input)",
    )
    parser.add_argument(
        "--keep-annots",
        action="store_true",
        help="Do not bake annotations (highlights, freetext, etc.)",
    )
    parser.add_argument(
        "--keep-widgets",
        action="store_true",
        help="Do not bake form widgets / leave AcroForm in place",
    )
    parser.add_argument(
        "--rasterize",
        type=int,
        nargs="?",
        const=200,
        default=None,
        metavar="DPI",
        help=(
            "Re-render each page as a raster image at given DPI (default 200) "
            "and rebuild the PDF from images. Strongest non-editable result, "
            "but loses text selection/search."
        ),
    )
    args = parser.parse_args()

    if not args.pdf.is_file():
        print(f"error: not a file: {args.pdf}", file=sys.stderr)
        return 1

    out = args.output or args.pdf.with_name(args.pdf.stem + ".flat.pdf")

    flatten(
        args.pdf,
        out,
        annots=not args.keep_annots,
        widgets=not args.keep_widgets,
        rasterize_dpi=args.rasterize,
    )
    mode = f"rasterized@{args.rasterize}dpi" if args.rasterize else "baked"
    print(f"Wrote {out} ({mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
