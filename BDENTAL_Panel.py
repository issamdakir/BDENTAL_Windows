import bpy, os, sys
from os.path import join, dirname, exists, abspath


ADDON_DIR = dirname(abspath(__file__))
Addon_Version_Path = join(ADDON_DIR, "Resources", "BDENTAL_Version.txt")
if exists(Addon_Version_Path):
    with open(Addon_Version_Path, "r") as rf:
        lines = rf.readlines()
        Addon_Version_Date = lines[0].split(";")[0]
else:
    Addon_Version_Date = "  "
# Selected icons :
red_icon = "COLORSET_01_VEC"
orange_icon = "COLORSET_02_VEC"
green_icon = "COLORSET_03_VEC"
blue_icon = "COLORSET_04_VEC"
violet_icon = "COLORSET_06_VEC"
yellow_icon = "COLORSET_09_VEC"
yellow_point = "KEYTYPE_KEYFRAME_VEC"
blue_point = "KEYTYPE_BREAKDOWN_VEC"

Wmin, Wmax = -400, 3000


class BDENTAL_PT_MainPanel(bpy.types.Panel):
    """ BDENTAL Main Panel"""

    bl_idname = "BDENTAL_PT_MainPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"  # blender 2.7 and lower = TOOLS
    bl_category = "BDENTAL"
    bl_label = "BDENTAL"
    # bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):

        # Draw Addon UI :
        layout = self.layout

        box = layout.box()

        row = box.row()
        row.alert = True
        row.alignment = "CENTER"
        row.label(text=f"WINDOWS VERSION : {Addon_Version_Date}")

        row = box.row()
        row.alignment = "CENTER"
        row.operator("bdental.template", text="BDENTAL THEME")


class BDENTAL_PT_ScanPanel(bpy.types.Panel):
    """ BDENTAL Scan Panel"""

    bl_idname = "BDENTAL_PT_ScanPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"  # blender 2.7 and lower = TOOLS
    bl_category = "BDENTAL"
    bl_label = "SCAN VIEWER"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):

        BDENTAL_Props = context.scene.BDENTAL_Props
        GroupNodeName = BDENTAL_Props.GroupNodeName
        VGS = bpy.data.node_groups.get(GroupNodeName)

        # Draw Addon UI :
        layout = self.layout

        row = layout.row()
        split = row.split()
        col = split.column()
        col.label(text="Project Directory :")
        col = split.column()
        col.prop(BDENTAL_Props, "UserProjectDir", text="")

        if BDENTAL_Props.UserProjectDir:

            row = layout.row()
            split = row.split()
            col = split.column()
            col.label(text="Scan Data Type :")
            col = split.column()
            col.prop(BDENTAL_Props, "DataType", text="")

            if BDENTAL_Props.DataType == "DICOM Series":

                row = layout.row()
                split = row.split()
                col = split.column()
                col.label(text="DICOM Directory :")
                col = split.column()
                col.prop(BDENTAL_Props, "UserDcmDir", text="")

                if BDENTAL_Props.UserDcmDir:

                    Box = layout.box()
                    # Box.alert = True
                    row = Box.row()
                    row.alignment = "CENTER"
                    row.scale_y = 2
                    row.operator("bdental.volume_render", icon="IMPORT")
            if BDENTAL_Props.DataType == "3D Image File":

                row = layout.row()
                split = row.split()
                col = split.column()
                col.label(text="3D Image File :")
                col = split.column()
                col.prop(BDENTAL_Props, "UserImageFile", text="")

                if BDENTAL_Props.UserImageFile:

                    Box = layout.box()
                    # Box.alert = True
                    row = Box.row()
                    row.alignment = "CENTER"
                    row.scale_y = 2
                    row.operator("bdental.volume_render", icon="IMPORT")
        if context.object:
            if context.object.name.startswith("BD") and context.object.name.endswith(
                "CTVolume"
            ):
                row = layout.row()
                row.operator("bdental.reset_ctvolume_position")
                row = layout.row()
                row.label(text=f"Threshold {Wmin} to {Wmax} HU :")
                row = layout.row()
                row.prop(BDENTAL_Props, "Treshold", text="TRESHOLD", slider=True)

                layout.separator()

                row = layout.row()
                row.label(text="Segments :")

                Box = layout.box()
                row = Box.row()
                row.prop(BDENTAL_Props, "SoftTreshold", text="Soft Tissu")
                row.prop(BDENTAL_Props, "SoftSegmentColor", text="")
                row.prop(BDENTAL_Props, "SoftBool", text="")
                row = Box.row()
                row.prop(BDENTAL_Props, "BoneTreshold", text="Bone")
                row.prop(BDENTAL_Props, "BoneSegmentColor", text="")
                row.prop(BDENTAL_Props, "BoneBool", text="")

                row = Box.row()
                row.prop(BDENTAL_Props, "TeethTreshold", text="Teeth")
                row.prop(BDENTAL_Props, "TeethSegmentColor", text="")
                row.prop(BDENTAL_Props, "TeethBool", text="")

                Box = layout.box()
                row = Box.row()
                row.operator("bdental.multitresh_segment")
            if context.object.name.startswith("BD") and context.object.name.endswith(
                ("CTVolume", "SEGMENTATION")
            ):
                row = Box.row()
                split = row.split()
                col = split.column()
                col.operator("bdental.addslices", icon="EMPTY_AXIS")
                col = split.column()
                col.operator("bdental.multiview")


class BDENTAL_PT_Measurements(bpy.types.Panel):
    """ BDENTAL_FULL Scan Panel"""

    bl_idname = "BDENTAL_PT_Measurements"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"  # blender 2.7 and lower = TOOLS
    bl_category = "BDENTAL"
    bl_label = "MEASUREMENTS"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        Box = layout.box()
        row = Box.row()
        row.operator("bdental.add_markup_point")
        row.operator("bdental.add_reference_planes")
        row = Box.row()
        row.operator("bdental.ctvolume_orientation")


class BDENTAL_PT_MeshesTools_Panel(bpy.types.Panel):
    """ BDENTAL Meshes Tools Panel"""

    bl_idname = "BDENTAL_PT_MeshesTools_Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"  # blender 2.7 and lower = TOOLS
    bl_category = "BDENTAL"
    bl_label = "MESH TOOLS"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        BDENTAL_Props = context.scene.BDENTAL_Props
        layout = self.layout

        # Join / Link ops :

        row = layout.row()
        row.label(text="PARENT / JOIN :")
        row = layout.row()
        row.operator("bdental.parent_object", text="Parent", icon="LINKED")
        row.operator(
            "bdental.unparent_objects", text="Un-Parent", icon="LIBRARY_DATA_OVERRIDE"
        )
        row.operator("bdental.join_objects", text="Join", icon="SNAP_FACE")
        row.operator("bdental.separate_objects", text="Separate", icon="SNAP_VERTEX")

        # Align Tools :
        layout.row().separator()
        row = layout.row()
        row.label(text="Align Tools")
        row = layout.row()
        row.operator("bdental.align_to_front", text="ALIGN FRONT", icon="AXIS_FRONT")
        row.operator("bdental.to_center", text="TO CENTER", icon="SNAP_FACE_CENTER")
        row.operator("bdental.center_cursor", text="Center Cursor", icon="PIVOT_CURSOR")

        split = layout.split(factor=2 / 3, align=False)
        col = split.column()
        row = col.row()
        row.operator("bdental.occlusalplane", text="OCCLUSAL PLANE")
        col = split.column()
        row = col.row()
        row.alert = True
        row.operator("bdental.occlusalplaneinfo", text="INFO", icon="INFO")

        # Model Repair Tools :
        layout.row().separator()
        row = layout.row()
        row.label(text="REPAIR TOOLS", icon=yellow_point)

        split = layout.split(factor=2 / 3, align=False)
        col = split.column()

        row = col.row(align=True)
        row.operator("bdental.decimate", text="DECIMATE", icon="MOD_DECIM")
        row.prop(BDENTAL_Props, "decimate_ratio", text="")
        row = col.row()
        row.operator("bdental.fill", text="FILL", icon="OUTLINER_OB_LIGHTPROBE")
        row.operator("bdental.retopo_smooth", text="RETOPO SMOOTH", icon="BRUSH_SMOOTH")
        try:
            ActiveObject = bpy.context.view_layer.objects.active
            if ActiveObject:
                if ActiveObject.mode == "SCULPT":
                    row.operator(
                        "sculpt.sample_detail_size", text="", icon="EYEDROPPER"
                    )
        except Exception:
            pass

        col = split.column()
        row = col.row()
        # row.scale_y = 2
        row.operator("bdental.clean_mesh", text="CLEAN MESH", icon="BRUSH_DATA")
        row = col.row()
        row.operator("bdental.voxelremesh")

        # Cutting Tools :
        layout.row().separator()
        row = layout.row()
        row.label(text="Cutting Tools :", icon=yellow_point)
        row = layout.row()
        row.prop(BDENTAL_Props, "Cutting_Tools_Types_Prop", text="")
        if BDENTAL_Props.Cutting_Tools_Types_Prop == "Curve Cutter 1":
            row = layout.row()
            row.operator("bdental.curvecutteradd", icon="GP_SELECT_STROKES")
            row.operator("bdental.curvecuttercut", icon="GP_MULTIFRAME_EDITING")

        elif BDENTAL_Props.Cutting_Tools_Types_Prop == "Curve Cutter 2":
            row = layout.row()
            row.operator("bdental.curvecutteradd2", icon="GP_SELECT_STROKES")
            row.operator("bdental.curvecutter2_shortpath", icon="GP_MULTIFRAME_EDITING")

        elif BDENTAL_Props.Cutting_Tools_Types_Prop == "Square Cutting Tool":

            # Cutting mode column :
            row = layout.row()
            row.label(text="Select Cutting Mode :")
            row.prop(BDENTAL_Props, "cutting_mode", text="")

            row = layout.row()
            row.operator("bdental.square_cut")
            row.operator("bdental.square_cut_confirm")
            row.operator("bdental.square_cut_exit")

        elif BDENTAL_Props.Cutting_Tools_Types_Prop == "Paint Cutter":

            row = layout.row()
            row.operator("bdental.paintarea_toggle")
            row.operator("bdental.paintarea_plus", text="", icon="ADD")
            row.operator("bdental.paintarea_minus", text="", icon="REMOVE")
            row = layout.row()
            row.operator("bdental.paint_cut")


#################################################################################################
# Registration :
#################################################################################################

classes = [
    BDENTAL_PT_MainPanel,
    BDENTAL_PT_ScanPanel,
    BDENTAL_PT_Measurements,
    BDENTAL_PT_MeshesTools_Panel,
]


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


##########################################################
# TreshRamp = VGS.nodes.get("TresholdRamp")
# ColorPresetRamp = VGS.nodes.get("ColorPresetRamp")
# row = layout.row()
# row.label(
#     text=f"Volume Treshold ({BDENTAL_Props.Wmin}/{BDENTAL_Props.Wmax} HU) :"
# )
# row.template_color_ramp(
#     TreshRamp,
#     "color_ramp",
#     expand=True,
# )
# row = layout.row()
# row.prop(BDENTAL_Props, "Axial_Loc", text="AXIAL Location :")
# row = layout.row()
# row.prop(BDENTAL_Props, "Axial_Rot", text="AXIAL Rotation :")