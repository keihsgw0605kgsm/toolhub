#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz


INCH_PER_POINT = 1.0 / 72.0

PAGE_SIZE_PRESETS: dict[str, tuple[float, float]] = {
    "a4": (595.0, 842.0),
    "a4landscape": (842.0, 595.0),
    "a3": (842.0, 1191.0),
    "letter": (612.0, 792.0),
}


def parse_size(s: str) -> tuple[float, float]:
    s = s.strip().lower()
    if s in PAGE_SIZE_PRESETS:
        return PAGE_SIZE_PRESETS[s]
    if "x" in s:
        a, b = s.split("x", 1)
        return float(a.strip()), float(b.strip())
    raise argparse.ArgumentTypeError(
        f"Unknown size {s!r}. Use a4, a3, letter, a4landscape, or WIDTHxHEIGHT (points)."
    )


def resize_pages_to(
    src: Path,
    dst: Path,
    target_w: float,
    target_h: float,
) -> int:
    target = fitz.Rect(0, 0, target_w, target_h)
    out = fitz.open()
    src_doc = fitz.open(src)
    try:
        # Preserve visual appearance of annotations / widgets.
        src_doc.bake(annots=True, widgets=True)
        for i in range(src_doc.page_count):
            out.new_page(width=target_w, height=target_h)
            out[-1].show_pdf_page(target, src_doc, i)
        out.save(dst)
        return src_doc.page_count
    finally:
        src_doc.close()
        out.close()


@dataclass(frozen=True)
class DpiSample:
    page_index: int
    xref: int
    dpi_x: float
    dpi_y: float
    px_w: int
    px_h: int
    rect_w_pt: float
    rect_h_pt: float


def human_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    units = ["KiB", "MiB", "GiB", "TiB"]
    v = float(n)
    for u in units:
        v /= 1024.0
        if v < 1024.0:
            return f"{v:.2f} {u}"
    return f"{v:.2f} PiB"


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    x = (len(sorted_vals) - 1) * p
    i = int(math.floor(x))
    j = int(math.ceil(x))
    if i == j:
        return sorted_vals[i]
    w = x - i
    return sorted_vals[i] * (1 - w) + sorted_vals[j] * w


def collect_image_dpi_samples(doc: fitz.Document) -> list[DpiSample]:
    samples: list[DpiSample] = []
    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        for img in page.get_images(full=True):
            xref = int(img[0])
            rects = page.get_image_rects(xref)
            if not rects:
                continue

            try:
                info = doc.extract_image(xref)
                px_w = int(info.get("width") or 0)
                px_h = int(info.get("height") or 0)
            except Exception:
                continue

            if px_w <= 0 or px_h <= 0:
                continue

            for r in rects:
                rect_w_pt = float(r.width)
                rect_h_pt = float(r.height)
                if rect_w_pt <= 0 or rect_h_pt <= 0:
                    continue

                w_in = rect_w_pt * INCH_PER_POINT
                h_in = rect_h_pt * INCH_PER_POINT
                if w_in <= 0 or h_in <= 0:
                    continue

                dpi_x = px_w / w_in
                dpi_y = px_h / h_in

                if not (math.isfinite(dpi_x) and math.isfinite(dpi_y)):
                    continue

                samples.append(
                    DpiSample(
                        page_index=page_index,
                        xref=xref,
                        dpi_x=dpi_x,
                        dpi_y=dpi_y,
                        px_w=px_w,
                        px_h=px_h,
                        rect_w_pt=rect_w_pt,
                        rect_h_pt=rect_h_pt,
                    )
                )
    return samples


def cmd_info(pdf: Path) -> int:
    if not pdf.is_file():
        print(f"error: not a file: {pdf}", file=sys.stderr)
        return 1

    size = pdf.stat().st_size
    doc = fitz.open(pdf)
    try:
        samples = collect_image_dpi_samples(doc)
        dpi_vals = sorted((min(s.dpi_x, s.dpi_y) for s in samples if s.dpi_x > 0 and s.dpi_y > 0))

        print(f"File: {pdf}")
        print(f"Size: {human_bytes(size)} ({size} bytes)")
        print(f"Pages: {doc.page_count}")
        if doc.page_count:
            # Print page size summary; some PDFs have unexpectedly huge MediaBox.
            sizes = []
            for i in range(doc.page_count):
                r = doc.load_page(i).rect
                sizes.append((r.width, r.height))
            uniq = sorted({(round(w, 1), round(h, 1)) for (w, h) in sizes})
            if len(uniq) == 1:
                w, h = uniq[0]
                print(f"Page size: {w:.1f} x {h:.1f} pt")
            else:
                print("Page sizes (pt):")
                for i, (w, h) in enumerate(sizes, start=1):
                    print(f"  - page {i}: {w:.1f} x {h:.1f} pt")

        if not samples:
            print("Images: (no extractable images found)")
            return 0

        p10 = percentile(dpi_vals, 0.10)
        p50 = percentile(dpi_vals, 0.50)
        p90 = percentile(dpi_vals, 0.90)
        mn = dpi_vals[0]
        mx = dpi_vals[-1]

        print(f"Images: {len(samples)} placements (effective DPI is estimated)")
        print(f"Effective DPI (min/10%/median/90%/max): {mn:.0f} / {p10:.0f} / {p50:.0f} / {p90:.0f} / {mx:.0f}")

        # Show a small per-page summary (top 10 pages by worst DPI)
        worst_by_page: dict[int, float] = {}
        for s in samples:
            v = min(s.dpi_x, s.dpi_y)
            prev = worst_by_page.get(s.page_index)
            if prev is None or v < prev:
                worst_by_page[s.page_index] = v

        worst_pages = sorted(worst_by_page.items(), key=lambda kv: kv[1])[:10]
        if worst_pages:
            print("Worst pages (by effective DPI, smaller = more compressed/blurrier when printed):")
            for page_index, v in worst_pages:
                print(f"  - page {page_index + 1}: ~{v:.0f} dpi")

        return 0
    finally:
        doc.close()


GS_PRESETS = {
    "screen": "/screen",
    "ebook": "/ebook",
    "printer": "/printer",
    "prepress": "/prepress",
    "default": "/default",
}


def find_ghostscript() -> str | None:
    return shutil.which("gs") or shutil.which("gswin64c") or shutil.which("gswin32c")


def compress_with_ghostscript(
    gs: str,
    src: Path,
    dst: Path,
    dpi: int | None,
    preset: str,
    keep_color: bool,
) -> None:
    # Ghostscript uses points (1/72 inch) internally; we request downsampling resolution.
    # If dpi is None, rely on preset only.
    args = [
        gs,
        "-q",
        "-dNOPAUSE",
        "-dBATCH",
        "-dSAFER",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={GS_PRESETS[preset]}",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        "-dSubsetFonts=true",
        "-dAutoRotatePages=/None",
        "-dDownsampleColorImages=true",
        "-dDownsampleGrayImages=true",
        "-dDownsampleMonoImages=true",
        "-dColorImageDownsampleType=/Bicubic",
        "-dGrayImageDownsampleType=/Bicubic",
        "-dMonoImageDownsampleType=/Subsample",
    ]

    if dpi is not None:
        args += [
            f"-dColorImageResolution={dpi}",
            f"-dGrayImageResolution={dpi}",
            f"-dMonoImageResolution={dpi}",
        ]

    if keep_color:
        args += ["-sColorConversionStrategy=LeaveColorUnchanged"]
    else:
        args += ["-sColorConversionStrategy=RGB"]

    args += [
        f"-sOutputFile={str(dst)}",
        str(src),
    ]

    subprocess.run(args, check=True)


def compress_with_pymupdf(src: Path, dst: Path) -> None:
    doc = fitz.open(src)
    try:
        # This does not change DPI; it can still reduce size (object cleanup + deflate).
        doc.save(
            dst,
            garbage=4,
            deflate=True,
            clean=True,
            deflate_images=True,
            deflate_fonts=True,
            pretty=False,
            linear=False,
        )
    finally:
        doc.close()


def cmd_compress(pdf: Path, out: Path, dpi: int | None, preset: str, force: bool) -> int:
    if not pdf.is_file():
        print(f"error: not a file: {pdf}", file=sys.stderr)
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and not force:
        print(f"error: output exists: {out} (use --force to overwrite)", file=sys.stderr)
        return 1

    gs = find_ghostscript()
    before = pdf.stat().st_size

    try:
        if gs:
            compress_with_ghostscript(
                gs=gs,
                src=pdf,
                dst=out,
                dpi=dpi,
                preset=preset,
                keep_color=True,
            )
            method = f"ghostscript ({os.path.basename(gs)})"
        else:
            compress_with_pymupdf(pdf, out)
            method = "pymupdf optimize-save (no DPI change)"
    except subprocess.CalledProcessError as e:
        print(f"error: ghostscript failed: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"error: compress failed: {e}", file=sys.stderr)
        return 2

    after = out.stat().st_size if out.exists() else 0
    ratio = (after / before) if before > 0 else float("nan")
    print(f"Input : {pdf} ({human_bytes(before)})")
    print(f"Output: {out} ({human_bytes(after)})")
    if math.isfinite(ratio):
        print(f"Ratio : {ratio:.3f}")
    print(f"Method: {method}")
    if not gs:
        print("Note  : Install 'gs' to downsample by DPI.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Inspect PDF size/DPI and compress PDFs.")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_info = sub.add_parser("info", help="Show PDF size and estimated effective DPI for images")
    p_info.add_argument("pdf", type=Path, help="Input PDF path")
    p_info.set_defaults(_fn=lambda a: cmd_info(a.pdf))

    p_resize = sub.add_parser(
        "resize",
        help="Normalize page size (e.g., to A4) while keeping aspect ratio",
    )
    p_resize.add_argument("pdf", type=Path, help="Input PDF path")
    p_resize.add_argument("-o", "--output", type=Path, required=True, help="Output PDF path")
    p_resize.add_argument(
        "--size",
        type=parse_size,
        default=parse_size("a4"),
        metavar="SPEC",
        help="Target page size: a4 (default), a3, letter, a4landscape, or WIDTHxHEIGHT in points",
    )
    p_resize.add_argument("--force", action="store_true", help="Overwrite output if it exists")

    def _resize(a: argparse.Namespace) -> int:
        if not a.pdf.is_file():
            print(f"error: not a file: {a.pdf}", file=sys.stderr)
            return 1
        a.output.parent.mkdir(parents=True, exist_ok=True)
        if a.output.exists() and not a.force:
            print(
                f"error: output exists: {a.output} (use --force to overwrite)",
                file=sys.stderr,
            )
            return 1
        tw, th = a.size
        n = resize_pages_to(a.pdf, a.output, tw, th)
        print(f"Wrote {a.output}: {n} pages at {tw:.0f}x{th:.0f} pt")
        return 0

    p_resize.set_defaults(_fn=_resize)

    p_comp = sub.add_parser("compress", help="Compress PDF (downsample images if Ghostscript is available)")
    p_comp.add_argument("pdf", type=Path, help="Input PDF path")
    p_comp.add_argument("-o", "--output", type=Path, required=True, help="Output PDF path")
    p_comp.add_argument(
        "--dpi",
        type=int,
        default=None,
        help="Target image downsample DPI (Ghostscript only). If omitted, preset controls it.",
    )
    p_comp.add_argument(
        "--preset",
        choices=sorted(GS_PRESETS.keys()),
        default="ebook",
        help="Ghostscript PDFSETTINGS preset (default: ebook)",
    )
    p_comp.add_argument("--force", action="store_true", help="Overwrite output if it exists")
    p_comp.set_defaults(_fn=lambda a: cmd_compress(a.pdf, a.output, a.dpi, a.preset, a.force))

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args._fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
