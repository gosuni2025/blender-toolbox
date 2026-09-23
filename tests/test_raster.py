"""Run with Python + NumPy, or Blender's bundled Python."""
import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'uv_pixel_transform'))
from raster import PixelSelection, TransformError, affine, triangle_mask, sample


def rectangle(x, y, w, h):
    return np.array([[(x, y), (x + w, y), (x + w, y + h)],
                     [(x, y), (x + w, y + h), (x, y + h)]], dtype=float)


class RasterTests(unittest.TestCase):
    def setUp(self):
        self.image = np.zeros((32, 64, 4), dtype=np.float32)
        yy, xx = np.mgrid[:4, :4]
        self.patch = np.stack((xx / 3, yy / 3, np.full_like(xx, .5, dtype=float), np.ones_like(xx)), axis=-1)
        self.image[4:8, 4:8] = self.patch
        self.tris = rectangle(4, 4, 4, 4)

    def test_integer_move_is_exact_and_erases_source(self):
        selection = PixelSelection(self.image, self.tris, padding=0)
        result = selection.render(affine((6, 6), (12, 8)))
        np.testing.assert_array_equal(result[12:16, 16:20], self.patch.astype(np.float32))
        self.assertFalse(result[4:8, 4:8].any())
        np.testing.assert_array_equal(selection.image, self.image)

    def test_double_scale_nearest(self):
        selection = PixelSelection(self.image, self.tris, padding=0)
        result = selection.render(affine((4, 4), (12, 8), 2), 'NEAREST')
        expected = np.repeat(np.repeat(self.patch, 2, axis=0), 2, axis=1).astype(np.float32)
        np.testing.assert_array_equal(result[12:20, 16:24], expected)

    def test_rotation_non_square_image(self):
        selection = PixelSelection(self.image, self.tris, padding=0)
        result = selection.render(affine((6, 6), (12, 8), 1, math.pi / 2), 'NEAREST')
        # Positive Y is up, so a counterclockwise rotation is clockwise in row order.
        np.testing.assert_array_equal(result[12:16, 16:20], np.rot90(self.patch, -1).astype(np.float32))

    def test_identity_preserves_every_pixel(self):
        selection = PixelSelection(self.image, self.tris, padding=2)
        np.testing.assert_array_equal(selection.render(np.eye(3)), self.image)

    def test_copy_keeps_original(self):
        selection = PixelSelection(self.image, self.tris, padding=0)
        result = selection.render(affine((6, 6), (12, 8)), clear_source=False)
        np.testing.assert_array_equal(result[4:8, 4:8], self.patch.astype(np.float32))

    def test_concave_mask_does_not_move_bounding_box(self):
        tris = np.concatenate((rectangle(4, 4, 2, 6), rectangle(6, 4, 4, 2)))
        image = np.zeros_like(self.image)
        image[4:10, 4:10] = [0.2, 0.4, 0.6, 1]
        mask = triangle_mask(tris, 64, 32)
        selection = PixelSelection(image, tris, padding=0)
        result = selection.render(affine((7, 7), (12, 0)), 'NEAREST')
        np.testing.assert_array_equal(result[7:10, 7:10], image[7:10, 7:10])
        self.assertEqual(np.count_nonzero(mask), 20)
        self.assertFalse(result[7:10, 19:22].any())

    def test_overlapping_move_reads_original_pixels(self):
        selection = PixelSelection(self.image, self.tris, padding=0)
        result = selection.render(affine((6, 6), (1, 0)), 'NEAREST')
        np.testing.assert_array_equal(result[4:8, 5:9], self.patch.astype(np.float32))

    def test_stationary_island_and_padding_are_protected(self):
        image = self.image.copy()
        image[19:25, 29:35] = [1, 0, 0, 1]
        selection = PixelSelection(image, self.tris, rectangle(30, 20, 4, 4), padding=1)
        with self.assertRaisesRegex(TransformError, 'overlaps'):
            selection.render(affine((6, 6), (26, 16)))
        result = selection.render(affine((6, 6), (12, 8)))
        np.testing.assert_array_equal(result[19:25, 29:35], image[19:25, 29:35])

    def test_source_overlap_rejected(self):
        with self.assertRaisesRegex(TransformError, 'share pixels'):
            PixelSelection(self.image, self.tris, self.tris, padding=0)

    def test_self_scale_clips_padding_instead_of_rejecting_gutter_contact(self):
        image = self.image.copy()
        image[2:10, 9:17] = [0, .6, .8, 1]
        selection = PixelSelection(image, self.tris, rectangle(11, 4, 4, 4), padding=2)
        protected_before = image[selection.protected].copy()
        for clear in (False, True):
            result = selection.render(affine((6, 6), scale=1.2), clear_source=clear, composite=True)
            np.testing.assert_array_equal(result[selection.protected], protected_before)
            np.testing.assert_array_equal(selection.image, image)
            self.assertTrue(result[selection.mask, 3].any())

    def test_source_pixels_remain_usable_inside_existing_neighbour_gutter(self):
        image = self.image.copy()
        image[4:8, 9:13] = [0, .6, .8, 1]
        selection = PixelSelection(image, self.tris, rectangle(9, 4, 4, 4), padding=2)
        for clear in (False, True):
            result = selection.render(affine((6, 6), scale=.9), clear_source=clear, composite=True)
            np.testing.assert_array_equal(result[selection.stationary], image[selection.stationary])
            np.testing.assert_array_equal(result[selection.protected], image[selection.protected])

    def test_uv_body_entering_neighbour_gutter_is_still_rejected(self):
        selection = PixelSelection(self.image, self.tris, rectangle(11, 4, 4, 4), padding=2)
        with self.assertRaisesRegex(TransformError, 'overlaps'):
            selection.render(affine((6, 6), (3, 0)))
        np.testing.assert_array_equal(selection.image, self.image)

    def test_out_of_bounds_rejected_without_mutation(self):
        selection = PixelSelection(self.image, self.tris, padding=0)
        with self.assertRaisesRegex(TransformError, 'inside'):
            selection.render(affine((6, 6), (-5, 0)))
        np.testing.assert_array_equal(selection.image, self.image)

    def test_premultiplied_filter_has_no_transparent_color_fringe(self):
        image = np.array([[[1, 0, 0, 1], [0, 0, 1, 0]]], dtype=np.float32)
        result = sample(image, np.array([[1.0, .5]]))
        np.testing.assert_allclose(result, [[1, 0, 0, .5]])

    def test_repeated_previews_never_accumulate_resampling(self):
        selection = PixelSelection(self.image, self.tris, padding=0)
        target = affine((6, 6), (10, 10), 1.6, .2)
        expected = selection.render(target)
        for factor in (1.1, 1.4, 1.9, 1.2):
            selection.render(affine((6, 6), (10, 10), factor))
        np.testing.assert_array_equal(selection.render(target), expected)

    def test_edge_extrusion_keeps_background_out_of_scaled_edges(self):
        image = np.full_like(self.image, [0, 1, 0, 1])
        image[4:8, 4:8] = [1, 0, 0, 1]
        selection = PixelSelection(image, self.tris, padding=1)
        result = selection.render(affine((4, 4), (12, 8), 2))
        np.testing.assert_allclose(result[12:20, 16:24], np.broadcast_to([1, 0, 0, 1], (8, 8, 4)))

    def test_invalid_scale_and_tiny_selection(self):
        with self.assertRaises(TransformError):
            affine((0, 0), scale=0)
        with self.assertRaises(TransformError):
            PixelSelection(self.image, rectangle(0, 0, .1, .1))

    def test_outside_preview_retains_source_for_return_after_scale_rotation(self):
        selection = PixelSelection(self.image, self.tris, padding=0)
        outside = affine((6, 6), (-100, 0), 2, .7)
        result = selection.render(outside, allow_outside=True)
        self.assertFalse(result.any())
        partial = selection.render(affine((6, 6), (-6, 0)), allow_outside=True)
        np.testing.assert_array_equal(partial[4:8, :2], self.patch[:, 2:].astype(np.float32))
        returned = affine((6, 6), (12, 8), 2, .7)
        expected = PixelSelection(self.image, self.tris, padding=0).render(returned)
        np.testing.assert_array_equal(selection.render(returned, allow_outside=True), expected)
        np.testing.assert_array_equal(selection.render(np.eye(3)), self.image)

    def test_outside_option_still_protects_neighbours_and_rejects_tiny_inside(self):
        selection = PixelSelection(self.image, self.tris, rectangle(20, 4, 4, 4), padding=0)
        with self.assertRaisesRegex(TransformError, 'overlaps'):
            selection.render(affine((6, 6), (16, 0)), allow_outside=True)
        with self.assertRaisesRegex(TransformError, 'smaller'):
            selection.render(affine((6, 6), scale=.01), allow_outside=True)

    def test_layer_composites_over_background_and_keeps_original_when_requested(self):
        image = self.image.copy()
        image[4:8, 4:8] = [1, 0, 0, .5]
        image[12:16, 16:20] = [0, 0, 1, 1]
        selection = PixelSelection(image, self.tris, padding=0)
        result = selection.render(affine((6, 6), (12, 8)), clear_source=False, composite=True)
        np.testing.assert_array_equal(result[4:8, 4:8], image[4:8, 4:8])
        np.testing.assert_allclose(result[12:16, 16:20], np.broadcast_to([.5, 0, .5, 1], (4, 4, 4)))

    def test_explicitly_allow_overwriting_other_islands(self):
        selection = PixelSelection(self.image, self.tris, rectangle(20, 4, 4, 4), padding=0)
        result = selection.render(affine((6, 6), (16, 0)), protect=False)
        np.testing.assert_array_equal(result[4:8, 20:24], self.patch.astype(np.float32))

    def test_all_filters_preserve_integer_move_and_avoid_transparent_fringe(self):
        selection = PixelSelection(self.image, self.tris, padding=0)
        for interpolation in ('NEAREST', 'BILINEAR', 'BICUBIC', 'LANCZOS3'):
            result = selection.render(affine((6, 6), (12, 8)), interpolation)
            np.testing.assert_allclose(result[12:16, 16:20], self.patch.astype(np.float32), atol=1e-6)
            transparent = np.array([[[1, 0, 0, 1], [0, 0, 1, 0]]], dtype=np.float32)
            filtered = sample(transparent, np.array([[.8, .5]]), interpolation)
            np.testing.assert_allclose(filtered[0, :3], [1, 0, 0], atol=1e-6)
            self.assertTrue(np.isfinite(filtered).all())

    def test_bicubic_and_lanczos_are_distinct_from_bilinear(self):
        impulse = np.zeros((5, 7, 4), dtype=np.float32)
        impulse[..., 3] = 1
        impulse[2, 3, :3] = 1
        point = np.array([[3.75, 2.5]])
        values = [float(sample(impulse, point, f)[0, 0]) for f in ('BILINEAR','BICUBIC','LANCZOS3')]
        self.assertEqual(len({round(v, 5) for v in values}), 3)


if __name__ == '__main__':
    unittest.main()
