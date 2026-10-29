"""Local text recognition with the macOS Vision framework (no cloud, no Tesseract)."""

from __future__ import annotations

import math
import re
import statistics

LANGUAGES = ["de-DE", "en-US"]


def _image_size(data) -> tuple[float, float, int]:
    """Pixel width, height (after EXIF rotation) and EXIF orientation."""
    import Quartz

    source = Quartz.CGImageSourceCreateWithData(data, None)
    props = Quartz.CGImageSourceCopyPropertiesAtIndex(source, 0, None) if source else None
    if not props:
        return 1.0, 1.0, 1
    width, height = float(props.get("PixelWidth", 1)), float(props.get("PixelHeight", 1))
    orientation = int(props.get("Orientation", 1))
    return (height, width, orientation) if orientation >= 5 else (width, height, orientation)


def _corners(rect, width: float, height: float) -> list[tuple[float, float]]:
    """Corners of a Vision rectangle in pixels, origin top-left."""
    return [(point.x * width, (1 - point.y) * height)
            for point in (rect.topLeft(), rect.topRight(), rect.bottomRight(), rect.bottomLeft())]


def recognize(image: bytes) -> str:
    """Return the text in an encoded image (PNG/JPEG/TIFF/GIF/HEIC), lines in reading order."""
    import Vision
    from Foundation import NSData

    data = NSData.dataWithBytes_length_(image, len(image))
    width, height, orientation = _image_size(data)
    handler = Vision.VNImageRequestHandler.alloc().initWithData_orientation_options_(data, orientation, None)
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setRecognitionLanguages_(LANGUAGES)
    request.setUsesLanguageCorrection_(True)
    ok, _ = handler.performRequests_error_([request], None)
    if not ok:
        return ""

    # Vision sometimes joins aligned lines of neighbouring columns into one observation.
    # Split observations at gaps much wider than a word space, using per-word positions.
    segments, angles = [], []
    for observation in request.results() or []:
        candidates = observation.topCandidates_(1)
        if not candidates:
            continue
        candidate = candidates[0]
        text = candidate.string()
        line = _corners(observation, width, height)
        line_height = math.dist(line[0], line[3])
        dx, dy = line[2][0] - line[3][0], line[2][1] - line[3][1]
        if math.hypot(dx, dy) > 4 * line_height:
            angles.append(math.atan2(dy, dx))
        words = []
        for match in re.finditer(r"\S+", text):
            box, _ = candidate.boundingBoxForRange_error_((match.start(), match.end() - match.start()), None)
            if box is not None:
                words.append((match.group(), _corners(box, width, height)))
        if len(words) < 2:
            segments.append((text, line))
            continue
        current = [words[0]]
        for word in words[1:]:
            if math.dist(current[-1][1][1], word[1][0]) > 1.5 * line_height:
                segments.append((" ".join(w[0] for w in current), [p for w in current for p in w[1]]))
                current = []
            current.append(word)
        segments.append((" ".join(w[0] for w in current), [p for w in current for p in w[1]]))

    # Straighten photographed pages so slanted neighbouring lines do not overlap.
    angle = statistics.median(angles) if angles else 0.0
    cos, sin = math.cos(-angle), math.sin(-angle)
    boxes = []
    for text, points in segments:
        rotated = [(x * cos - y * sin, x * sin + y * cos) for x, y in points]
        xs, ys = [p[0] for p in rotated], [p[1] for p in rotated]
        boxes.append((min(ys) / height, min(xs) / width, max(ys) / height, max(xs) / width, text))
    return "\n".join(_layout(boxes)).strip()


# Minimum gutter between text columns and minimum typical line width of a real text
# column (share of the image width). Narrower "columns" are table cells or diagram
# labels and are read row by row instead.
GUTTER = 0.015
COLUMN_WIDTH = 0.18


def _rows(boxes: list[tuple]) -> list[str]:
    """Join side-by-side fragments of the same visual line, top to bottom.

    Fragments that overlap horizontally are never the same line, which keeps
    slightly curved or slanted lines of photographed pages apart.
    """
    lines: list[list[tuple]] = []
    for box in sorted(boxes):
        centre = (box[0] + box[2]) / 2
        for line in reversed(lines[-3:]):
            first = line[0]
            close = abs((first[0] + first[2]) / 2 - centre) < max(box[2] - box[0], first[2] - first[0]) / 2
            if close and all(box[3] <= other[1] or box[1] >= other[3] for other in line):
                line.append(box)
                break
        else:
            lines.append([box])
    return [" ".join(part[4] for part in sorted(line, key=lambda p: p[1])) for line in lines]


def _layout(boxes: list[tuple]) -> list[str]:
    """Reading order for multi-column pages: whole columns left to right, spanning lines around them.

    Looks for the vertical cut that runs through the longest stretch of lines
    without crossing any of them, splits there and recurses on all parts.
    """
    if len(boxes) <= 1:
        return [box[4] for box in boxes]
    bands: list[list[tuple]] = []
    for box in sorted(boxes):
        if bands and box[0] < max(b[2] for b in bands[-1]) - 0.3 * (box[2] - box[0]):
            bands[-1].append(box)
        else:
            bands.append([box])

    candidates = set()
    for band in bands:
        edges = sorted((b[1], b[3]) for b in band)
        reach = edges[0][1]
        for left, right in edges[1:]:
            if left - reach >= GUTTER:
                candidates.add(round((reach + left) / 2, 3))
            reach = max(reach, right)

    def crosses(band, x):
        return any(b[1] < x < b[3] for b in band)

    def median_width(side):
        widths = sorted(b[3] - b[1] for b in side)
        return widths[len(widths) // 2]

    best = None
    for x in candidates:
        i = 0
        while i < len(bands):
            if crosses(bands[i], x):
                i += 1
                continue
            j = i
            while j < len(bands) and not crosses(bands[j], x):
                j += 1
            members = [b for band in bands[i:j] for b in band]
            left = [b for b in members if b[3] <= x]
            right = [b for b in members if b[1] >= x]
            if (j - i >= 2 and left and right and median_width(left) >= COLUMN_WIDTH
                    and median_width(right) >= COLUMN_WIDTH and (best is None or len(members) > best[0])):
                best = (len(members), i, j, left, right)
            i = j
    if best is None:
        return _rows(boxes)
    _, i, j, left, right = best
    before = [b for band in bands[:i] for b in band]
    after = [b for band in bands[j:] for b in band]
    return _layout(before) + _layout(left) + _layout(right) + _layout(after)
