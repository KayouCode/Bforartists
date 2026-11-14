# SPDX-FileCopyrightText: 2026 LeStudio contributors
#
# SPDX-License-Identifier: GPL-2.0-or-later
"""GUI startup regression; invoke with the isolated launcher and --factory-startup.

A background run cannot exercise file-browser notifier initialization.
This test must survive native startup and draw the actual modeling workspace.
It records technical evidence only, never visual conformity.
"""
import json
import os
from pathlib import Path
import sys
import bpy

if bpy.app.background:
    raise RuntimeError("This regression requires a graphical application session")
if not os.environ.get("BLENDER_USER_CONFIG"):
    raise RuntimeError("Use an isolated BLENDER_USER_CONFIG for this test")
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(args) != 1:
    raise RuntimeError("Pass a dedicated evidence directory after --")
output = Path(args[0]).resolve()
output.mkdir(parents=True, exist_ok=True)
result = {"status": "STARTING", "build": bpy.app.build_hash.decode(),
          "background": bpy.app.background, "visual_conformity": "NOT_EVALUATED"}
(output / "startup.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

def verify():
    window = bpy.context.window_manager.windows[0]
    required = {"Accueil", "Modélisation", "Sculpture", "Matériaux", "Rendu", "Animation", "Scripting"}
    names = {workspace.name for workspace in bpy.data.workspaces}
    assert required <= names, names
    assert window.workspace.name == "Modélisation", window.workspace.name
    assert {"VIEW_3D", "FILE_BROWSER", "PROPERTIES"} <= {area.type for area in window.screen.areas}
    browser = next(area for area in window.screen.areas if area.ui_type == "ASSETS")
    assert browser.spaces.active.params is not None
    assert window.scene.camera is not None
    assert bpy.data.objects.get("Cube") is not None
    with bpy.context.temp_override(window=window, area=browser):
        bpy.ops.screen.screenshot(filepath=str(output / "startup-native.png"))
    result.update(status="GUI_STARTUP_PASS", workspaces=sorted(names),
                  objects=sorted(obj.name for obj in window.scene.objects))
    (output / "startup.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("LESTUDIO_GUI_STARTUP_PASS", json.dumps(result, ensure_ascii=False), flush=True)
    bpy.app.timers.register(quit_test, first_interval=1.0)
    return None

def quit_test():
    bpy.ops.wm.quit_blender()
    return None

bpy.app.timers.register(verify, first_interval=6.0)
