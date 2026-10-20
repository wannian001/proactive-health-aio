#!/usr/bin/env python3
"""Build the Recovery page's turnable body, healthaio/web/models/recovery/body.bin, from MakeHuman's base mesh.

    python3 tools/make_body_mesh.py                 # downloads the MakeHuman files once, into ~/.cache/healthaio
    python3 tools/make_body_mesh.py --weight 0.3    # a lighter build; see --help for the other dials

Everything it reads comes from the MakeHuman 1.x repository at one pinned commit, released there as CC0: the base
mesh, the macro targets (gender, age, muscle, weight, height, proportions), the default skeleton and its vertex
weights. It needs numpy, scipy and scikit-image; the app reads the finished file and has no new dependency.

The figure is a cartoon, not a portrait (a realistic body read as uncanny): a lean build rounded like a toy, a
slightly big head with no face, mitten-like hands, slate shorts, and the muscles' places drawn as lines the way a
fitness chart draws them. In order (models/recovery/MODEL.md says the same for readers of the app):
1. the base mesh's body (a closed quad mesh); the helper geometry (eyes, teeth, lashes, clothes helpers) is left out
2. the macro targets mixed the way MakeHuman mixes them, for a lean, fit man of 25 (age 0.5)
3. a relaxed stance by linear blend skinning: the elbows straightened from MakeHuman's bent rest pose (a few degrees
   of bend kept), then the arms lowered about the shoulders
4. the shorts: Taubin smoothing (which keeps volume) until the fabric hides what is under it, then 5 mm proud
5. one Catmull-Clark subdivision, for round outlines; then each vertex's region, one of the seven check-in regions
   (schema.SORE_REGIONS) or "other" (forearms, hands, thighs, feet): the arms are what the skeleton's weights put on
   the arm bones, split at the elbow; the rest is cut by height at the skeleton's joints (mid-neck, waist, below the
   crotch, knee, ankle); six passes of averaging over neighbours soften the edges
6. a toy's build: the whole skin rounded by Taubin smoothing, the hands three times as much
7. the muscle lines: polylines drawn in a front and a back view, hung from the skeleton's heights (under the
   pectorals, the abdomen's six blocks, the spine, trapezius, shoulder blades, lats, kneecaps, thighs, shins, calves),
   dropped straight onto the skin; on each arm the deltoid's V and the line between biceps and triceps, from the
   arm's own axis. Each becomes a thin strip lying 1.2 mm above the skin, so it is drawn as finely on the coarse
   back as on the dense chest
8. the neck and head sculpted smooth: turned into a solid (openings up to about 2 cm closed), its distance field
   blurred so ears, eyes, nose and mouth melt into the head's own shape, meshed by marching cubes, overlapping the
   body's own neck a hair inside it so there is no seam; then the head a size up, as a cartoon's is
9. vertex normals; ambient occlusion baked per vertex from 160 directions (how much of the sky each point sees);
   a few surface points per region for the page's marker; then one little-endian file:

   "HAB2", uint32 header length, the JSON header (space-padded to 4 bytes), then
   positions int16 x3 (padded to 4 bytes), normals int8 x4 (xyz, 0), extra uint8 x4 (occlusion, cloth, 0, 0),
   region shares uint8 x8, triangles uint16 x3; then, each block 4-byte aligned, the muscle lines' positions
   int16 x3 and triangles uint16 x3 (counts in the header's "lines")

Positions are metres, the soles at y = 0, facing +z, the person's left at +x. A position is center + q / 32767 * extent.
Occlusion 255 sees the whole sky. Cloth is how much a vertex may be covered by the shorts (0 on the arms and hands);
the header's "shorts" says between which heights.
"""
import argparse
import json
import math
import struct
import urllib.request
from pathlib import Path

import numpy as np

COMMIT = "a8bc2d54ff0ac92e78ff71431b1023eda42bf482"
RAW = f"https://raw.githubusercontent.com/makehumancommunity/makehuman/{COMMIT}/makehuman/data"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "healthaio" / "web" / "models" / "recovery" / "body.bin"
REGIONS = ("head", "torso", "pelvis", "left_upper_arm", "right_upper_arm", "left_calf", "right_calf", "other")
LEVELS = ("min", "average", "max")
RACES = ("african", "asian", "caucasian")


def fetch(cache: Path, rel: str) -> Path:
    path = cache / rel
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(f"{RAW}/{rel}", timeout=60) as r:
            path.write_bytes(r.read())
    return path


def read_obj(path: Path, group: str):
    verts, faces, current = [], [], None
    for line in path.open(encoding="utf-8"):
        if line.startswith("v "):
            verts.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("g "):
            current = line.split()[1]
        elif line.startswith("f ") and current == group:
            faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
    return np.array(verts), np.array(faces)


def read_target(path: Path, n: int) -> np.ndarray:
    delta = np.zeros((n, 3))
    for line in path.open(encoding="utf-8"):
        if line.strip() and not line.startswith("#"):
            i, x, y, z = line.split()
            delta[int(i)] = float(x), float(y), float(z)
    return delta


def thirds(value: float) -> dict:
    """MakeHuman's split of a 0..1 dial into its min / average / max targets (0.5 is all average)."""
    if value < 0.5:
        return {"min": 1 - value * 2, "average": value * 2, "max": 0.0}
    return {"min": 0.0, "average": 2 - value * 2, "max": value * 2 - 1}


def shape(cache: Path, base: np.ndarray, muscle: float, weight: float, height: float, proportions: float) -> np.ndarray:
    """Gender 1 (male) and age 0.5 (young, 25) leave only the male-young targets; the races stay MakeHuman's 1/3 each."""
    v, n = base.copy(), len(base)
    mus, wei = thirds(muscle), thirds(weight)
    tall = {"min": max(0.0, 1 - height * 2), "max": max(0.0, height * 2 - 1)}
    ideal = max(0.0, proportions * 2 - 1)
    uncommon = max(0.0, 1 - proportions * 2)
    for race in RACES:
        v += read_target(fetch(cache, f"targets/macrodetails/{race}-male-young.target"), n) / 3
    for m in LEVELS:
        for w in LEVELS:
            share = mus[m] * wei[w]
            if share == 0:
                continue
            combo = f"{m}muscle-{w}weight"
            if (m, w) != ("average", "average"):
                v += share * read_target(fetch(cache, f"targets/macrodetails/universal-male-young-{combo}.target"), n)
            for end in ("min", "max"):
                if tall[end]:
                    v += share * tall[end] * read_target(fetch(cache, f"targets/macrodetails/height/male-young-{combo}-{end}height.target"), n)
            for kind, k in (("ideal", ideal), ("uncommon", uncommon)):
                if k:
                    v += share * k * read_target(fetch(cache, f"targets/macrodetails/proportions/male-young-{combo}-{kind}proportions.target"), n)
    return v


def rotation(axis, angle: float) -> np.ndarray:
    x, y, z = np.asarray(axis, float) / np.linalg.norm(axis)
    c, s, t = math.cos(angle), math.sin(angle), 1 - math.cos(angle)
    return np.array([[t * x * x + c, t * x * y - s * z, t * x * z + s * y],
                     [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
                     [t * x * z - s * y, t * y * z + s * x, t * z * z + c]])


def about(R: np.ndarray, pivot) -> np.ndarray:
    """A 3x4 transform: turn by R about a pivot."""
    return np.hstack([R, (pivot - R @ pivot)[:, None]])


def then(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a, then b."""
    return np.hstack([b[:, :3] @ a[:, :3], (b[:, :3] @ a[:, 3] + b[:, 3])[:, None]])


def apply(T: np.ndarray, p):
    return np.asarray(p) @ T[:, :3].T + T[:, 3]


def edges_of(quads: np.ndarray) -> np.ndarray:
    e = np.concatenate([quads[:, [0, 1]], quads[:, [1, 2]], quads[:, [2, 3]], quads[:, [3, 0]]])
    return np.unique(np.sort(e, axis=1), axis=0)


def taubin(P: np.ndarray, edges: np.ndarray, weight: np.ndarray, steps: int, lam=0.5, mu=-0.53) -> np.ndarray:
    """Smoothing that keeps volume (Taubin 1995): a shrinking step, then an inflating one; weight 0 holds a vertex still."""
    n = len(P)
    degree = np.bincount(edges.ravel(), minlength=n)[:, None]
    w = weight[:, None]
    for _ in range(steps):
        for f in (lam, mu):
            near = np.stack([np.bincount(edges[:, 0], P[edges[:, 1], k], n) + np.bincount(edges[:, 1], P[edges[:, 0], k], n)
                             for k in range(3)], axis=1)
            P = P + f * w * (near / degree - P)
    return P


def quad_normals(P: np.ndarray, quads: np.ndarray) -> np.ndarray:
    N = np.zeros_like(P)
    for a, b, c in ((0, 1, 2), (0, 2, 3)):
        f = np.cross(P[quads[:, b]] - P[quads[:, a]], P[quads[:, c]] - P[quads[:, a]])
        for k in (a, b, c):
            np.add.at(N, quads[:, k], f)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def tri_normals(P: np.ndarray, tris: np.ndarray) -> np.ndarray:
    N = np.zeros_like(P)
    f = np.cross(P[tris[:, 1]] - P[tris[:, 0]], P[tris[:, 2]] - P[tris[:, 0]])
    for k in range(3):
        np.add.at(N, tris[:, k], f)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def tri_edges(tris: np.ndarray) -> np.ndarray:
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    return np.unique(np.sort(e, axis=1), axis=0)


def sculpted_head(P: np.ndarray, N: np.ndarray, below: float, blur_from: float, blur: float = 0.016, voxel: float = 0.0035):
    """The neck and head again, as a sculptor would smooth them. The body's surface becomes a solid (inside by the
    nearest vertices' normals; openings up to about 2 cm closed, so the mouth and eye sockets fill), its distance
    field is blurred by `blur` metres above `blur_from` so ears, eyes, nose and mouth melt into the head's own
    shape, and marching cubes mesh it from `below` up. Near `below` the field is the body's own surface, a hair
    inside it, so the two overlap without a seam."""
    from scipy.ndimage import binary_closing, binary_fill_holes, distance_transform_edt, gaussian_filter
    from scipy.spatial import cKDTree
    from skimage.measure import marching_cubes
    near = P[:, 1] > below - 0.03
    tree, pts, nrm = cKDTree(P[near]), P[near], N[near]
    lo = np.array([P[near, 0].min() - 0.03, below, P[near, 2].min() - 0.03])
    hi = np.array([P[near, 0].max() + 0.03, P[:, 1].max() + 0.02, P[near, 2].max() + 0.03])
    axes = [np.arange(l, h + voxel, voxel) for l, h in zip(lo, hi)]
    grid = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
    dist, idx = tree.query(grid, k=8)
    w = 1 / (dist ** 2 + 1e-6)
    plane = (np.einsum("nkd,nkd->nk", grid[:, None, :] - pts[idx], nrm[idx]) * w).sum(axis=1) / w.sum(axis=1)
    field = np.where(dist[:, 0] < 0.01, plane, np.sign(plane) * dist[:, 0]).reshape([len(a) for a in axes])
    ball = np.linalg.norm(np.mgrid[-6:7, -6:7, -6:7], axis=0) <= 6.2
    solid = binary_fill_holes(binary_closing(np.pad(field < 0, 7), structure=ball))[7:-7, 7:-7, 7:-7]
    solid_field = (distance_transform_edt(~solid) - distance_transform_edt(solid)) * voxel
    soft = gaussian_filter(solid_field, blur / voxel, mode="nearest")
    t = np.clip((axes[1] - blur_from) / 0.04, 0, 1)
    mix = (t * t * (3 - 2 * t))[None, :, None]
    field = field * (1 - mix) + soft * mix
    verts, faces, _, _ = marching_cubes(field, level=-0.0012, spacing=(voxel,) * 3)
    verts += lo
    # only the outer skin: pockets left inside (the mouth, the sockets) are separate pieces
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    e = tri_edges(faces)
    _, part = connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(len(verts),) * 2), directed=False)
    main_part = np.bincount(part).argmax()
    faces = faces[part[faces[:, 0]] == main_part]
    used = np.unique(faces)
    remap = -np.ones(len(verts), dtype=np.int64)
    remap[used] = np.arange(len(used))
    verts, faces = verts[used], remap[faces]
    normals = tri_normals(verts, faces)
    if (normals * (verts - verts.mean(axis=0))).sum() < 0:
        faces = faces[:, [0, 2, 1]]
        normals = -normals
    return verts, faces


def muscle_chart(P, N, tris, arm, along, m):
    """The muscle lines of a fitness chart, drawn in a front and a back view of this body and laid onto its skin
    (each view's point on the skin nearest the viewer), plus two on each arm cut by its own axis. `m` holds the
    heights they hang from: neck, shoulder, chest (MakeHuman's breast joint), waist, shorts' hem, knee, ankle.
    Returns the strokes: arrays of points on the skin, NaN where a stroke misses it."""
    from scipy.spatial import cKDTree
    torso = arm["L"] + arm["R"] < 0.5
    neck, shoulder, chest, waist, hem, knee, ankle = (m[k] for k in ("neck", "shoulder", "chest", "waist", "hem", "knee", "ankle"))

    def leg(y, side):  # the middle of one leg at a height, seen from the front
        near = torso & (np.abs(P[:, 1] - y) < 0.01) & (np.sign(P[:, 0]) == side)
        return float(np.median(P[near, 0]))

    def path(points, step=0.002):  # a polyline, one point every 2 mm
        points = np.asarray(points, float)
        out = [points[:1]]
        for a, b in zip(points[:-1], points[1:]):
            n = max(1, int(np.linalg.norm(b - a) / step))
            out.append(a + (b - a) * np.linspace(0, 1, n + 1)[1:, None])
        return np.concatenate(out)

    def onto(xy, facing):  # a 2D (x, y) line of a view dropped straight onto the nearest skin (+1 front, -1 back); NaN off it
        T = tris[torso[tris].all(axis=1)]  # the body without the arms; the first skin hit from that side wins
        _, k = cKDTree(P[T].mean(axis=1)[:, :2]).query(xy, k=32, distance_upper_bound=0.03)
        k = np.where(k < len(T), k, 0)
        A, B, C = (P[T[k][..., i]] for i in range(3))
        v0, v1, v2 = B[..., :2] - A[..., :2], C[..., :2] - A[..., :2], xy[:, None, :] - A[..., :2]
        den = v0[..., 0] * v1[..., 1] - v1[..., 0] * v0[..., 1]
        den = np.where(np.abs(den) < 1e-12, 1e-12, den)
        u = (v2[..., 0] * v1[..., 1] - v1[..., 0] * v2[..., 1]) / den
        v = (v0[..., 0] * v2[..., 1] - v2[..., 0] * v0[..., 1]) / den
        inside = (u >= -1e-4) & (v >= -1e-4) & (u + v <= 1 + 1e-4)
        z = np.where(inside, A[..., 2] + u * (B[..., 2] - A[..., 2]) + v * (C[..., 2] - A[..., 2]), -np.inf * facing)
        best = (z * facing).max(axis=1)
        return np.column_stack([xy, np.where(np.isfinite(best), best * facing, np.nan)])

    ring = lambda cx, cy, rx, ry, a0=0, a1=2 * np.pi: path([(cx + rx * np.cos(t), cy + ry * np.sin(t)) for t in np.linspace(a0, a1, 48)])
    abs_top = chest - 0.04
    front = [path([(0, neck - 0.045), (0, abs_top)]), path([(0, abs_top), (0, waist + 0.005)])]
    front += [path([(-0.058, y), (0.058, y)]) for y in abs_top - (abs_top - waist) * np.array([0.27, 0.52, 0.77])]  # six blocks
    back = [path([(0, neck - 0.01), (0, waist + 0.005)])]
    for s in (1, -1):
        front += [path([(s * x, chest - 0.035 + 0.07 * (x / 0.125) ** 1.7) for x in np.linspace(0, 0.125, 30)]),  # under the pectoral
                  path([(s * 0.064, abs_top - 0.005), (s * 0.056, waist + 0.005)])]                               # the abdomen's sides
        back += [path([(s * 0.12, shoulder - 0.005), (0, shoulder - 0.25)]),                                     # the trapezius
                 ring(s * 0.1, shoulder - 0.135, 0.036, 0.048),                                                  # a shoulder blade
                 path([(s * (0.15 - 0.08 * t), shoulder - 0.13 - (shoulder - 0.13 - waist - 0.03) * t + 0.03 * np.sin(np.pi * t))
                       for t in np.linspace(0, 1, 30)])]                                                         # the lat's edge
        c, top_q, low_q = leg(knee + 0.015, s), leg(hem - 0.02, s), leg(knee + 0.06, s)
        front += [ring(c, knee + 0.015, 0.03, 0.032),                                                            # the kneecap
                  path([(top_q + 0.03, hem - 0.02), (low_q + 0.012, knee + 0.06)]),                              # the front of the thigh
                  path([(top_q - 0.03, hem - 0.02), (low_q - 0.012, knee + 0.06)]),
                  path([(leg(knee - 0.05, s) + s * 0.012, knee - 0.05), (leg(ankle + 0.08, s) + s * 0.008, ankle + 0.08)])]  # the shin
        back += [path([(leg(hem - 0.02, s), hem - 0.02), (leg(knee + 0.07, s), knee + 0.07)]),                   # the hamstrings
                 path([(leg(knee - 0.02, s), knee - 0.02), (leg(knee - 0.15, s), knee - 0.15)]),                 # the calf's two heads
                 ring(leg(knee - 0.15, s), knee - 0.15, 0.036, 0.055, np.pi, 2 * np.pi)]                         # and where they end
    strokes = [onto(line, 1) for line in front] + [onto(line, -1) for line in back]
    for side, s in (("L", 1), ("R", -1)):
        on = arm[side] > 0.5
        a0, a1 = m["arm"][side]
        axis = (a1 - a0) / np.linalg.norm(a1 - a0)
        out = np.cross(axis, [0, 0, 1])
        out *= s * np.sign(out[0]) or 1          # pointing away from the body
        fwd = np.cross(out, axis)
        fwd *= np.sign(fwd[2]) or 1               # pointing forward

        def surface(t, th):  # the point of the arm's skin a fraction t of the way to the elbow, at an angle round it
            c = a0 + (a1 - a0) * t
            rel = P[on & (np.abs(along[side] - t) < 0.03)] - c
            rel -= np.outer(rel @ axis, axis)
            gap = np.abs((np.arctan2(rel @ fwd, rel @ out) - th + np.pi) % (2 * np.pi) - np.pi)
            if (gap < 0.3).sum() < 3:
                return None
            return c + np.median(np.linalg.norm(rel, axis=1)[gap < 0.3]) * (np.cos(th) * out + np.sin(th) * fwd)
        delt = [surface(0.44 - 0.14 * abs(th) / 1.6, th) for th in np.linspace(-1.6, 1.6, 50)]                # the deltoid's V
        split = [surface(t, 0.0) for t in np.linspace(0.5, 0.95, 24)]                                          # biceps | triceps
        nan = np.full(3, np.nan)
        strokes += [np.array([nan if q is None else q for q in delt]), np.array([nan if q is None else q for q in split])]
    return strokes


def ribbons(strokes, P, N, keep, width=0.0055):
    """Each stroke as a thin strip lying on the skin (1.2 mm proud of it), tapered at the ends like a pen line: the
    page draws these over the body, so a line is as fine and even on the coarse back as on the dense chest. A stroke
    breaks where it leaves the skin, jumps, or crosses where `keep` (per vertex) is false."""
    from scipy.spatial import cKDTree
    tree = cKDTree(P)
    verts, tris = [], []
    for stroke in strokes:
        ok = np.isfinite(stroke).all(axis=1)
        _, near = tree.query(np.where(ok[:, None], stroke, 0))
        ok &= keep[near]
        pieces, cur = [], []
        for i in range(len(stroke)):
            if ok[i] and (not cur or np.linalg.norm(stroke[i] - stroke[cur[-1]]) < 0.012):
                cur.append(i)
            else:
                pieces.append(cur)
                cur = [i] if ok[i] else []
        pieces.append(cur)
        for idx in pieces:
            if len(idx) < 4:
                continue
            q = stroke[idx]
            # resample every 3 mm along the stroke
            seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))]
            at = np.arange(0, seg[-1], 0.003)
            q = np.stack([np.interp(at, seg, q[:, k]) for k in range(3)], axis=1)
            n = N[tree.query(q)[1]]
            t = np.gradient(q, axis=0)
            side = np.cross(t, n)
            side /= np.maximum(np.linalg.norm(side, axis=1, keepdims=True), 1e-9)
            m = len(q)
            taper = np.minimum(1, np.minimum(np.arange(m), np.arange(m)[::-1]) / 4 + 0.25)
            base = sum(len(v) for v in verts)
            lift = q + n * 0.0012
            verts.append(np.concatenate([lift + side * (width / 2 * taper)[:, None], lift - side * (width / 2 * taper)[:, None]]))
            i = np.arange(m - 1)
            tris.append(np.concatenate([np.stack([i, i + 1, m + i], axis=1), np.stack([i + 1, m + i + 1, m + i], axis=1)]) + base)
    return np.concatenate(verts), np.concatenate(tris)


def catmull_clark(P: np.ndarray, quads: np.ndarray, attrs: np.ndarray):
    """One Catmull-Clark step on a closed quad mesh; per-vertex attributes are carried along linearly."""
    nv, nf = len(P), len(quads)
    pairs = np.sort(np.stack([quads, np.roll(quads, -1, axis=1)], axis=2), axis=2)       # (nf, 4, 2) face edges
    edges, inverse = np.unique(pairs.reshape(-1, 2), axis=0, return_inverse=True)
    inverse = inverse.reshape(nf, 4)
    ne = len(edges)
    face_p, face_a = P[quads].mean(axis=1), attrs[quads].mean(axis=1)
    # each edge has exactly two faces on a closed mesh
    assert (np.bincount(inverse.ravel(), minlength=ne) == 2).all(), "the body mesh should be closed"
    edge_faces = np.repeat(np.arange(nf), 4)[np.argsort(inverse.ravel(), kind="stable")].reshape(ne, 2)
    mid = P[edges].mean(axis=1)
    edge_p = (P[edges[:, 0]] + P[edges[:, 1]] + face_p[edge_faces[:, 0]] + face_p[edge_faces[:, 1]]) / 4
    edge_a = attrs[edges].mean(axis=1)
    valence = np.bincount(edges.ravel(), minlength=nv).astype(float)[:, None]
    Q = np.zeros_like(P)
    np.add.at(Q, quads.ravel(), np.repeat(face_p, 4, axis=0))
    Q /= valence  # on a closed quad mesh a vertex has as many faces as edges
    Rm = np.zeros_like(P)
    np.add.at(Rm, edges[:, 0], mid)
    np.add.at(Rm, edges[:, 1], mid)
    Rm /= valence
    vert_p = (Q + 2 * Rm + (valence - 3) * P) / valence
    newP = np.concatenate([vert_p, edge_p, face_p])
    newA = np.concatenate([attrs, edge_a, face_a])
    E, F = nv + inverse, nv + ne + np.arange(nf)
    new_quads = np.concatenate([np.stack([quads[:, i], E[:, i], F, E[:, (i - 1) % 4]], axis=1) for i in range(4)])
    return newP, new_quads, newA


def occlusion(P: np.ndarray, N: np.ndarray, directions: int = 160, pixel: float = 0.006) -> np.ndarray:
    """How much of the sky each vertex sees: for each direction a depth buffer of the vertices, splatted 3x3 pixels wide."""
    k = np.arange(directions) + 0.5
    phi, z = k * math.pi * (3 - math.sqrt(5)), 1 - 2 * k / directions
    D = np.stack([np.sqrt(1 - z * z) * np.cos(phi), np.sqrt(1 - z * z) * np.sin(phi), z], axis=1)
    seen, total = np.zeros(len(P)), np.zeros(len(P))
    for d in D:
        u = np.cross(d, [0, 1, 0] if abs(d[1]) < 0.9 else [1, 0, 0])
        u /= np.linalg.norm(u)
        v = np.cross(d, u)
        a, b, depth = P @ u, P @ v, P @ d
        ia, ib = ((a - a.min()) / pixel).astype(int) + 1, ((b - b.min()) / pixel).astype(int) + 1
        W = ib.max() + 2
        buf = np.full((ia.max() + 2) * W, -np.inf)
        for da in (-1, 0, 1):
            for db in (-1, 0, 1):
                np.maximum.at(buf, (ia + da) * W + ib + db, depth)
        lit = np.maximum(N @ d, 0)
        # a neighbour up to 1.5 pixels away on the same slope sits this much nearer: not an occluder
        slope = np.sqrt(1 - np.minimum(lit, 1) ** 2) / np.maximum(lit, 0.15)
        seen += lit * (depth >= buf[ia * W + ib] - 0.004 - 1.6 * pixel * slope)
        total += lit
    return seen / np.maximum(total, 1e-9)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cache", type=Path, default=Path.home() / ".cache" / "healthaio" / "makehuman" / COMMIT[:12])
    ap.add_argument("--muscle", type=float, default=0.85, help="0..1, MakeHuman's muscle dial (0.5 average)")
    ap.add_argument("--weight", type=float, default=0.25, help="0..1, MakeHuman's weight dial (0.5 average; lower is leaner)")
    ap.add_argument("--round", type=int, default=25, help="steps of smoothing that round the body like a toy")
    ap.add_argument("--head", type=float, default=1.15, help="how much bigger the head is than MakeHuman's (a cartoon's proportions)")
    ap.add_argument("--height", type=float, default=0.55, help="0..1, MakeHuman's height dial (0.5 average)")
    ap.add_argument("--proportions", type=float, default=0.75, help="0..1, MakeHuman's body proportions (1 ideal)")
    ap.add_argument("--arms", type=float, default=16, help="degrees of each upper arm from vertical, seen from the front")
    ap.add_argument("--elbows", type=float, default=8, help="degrees of bend left in each elbow")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    # 1, 2
    base, quads = read_obj(fetch(a.cache, "3dobjs/base.obj"), "body")
    skel = json.loads(fetch(a.cache, "rigs/default.mhskel").read_text(encoding="utf-8"))
    bone_weights = json.loads(fetch(a.cache, "rigs/default_weights.mhw").read_text(encoding="utf-8"))["weights"]
    v = shape(a.cache, base, a.muscle, a.weight, a.height, a.proportions) / 10  # decimetres to metres
    bones, n = skel["bones"], len(v)
    joint = {name: v[idx].mean(axis=0) for name, idx in skel["joints"].items()}
    at = {b: joint[bones[b]["head"]] for b in bones}  # where each bone starts
    W = {b: np.zeros(n) for b in bones}
    for b, pairs in bone_weights.items():
        for i, w in pairs:
            W[b][i] = w
    total = sum(W.values())
    total[total == 0] = 1

    def chain(root):
        out, todo = set(), [root]
        while todo:
            b = todo.pop()
            out.add(b)
            todo += [c for c in bones if bones[c]["parent"] == b]
        return out

    # 3. per bone, a transform; each vertex moves by its weights' blend of them
    T = {b: np.hstack([np.eye(3), np.zeros((3, 1))]) for b in bones}
    for side in ("L", "R"):
        shoulder, elbow, wrist = at[f"upperarm01.{side}"], at[f"lowerarm01.{side}"], at[f"wrist.{side}"]
        upper, fore = elbow - shoulder, wrist - elbow
        bend = math.acos(np.clip(upper @ fore / np.linalg.norm(upper) / np.linalg.norm(fore), -1, 1))
        straighten = about(rotation(np.cross(upper, fore), -(bend - math.radians(a.elbows))), elbow)
        now = math.degrees(math.atan2(abs(upper[0]), -upper[1]))
        lower = about(rotation([0, 0, 1], math.copysign(math.radians(now - a.arms), -upper[0])), shoulder)
        T[f"shoulder01.{side}"] = about(rotation([0, 0, 1], math.copysign(0.4 * math.radians(now - a.arms), -upper[0])), shoulder)
        for b in chain(f"upperarm01.{side}"):
            T[b] = lower
        for b in chain(f"lowerarm01.{side}"):
            T[b] = then(straighten, lower)
        print(f"{side} arm: {now:.0f}° from vertical -> {a.arms:.0f}°, elbow bent {math.degrees(bend):.0f}° -> {a.elbows:.0f}°")
    posed = sum((W[b] / total)[:, None] * apply(T[b], v) for b in bones)
    posed += (1 - sum(W[b] / total for b in bones))[:, None] * v  # vertices without weights stay put
    elbow_now = {s: apply(T[f"upperarm01.{s}"], at[f"lowerarm01.{s}"]) for s in "LR"}
    shoulder_now = {s: at[f"upperarm01.{s}"] for s in "LR"}

    # keep the body's vertices, standing on y = 0, turning about the middle of the hips
    used = np.unique(quads)
    remap = -np.ones(n, dtype=np.int64)
    remap[used] = np.arange(len(used))
    quads = remap[quads]
    P = posed[used]
    hips = (at["upperleg01.L"] + at["upperleg01.R"]) / 2
    shift = np.array([-(P[:, 0].max() + P[:, 0].min()) / 2, -P[:, 1].min(), -hips[2]])
    P += shift
    y_of = lambda b: at[b][1] + shift[1]
    hip_y = (y_of("upperleg01.L") + y_of("upperleg01.R")) / 2
    knee_y = (y_of("lowerleg01.L") + y_of("lowerleg01.R")) / 2
    ankle_y = (y_of("foot.L") + y_of("foot.R")) / 2
    neck_y, waist_y = y_of("neck02"), hip_y + 0.09
    hem_y = hip_y - 0.45 * (hip_y - knee_y)
    middle = np.abs(P[:, 0]) < 0.004
    crotch_y = P[middle & (P[:, 1] > knee_y) & (P[:, 1] < waist_y), 1].min()

    # what the arm bones carry, for the regions (decided after subdividing) and the shorts
    y = P[:, 1]
    arm = {side: sum((W[b] / total) for b in chain(f"shoulder01.{side}"))[used] for side in "LR"}
    cloth = np.clip(1 - arm["L"] - arm["R"], 0, 1) * (y < neck_y - 0.05)

    # 4. the shorts' fabric
    edges = edges_of(quads)
    smooth = lambda lo, hi, x: np.clip((x - lo) / (hi - lo), 0, 1) ** 2 * (3 - 2 * np.clip((x - lo) / (hi - lo), 0, 1))
    shorts = cloth * smooth(hem_y - 0.01, hem_y + 0.01, y) * (1 - smooth(waist_y - 0.01, waist_y + 0.01, y))
    P = taubin(P, edges, shorts, 40)
    P = P + quad_normals(P, quads) * (0.005 * shorts)[:, None]

    # 5. subdivide, then the regions on the finer mesh, so their edges run smooth
    attrs = np.stack([arm["L"], arm["R"], cloth], axis=1)
    P, quads, attrs = catmull_clark(P, quads, attrs)
    arm, cloth = {"L": attrs[:, 0], "R": attrs[:, 1]}, attrs[:, 2]
    y = P[:, 1]
    label = np.full(len(P), REGIONS.index("other"))
    label[y >= neck_y] = REGIONS.index("head")
    label[(y < neck_y) & (y >= waist_y)] = REGIONS.index("torso")
    label[(y < waist_y) & (y >= crotch_y - 0.02)] = REGIONS.index("pelvis")
    calf = (y < knee_y) & (y >= ankle_y)
    label[calf & (P[:, 0] > 0)] = REGIONS.index("left_calf")
    label[calf & (P[:, 0] <= 0)] = REGIONS.index("right_calf")
    for side, name in (("L", "left_upper_arm"), ("R", "right_upper_arm")):
        axis = elbow_now[side] - shoulder_now[side]
        along = (P - (shoulder_now[side] + shift)) @ axis / (axis @ axis)
        label[arm[side] > 0.5] = REGIONS.index("other")
        label[(arm[side] > 0.5) & (along < 1)] = REGIONS.index(name)
    assert P[label == REGIONS.index("left_upper_arm"), 0].mean() > 0, "MakeHuman's .L bones should be the person's left, at +x"
    R = np.eye(len(REGIONS))[label]
    edges = edges_of(quads)
    degree = np.bincount(edges.ravel(), minlength=len(P))[:, None]
    for _ in range(6):
        near = np.zeros_like(R)
        np.add.at(near, edges[:, 0], R[edges[:, 1]])
        np.add.at(near, edges[:, 1], R[edges[:, 0]])
        R = (R + near / degree) / 2
    tris = np.concatenate([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])
    N = quad_normals(P, quads)
    chest = (R[:, REGIONS.index("torso")] > 0.9) & (np.abs(P[:, 0]) < 0.03) & (P[:, 2] > 0)
    outward = 1 if N[chest, 2].mean() >= 0 else -1
    if outward < 0:  # faces wound the other way: flip both
        tris = tris[:, [0, 2, 1]]
        N = -N

    y = P[:, 1]
    shorts = cloth * smooth(hem_y - 0.02, hem_y + 0.02, y) * (1 - smooth(waist_y - 0.02, waist_y + 0.02, y))
    hands = np.clip((arm["L"] + arm["R"] - 0.5) * 2, 0, 1) * (1 - smooth(hip_y - 0.05, hip_y + 0.05, y))

    # 6. a toy's build: every surface rounded, the hands like mittens
    P = taubin(P, edges, np.ones(len(P)), a.round)
    P = taubin(P, edges, hands, 3 * a.round)
    N = quad_normals(P, quads) * outward

    # 7. the muscles: lines like a fitness chart's (under the pectorals, the abdomen's six blocks, the spine, the
    # trapezius, shoulder blades, lats, deltoids, biceps and triceps, kneecaps, thighs, shins, calves)
    along = {s: (P - (shoulder_now[s] + shift)) @ (elbow_now[s] - shoulder_now[s]) / np.sum((elbow_now[s] - shoulder_now[s]) ** 2) for s in "LR"}
    strokes = muscle_chart(P, N, tris, arm, along, {"neck": y_of("neck01"), "shoulder": y_of("upperarm01.L"), "chest": y_of("breast.L"),
                                            "waist": waist_y, "hem": hem_y, "knee": knee_y, "ankle": ankle_y,
                                            "arm": {s: (shoulder_now[s] + shift, elbow_now[s] + shift) for s in "LR"}})
    line_P, line_tris = ribbons(strokes, P, N, (shorts < 0.5) & (hands < 0.5) & (y < neck_y - 0.01))
    print(f"muscle lines: {len(strokes)} strokes, {len(line_P)} ribbon vertices")

    # 8. the neck and head, sculpted smooth (no face, no ears); the body keeps its own surface up to a band at the
    # neck, where the two overlap
    band = neck_y - 0.028
    head_P, head_tris = sculpted_head(P, N, band, neck_y)
    head_P = taubin(head_P, tri_edges(head_tris), np.clip((head_P[:, 1] - band - 0.01) / 0.02, 0, 1), 12)
    # a cartoon's head, a size up from the neck
    grow = 1 + (a.head - 1) * smooth(neck_y, neck_y + 0.06, head_P[:, 1])
    pivot = np.array([0, neck_y, head_P[head_P[:, 1] > neck_y + 0.05, 2].mean()])
    head_P = pivot + (head_P - pivot) * grow[:, None]
    tris = tris[(P[tris, 1] <= band + 0.008).any(axis=1)]
    kept = np.unique(tris)
    remap = -np.ones(len(P), dtype=np.int64)
    remap[kept] = np.arange(len(kept))
    P, R, cloth, tris = P[kept], R[kept], cloth[kept], remap[tris]
    head_share = np.clip((head_P[:, 1] - neck_y) / 0.01 + 0.5, 0, 1)
    shares = np.zeros((len(head_P), len(REGIONS)))
    shares[:, REGIONS.index("head")], shares[:, REGIONS.index("torso")] = head_share, 1 - head_share
    P = np.concatenate([P, head_P])
    R = np.concatenate([R, shares])
    cloth = np.concatenate([cloth, np.zeros(len(head_P))])
    tris = np.concatenate([tris, head_tris + len(kept)])
    N = tri_normals(P, tris)
    print(f"neck and head: {len(head_P)} vertices from marching cubes, from {band:.3f} m up")

    # 9. occlusion, marker points
    edges = tri_edges(tris)
    degree = np.bincount(edges.ravel(), minlength=len(P))
    ao = occlusion(P, N)
    for _ in range(2):
        near = np.bincount(edges[:, 0], ao[edges[:, 1]], len(P)) + np.bincount(edges[:, 1], ao[edges[:, 0]], len(P))
        ao = (ao + near / np.maximum(degree, 1)) / 2

    anchors = {}
    for i, name in enumerate(REGIONS[:-1]):
        core = np.where(R[:, i] > 0.8)[0]
        mid = np.median(P[core, 1])
        points = []
        for k in range(8):
            d = np.array([math.sin(k * math.pi / 4), 0, math.cos(k * math.pi / 4)])
            j = core[np.argmax(N[core] @ d - 3 * np.abs(P[core, 1] - mid))]
            points.append([round(float(x), 4) for x in (*P[j], *N[j])])
        anchors[name] = points

    lo, hi = np.minimum(P.min(axis=0), line_P.min(axis=0)), np.maximum(P.max(axis=0), line_P.max(axis=0))
    center, extent = (lo + hi) / 2, (hi - lo) / 2
    q = np.round((P - center) / extent * 32767).astype("<i2")
    header = {
        "format": 2, "vertices": int(len(P)), "triangles": int(len(tris)),
        "center": [round(float(x), 6) for x in center], "extent": [round(float(x), 6) for x in extent],
        "regions": list(REGIONS), "anchors": anchors,
        "lines": {"vertices": int(len(line_P)), "triangles": int(len(line_tris))},
        "shorts": {"waist": round(float(waist_y), 4), "hem": round(float(hem_y), 4)},
        "made": {"gender": 1.0, "age": 0.5, "muscle": a.muscle, "weight": a.weight, "height": a.height,
                 "proportions": a.proportions, "arms": a.arms, "elbows": a.elbows, "round": a.round, "head": a.head},
        "source": f"MakeHuman 1.x base mesh, macro targets, default skeleton and weights (CC0), commit {COMMIT}",
    }
    text = json.dumps(header, separators=(",", ":")).encode()
    text += b" " * (-len(text) % 4)
    blob = bytearray(b"HAB2" + struct.pack("<I", len(text)) + text)
    blob += q.tobytes() + b"\0" * (-q.nbytes % 4)
    blob += np.concatenate([np.round(N * 127), np.zeros((len(P), 1))], axis=1).astype("i1").tobytes()
    extra = np.zeros((len(P), 4))
    extra[:, 0], extra[:, 1] = ao, cloth
    blob += np.round(extra * 255).astype("u1").tobytes()
    blob += np.round(R * 255).astype("u1").tobytes()
    assert len(P) < 65536, "triangles are uint16"
    blob += tris.astype("<u2").tobytes()
    # the muscle lines: positions as the body's, padded to 4 bytes, then their triangles
    lq = np.round((line_P - center) / extent * 32767).clip(-32767, 32767).astype("<i2")
    blob += b"\0" * (-len(blob) % 4) + lq.tobytes() + b"\0" * (-lq.nbytes % 4) + line_tris.astype("<u2").tobytes()
    a.out.write_bytes(bytes(blob))
    print(f"{len(P)} vertices, {len(tris)} triangles, {hi[1] - lo[1]:.2f} m tall, {hi[0] - lo[0]:.2f} m wide, "
          f"{len(blob) / 1024:.0f} KB -> {a.out}")


if __name__ == "__main__":
    main()
