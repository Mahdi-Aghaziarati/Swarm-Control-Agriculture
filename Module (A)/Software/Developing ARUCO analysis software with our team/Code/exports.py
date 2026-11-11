"""Export helpers shared by the desktop UI and tests."""
import csv
import io
import json

COLUMNS = ("instance", "id", "center_x_px", "center_y_px", "mean_side_px",
           "area_px2", "orientation_deg", "bit_errors", "border_errors", "source")


def csv_bytes(report):
    stream = io.StringIO(newline="")
    fields = list(COLUMNS) + ["perimeter_px", "side_ratio", "corners_px", "pose"]
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for marker in report["markers"]:
        row = dict(marker)
        row["corners_px"] = json.dumps(row["corners_px"])
        row["pose"] = json.dumps(row.get("pose"))
        writer.writerow(row)
    return stream.getvalue().encode("utf-8-sig")
