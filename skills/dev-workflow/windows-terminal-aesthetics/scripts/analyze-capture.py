#!/usr/bin/env python3
"""Measure what a window capture actually paints.

Companion to capture-window.ps1. Answers the questions that eyeballing cannot:
where the body colour actually is, whether the tab row leaves a seam across the
window, how much of the window the backdrop material contributes, and where
text really starts.

Only the standard library is required (zlib + struct decode the PNG), so this
runs anywhere Python 3.9+ is available - no Pillow, no numpy.

Typical use:

    python analyze-capture.py shot.png
    python analyze-capture.py shot.png --expect 0C0C0C     # calibration check
    python analyze-capture.py shot.png --json

Reading the report:

    body    The dominant colour of the lower part of the window: the terminal
            background as actually composited. Compare it to what the colour
            scheme asked for - the difference is what the backdrop material and
            opacity contributed.
    bands   Row ranges grouped by their dominant colour. A 1px band is a frame,
            a ~38px band near the top is the title bar / tab row, everything
            below is the body. A tab-row band whose colour differs from body is
            a visible seam.
    seam    |chrome - body| per channel against --threshold. This is the
            objective definition of "edgeless": the chrome may exist, it may
            hold tabs and buttons, but it must not paint a different colour.
    ink     First row with at least --min-ink pixels differing from body, and
            the horizontal extent of those pixels. Use it to report padding and
            to prove content starts where the theme said it should.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib
from collections import Counter

CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


class PngError(Exception):
    pass


def decode_png(path: str) -> tuple[int, int, list[bytes], int]:
    """Decode a non-interlaced 8-bit PNG into (width, height, rows, nchannels)."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise PngError("not a PNG file")

    pos, idat, palette = 8, bytearray(), None
    width = height = bitdepth = colortype = None
    while pos + 8 <= len(data):
        (length,) = struct.unpack_from(">I", data, pos)
        ctype = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            width, height, bitdepth, colortype, _comp, _filt, interlace = struct.unpack(">IIBBBBB", chunk)
            if interlace:
                raise PngError("interlaced PNG is not supported; re-save without interlacing")
            if bitdepth != 8:
                raise PngError(f"bit depth {bitdepth} is not supported (8-bit only)")
            if colortype not in CHANNELS:
                raise PngError(f"colour type {colortype} is not supported")
        elif ctype == b"PLTE":
            palette = [tuple(chunk[i:i + 3]) for i in range(0, len(chunk), 3)]
        elif ctype == b"IDAT":
            idat += chunk
        elif ctype == b"IEND":
            break
    if width is None:
        raise PngError("missing IHDR")

    nch = CHANNELS[colortype]
    stride = width * nch
    raw = zlib.decompress(bytes(idat))

    rows: list[bytes] = []
    prev = bytearray(stride)
    pos = 0
    for _ in range(height):
        filt = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        if filt == 1:
            for i in range(nch, stride):
                line[i] = (line[i] + line[i - nch]) & 0xFF
        elif filt == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif filt == 3:
            for i in range(stride):
                left = line[i - nch] if i >= nch else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif filt == 4:
            for i in range(stride):
                left = line[i - nch] if i >= nch else 0
                up = prev[i]
                upleft = prev[i - nch] if i >= nch else 0
                p = left + up - upleft
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - upleft)
                pred = left if (pa <= pb and pa <= pc) else (up if pb <= pc else upleft)
                line[i] = (line[i] + pred) & 0xFF
        elif filt != 0:
            raise PngError(f"unknown filter type {filt} on row {len(rows)}")

        if colortype == 3 and palette is not None:
            line = bytes(b for idx in line for b in palette[idx])
        elif colortype in (0, 4):
            step = 1
            line = bytes(b for i in range(0, len(line), step) for b in (line[i], line[i], line[i]))
        rows.append(bytes(line))
        prev = line
    return width, height, rows, nch


def rgb_rows(width: int, rows: list[bytes], nch: int) -> list[list[tuple[int, int, int]]]:
    if nch == 3:
        return [list(zip(row[0::3], row[1::3], row[2::3])) for row in rows]
    if nch == 4:
        return [list(zip(row[0::4], row[1::4], row[2::4])) for row in rows]
    if nch == 2:
        return [list(zip(row[0::2], row[0::2], row[0::2])) for row in rows]
    return [list(zip(row[0::1], row[0::1], row[0::1])) for row in rows]


def hexstr(color) -> str:
    return "#{:02X}{:02X}{:02X}".format(*color)


def manhattan(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def _near(a, b, tol: int) -> bool:
    return max(abs(x - y) for x, y in zip(a, b)) <= tol


def _bands(rows, band_tolerance: int) -> list[dict]:
    """Group rows by dominant colour, merging neighbours within a tolerance.

    Backdrop materials dither by a unit or two, so exact-equality grouping
    shatters a uniform field into dozens of one-row bands and hides the real
    structure. A small tolerance collapses the dither while still separating a
    frame, a tab row and a body.
    """
    bands: list[dict] = []
    for y, row in enumerate(rows):
        color = Counter(row).most_common(1)[0][0]
        if bands and _near(bands[-1]["color"], color, band_tolerance):
            bands[-1]["end"] = y
            bands[-1]["rows"] += 1
        else:
            bands.append({"start": y, "end": y, "rows": 1, "color": color})
    return bands


def analyze(path: str, body_fraction: float, threshold: int, ink_tolerance: int,
            min_ink: int, expect: str | None, band_tolerance: int = 2,
            edge_max: int = 4, ink_fraction: float = 0.01) -> dict:
    width, height, raw_rows, nch = decode_png(path)
    rows = rgb_rows(width, raw_rows, nch)

    body_start = max(0, int(height * (1.0 - body_fraction)))
    body_rows = rows[body_start:]
    body_counter: Counter = Counter()
    sums = [0, 0, 0]
    npx = 0
    for row in body_rows:
        body_counter.update(row)
        npx += len(row)
        for i in range(3):
            sums[i] += sum(px[i] for px in row)
    body, body_count = body_counter.most_common(1)[0]
    body_mean = tuple(round(s / max(1, npx)) for s in sums)

    bands = _bands(rows, band_tolerance)
    body_idx = next((i for i, b in enumerate(bands) if _near(b["color"], body, band_tolerance)), None)
    ink_start = bands[body_idx]["start"] if body_idx is not None else 0

    # Two different quantities live at the top of a window and must not be
    # confused: the chrome (title bar / tab row), which the theme controls and
    # which is what "edgeless" is about, and the outermost frame line drawn by
    # the window manager, which theme colour settings generally cannot change.
    # The chrome seam decides PASS/FAIL; the edge line is reported for context.
    def band_info(b) -> dict:
        delta = [abs(a - c) for a, c in zip(b["color"], body)]
        return {"band": f"y={b['start']}..{b['end']} ({b['rows']}px)", "color": hexstr(b["color"]),
                "delta": delta, "max_delta": max(delta)}

    top = bands[:body_idx] if body_idx is not None else []
    edge = top[0] if top and top[0]["start"] == 0 and top[0]["rows"] <= edge_max else None
    chrome_bands = [b for b in top
                    if b is not edge and not _near(b["color"], body, band_tolerance)]
    chrome_band = max(chrome_bands, key=lambda b: b["rows"]) if chrome_bands else None

    seam = None
    if chrome_band is not None:
        seam = band_info(chrome_band)
        seam["pass"] = seam["max_delta"] <= threshold
    edge_info = band_info(edge) if edge is not None else None

    # ------------------------------------------------------- unpainted margins
    # A capture can include edges that are not window content: an unpainted
    # strip down the left, a 1px window-manager frame line, a bottom edge line.
    # Such an edge is constant along its entire length, which is exactly what
    # separates it from content - text rows are mixed, a dithered material is
    # spread across several near-identical colours, but a strip of border is one
    # colour for its whole length. Trimming them matters: without it every row
    # counts as containing ink, and the content measurements are off by the
    # width of the strip.
    def uniform_not_body(pixels) -> bool:
        common, count = Counter(pixels).most_common(1)[0]
        return count >= 0.95 * len(pixels) and manhattan(common, body) > 4

    x0 = 0
    while x0 < width - 1 and uniform_not_body([rows[y][x0] for y in range(height)]):
        x0 += 1
    x1 = width - 1
    while x1 > x0 and uniform_not_body([rows[y][x1] for y in range(height)]):
        x1 -= 1
    y0 = 0
    while y0 < height - 1 and uniform_not_body(rows[y0][x0:x1 + 1]):
        y0 += 1
    y1 = height - 1
    while y1 > y0 and uniform_not_body(rows[y1][x0:x1 + 1]):
        y1 -= 1

    # Content scan starts at the first body-coloured row: the tab row is not
    # content either, though with a seamless theme it is body coloured and its
    # own glyphs (tab icon and title) do read as ink - which is why ink rows are
    # grouped into runs rather than reported as one "first content row".
    ink_threshold = max(min_ink, int(round((x1 - x0 + 1) * ink_fraction)))
    ink_rows = []
    first_ink = None
    for y in range(max(ink_start, y0), y1 + 1):
        hits = [x for x in range(x0, x1 + 1) if manhattan(rows[y][x], body) > ink_tolerance]
        if len(hits) >= ink_threshold:
            ink_rows.append(y)
            if first_ink is None:
                first_ink = {"y": y, "count": len(hits), "x_min": hits[0], "x_max": hits[-1]}

    ink_runs: list[list[int]] = []
    for y in ink_rows:
        if ink_runs and y == ink_runs[-1][1] + 1:
            ink_runs[-1][1] = y
        else:
            ink_runs.append([y, y])

    result = {
        "capture": path,
        "size": f"{width}x{height}",
        "width": width,
        "height": height,
        "channels": nch,
        "body": {"hex": hexstr(body), "rgb": list(body), "mean": list(body_mean),
                 "share": round(body_count / max(1, width * len(body_rows)), 4),
                 "sampled_rows": f"{body_start}..{height - 1}"},
        "band_tolerance": band_tolerance,
        "bands": [{"range": f"y={b['start']}..{b['end']}", "height": b["rows"],
                   "hex": hexstr(b["color"]), "rows": b["rows"]} for b in bands],
        "seam": seam,
        "seam_threshold": threshold,
        "edge": edge_info,
        "ink_start_row": ink_start,
        "content_box": {"x": [x0, x1], "y": [y0, y1],
                        "trimmed_left": x0, "trimmed_right": width - 1 - x1,
                        "trimmed_top": y0, "trimmed_bottom": height - 1 - y1},
        "ink_threshold": ink_threshold,
        "first_ink": first_ink,
        "ink_row_count": len(ink_rows),
        "ink_runs": [{"range": f"y={a}..{b}", "rows": b - a + 1} for a, b in ink_runs[:12]],
        "ink_run_count": len(ink_runs),
    }
    if expect:
        want = tuple(int(expect.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        result["expect"] = {"hex": hexstr(want), "body_delta": [abs(a - b) for a, b in zip(body, want)]}
    return result


def report(res: dict) -> None:
    print(f"capture  : {res['capture']}")
    print(f"size     : {res['size']}  channels={res['channels']}")
    b = res["body"]
    print(f"body     : {b['hex']} rgb{tuple(b['rgb'])}  mean=rgb{tuple(b['mean'])}  "
          f"share={b['share']:.1%}  (rows {b['sampled_rows']})")
    print(f"           a low share with a mean close to the mode means a dithered field, not texture")
    if "expect" in res:
        e = res["expect"]
        delta = e["body_delta"]
        flag = "MATCH" if max(delta) <= 2 else "DIFFERS"
        print(f"expected : {e['hex']}  delta={tuple(delta)}  -> {flag}")
    print(f"bands    : (merged within {res['band_tolerance']} per channel)")
    for band in res["bands"]:
        print(f"           {band['range']:>14}  {band['height']:>4}px  {band['hex']}")
    seam = res["seam"]
    if seam:
        verdict = "PASS" if seam["pass"] else "FAIL"
        print(f"seam     : chrome {seam['color']} @ {seam['band']}  delta={tuple(seam['delta'])}  "
              f"max={seam['max_delta']} (<= {res['seam_threshold']})  -> {verdict}")
    else:
        print("seam     : PASS by construction - no band above the body paints a different colour")
    edge = res.get("edge")
    if edge:
        print(f"edge     : {edge['color']} @ {edge['band']}  delta={tuple(edge['delta'])}  "
              f"-> window-manager frame line, not themeable by colour settings")
    box = res["content_box"]
    print(f"content  : x={box['x'][0]}..{box['x'][1]}  y={box['y'][0]}..{box['y'][1]}  "
          f"(trimmed L{box['trimmed_left']} R{box['trimmed_right']} T{box['trimmed_top']} B{box['trimmed_bottom']} "
          f"as unpainted/uniform edges)")
    ink = res["first_ink"]
    if ink:
        print(f"ink      : {res['ink_run_count']} run(s), >= {res['ink_threshold']} px/row counted as content")
        for run in res["ink_runs"]:
            print(f"           {run['range']:>14}  {run['rows']:>4}px")
        print(f"           first run starts at y={ink['y']} with {ink['count']} px at x={ink['x_min']}..{ink['x_max']}"
              f"  (tab icon/title when the tab row is seamless, else terminal text)")
    else:
        print("ink      : none found")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Measure body colour, band structure, seam and text origin of a window capture.")
    ap.add_argument("capture")
    ap.add_argument("--body-fraction", type=float, default=0.35,
                    help="fraction of the bottom of the image used to determine the body colour (default 0.35)")
    ap.add_argument("--threshold", type=int, default=8,
                    help="max per-channel difference between chrome and body still counted as seamless (default 8)")
    ap.add_argument("--ink-tolerance", type=int, default=30,
                    help="manhattan distance from body colour above which a pixel counts as ink (default 30)")
    ap.add_argument("--min-ink", type=int, default=3,
                    help="ink pixels in a row needed to call it a content row (default 3)")
    ap.add_argument("--band-tolerance", type=int, default=2,
                    help="per-channel difference within which adjacent row colours are merged into one band "
                         "(default 2; raise it for dithered backdrop materials)")
    ap.add_argument("--edge-max", type=int, default=4,
                    help="rows at most for the top row band to be treated as the window-manager frame line "
                         "rather than chrome (default 4)")
    ap.add_argument("--ink-fraction", type=float, default=0.01,
                    help="share of the content width a row must cover to count as a content row, on top of "
                         "--min-ink (default 0.01, i.e. 1%%)")
    ap.add_argument("--expect", help="hex colour the body should equal, for calibration (e.g. 0C0C0C)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a report")
    args = ap.parse_args(argv)

    try:
        res = analyze(args.capture, args.body_fraction, args.threshold, args.ink_tolerance,
                      args.min_ink, args.expect, args.band_tolerance, args.edge_max, args.ink_fraction)
    except (PngError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        report(res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
