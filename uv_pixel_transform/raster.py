"""Image-space transforms, independent of Blender. Pixels use bottom-left origin.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import math
import numpy as np


class TransformError(ValueError):
    """A transform cannot be applied without losing or overwriting data."""


def affine(pivot, offset=(0, 0), scale=1.0, angle=0.0):
    """Homogeneous pixel-space affine matrix; angle is counterclockwise radians."""
    if not np.isfinite([*pivot, *offset, scale, angle]).all() or scale <= 0:
        raise TransformError("Use finite values and a positive scale.")
    c, s = math.cos(angle) * scale, math.sin(angle) * scale
    linear = np.array(((c, -s), (s, c)), dtype=np.float64)
    result = np.eye(3)
    result[:2, :2] = linear
    result[:2, 2] = np.asarray(pivot) + offset - linear @ pivot
    return result


def transform_points(points, matrix):
    return np.asarray(points) @ matrix[:2, :2].T + matrix[:2, 2]


def triangle_mask(triangles, width, height):
    """Rasterize a union, testing pixel centers, without filling concave notches."""
    mask = np.zeros((height, width), dtype=bool)
    for tri in np.asarray(triangles).reshape(-1, 3, 2):
        a, b, c = tri
        ab, ac = b - a, c - a
        det = ab[0] * ac[1] - ab[1] * ac[0]
        if abs(det) < 1e-10:
            continue
        low = np.maximum(np.floor(tri.min(axis=0)).astype(int), 0)
        high = np.minimum(np.ceil(tri.max(axis=0)).astype(int), (width, height))
        if np.any(low >= high):
            continue
        # Limit temporary arrays even for large triangles.
        for y0 in range(low[1], high[1], 128):
            y1 = min(y0 + 128, high[1])
            yy, xx = np.mgrid[y0:y1, low[0]:high[0]]
            x, y = xx + 0.5 - a[0], yy + 0.5 - a[1]
            u = (x * (c[1] - a[1]) - y * (c[0] - a[0])) / det
            v = ((b[0] - a[0]) * y - (b[1] - a[1]) * x) / det
            mask[y0:y1, low[0]:high[0]] |= (u >= -1e-8) & (v >= -1e-8) & (u + v <= 1 + 1e-8)
    return mask


def dilate(mask, steps):
    result = mask.copy()
    for _ in range(steps):
        p = np.pad(result, 1)
        result = np.logical_or.reduce([p[y:y + mask.shape[0], x:x + mask.shape[1]]
                                       for y in range(3) for x in range(3)])
    return result


def extend_colors(image, mask, steps, forbidden=None):
    """Extend nearest available edge colors into the gutter, without alpha mixing."""
    result = image.copy()
    filled = mask.copy()
    h, w = mask.shape
    for _ in range(steps):
        frontier = dilate(filled, 1) & ~filled
        if forbidden is not None:
            frontier &= ~forbidden
        yy, xx = np.nonzero(frontier)
        remaining = np.ones(len(xx), dtype=bool)
        # Deterministic tie break; new texels cannot seed others in this pass.
        # Visit only the frontier, rather than gathering RGBA from the whole
        # island eight times per padding pixel.
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            sy, sx = yy - dy, xx - dx
            indices = np.flatnonzero(remaining & (sy >= 0) & (sy < h) & (sx >= 0) & (sx < w))
            take = indices[filled[sy[indices], sx[indices]]]
            result[yy[take], xx[take]] = result[sy[take], sx[take]]
            remaining[take] = False
        filled[yy[~remaining], xx[~remaining]] = True
    return result, filled


def cubic_weight(x):
    x = np.abs(x)
    return np.where(x <= 1, (1.5 * x - 2.5) * x * x + 1,
                    np.where(x < 2, ((-.5 * x + 2.5) * x - 4) * x + 2, 0))


def sample(image, coordinates, interpolation="BILINEAR", premultiplied=None):
    """Sample straight RGBA with premultiplied-alpha bilinear filtering."""
    h, w, _ = image.shape
    p = np.asarray(coordinates) - 0.5
    if interpolation == "NEAREST":
        x = np.clip(np.floor(p[:, 0] + 0.5).astype(int), 0, w - 1)
        y = np.clip(np.floor(p[:, 1] + 0.5).astype(int), 0, h - 1)
        return image[y, x]
    if interpolation not in {"BILINEAR", "BICUBIC", "LANCZOS3"}:
        raise TransformError("Unknown sampling method.")
    base = np.floor(p).astype(int)
    f = (p - base).astype(np.float32)
    if premultiplied is None:
        premultiplied = image.copy()
        premultiplied[..., :3] *= premultiplied[..., 3:4]
    if interpolation != 'BILINEAR':
        offsets = range(-1, 3) if interpolation == 'BICUBIC' else range(-2, 4)
        kernel = cubic_weight if interpolation == 'BICUBIC' else lambda x: np.sinc(x) * np.sinc(x / 3)
        wx = np.array([kernel(f[:, 0] - dx) for dx in offsets], dtype=np.float32)
        wy = np.array([kernel(f[:, 1] - dy) for dy in offsets], dtype=np.float32)
        wx /= wx.sum(axis=0)
        wy /= wy.sum(axis=0)
        result = np.zeros((len(p), 4), dtype=np.float32)
        for iy, dy in enumerate(offsets):
            y = np.clip(base[:, 1] + dy, 0, h - 1)
            for ix, dx in enumerate(offsets):
                x = np.clip(base[:, 0] + dx, 0, w - 1)
                result += premultiplied[y, x] * (wx[ix] * wy[iy])[:, None]
        alpha = result[:, 3:4].copy()
        np.divide(result[:, :3], alpha, out=result[:, :3], where=alpha > 1e-8)
        result[alpha[:, 0] <= 1e-8, :3] = 0
        result[:, 3] = np.clip(result[:, 3], 0, 1)
        return result
    x0 = np.clip(base[:, 0], 0, w - 1)
    x1 = np.clip(base[:, 0] + 1, 0, w - 1)
    y0 = np.clip(base[:, 1], 0, h - 1)
    y1 = np.clip(base[:, 1] + 1, 0, h - 1)
    fx, fy = f[:, 0:1], f[:, 1:2]
    top = premultiplied[y0, x0] * (1 - fx) + premultiplied[y0, x1] * fx
    bottom = premultiplied[y1, x0] * (1 - fx) + premultiplied[y1, x1] * fx
    result = top * (1 - fy) + bottom * fy
    np.divide(result[:, :3], result[:, 3:4], out=result[:, :3], where=result[:, 3:4] > 1e-8)
    result[result[:, 3] <= 1e-8, :3] = 0
    return result


class PixelSelection:
    """Immutable source for repeated previews; each preview resamples once."""

    def __init__(self, image, triangles, stationary=(), padding=2):
        self.image = np.asarray(image, dtype=np.float32).copy()
        if self.image.ndim != 3 or self.image.shape[2] != 4:
            raise TransformError("Expected an RGBA image.")
        self.height, self.width = self.image.shape[:2]
        self.triangles = np.asarray(triangles, dtype=np.float64).reshape(-1, 3, 2)
        self.padding = int(padding)
        if not 0 <= self.padding <= 16:
            raise TransformError("Padding must be between 0 and 16 pixels.")
        self._bounds(self.triangles)
        self.mask = triangle_mask(self.triangles, self.width, self.height)
        if not self.mask.any():
            raise TransformError("Selection is smaller than a pixel. Increase image resolution.")
        other = np.asarray(stationary, dtype=np.float64).reshape(-1, 3, 2)
        self._bounds(other)
        self.stationary = triangle_mask(other, self.width, self.height)
        if np.any(self.mask & self.stationary):
            raise TransformError("Selected and unselected UVs share pixels. Select all stacked islands together.")
        # Dense atlases can already place the source inside a neighbour's
        # nominal gutter. Those pixels belong to the selected island, and
        # must remain usable when scaling/rotating over its original area.
        self.protected = dilate(self.stationary, self.padding) & ~self.mask
        self.erase_mask = self.mask | (dilate(self.mask, self.padding) & ~self.protected)
        self.erase_indices = np.flatnonzero(self.erase_mask)
        # Extrude only the selected pixels before interpolation. This prevents
        # the checkerboard / neighbouring island from bleeding into scaled edges.
        self.source, _ = extend_colors(self.image, self.mask, max(3, self.padding), self.stationary)
        self.premultiplied = self.source.copy()
        self.premultiplied[..., :3] *= self.premultiplied[..., 3:4]

    def _bounds(self, triangles):
        if not np.isfinite(triangles).all():
            raise TransformError("UV coordinates must be finite.")
        if triangles.size and (np.any(triangles < -1e-5) or
                               np.any(triangles > np.array((self.width, self.height)) + 1e-5)):
            raise TransformError("Keep all UVs inside the image (0–1 tile). UDIM/repeated UVs are not supported yet.")

    def render(self, matrix, interpolation="BILINEAR", clear_source=True, allow_outside=False,
               protect=True, composite=False):
        matrix = np.asarray(matrix, dtype=np.float64)
        if matrix.shape != (3, 3) or not np.isfinite(matrix).all() or abs(np.linalg.det(matrix)) < 1e-10:
            raise TransformError("Transform must be finite and invertible.")
        if np.allclose(matrix, np.eye(3), atol=1e-10):
            return self.image.copy()
        target = transform_points(self.triangles, matrix)
        outside = np.any(target < -1e-5) or np.any(target > np.array((self.width, self.height)) + 1e-5)
        if not allow_outside:
            self._bounds(target)
        # Only rasterize/extrude the destination's bounding box. A small island
        # should not run eight full-image neighbour passes on every mouse move.
        low = np.clip(np.floor(target.min(axis=(0, 1))).astype(int) - self.padding,
                      0, (self.width, self.height))
        high = np.clip(np.ceil(target.max(axis=(0, 1))).astype(int) + self.padding,
                       0, (self.width, self.height))
        result = self.image.copy()
        if clear_source:
            result.reshape(-1, 4)[self.erase_indices] = 0
        if np.any(low >= high):
            return result
        x0, y0 = low
        x1, y1 = high
        mask = triangle_mask(target - low, x1 - x0, y1 - y0)
        protected = self.protected[y0:y1, x0:x1] if protect else np.zeros_like(mask)
        if not mask.any():
            if allow_outside and outside:
                return result
            raise TransformError("The transformed selection is smaller than a pixel.")
        # Padding is best-effort: clip destination extrusion against protected
        # texels below. Overlapping two gutters must not reject the UV body.
        if np.any(mask & protected):
            raise TransformError("Destination overlaps another island or its padding. Move it or reduce Padding.")
        patch = result[y0:y1, x0:x1]
        inverse = np.linalg.inv(matrix)
        yy, xx = np.nonzero(mask)
        for start in range(0, len(xx), 131072):
            x, y = xx[start:start + 131072], yy[start:start + 131072]
            coords = np.column_stack((x + x0 + 0.5, y + y0 + 0.5))
            colors = sample(self.source, transform_points(coords, inverse), interpolation,
                            self.premultiplied)
            if composite:
                background = patch[y, x]
                alpha = colors[:, 3:4] + background[:, 3:4] * (1 - colors[:, 3:4])
                rgb = (colors[:, :3] * colors[:, 3:4] +
                       background[:, :3] * background[:, 3:4] * (1 - colors[:, 3:4]))
                np.divide(rgb, alpha, out=rgb, where=alpha > 1e-8)
                colors = np.concatenate((rgb, alpha), axis=1)
            patch[y, x] = colors
        if self.padding:
            padded, _ = extend_colors(patch, mask, self.padding, protected)
            patch[:] = padded
        return result
