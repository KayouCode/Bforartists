# SPDX-FileCopyrightText: 2026 LeStudio contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Native GUI integration evidence, never automatic visual acceptance.

Run the isolated package with --factory-startup --python this_file -- output_dir.
The test uses a disposable project in output_dir; no existing project is opened.
"""
import json
import os
from pathlib import Path
import sys
import traceback
import bpy

if bpy.app.background or not os.environ.get("BLENDER_USER_CONFIG"):
    raise RuntimeError("A graphical session with an isolated profile is required")
args = sys.argv[sys.argv.index("--") + 1:]
if len(args) != 1:
    raise RuntimeError("Pass a dedicated evidence directory")
output = Path(args[0]).resolve()
output.mkdir(parents=True, exist_ok=True)
project = output / "native-ui-test.blend"
if project.exists():
    raise RuntimeError("Use a fresh output directory; existing projects are preserved")
report = {"build": bpy.app.build_hash.decode(), "status": "STARTING",
          "visual_conformity": "NOT_EVALUATED", "checks": []}
window = bpy.context.window_manager.windows[0]
order = ["Cube", "Sphère", "Cylindre", "Cône", "Tore", "Plan",
         "Cercle", "Icosphère", "UV Sphère", "Suzanne"]

def publish():
    (output / "native-ui.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

def check(name, details=None):
    report["checks"].append({"name": name, "result": "PASS", "details": details})
    publish()

def snapshot():
    cube = bpy.data.objects["Cube"]
    return {"mesh": [list(v.co) for v in cube.data.vertices],
            "location": list(cube.location), "scale": list(cube.scale),
            "rotation": list(cube.rotation_euler),
            "materials": [material.name if material else None for material in cube.data.materials],
            "workspaces": sorted(workspace.name for workspace in bpy.data.workspaces)}

def inspect_startup():
    assert not bpy.data.filepath, "Factory startup must not open a user project"
    assert window.workspace.name == "Modélisation"
    assert set(snapshot()["workspaces"]) == {
        "Accueil", "Modélisation", "Sculpture", "Matériaux", "Rendu", "Animation", "Scripting"}
    browser = next(area for area in window.screen.areas if area.ui_type == "ASSETS")
    region = next(region for region in browser.regions if region.type == "WINDOW")
    params = browser.spaces.active.params
    assert params.asset_library_reference == "LeStudio Primitives"
    from bl_ui.space_lestudio import _set_library_order
    params.sort_method = "FILE_SORT_ALPHA"
    _set_library_order(params, "PRIMITIVES")
    assert params.sort_method == "ASSET_CATALOG", params.sort_method
    with bpy.context.temp_override(window=window, area=browser, region=region):
        bpy.ops.file.select_all(action="SELECT")
        actual = [asset.name for asset in bpy.context.selected_assets]
        assert actual == order, actual
        bpy.ops.file.select_all(action="DESELECT")
    check("actual_native_asset_order", actual)
    properties = next(area for area in window.screen.areas if area.type == "PROPERTIES")
    assert any(region.type == "TOOL_HEADER" and region.height > 0 for region in properties.regions)
    check("properties_alignment_region")
    from bl_ui.space_lestudio import _quality_target
    scene = window.scene
    original_engine = scene.render.engine
    for engine in ("BLENDER_EEVEE", "CYCLES", "BLENDER_WORKBENCH"):
        scene.render.engine = engine
        target, field, values = _quality_target(scene)
        original = getattr(target, field)
        for preset, expected in zip(("LOW", "MEDIUM", "HIGH"), values):
            bpy.ops.lestudio.render_quality(preset=preset)
            assert getattr(target, field) == expected
        setattr(target, field, original)
        check("native_sampling_" + engine, field)
    scene.render.engine = original_engine
    report["before"] = snapshot()
    view = next(area for area in window.screen.areas if area.type == "VIEW_3D")
    region = next(region for region in view.regions if region.type == "WINDOW")
    with bpy.context.temp_override(window=window, area=view, region=region):
        bpy.ops.ed.undo_push(message="Before native UI test")
        bpy.ops.transform.translate("EXEC_DEFAULT", True, value=(1.25, 0, 0))
    assert abs(bpy.data.objects["Cube"].location.x - 1.25) < 1e-6
    check("native_transform")

def undo():
    with bpy.context.temp_override(window=window):
        bpy.ops.ed.undo()
    assert snapshot() == report["before"]
    check("native_undo")

def redo():
    with bpy.context.temp_override(window=window):
        bpy.ops.ed.redo()
    assert abs(bpy.data.objects["Cube"].location.x - 1.25) < 1e-6
    check("native_redo")
    report["saved"] = snapshot()
    bpy.ops.wm.save_as_mainfile(filepath=str(project))
    assert project.is_file() and project.stat().st_size > 0
    check("save", project.stat().st_size)

def reload():
    bpy.ops.wm.open_mainfile(filepath=str(project), load_ui=True)
    bpy.app.timers.register(after_reload, first_interval=3.0)

def after_reload():
    try:
        assert snapshot() == report["saved"]
        browser = next(area for area in bpy.context.window.screen.areas if area.ui_type == "ASSETS")
        assert browser.spaces.active.params.sort_method == "ASSET_CATALOG"
        check("reload_exact_native_state")
        bpy.ops.screen.screenshot(filepath=str(output / "native-ui.png"))
        report["status"] = "NATIVE_UI_INTEGRATION_PASS"
        publish()
        print("LESTUDIO_NATIVE_UI_PASS", json.dumps(report, ensure_ascii=False), flush=True)
    except Exception:
        report["status"] = "FAIL"
        report["error"] = traceback.format_exc()
        publish()
        traceback.print_exc()
    bpy.app.timers.register(quit_test, first_interval=1.0)
    return None

def quit_test():
    bpy.ops.wm.quit_blender()
    return None

steps = iter((inspect_startup, undo, redo, reload))
def advance():
    try:
        action = next(steps)
        action()
        return None if action is reload else 1.0
    except Exception:
        report["status"] = "FAIL"
        report["error"] = traceback.format_exc()
        publish()
        traceback.print_exc()
        bpy.app.timers.register(quit_test, first_interval=1.0)
        return None

publish()
bpy.app.timers.register(advance, first_interval=8.0)
