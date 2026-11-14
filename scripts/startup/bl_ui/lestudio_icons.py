# SPDX-FileCopyrightText: 2026 LeStudio contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Gold vector tool symbols; geometry is display-only, never scene data."""

import math
import bpy

_cache = {}


def tool_icon(tool_id, compact=False):
    kind = {
        "builtin.select": "select", "builtin.select_box": "box",
        "builtin.select_circle": "circle", "builtin.select_lasso": "circle",
        "builtin.cursor": "circle", "builtin.move": "move",
        "builtin.rotate": "rotate", "builtin.scale": "scale",
        "builtin.transform": "transform", "builtin.annotate": "pencil",
        "builtin.annotate_line": "pencil", "builtin.annotate_polygon": "triangle",
        "builtin.annotate_eraser": "pencil", "builtin.measure": "pencil",
        "builtin.primitive_cube_add": "cube", "builtin.primitive_uv_sphere_add": "sphere",
        "builtin.extrude_region": "cube", "builtin.inset": "box",
        "builtin.bevel": "pencil", "builtin.loopcut_slide": "cube",
        "builtin.knife": "pencil", "builtin.poly_build": "triangle",
    }.get(tool_id)
    if kind is None:
        return None
    key = (kind, compact)
    if key in _cache:
        return _cache[key]
    triangles = []

    def polygon(points):
        for i in range(1, len(points) - 1):
            triangles.extend((points[0], points[i], points[i + 1]))

    def line(a, b, width=12):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length == 0:
            return
        nx, ny = -dy / length * width / 2, dx / length * width / 2
        polygon(((a[0]+nx,a[1]+ny),(a[0]-nx,a[1]-ny),(b[0]-nx,b[1]-ny),(b[0]+nx,b[1]+ny)))

    def path(points, width=12, closed=False):
        for a, b in zip(points, points[1:] + ([points[0]] if closed else [])):
            line(a, b, width)

    def circle(cx, cy, radius, dashed=False, start=0, end=2*math.pi):
        count = 48
        points = [(cx+radius*math.cos(start+(end-start)*i/count),cy+radius*math.sin(start+(end-start)*i/count)) for i in range(count+1)]
        for i in range(count):
            if not dashed or i % 6 < 4:
                line(points[i], points[i+1], 10)

    if kind == "select":
        polygon([(50,220),(205,105),(142,98),(166,42),(136,28),(110,85),(63,42)])
    elif kind in {"box", "scale"}:
        path([(48,48),(208,48),(208,208),(48,208)], 10, True)
        if kind == "scale":
            for x,y in [(48,48),(208,48),(208,208),(48,208)]:
                polygon([(x-16,y-16),(x+16,y-16),(x+16,y+16),(x-16,y+16)])
    elif kind in {"circle", "sphere"}:
        circle(128,128,88,kind=="circle")
        if kind == "sphere":
            path([(45,128),(211,128)],8)
            path([(128,40),(89,80),(81,128),(89,176),(128,216),(167,176),(175,128),(167,80),(128,40)],8)
    elif kind in {"move", "transform"}:
        line((128,32),(128,224),11); line((32,128),(224,128),11)
        for points in [[(128,235),(104,202),(152,202)],[(128,21),(104,54),(152,54)],[(21,128),(54,104),(54,152)],[(235,128),(202,104),(202,152)]]:
            polygon(points)
        if kind == "transform":
            circle(128,128,65)
    elif kind == "rotate":
        circle(128,128,80,start=0.35,end=5.6)
        polygon([(214,162),(164,177),(200,213)])
    elif kind == "pencil":
        polygon([(54,54),(67,99),(175,207),(202,180),(94,72)])
        line((179,213),(210,182),11)
    elif kind == "cube":
        path([(128,225),(218,179),(218,75),(128,28),(38,75),(38,179)],10,True)
        path([(38,179),(128,130),(218,179)],10)
        line((128,130),(128,28),10); line((128,225),(128,130),8)
    elif kind == "triangle":
        points=[(128,220),(37,45),(219,45)]
        path(points,10,True)
        for x,y in points:
            circle(x,y,12)
    coords=bytes(max(0,min(255,round(128+(v-128)*(0.5 if compact else 1.0)))) for point in triangles for v in point)
    colors=bytes((212,175,55,255))*len(triangles)
    _cache[key]=bpy.app.icons.new_triangles((0,255),coords,colors)
    return _cache[key]


def release():
    for value in _cache.values():
        bpy.app.icons.release(value)
    _cache.clear()
