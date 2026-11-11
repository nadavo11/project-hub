"""Numerical controls use synthetic fixtures, never scientific findings."""

import unittest

try:
    import cv2
    import numpy as np
    from .failure_atlas_run import analyze, coverage, solve
except ModuleNotFoundError:
    np = None


@unittest.skipIf(np is None, "Run with the existing localization-models NumPy/OpenCV interpreter")
class FailureAnalysisTests(unittest.TestCase):
    def test_self_consistency_does_not_invent_point_accuracy_or_pose(self):
        q = np.array([(x, y) for x in (20., 60., 100., 140.) for y in (20., 60., 100., 140.)])
        case = {"query": {"width": 200, "height": 200}, "target": {"width": 200, "height": 200},
                "camera": {"metric_pose_supported": False, "reason": "No calibrated depth"},
                "geography": {"status": "identity verified"}, "point_ground_truth": "Unavailable"}
        result = analyze(case, q, q + 2, np.ones(len(q)), {})
        self.assertEqual(result["homography"]["inliers"], 16)
        self.assertIsNone(result["point_accuracy"])
        self.assertEqual(result["pose"]["status"], "unsupported")
        self.assertEqual(result["stage"], "missing metric geometry")

    def test_collinear_coverage_is_not_spatial_information(self):
        self.assertEqual(coverage(np.column_stack([np.arange(20), np.arange(20)]), [100, 100])["hull_fraction"], 0)
        self.assertLess(coverage(np.column_stack([np.arange(20), np.arange(20)]), [100, 100])["axis_ratio"], 1e-10)

    def test_calibrated_pnp_recovers_known_camera_on_real_solver(self):
        rng = np.random.default_rng(42)
        points = rng.uniform([-2, -2, 5], [2, 2, 9], (80, 3))
        K = np.array([[500., 0, 320], [0, 500., 240], [0, 0, 1.]])
        r, t = np.array([.1, -.1, .05]), np.array([.3, .1, .2])
        pixels = cv2.projectPoints(points, r, t, K, None)[0].reshape(-1, 2)
        truth = (-cv2.Rodrigues(r)[0].T @ t) * [1, -1, 1]
        result, mask, errors = solve(points, pixels, K, np.zeros(5), truth)
        self.assertEqual(result["status"], "estimated")
        self.assertTrue(mask.all())
        self.assertLess(result["horizontal_error_m"], .001)
        self.assertLess(errors.max(), .001)

    def test_insufficient_matches_never_returns_metric_error(self):
        result, _, _ = solve(np.zeros((3, 3)), np.zeros((3, 2)), np.eye(3), np.zeros(5), np.zeros(3))
        self.assertEqual(result["status"], "unsolved")
        self.assertIsNone(result["horizontal_error_m"])


if __name__ == "__main__":
    unittest.main()
