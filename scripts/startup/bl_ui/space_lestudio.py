# SPDX-FileCopyrightText: 2026 LeStudio contributors
#
# SPDX-License-Identifier: GPL-2.0-or-later
"""LeStudio modeling workspace panels backed by native Bforartists data."""

import bpy
from pathlib import Path
from bpy.props import BoolProperty
from bpy.types import Panel


class _LeStudioPropertiesPanel:
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return context.window is not None and context.window.workspace.name == "Modélisation"


class LESTUDIO_PT_properties(_LeStudioPropertiesPanel, Panel):
    bl_label = "Propriétés"
    bl_idname = "LESTUDIO_PT_properties"
    bl_order = -100

    def draw(self, context):
        obj = context.object
        advanced = self.layout.row()
        advanced.alignment = "RIGHT"
        advanced.prop(
            context.window_manager,
            "lestudio_show_native_object_panels",
            text="",
            icon="PREFERENCES",
            emboss=False,
        )
        if obj is None:
            self.layout.label(text="Aucun objet sélectionné", icon="INFO")
            return
        self.layout.prop(obj, "name", text="", icon="OBJECT_DATA")


class LESTUDIO_PT_transform(_LeStudioPropertiesPanel, Panel):
    bl_label = "Transformations"
    bl_idname = "LESTUDIO_PT_transform"
    bl_parent_id = "LESTUDIO_PT_properties"

    def draw(self, context):
        obj = context.object
        if obj is None:
            return
        layout = self.layout
        for label, property_name in (
            ("Position", "location"),
            ("Rotation", "rotation_euler"),
            ("Échelle", "scale"),
        ):
            if property_name == "rotation_euler" and obj.rotation_mode not in {"XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"}:
                layout.prop(obj, "rotation_mode", text="Rotation")
                layout.prop(obj, "rotation_quaternion" if obj.rotation_mode == "QUATERNION" else "rotation_axis_angle", text="")
                continue
            row = layout.row(align=True)
            row.label(text=label)
            for axis_index, axis in enumerate("XYZ"):
                row.prop(obj, property_name, index=axis_index, text=axis)


class LESTUDIO_PT_material(_LeStudioPropertiesPanel, Panel):
    bl_label = "Matériaux"
    bl_idname = "LESTUDIO_PT_material"
    bl_parent_id = "LESTUDIO_PT_properties"

    def draw(self, context):
        obj = context.object
        layout = self.layout
        if obj is None or not hasattr(obj.data, "materials"):
            layout.label(text="Matériau indisponible", icon="INFO")
            return
        layout.template_ID(obj, "active_material", new="material.new")
        material = obj.active_material
        if material is None:
            return
        shader = None
        if material.use_nodes and material.node_tree:
            shader = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
        if shader is None:
            layout.prop(material, "diffuse_color", text="Couleur de base")
            return
        for label, input_name in (
            ("Couleur de base", "Base Color"),
            ("Rugosité", "Roughness"),
            ("Métallicité", "Metallic"),
        ):
            socket = shader.inputs.get(input_name)
            if socket is not None:
                layout.prop(socket, "default_value", text=label)


class LESTUDIO_PT_modifiers(_LeStudioPropertiesPanel, Panel):
    bl_label = "Modificateurs"
    bl_idname = "LESTUDIO_PT_modifiers"
    bl_parent_id = "LESTUDIO_PT_properties"

    def draw(self, context):
        obj = context.object
        layout = self.layout
        if obj is None:
            return
        layout.operator_menu_enum("object.modifier_add", "type", text="Ajouter", icon="ADD")
        if not obj.modifiers:
            layout.label(text="Aucun modificateur", icon="MODIFIER")
        for modifier in obj.modifiers:
            layout.prop(modifier, "name", text="", icon="MODIFIER")


class LESTUDIO_PT_render(_LeStudioPropertiesPanel, Panel):
    bl_label = "Rendu"
    bl_idname = "LESTUDIO_PT_render"
    bl_parent_id = "LESTUDIO_PT_properties"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene.render, "engine", text="Moteur de rendu")
        layout.prop(scene.render, "resolution_percentage", text="Qualité")
        if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
            layout.prop(scene.eevee, "taa_render_samples", text="Échantillonnage")
        layout.operator("render.render", text="Lancer un rendu", icon="RENDER_STILL")


classes = (
    LESTUDIO_PT_properties,
    LESTUDIO_PT_transform,
    LESTUDIO_PT_material,
    LESTUDIO_PT_modifiers,
    LESTUDIO_PT_render,
)


def _color(value, alpha=1.0):
    return (*(int(value[offset:offset + 2], 16) / 255.0 for offset in (1, 3, 5)), alpha)


def _set_color(target, name, color):
    if hasattr(target, name):
        setattr(target, name, color[:len(getattr(target, name))])


def _apply_theme():
    preferences = bpy.context.preferences
    preferences.view.language = "fr_FR"
    preferences.view.use_translate_interface = True
    theme = preferences.themes[0]
    ui = theme.user_interface
    gold = _color("#D4AF37")
    burgundy = _color("#6B0F1A")
    _set_color(theme.topbar.space, "header", _color("#151617"))
    _set_color(theme.view_3d.space, "header", _color("#1a1b1e"))
    _set_color(theme.properties.space, "back", _color("#390911"))
    _set_color(theme.properties.space, "header", burgundy)
    _set_color(theme.properties.space, "header_text_hi", gold)
    _set_color(theme.view_3d.space.gradients, "gradient", _color("#1b1d21"))
    _set_color(theme.view_3d.space.gradients, "high_gradient", _color("#25272c"))
    theme.view_3d.space.gradients.background_type = "LINEAR"
    _set_color(theme.view_3d, "grid", _color("#34383f"))
    _set_color(theme.view_3d, "grid_major", _color("#34383f"))
    _set_color(ui, "panel_header", burgundy)
    _set_color(ui, "panel_back", _color("#3b0712"))
    _set_color(ui, "panel_sub_back", _color("#500d19"))
    _set_color(ui, "panel_title", gold)
    _set_color(ui, "panel_text", _color("#f4f1f1"))
    _set_color(ui, "panel_outline", _color("#D4AF37", 0.35))
    _set_color(ui.wcol_tool, "inner", _color("#440b15"))
    _set_color(ui.wcol_tool, "inner_sel", gold)
    _set_color(ui.wcol_toolbar_item, "inner", _color("#440b15"))
    _set_color(ui.wcol_toolbar_item, "inner_sel", gold)
    _set_color(ui.wcol_toolbar_item, "outline", burgundy)
    _set_color(ui.wcol_toolbar_item, "text", gold)
    _set_color(ui.wcol_numslider, "item", gold)
    _set_color(ui.wcol_numslider, "inner_sel", _color("#75571b"))
    _set_color(ui.wcol_regular, "inner_sel", _color("#75571b"))
    _set_color(ui.wcol_menu, "inner_sel", _color("#75571b"))
    _set_color(ui.wcol_tab, "inner_sel", _color("#75571b"))
    _set_color(ui, "icon_object", gold)
    _set_color(ui, "icon_modifier", gold)
    _set_color(ui, "icon_shading", gold)
    _set_color(theme.regions.asset_shelf, "back", _color("#1a1b1d"))
    _set_color(theme.regions.asset_shelf, "header_back", _color("#18191b"))
    _set_color(theme.regions.sidebars, "back", _color("#3b0712"))
    _set_color(theme.regions.sidebars, "tab_back", _color("#28060e"))


def _register_primitives():
    directory = Path(__file__).resolve().parents[3] / "datafiles" / "assets" / "lestudio_primitives"
    if not (directory / "LeStudio_Primitives.blend").is_file():
        return
    libraries = bpy.context.preferences.filepaths.asset_libraries
    library = libraries.get("LeStudio Primitives")
    if library is None:
        library = libraries.new(name="LeStudio Primitives")
    library.path = str(directory)


def _select_startup_primitives():
    """Show the bundled native assets in the initial modeling shelf."""
    if bpy.data.filepath or bpy.context.preferences.filepaths.asset_libraries.get("LeStudio Primitives") is None:
        return None
    for window in bpy.context.window_manager.windows:
        if window.workspace.name != "Modélisation":
            continue
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue
            region = next((item for item in area.regions if item.type == "ASSET_SHELF_HEADER"), None)
            if region is None:
                continue
            with bpy.context.temp_override(window=window, area=area, region=region):
                shelf = bpy.context.asset_shelf
                if shelf is not None:
                    shelf.asset_library_reference = "LeStudio Primitives"
                    shelf.show_names = True
                    shelf.preview_size = 64
                    area.tag_redraw()
    return None


def register_props():
    bpy.types.WindowManager.lestudio_show_native_object_panels = BoolProperty(
        name="Afficher les propriétés natives avancées",
        description="Afficher tous les réglages objet natifs de Bforartists",
        default=False,
    )
    _apply_theme()
    _register_primitives()
    bpy.app.timers.register(_select_startup_primitives, first_interval=2.0)


def unregister_props():
    del bpy.types.WindowManager.lestudio_show_native_object_panels
