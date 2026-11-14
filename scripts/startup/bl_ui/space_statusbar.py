# SPDX-FileCopyrightText: 2018-2023 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

from bpy.types import Header


class STATUSBAR_HT_header(Header):
    bl_space_type = 'STATUSBAR'

    def draw(self, context):
        layout = self.layout

        if context.workspace.name == "Modélisation":
            # Keep native hints, warnings, counters and running jobs. Only move
            # their presentation to the reference's left-to-right arrangement.
            layout.template_input_status()
            layout.template_status_info()
            layout.separator_spacer()
            layout.template_reports_banner()
            layout.template_running_jobs()
            layout.separator_spacer()
            layout.operator("wm.splash_about", text="LeStudio", emboss=False)
            return

        # input status
        layout.template_input_status()

        layout.separator_spacer()

        # Messages
        layout.template_reports_banner()

        # Progress Bar
        layout.template_running_jobs()

        layout.separator_spacer()

        row = layout.row()
        row.alignment = 'RIGHT'

        # Stats & Info
        layout.template_status_info()


classes = (
    STATUSBAR_HT_header,
)

if __name__ == "__main__":  # only for live edit.
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

