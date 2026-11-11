import json
import unittest
from pathlib import Path

import cv2
import numpy as np

from engine import (Settings, analyze, annotate, bit_distance, dictionary, encode_png,
                    estimate_pose, load_image, validate_calibration)

ROOT = Path(__file__).resolve().parents[1]


def generated(ids=(12,), size=160):
    image = np.full((size+100, len(ids)*(size+60)+40, 3), 255, np.uint8)
    for j, marker_id in enumerate(ids):
        marker = cv2.aruco.generateImageMarker(dictionary("DICT_4X4_250"), marker_id, size)
        x = 40+j*(size+60)
        image[50:50+size, x:x+size] = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
    return image


class DetectionTests(unittest.TestCase):
    def test_uploaded_sample(self):
        image = load_image((ROOT/"samples/demo.webp").read_bytes())
        result = analyze(image)
        self.assertEqual(result["count"], 45)
        self.assertEqual(result["unique_ids"], list(range(100, 145)))
        self.assertEqual(result["dictionary"], "DICT_4X4_250")
        self.assertIn("DICT_4X4_1000", result["tied_dictionaries"])
        self.assertEqual(sum(m["bit_errors"] for m in result["markers"]), 0)
        self.assertEqual(result["duplicate_ids"], {})
        self.assertEqual(annotate(image, result).shape, image.shape)
        self.assertTrue(encode_png(annotate(image, result)).startswith(b"\x89PNG"))
        json.dumps(result, allow_nan=False)

    def test_duplicate_ids_are_not_collapsed(self):
        report = analyze(generated((12, 12, 121)), Settings(dictionary="DICT_4X4_250"))
        self.assertEqual(report["count"], 3)
        self.assertEqual(report["duplicate_ids"], {"12": 2})
        self.assertEqual(report["unique_ids"], [12, 121])

    def test_rotation(self):
        image = cv2.rotate(generated((32,)), cv2.ROTATE_90_CLOCKWISE)
        result = analyze(image, Settings(dictionary="DICT_4X4_250", enhanced=False))
        self.assertEqual(result["unique_ids"], [32])
        self.assertEqual(result["markers"][0]["bit_errors"], 0)
        self.assertAlmostEqual(abs(result["markers"][0]["orientation_deg"]), 90, delta=1)

    def test_perspective_and_blur(self):
        image = generated((45,))
        h, w = image.shape[:2]
        transform = cv2.getPerspectiveTransform(np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]]),
            np.float32([[15,10],[w-20,20],[w-5,h-30],[20,h-5]]))
        image = cv2.warpPerspective(image, transform, (w,h), borderValue=(255,255,255))
        image = cv2.GaussianBlur(image, (3,3), .65)
        report = analyze(image, Settings(dictionary="DICT_4X4_250"))
        self.assertEqual(report["unique_ids"], [45])

    def test_blank(self):
        result = analyze(np.full((300,400,3), 255, np.uint8),
                         Settings(dictionary="DICT_4X4_250", enhanced=False))
        self.assertEqual(result["count"], 0)
        self.assertTrue(result["warnings"])

    def test_wrong_dictionary(self):
        result = analyze(generated((121,)), Settings(dictionary="DICT_4X4_50", enhanced=False))
        self.assertEqual(result["count"], 0)

    def test_invalid_bytes(self):
        with self.assertRaises(ValueError):
            load_image(b"not an image")

    def test_transparency_is_composited_white(self):
        from PIL import Image
        import io
        b = io.BytesIO()
        Image.new("RGBA", (20,30), (0,0,0,0)).save(b, format="PNG")
        self.assertTrue(np.all(load_image(b.getvalue()) == 255))

    def test_invalid_settings(self):
        with self.assertRaises(ValueError):
            analyze(generated(), Settings(border_bits=0))

    def test_calibration_resolution(self):
        c = {"camera_matrix": [[800,0,320],[0,800,240],[0,0,1]], "dist_coeffs": [0]*5,
             "image_width":640,"image_height":480}
        validate_calibration(c, 640, 480)
        with self.assertRaises(ValueError):
            validate_calibration(c, 1280, 960)

    def test_pose_with_known_projection(self):
        k = np.float64([[800,0,320],[0,800,240],[0,0,1]])
        dist = np.zeros(5)
        length = .05
        obj = np.float32([[-.025,.025,0],[.025,.025,0],[.025,-.025,0],[-.025,-.025,0]])
        rv = np.float64([2.9,.1,.2])
        tv = np.float64([.02,-.01,.6])
        corners, _ = cv2.projectPoints(obj, rv, tv, k, dist)
        pose = estimate_pose(corners.reshape(4,2), length, k, dist)
        self.assertIsNotNone(pose)
        self.assertLess(pose["reprojection_rmse_px"], .01)
        np.testing.assert_allclose(pose["tvec_m"], tv, atol=1e-4)


if __name__ == "__main__":
    unittest.main()
