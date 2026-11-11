"""ArUco analysis engine. Coordinates always refer to the EXIF-oriented input."""
from __future__ import annotations

import argparse
import io
import json
import math
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

DICTIONARIES = [f"DICT_{n}X{n}_{s}" for n in (4, 5, 6, 7) for s in (50, 100, 250, 1000)] + [
    "DICT_ARUCO_ORIGINAL", "DICT_APRILTAG_16h5", "DICT_APRILTAG_25h9",
    "DICT_APRILTAG_36h10", "DICT_APRILTAG_36h11", "DICT_ARUCO_MIP_36h12",
]
DICTIONARIES = [n for n in DICTIONARIES if hasattr(cv2.aruco, n)]
MAX_PIXELS = 24_000_000


@dataclass(frozen=True)
class Settings:
    dictionary: str = "AUTO"
    enhanced: bool = True
    inverted: bool = False
    correction_rate: float = 0.35
    border_bits: int = 1


def load_image(data: bytes) -> np.ndarray:
    try:
        with Image.open(io.BytesIO(data)) as raw:
            if raw.width * raw.height > MAX_PIXELS:
                raise ValueError("Image exceeds 24 megapixels. Resize it before opening.")
            image = ImageOps.exif_transpose(raw).convert("RGBA")
            bg = Image.new("RGBA", image.size, "white")
            bg.alpha_composite(image)
            return cv2.cvtColor(np.asarray(bg.convert("RGB")), cv2.COLOR_RGB2BGR)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("The image file is invalid or cannot be read.") from exc


def dictionary(name):
    if name not in DICTIONARIES:
        raise ValueError(f"Unsupported dictionary: {name}")
    return cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, name))


def detect(gray, name, settings):
    p = cv2.aruco.DetectorParameters()
    p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    p.cornerRefinementWinSize = 3
    p.cornerRefinementMaxIterations = 50
    p.cornerRefinementMinAccuracy = 0.01
    p.adaptiveThreshWinSizeMin = 3
    p.adaptiveThreshWinSizeMax = 53
    p.adaptiveThreshWinSizeStep = 10
    p.minMarkerPerimeterRate = 0.008
    p.errorCorrectionRate = settings.correction_rate
    p.markerBorderBits = settings.border_bits
    p.detectInvertedMarker = settings.inverted
    return cv2.aruco.ArucoDetector(dictionary(name), p).detectMarkers(gray)


def same_location(a, b):
    a, b = np.asarray(a).reshape(4, 2), np.asarray(b).reshape(4, 2)
    side = min(np.linalg.norm(np.roll(a, -1, axis=0) - a, axis=1).mean(),
               np.linalg.norm(np.roll(b, -1, axis=0) - b, axis=1).mean())
    return np.linalg.norm(a.mean(axis=0) - b.mean(axis=0)) < max(3, side * 0.35)


def bit_distance(gray, corners, marker_id, d, border_bits):
    """Diagnostic Hamming distance, not a confidence/probability estimate."""
    cells = d.markerSize + 2 * border_bits
    size = cells * 12
    target = np.float32([[0, 0], [size-1, 0], [size-1, size-1], [0, size-1]])
    transform = cv2.getPerspectiveTransform(np.float32(corners), target)
    patch = cv2.warpPerspective(gray, transform, (size, size))
    _, binary = cv2.threshold(patch, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bits = np.array([[int(binary[y*12+3:y*12+9, x*12+3:x*12+9].mean() > 127)
                      for x in range(cells)] for y in range(cells)], dtype=np.uint8)
    mask = np.ones_like(bits, dtype=bool)
    mask[border_bits:-border_bits, border_bits:-border_bits] = False
    # Also account for explicitly enabled inverted markers.
    if bits[mask].mean() > 0.5:
        bits = 1 - bits
    payload = bits[border_bits:-border_bits, border_bits:-border_bits].copy()
    return int(d.getDistanceToId(payload, int(marker_id), True)), int(bits[mask].sum())


def validate_calibration(data, width, height):
    k = np.asarray(data["camera_matrix"], dtype=np.float64)
    dist = np.asarray(data["dist_coeffs"], dtype=np.float64).reshape(-1, 1)
    if k.shape != (3, 3) or not np.isfinite(k).all() or k[0, 0] <= 0 or k[1, 1] <= 0:
        raise ValueError("camera_matrix must be a valid 3 x 3 intrinsic matrix.")
    if not np.allclose(k[2], [0, 0, 1]) or not np.allclose([k[0, 1], k[1, 0]], 0):
        raise ValueError("A standard OpenCV intrinsic matrix is required.")
    if dist.size not in (4, 5, 8, 12, 14) or not np.isfinite(dist).all():
        raise ValueError("dist_coeffs must contain 4, 5, 8, 12, or 14 finite coefficients.")
    if data.get("image_width") != width or data.get("image_height") != height:
        raise ValueError("Calibration dimensions must match the EXIF-oriented image exactly.")
    return k, dist


def estimate_pose(corners, length, k, dist):
    half = length / 2
    obj = np.float32([[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]])
    found, rvecs, tvecs, _ = cv2.solvePnPGeneric(obj, np.float32(corners), k, dist,
                                               flags=cv2.SOLVEPNP_IPPE_SQUARE)
    solutions = []
    if found:
        for rv, tv in zip(rvecs, tvecs):
            rotation, _ = cv2.Rodrigues(rv)
            if np.any((rotation @ obj.T + tv)[2] <= 0):
                continue
            projected, _ = cv2.projectPoints(obj, rv, tv, k, dist)
            error = float(np.sqrt(np.mean(np.sum((projected.reshape(4, 2)-corners)**2, axis=1))))
            solutions.append((error, rv, tv))
    if not solutions:
        return None
    error, rv, tv = min(solutions, key=lambda x: x[0])
    return {"rvec": rv.ravel().tolist(), "tvec_m": tv.ravel().tolist(),
            "distance_m": float(np.linalg.norm(tv)), "reprojection_rmse_px": error,
            "valid_planar_solutions": len(solutions)}


def analyze(image, settings=Settings(), calibration=None, marker_length_m=None):
    started = time.perf_counter()
    if image is None or image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError("Expected uint8 BGR image")
    if not 0 <= settings.correction_rate <= 1 or settings.border_bits not in (1, 2, 3):
        raise ValueError("Invalid detection settings")
    h, w = image.shape[:2]
    if h * w > MAX_PIXELS:
        raise ValueError("Image exceeds 24 MP")
    k = dist = None
    if calibration is not None:
        if marker_length_m is None or not math.isfinite(marker_length_m) or marker_length_m <= 0:
            raise ValueError("A positive physical marker side length in meters is required.")
        k, dist = validate_calibration(calibration, w, h)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    names = DICTIONARIES if settings.dictionary == "AUTO" else [settings.dictionary]
    runs, rankings = {}, []
    for name in names:
        corners, ids, rejected = detect(gray, name, settings)
        runs[name] = (corners, ids, rejected)
        distances = [bit_distance(gray, c.reshape(4, 2), i, dictionary(name), settings.border_bits)[0]
                     for c, i in zip(corners, ids.ravel())] if ids is not None else []
        rankings.append({"dictionary": name, "count": len(corners),
                         "zero_bit_matches": distances.count(0), "total_bit_errors": sum(distances)})
    rankings.sort(key=lambda r: (-r["count"], -r["zero_bit_matches"], r["total_bit_errors"], DICTIONARIES.index(r["dictionary"])))
    chosen = rankings[0]["dictionary"]
    corners, ids, rejected = runs[chosen]
    observations = [{"corners": c.reshape(4, 2), "id": int(i), "source": "original"}
                    for c, i in zip(corners, ids.ravel())] if ids is not None else []
    conflicts = []
    if settings.enhanced:
        variants = [("clahe", cv2.createCLAHE(2.0, (8, 8)).apply(gray), 1.0)]
        if h * w <= 6_000_000:
            variants.append(("upscale_2x", cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC), 2.0))
        for source, variant, scale in variants:
            cc, ii, _ = detect(variant, chosen, settings)
            for c, marker_id in zip(cc, ii.ravel() if ii is not None else []):
                c = c.reshape(4, 2) / scale
                # Pixel-center mapping for OpenCV resize.
                if scale != 1:
                    c -= (scale - 1) / (2 * scale)
                existing = next((m for m in observations if same_location(m["corners"], c)), None)
                if existing is None:
                    observations.append({"corners": c, "id": int(marker_id), "source": source})
                elif existing["id"] != int(marker_id):
                    conflicts.append({"kept_id": existing["id"], "alternative_id": int(marker_id),
                                      "center_px": c.mean(axis=0).tolist(), "source": source})
    observations.sort(key=lambda m: (float(m["corners"][:, 1].mean()), float(m["corners"][:, 0].mean())))
    markers = []
    d = dictionary(chosen)
    for index, m in enumerate(observations, 1):
        c = m["corners"]
        sides = np.linalg.norm(np.roll(c, -1, axis=0)-c, axis=1)
        center = c.mean(axis=0)
        errors, border_errors = bit_distance(gray, c, m["id"], d, settings.border_bits)
        row = {"instance": index, "id": m["id"], "center_x_px": float(center[0]),
               "center_y_px": float(center[1]), "corners_px": c.tolist(),
               "mean_side_px": float(sides.mean()), "perimeter_px": float(sides.sum()),
               "area_px2": float(abs(cv2.contourArea(c.astype(np.float32)))),
               "orientation_deg": float(np.degrees(np.arctan2(*(c[1]-c[0])[::-1]))),
               "side_ratio": float(sides.min()/sides.max()), "bit_errors": errors,
               "border_errors": border_errors, "source": m["source"]}
        if k is not None:
            row["pose"] = estimate_pose(c, marker_length_m, k, dist)
        markers.append(row)
    counts = Counter(m["id"] for m in markers)
    top = rankings[0]
    ties = [r["dictionary"] for r in rankings if r["count"] > 0 and
            (r["count"], r["zero_bit_matches"], r["total_bit_errors"]) ==
            (top["count"], top["zero_bit_matches"], top["total_bit_errors"])]
    warnings = []
    if settings.dictionary == "AUTO":
        warnings.append("Auto selection ranks detection count and bit matches. Confirm the printed dictionary. Different families are not merged.")
    if len(ties) > 1:
        warnings.append("Dictionary is ambiguous: multiple dictionaries have the same score.")
    if conflicts:
        warnings.append("Conflicting IDs were found across processing passes. Earlier detections were retained. Manual review is required.")
    if not markers:
        warnings.append("No markers detected. Check dictionary, borders, resolution, lighting, and inversion settings.")
    if k is not None:
        warnings.append("3D pose is an estimate. Planar ambiguity and calibration errors may remain. Reprojection RMSE does not guarantee physical accuracy.")
    return {"schema_version": "1.0", "opencv_version": cv2.__version__, "image": {"width": w, "height": h},
            "settings": vars(settings), "dictionary": chosen, "tied_dictionaries": ties,
            "dictionary_scan": rankings, "count": len(markers), "unique_ids": sorted(counts),
            "duplicate_ids": {str(i): n for i, n in counts.items() if n > 1},
            "rejected_candidates_original": len(rejected), "markers": markers, "conflicts": conflicts,
            "warnings": warnings, "marker_length_m": marker_length_m if k is not None else None,
            "elapsed_ms": round((time.perf_counter()-started)*1000, 1)}


def annotate(image, report, labels=True, centers=True, selected_ids=None):
    out = image.copy()
    thickness = max(1, round(min(image.shape[:2])/700))
    for m in report["markers"]:
        if selected_ids is not None and m["id"] not in selected_ids:
            continue
        c = np.rint(m["corners_px"]).astype(np.int32)
        cv2.polylines(out, [c], True, (170, 220, 25), thickness, cv2.LINE_AA)
        cv2.circle(out, tuple(c[0]), thickness*3, (80, 145, 255), -1, cv2.LINE_AA)
        if centers:
            cv2.drawMarker(out, (round(m["center_x_px"]), round(m["center_y_px"])),
                           (240, 180, 40), cv2.MARKER_CROSS, 10, thickness)
        if labels:
            text = f"ID {m['id']}"
            font, scale = cv2.FONT_HERSHEY_SIMPLEX, max(0.4, min(image.shape[:2])/1800)
            (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
            x = max(0, min(int(c[:, 0].min()), image.shape[1]-tw-8))
            y = max(th+10, int(c[:, 1].min())-6)
            cv2.rectangle(out, (x, y-th-6), (x+tw+6, y+baseline), (30, 39, 55), -1)
            cv2.putText(out, text, (x+3, y-2), font, scale, (230, 255, 245), thickness, cv2.LINE_AA)
    return out


def encode_png(image):
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("PNG encoding failed")
    return buffer.tobytes()


def main():
    parser = argparse.ArgumentParser(description="Analyze ArUco images locally")
    parser.add_argument("image", type=Path)
    parser.add_argument("--dictionary", default="AUTO", choices=["AUTO"]+DICTIONARIES)
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--marker-length-m", type=float)
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()
    image = load_image(args.image.read_bytes())
    calibration = json.loads(args.calibration.read_text()) if args.calibration else None
    result = analyze(image, Settings(dictionary=args.dictionary, enhanced=not args.fast), calibration, args.marker_length_m)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/"report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output/"annotated.png").write_bytes(encode_png(annotate(image, result)))
    print(f"{result['count']} markers | {result['dictionary']} | IDs: {result['unique_ids']}")


if __name__ == "__main__":
    main()
