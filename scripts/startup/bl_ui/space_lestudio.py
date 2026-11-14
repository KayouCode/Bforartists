# SPDX-FileCopyrightText: 2026 LeStudio contributors
#
# SPDX-License-Identifier: GPL-2.0-or-later
"""LeStudio modeling workspace panels backed by native Bforartists data."""

import bpy
from pathlib import Path
from bpy.props import BoolProperty, EnumProperty
from bpy.types import Menu, Operator, Panel

_FAVORITES_CATALOG = "71550f11-80fe-4421-9088-95872ea12dcb"


class LESTUDIO_OT_library_category(Operator):
    bl_idname = "lestudio.library_category"
    bl_label = "Choisir le catalogue"
    bl_description = "Afficher les assets du catalogue natif choisi"
    category: EnumProperty(items=(
        ("PRIMITIVES", "Primitives", "Primitives natives incluses"),
        ("OBJECTS", "Objets", "Assets du projet actuel"),
        ("ASSETS", "Assets", "Toutes les bibliothèques natives"),
        ("FAVORITES", "Favoris", "Catalogue Favoris de la bibliothèque LeStudio"),
    ))

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.ui_type == "ASSETS" and context.space_data.params is not None

    def execute(self, context):
        params = context.space_data.params
        params.asset_library_reference = {"OBJECTS": "LOCAL", "ASSETS": "ALL"}.get(self.category, "LeStudio Primitives")
        params.asset_catalog_visibility = "CATALOG" if self.category == "FAVORITES" else "ALL"
        _set_library_order(params, self.category)
        if self.category == "FAVORITES":
            params.catalog_id = _FAVORITES_CATALOG
        context.area.tag_redraw()
        return {"FINISHED"}


def _set_library_order(params, category):
    if category == "PRIMITIVES":
        params.sort_method = "ASSET_CATALOG"
    elif params.sort_method == "ASSET_CATALOG":
        params.sort_method = "FILE_SORT_ALPHA"


def draw_library_header(layout, context):
    from bl_ui.lestudio_icons import tool_icon
    params = context.space_data.params
    if params is None:
        return
    library = params.asset_library_reference
    current = "OBJECTS" if library == "LOCAL" else "ASSETS" if library == "ALL" else "FAVORITES" if params.asset_catalog_visibility == "CATALOG" and params.catalog_id == _FAVORITES_CATALOG else "PRIMITIVES"
    for category, label, icon in (("PRIMITIVES", "Primitives", "MESH_CUBE"),
                                  ("OBJECTS", "Objets", "OBJECT_DATA"),
                                  ("ASSETS", "Assets", "ASSET_MANAGER"),
                                  ("FAVORITES", "Favoris", "FUND")):
        vector = {"PRIMITIVES": "ui.cube", "OBJECTS": "ui.cube",
                  "ASSETS": "ui.image", "FAVORITES": "ui.star"}[category]
        tint = (212, 175, 55, 255) if current == category else (238, 238, 238, 255)
        layout.operator("lestudio.library_category", text=label, icon_value=tool_icon(vector, color=tint),
                        depress=current == category).category = category
    layout.separator_spacer()
    search = layout.row()
    search.ui_units_x = 18
    search.prop(params, "filter_search", text="", icon="VIEWZOOM", placeholder="Rechercher un asset…")
    layout.prop(params, "display_type", expand=True, icon_only=True)
    layout.menu("ASSETBROWSER_MT_editor_menus", text="", icon="THREE_DOTS")


def draw_modeling_header(layout, context):
    from bl_ui.lestudio_icons import tool_icon
    layout.scale_y = 1.2
    view = context.space_data
    tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
    active = tool.idname if tool else ""
    icons = {"builtin.select": "RESTRICT_SELECT_OFF", "builtin.select_box": "BORDER_RECT",
             "builtin.select_circle": "CIRCLE_SELECT", "builtin.move": "TRANSFORM_MOVE",
             "builtin.rotate": "TRANSFORM_ROTATE", "builtin.scale": "TRANSFORM_SCALE",
             "builtin.transform": "TRANSFORM_GIZMO"}
    for group in (("builtin.select", "builtin.select_box", "builtin.select_circle"),
                  ("builtin.move", "builtin.rotate", "builtin.scale", "builtin.transform")):
        row = layout.row(align=True)
        for name in group:
            row.operator("wm.tool_set_by_id", text="", icon_value=tool_icon(
                             name, color=(212, 175, 55, 255) if active == name else (238, 238, 238, 255)),
                         depress=active == name).name = name
        layout.separator()
    layout.prop_with_popover(context.scene.transform_orientation_slots[0], "type",
                             text="", panel="VIEW3D_PT_transform_orientations")
    layout.prop(context.tool_settings, "transform_pivot_point", text="", icon_only=True)
    snap = layout.row(align=True)
    snap.prop(context.tool_settings, "use_snap", text="")
    snap.popover(panel="VIEW3D_PT_snapping", text="")
    layout.prop(view.overlay, "show_overlays", text="", icon="OVERLAY")
    # Native mode and complete View menus preserve the controls not pictured
    # in the compact strip. Keyboard bindings are not changed.
    layout.operator_menu_enum("object.mode_set", "mode", text="", icon="EDITMODE_HLT")
    layout.menu("VIEW3D_MT_view", text="", icon="DOWNARROW_HLT")
    if context.mode == "EDIT_MESH":
        layout.template_header_3D_mode()
    layout.separator_spacer()
    layout.prop(view.shading, "type", text="", expand=True)
    layout.popover(panel="VIEW3D_PT_shading", text="")


def draw_modeling_toolbar(layout, context):
    from bl_ui.lestudio_icons import tool_icon
    tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
    active = tool.idname if tool else ""
    for pair in (("builtin.select", "builtin.select_circle"),
                 ("builtin.move", "builtin.rotate"),
                 ("builtin.scale", "builtin.transform")):
        row = layout.row(align=False)
        row.scale_x = 1.65
        row.scale_y = 1.65
        for name in pair:
            row.operator("wm.tool_set_by_id", text="", icon_value=tool_icon(name),
                         depress=active == name).name = name
    layout.separator()
    for name in ("builtin.annotate", "ui.cube",
                 "builtin.primitive_cube_add", "builtin.measure"):
        row = layout.row()
        row.alignment = "LEFT"
        row.scale_x = 1.65
        row.scale_y = 1.65
        if name == "ui.cube":
            row.operator("wm.call_menu", text="", icon_value=tool_icon(name)).name = "VIEW3D_MT_mesh_add"
        else:
            row.operator("wm.tool_set_by_id", text="", icon_value=tool_icon(name),
                         depress=active == name).name = name
    layout.separator()
    for name in ("builtin.poly_build", "builtin.extrude_region"):
        row = layout.row()
        row.alignment = "LEFT"
        row.scale_x = 1.65
        row.scale_y = 1.65
        row.operator("lestudio.mesh_tool", text="", icon_value=tool_icon(name)).tool = name


class LESTUDIO_OT_mesh_tool(Operator):
    bl_idname = "lestudio.mesh_tool"
    bl_label = "Outil de maillage natif"
    bl_description = "Passer en mode Édition et activer l'outil natif sur le maillage sélectionné"
    tool: EnumProperty(items=(
        ("builtin.poly_build", "Construction de polygones", "Outil natif de construction de polygones"),
        ("builtin.extrude_region", "Extrusion", "Outil natif d'extrusion de région"),
    ))

    @classmethod
    def poll(cls, context):
        return (context.area is not None and context.area.type == "VIEW_3D" and
                context.object is not None and context.object.type == "MESH" and
                bpy.ops.object.mode_set.poll())

    def execute(self, context):
        bpy.ops.object.mode_set(mode="EDIT")
        return bpy.ops.wm.tool_set_by_id(name=self.tool)


def _quality_target(scene):
    """Display presets for existing native sampling settings, not a renderer."""
    if scene.render.engine == "BLENDER_EEVEE" and hasattr(scene, "eevee"):
        return scene.eevee, "taa_render_samples", (16, 64, 256)
    if scene.render.engine == "CYCLES" and hasattr(scene, "cycles"):
        return scene.cycles, "samples", (32, 128, 512)
    if scene.render.engine == "BLENDER_WORKBENCH":
        return scene.display, "render_aa", ("8", "16", "32")
    return None


class LESTUDIO_OT_render_quality(Operator):
    bl_idname = "lestudio.render_quality"
    bl_label = "Qualité d'échantillonnage"
    bl_description = "Appliquer un préréglage du nombre d'échantillons du moteur natif"
    bl_options = {"REGISTER", "UNDO"}
    preset: EnumProperty(items=(
        ("LOW", "Basse", "Échantillonnage natif réduit"),
        ("MEDIUM", "Moyenne", "Échantillonnage natif intermédiaire"),
        ("HIGH", "Élevée", "Échantillonnage natif élevé"),
    ))

    @classmethod
    def poll(cls, context):
        return _quality_target(context.scene) is not None

    def execute(self, context):
        target, field, values = _quality_target(context.scene)
        setattr(target, field, values[("LOW", "MEDIUM", "HIGH").index(self.preset)])
        return {"FINISHED"}


class LESTUDIO_MT_render_quality(Menu):
    bl_label = "Qualité"

    def draw(self, context):
        for value, label in (("LOW", "Basse"), ("MEDIUM", "Moyenne"), ("HIGH", "Élevée")):
            self.layout.operator("lestudio.render_quality", text=label).preset = value


def _quality_label(scene):
    result = _quality_target(scene)
    if result is None:
        return "Réglages natifs"
    target, field, values = result
    current = getattr(target, field)
    return next((label for value, label in zip(values, ("Basse", "Moyenne", "Élevée"))
                 if current == value), "Personnalisée")


class LESTUDIO_MT_mesh_menu(Menu):
    bl_label = "Maillage"

    def draw(self, context):
        if context.mode == "EDIT_MESH":
            bpy.types.VIEW3D_MT_edit_mesh.draw(self, context)
        elif context.object is not None and context.object.type == "MESH":
            self.layout.operator("object.mode_set", text="Passer en mode Édition", icon="EDITMODE_HLT").mode = "EDIT"
        else:
            self.layout.label(text="Sélectionnez un objet maillage", icon="INFO")


class LESTUDIO_OT_open_view_menu(Operator):
    bl_idname = "lestudio.open_view_menu"
    bl_label = "Ouvrir le menu natif de la vue 3D"
    bl_description = "Ouvrir les commandes natives dans le contexte réel du viewport"
    bl_options = {"INTERNAL"}
    menu: EnumProperty(items=tuple((value, label, label) for value, label in (
        ("OBJECT", "Objet"), ("VIEW", "Vue"), ("SELECT", "Sélection"),
        ("ADD", "Ajouter"), ("MESH", "Maillage"), ("TOOLS", "Outils"))))

    @classmethod
    def poll(cls, context):
        return context.window is not None and any(area.type == "VIEW_3D" for area in context.window.screen.areas)

    def execute(self, context):
        view = max((area for area in context.window.screen.areas if area.type == "VIEW_3D"),
                   key=lambda area: area.width * area.height)
        region = next(region for region in view.regions if region.type == "WINDOW")
        with context.temp_override(window=context.window, area=view, region=region):
            edit_mesh = context.mode == "EDIT_MESH"
            name = {
                "OBJECT": "VIEW3D_MT_object",
                "VIEW": "VIEW3D_MT_view",
                "SELECT": "VIEW3D_MT_select_edit_mesh" if edit_mesh else "VIEW3D_MT_select_object",
                "ADD": "VIEW3D_MT_mesh_add" if edit_mesh else "VIEW3D_MT_add",
                "MESH": "LESTUDIO_MT_mesh_menu",
                "TOOLS": "LESTUDIO_MT_tools_menu",
            }[self.menu]
            return bpy.ops.wm.call_menu("INVOKE_DEFAULT", name=name)


class LESTUDIO_MT_tools_menu(Menu):
    bl_label = "Outils"

    def draw(self, context):
        self.layout.operator("wm.toolbar", text="Tous les outils natifs", icon="TOOL_SETTINGS")
        self.layout.separator()
        native = bpy.types.VIEW3D_MT_edit_mesh_context_menu if context.mode == "EDIT_MESH" else bpy.types.VIEW3D_MT_object_context_menu
        native.draw(self, context)


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
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        obj = context.object
        if obj is None:
            self.layout.label(text="Aucun objet sélectionné", icon="INFO")
            return
        self.layout.prop(obj, "name", text="", icon="OBJECT_DATA")


class LESTUDIO_PT_transform(_LeStudioPropertiesPanel, Panel):
    bl_label = "Transformations"
    bl_idname = "LESTUDIO_PT_transform"
    bl_parent_id = "LESTUDIO_PT_properties"

    def draw_header_preset(self, context):
        obj = context.object
        if obj is not None:
            locked = any(obj.lock_location) or any(obj.lock_rotation) or any(obj.lock_scale)
            self.layout.popover(panel="LESTUDIO_PT_transform_locks", text="",
                                icon="LOCKED" if locked else "UNLOCKED")

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


class LESTUDIO_PT_transform_locks(Panel):
    bl_space_type = "PROPERTIES"
    bl_region_type = "HEADER"
    bl_label = "Verrouillage des transformations"

    def draw(self, context):
        obj = context.object
        if obj is None:
            return
        for label, field in (("Position", "lock_location"),
                             ("Rotation", "lock_rotation"),
                             ("Échelle", "lock_scale")):
            row = self.layout.row(align=True)
            row.label(text=label)
            for index, axis in enumerate("XYZ"):
                row.prop(obj, field, index=index, text=axis, toggle=True)


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
        selector = layout.row(align=False)
        preview = selector.row()
        preview.ui_units_x = 1.8
        preview.scale_y = 0.3
        preview.template_ID_preview(obj, "active_material", rows=4, cols=4, hide_buttons=True)
        selector.template_ID(obj, "active_material", new="material.new")
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
                row = layout.split(factor=0.35)
                row.label(text=label)
                if input_name == "Base Color":
                    row.prop(socket, "default_value", text="")
                else:
                    controls = row.split(factor=0.72, align=False)
                    controls.prop(socket, "default_value", text="", slider=True)
                    controls.prop(socket, "default_value", text="")


class LESTUDIO_PT_modifiers(_LeStudioPropertiesPanel, Panel):
    bl_label = "Modificateurs"
    bl_idname = "LESTUDIO_PT_modifiers"
    bl_parent_id = "LESTUDIO_PT_properties"

    def draw_header_preset(self, context):
        self.layout.operator_menu_enum("object.modifier_add", "type", text="", icon="ADD")

    def draw(self, context):
        obj = context.object
        layout = self.layout
        if obj is None:
            return
        if not obj.modifiers:
            row = layout.box().row()
            row.alignment = "CENTER"
            row.label(text="Aucun modificateur", icon="MODIFIER")
        for modifier in obj.modifiers:
            layout.prop(modifier, "name", text="", icon="MODIFIER")


class LESTUDIO_PT_render(_LeStudioPropertiesPanel, Panel):
    bl_label = "Rendu"
    bl_idname = "LESTUDIO_PT_render"
    bl_parent_id = "LESTUDIO_PT_properties"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.split(factor=0.35)
        row.label(text="Moteur de rendu")
        row.prop(scene.render, "engine", text="")
        row = layout.split(factor=0.35)
        row.label(text="Qualité")
        row.menu("LESTUDIO_MT_render_quality", text=_quality_label(scene))
        target = _quality_target(scene)
        if target:
            owner, field, values = target
            row = layout.split(factor=0.35)
            row.label(text="Échantillonnage")
            if scene.render.engine == "BLENDER_WORKBENCH":
                row.prop(owner, field, text="")
            else:
                controls = row.split(factor=0.72, align=False)
                controls.prop(owner, field, text="", slider=True)
                controls.prop(owner, field, text="")


class LESTUDIO_PT_render_options(_LeStudioPropertiesPanel, Panel):
    bl_label = "Options de rendu"
    bl_idname = "LESTUDIO_PT_render_options"
    bl_parent_id = "LESTUDIO_PT_render"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        render = context.scene.render
        layout.operator("render.render", text="Lancer un rendu", icon="RENDER_STILL")
        layout.prop(render, "resolution_x", text="Largeur")
        layout.prop(render, "resolution_y", text="Hauteur")
        layout.prop(render, "resolution_percentage", text="Résolution")


classes = (
    LESTUDIO_OT_mesh_tool,
    LESTUDIO_MT_tools_menu,
    LESTUDIO_OT_library_category,
    LESTUDIO_OT_render_quality,
    LESTUDIO_MT_render_quality,
    LESTUDIO_MT_mesh_menu,
    LESTUDIO_OT_open_view_menu,
    LESTUDIO_PT_properties,
    LESTUDIO_PT_transform,
    LESTUDIO_PT_transform_locks,
    LESTUDIO_PT_material,
    LESTUDIO_PT_modifiers,
    LESTUDIO_PT_render,
    LESTUDIO_PT_render_options,
)


def _color(value, alpha=1.0):
    return (*(int(value[offset:offset + 2], 16) / 255.0 for offset in (1, 3, 5)), alpha)


def _set_color(target, name, color):
    if hasattr(target, name):
        setattr(target, name, color[:len(getattr(target, name))])


def _apply_theme():
    preferences = bpy.context.preferences
    preferences.view.show_splash = False
    preferences.system.use_region_overlap = False
    # Keep the native XYZ orientation gizmo. Pan/zoom/camera remain accessible
    # through their native gestures and View menu without extra overlay buttons.
    preferences.view.show_navigate_ui = False
    preferences.view.language = "fr_FR"
    preferences.view.use_translate_interface = True
    preferences.view.show_statusbar_stats = True
    theme = preferences.themes[0]
    ui = theme.user_interface
    gold = _color("#D4AF37")
    burgundy = _color("#6B0F1A")
    _set_color(theme.topbar.space, "header", _color("#151617"))
    _set_color(theme.topbar.space, "back", _color("#151617"))
    _set_color(theme.view_3d.space, "header", _color("#1a1b1e"))
    _set_color(theme.properties.space, "back", _color("#24090f"))
    _set_color(theme.properties.space, "header", _color("#430b15"))
    _set_color(theme.properties.space, "header_text_hi", gold)
    _set_color(theme.view_3d.space.gradients, "gradient", _color("#1b1d21"))
    _set_color(theme.view_3d.space.gradients, "high_gradient", _color("#25272c"))
    theme.view_3d.space.gradients.background_type = "LINEAR"
    _set_color(theme.view_3d, "grid", _color("#34383f"))
    _set_color(theme.view_3d, "grid_major", _color("#34383f"))
    _set_color(ui, "panel_header", _color("#500f19"))
    _set_color(ui, "panel_back", _color("#290810"))
    _set_color(ui, "panel_sub_back", _color("#380c15"))
    ui.panel_roundness = 0.4
    _set_color(ui, "panel_title", gold)
    _set_color(ui, "panel_text", _color("#f4f1f1"))
    _set_color(ui, "panel_outline", _color("#D4AF37", 0.35))
    _set_color(ui.wcol_tool, "inner", _color("#440b15"))
    _set_color(ui.wcol_tool, "inner_sel", gold)
    _set_color(ui.wcol_toolbar_item, "inner", _color("#440b15"))
    _set_color(ui.wcol_toolbar_item, "inner_sel", _color("#75571b"))
    _set_color(ui.wcol_toolbar_item, "outline", burgundy)
    _set_color(ui.wcol_toolbar_item, "text", gold)
    _set_color(ui.wcol_numslider, "item", gold)
    _set_color(ui.wcol_numslider, "inner_sel", _color("#75571b"))
    _set_color(ui.wcol_box, "inner", _color("#241b1e"))
    _set_color(ui.wcol_box, "outline", _color("#573139"))
    _set_color(ui.wcol_regular, "inner_sel", _color("#75571b"))
    _set_color(ui.wcol_menu, "inner_sel", _color("#75571b"))
    _set_color(ui.wcol_tab, "inner_sel", _color("#75571b"))
    for widget in (ui.wcol_regular, ui.wcol_tool, ui.wcol_num, ui.wcol_numslider,
                   ui.wcol_text, ui.wcol_menu, ui.wcol_menu_back):
        _set_color(widget, "inner", _color("#292326"))
        _set_color(widget, "outline", _color("#573139"))
        _set_color(widget, "text", _color("#f4f1f1"))
        _set_color(widget, "text_sel", _color("#ffffff"))
        _set_color(widget, "inner_sel", _color("#75571b"))
    for widget in (ui.wcol_tool, ui.wcol_toolbar_item):
        _set_color(widget, "inner", _color("#3d101a"))
        _set_color(widget, "inner_sel", _color("#75571b"))
        _set_color(widget, "outline", _color("#60313a"))
        _set_color(widget, "outline_sel", gold)
        widget.roundness = 0.4
    _set_color(ui, "icon_object", gold)
    _set_color(ui, "icon_modifier", gold)
    _set_color(ui, "icon_shading", gold)
    _set_color(theme.regions.asset_shelf, "back", _color("#1a1b1d"))
    _set_color(theme.regions.asset_shelf, "header_back", _color("#18191b"))
    _set_color(theme.file_browser.space, "back", _color("#18191b"))
    _set_color(theme.file_browser.space, "header", _color("#18191b"))
    _set_color(theme.regions.sidebars, "back", _color("#290810"))
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
            if area.ui_type == "ASSETS" and area.spaces.active.params is not None:
                area.spaces.active.params.asset_library_reference = "LeStudio Primitives"
                _set_library_order(area.spaces.active.params, "PRIMITIVES")
                area.tag_redraw()
                continue
            if area.type != "VIEW_3D":
                continue
            area.spaces.active.show_toolshelf_tabs = False
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
    from bl_ui.lestudio_icons import release
    release()
    del bpy.types.WindowManager.lestudio_show_native_object_panels
