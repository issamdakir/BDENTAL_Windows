import bpy
from time import perf_counter as Tcounter
from bpy.props import (
    StringProperty,
    IntProperty,
    FloatProperty,
    EnumProperty,
    FloatVectorProperty,
    BoolProperty,
)
from .BDENTAL_Utils import *

Addon_Enable(AddonName="mesh_looptools", Enable=True)

class BDENTAL_OT_JoinObjects(bpy.types.Operator):
    " Join Objects "

    bl_idname = "bdental.join_objects"
    bl_label = "JOIN :"

    def execute(self, context):

        ActiveObj = context.active_object
        condition = (ActiveObj and ActiveObj in context.selected_objects and len(context.selected_objects)>=2)

        if not condition :

            message = [" Please select objects to join !"]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")

            return {"CANCELLED"}


        else:

            bpy.ops.object.join()

            return {"FINISHED"}


#######################################################################################
# Separate models operator :


class BDENTAL_OT_SeparateObjects(bpy.types.Operator):
    " Separate Objects "

    bl_idname = "bdental.separate_objects"
    bl_label = "SEPARATE :"

    Separate_Modes_List = ["Selection", "Loose Parts", ""]
    items = []
    for i in range(len(Separate_Modes_List)):
        item = (str(Separate_Modes_List[i]), str(Separate_Modes_List[i]), str(""), int(i))
        items.append(item)

    SeparateMode: EnumProperty(items=items, description="SeparateMode", default="Loose Parts")

    def execute(self, context):
        
        if self.SeparateMode == "Loose Parts" :
            bpy.ops.mesh.separate(type="LOOSE")

        if self.SeparateMode == "Selection" :
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.separate(type='SELECTED')

        bpy.ops.object.mode_set(mode="OBJECT")

        Parts = list(context.selected_objects)

        if Parts and len(Parts) > 1 :
            for obj in Parts :
                bpy.ops.object.select_all(action="DESELECT")
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="MEDIAN")
                
            bpy.ops.object.select_all(action="DESELECT")
            Parts[-1].select_set(True)
            bpy.context.view_layer.objects.active = Parts[-1]

        return {"FINISHED"}

    def invoke(self, context, event):

        self.ActiveObj = context.active_object
        condition = (self.ActiveObj and self.ActiveObj.type == 'MESH' and self.ActiveObj in bpy.context.selected_objects )

        if not condition :

            message = [" Please select the target object !"]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")

            return {"CANCELLED"}

        else :
            wm = context.window_manager
            return wm.invoke_props_dialog(self)

#######################################################################################
# Parent model operator :


class BDENTAL_OT_Parent(bpy.types.Operator):
    " Parent Object "

    bl_idname = "bdental.parent_object"
    bl_label = "PARENT"

    def execute(self, context):

        ActiveObj = context.active_object
        condition = (ActiveObj and ActiveObj in context.selected_objects and len(context.selected_objects)>=2)

        if not condition :
            message = [" Please select child objects,","parent object should be," ,"the last one selected!"]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")

            return {"CANCELLED"}

        else:
            parent = ActiveObj
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.parent_set(type="OBJECT", keep_transform=True)
            bpy.ops.object.select_all(action="DESELECT")
            parent.select_set(True)
            # bpy.ops.object.hide_view_set(unselected=True)

            return {"FINISHED"}


#######################################################################################
# Unparent model operator :


class BDENTAL_OT_Unparent(bpy.types.Operator):
    " Un-Parent objects"

    bl_idname = "bdental.unparent_objects"
    bl_label = "Un-Parent"

    def execute(self, context):

        ActiveObj = context.active_object
        condition = (ActiveObj and ActiveObj in bpy.context.selected_objects )

        if not condition :

            message = [" Please select the target objects !"]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")

            return {"CANCELLED"}

        else:
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
            bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="MEDIAN")

            return {"FINISHED"}

#######################################################################################
# Align model to front operator :


class BDENTAL_OT_align_to_front(bpy.types.Operator):
    """Align Model To Front view"""

    bl_idname = "bdental.align_to_front"
    bl_label = "Align to Front"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        ActiveObj = context.active_object
        condition = (ActiveObj and ActiveObj.type == 'MESH' and ActiveObj in bpy.context.selected_objects )

        if not condition :

            message = [" Please select the target object !"]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")

            return {"CANCELLED"}

        else:

            Model = bpy.context.view_layer.objects.active

            # get object rotation mode and invert it :

            rot_mod = Model.rotation_mode

            # Get VIEW_rotation matrix  :

            view3d_rot_matrix = (
                context.space_data.region_3d.view_rotation.to_matrix().to_4x4()
            )

            # create a 90 degrees arround X_axis Euler :
            Eul_90x = Euler((radians(90), 0, 0), rot_mod)

            # Euler to mattrix 4x4 :
            Eul_90x_matrix = Eul_90x.to_matrix().to_4x4()

            # Rotate Model :
            Model.matrix_world = (
                Eul_90x_matrix @ view3d_rot_matrix.inverted() @ Model.matrix_world
            )
            bpy.ops.view3d.view_all(center=True)
            bpy.ops.view3d.view_axis(type="FRONT")
            bpy.ops.wm.tool_set_by_id(name="builtin.cursor")

        return {"FINISHED"}


#######################################################################################
# Center model modal operator :


class BDENTAL_OT_to_center(bpy.types.Operator):
    " Center Model to world origin "

    bl_idname = "bdental.to_center"
    bl_label = "TO CENTER"

    yellow_stone = [1.0, 0.36, 0.06, 1.0]

    def modal(self, context, event):

        if not event.type in {"RET", "ESC"}:
            # allow navigation

            return {"PASS_THROUGH"}

        elif event.type == "RET":

            if event.value == ("PRESS"):

                if context.scene.cursor.location == (0, 0, 0):

                    bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
                    bpy.ops.view3d.snap_selected_to_cursor(use_offset=True)

                else:

                    bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
                    bpy.ops.view3d.snap_cursor_to_center()
                    bpy.ops.view3d.snap_selected_to_cursor(use_offset=True)
                    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="MEDIAN")

            bpy.ops.view3d.view_all(center=True)
            # bpy.ops.wm.tool_set_by_id(name="builtin.cursor")
            bpy.ops.wm.tool_set_by_id(name="builtin.select")

            return {"FINISHED"}

        elif event.type == ("ESC"):

            if event.value == ("PRESS"):

                bpy.ops.wm.tool_set_by_id(name="builtin.select")

                return {"CANCELLED"}

        return {"RUNNING_MODAL"}

    def invoke(self, context, event):

        ActiveObj = context.active_object
        condition = (ActiveObj and ActiveObj.type == 'MESH' and ActiveObj in bpy.context.selected_objects )

        if not condition :

            message = [" Please select the target object !"]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")

            return {"CANCELLED"}

        else:

            if context.space_data.type == "VIEW_3D":

                bpy.ops.ed.undo_push()

                bpy.ops.object.mode_set(mode="OBJECT")
                Model = bpy.context.view_layer.objects.active
                bpy.ops.object.select_all(action="DESELECT")
                Model.select_set(True)

                bpy.ops.wm.tool_set_by_id(name="builtin.cursor")

                message = [" Please move cursor to incisal Midline"," and click < ENTER >!"]
                ShowMessageBox(message=message, icon="COLORSET_02_VEC")

                context.window_manager.modal_handler_add(self)

                return {"RUNNING_MODAL"}

            else:

                self.report({"WARNING"}, "Active space must be a View3d")

                return {"CANCELLED"}


#######################################################################################
# Cursor to world origin operator :


class BDENTAL_OT_center_cursor(bpy.types.Operator):
    """Cursor to World Origin """

    bl_idname = "bdental.center_cursor"
    bl_label = "Center Cursor"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        bpy.ops.view3d.snap_cursor_to_center()

        return {"FINISHED"}

#######################################################################################
# Add Occlusal Plane :
class BDENTAL_OT_OcclusalPlane(bpy.types.Operator):
    """ Add Occlusal Plane"""

    bl_idname = "bdental.occlusalplane"
    bl_label = "OCCLUSAL PLANE"
    bl_options = {"REGISTER", "UNDO"}

    CollName = "Occlusal Points"
    OcclusalPionts = []

    def modal(self, context, event):

        if (
            event.type
            in [
                "LEFTMOUSE",
                "RIGHTMOUSE",
                "MIDDLEMOUSE",
                "WHEELUPMOUSE",
                "WHEELDOWNMOUSE",
                "N",
                "NUMPAD_2",
                "NUMPAD_4",
                "NUMPAD_6",
                "NUMPAD_8",
                "NUMPAD_1",
                "NUMPAD_3",
                "NUMPAD_5",
                "NUMPAD_7",
                "NUMPAD_9",
            ]
            and event.value == "PRESS"
        ):

            return {"PASS_THROUGH"}
        #########################################
        if event.type == "R":
            # Add Right point :
            if event.value == ("PRESS"):
                color = (1,0,0,1) #red
                CollName = self.CollName
                name = "Right_Occlusal_Point"
                OldPoint = bpy.data.objects.get(name)
                if OldPoint :
                    bpy.data.objects.remove(OldPoint)
                NewPoint = AddOcclusalPoint(name, color, CollName)
                self.RightPoint = NewPoint
                bpy.ops.object.select_all(action="DESELECT")
                self.OcclusalPoints = [obj for obj in bpy.context.scene.objects if obj.name.endswith("_Occlusal_Point") and not obj is self.RightPoint]
                self.OcclusalPoints.append(self.RightPoint)

        #########################################
        if event.type == "A":
            # Add Right point :
            if event.value == ("PRESS"):
                color = (0,1,0,1) # green
                CollName = self.CollName
                name = "Anterior_Occlusal_Point"
                OldPoint = bpy.data.objects.get(name)
                if OldPoint :
                    bpy.data.objects.remove(OldPoint)
                NewPoint = AddOcclusalPoint(name, color, CollName)
                self.AnteriorPoint = NewPoint
                bpy.ops.object.select_all(action="DESELECT")
                self.OcclusalPoints = [obj for obj in bpy.context.scene.objects if obj.name.endswith("_Occlusal_Point") and not obj is self.AnteriorPoint]
                self.OcclusalPoints.append(self.AnteriorPoint)
        #########################################
        if event.type == "L":
            # Add Right point :
            if event.value == ("PRESS"):
                color = (0,0,1,1) # blue
                CollName = self.CollName
                name = "Left_Occlusal_Point"
                OldPoint = bpy.data.objects.get(name)
                if OldPoint :
                    bpy.data.objects.remove(OldPoint)
                NewPoint = AddOcclusalPoint(name, color, CollName)
                self.LeftPoint = NewPoint
                bpy.ops.object.select_all(action="DESELECT")
                self.OcclusalPoints = [obj for obj in bpy.context.scene.objects if obj.name.endswith("_Occlusal_Point") and not obj is self.LeftPoint]
                self.OcclusalPoints.append(self.LeftPoint)
        #########################################

        elif event.type == ("DEL"):

            if self.OcclusalPionts :
                self.OcclusalPionts.pop()

            return {"PASS_THROUGH"}

        elif event.type == "RET":
            if event.value == ("PRESS"):

                Override, area3D, space3D = CtxOverride(context)

                OcclusalPlane = PointsToOcclusalPlane(Override,self.Target, self.RightPoint,self.AnteriorPoint,self.LeftPoint,color=(0.0, 0.0, 0.2, 0.7),subdiv=50)
                self.OcclusalPoints = [obj for obj in bpy.context.scene.objects if obj.name.endswith("_Occlusal_Point")]
                if self.OcclusalPoints :
                    for P in self.OcclusalPoints :
                        bpy.data.objects.remove(P)
                ##########################################################
                space3D.overlay.show_outline_selected = True
                space3D.overlay.show_object_origins = True
                space3D.overlay.show_annotation = True
                space3D.overlay.show_text = True
                space3D.overlay.show_extras = True
                space3D.overlay.show_floor = True
                space3D.overlay.show_axis_x = True
                space3D.overlay.show_axis_y = True
                ###########################################################

                bpy.ops.object.hide_view_clear(Override)
                bpy.ops.object.select_all(action='DESELECT')
#                bpy.ops.object.select_all(Override, action="DESELECT")
                for obj in self.visibleObjects:
                    obj.select_set(True)
                    bpy.context.view_layer.objects.active = obj
                OcclusalPlane.select_set(True)
                bpy.context.view_layer.objects.active = OcclusalPlane
                bpy.ops.object.hide_view_set(Override, unselected=True)
                bpy.ops.object.select_all(action='DESELECT')
#                bpy.ops.object.select_all(Override, action="DESELECT")
                OcclusalPlane.select_set(True)
                bpy.ops.wm.tool_set_by_id(Override, name="builtin.select")
                bpy.context.scene.tool_settings.use_snap = False
                space3D.shading.background_color = self.background_color
                space3D.shading.background_type = self.background_type
                
                bpy.context.scene.cursor.location = (0, 0, 0)
                bpy.ops.screen.region_toggle(Override, region_type="UI")
                bpy.ops.screen.screen_full_area(Override)

                
                ##########################################################

                finish = Tcounter()
                
                return {"FINISHED"}

        elif event.type == ("ESC"):

            for P in self.OcclusalPionts :
                bpy.data.objects.remove(P)

            Override, area3D, space3D = CtxOverride(context)
            ##########################################################
            space3D.overlay.show_outline_selected = True
            space3D.overlay.show_object_origins = True
            space3D.overlay.show_annotation = True
            space3D.overlay.show_text = True
            space3D.overlay.show_extras = True
            space3D.overlay.show_floor = True
            space3D.overlay.show_axis_x = True
            space3D.overlay.show_axis_y = True
            ###########################################################

            bpy.ops.object.hide_view_clear(Override)
            bpy.ops.object.select_all(action='DESELECT')
#            bpy.ops.object.select_all(Override, action="DESELECT")
            for obj in self.visibleObjects:
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
            bpy.ops.object.hide_view_set(Override, unselected=True)
            bpy.ops.object.select_all(action='DESELECT')
#            bpy.ops.object.select_all(Override, action="DESELECT")
            bpy.ops.wm.tool_set_by_id(Override, name="builtin.select")
            bpy.context.scene.tool_settings.use_snap = False
            space3D.shading.background_color = self.background_color
            space3D.shading.background_type = self.background_type
            
            bpy.context.scene.cursor.location = (0, 0, 0)
            bpy.ops.screen.region_toggle(Override, region_type="UI")
            bpy.ops.screen.screen_full_area(Override)

            message = [
                    " The Occlusal Plane Operation was Cancelled!",
                ]

            ShowMessageBox2(message=message, icon="COLORSET_03_VEC")

            return {"CANCELLED"}

        return {"RUNNING_MODAL"}
        

    def invoke(self, context, event):
        Condition_1 = bpy.context.selected_objects and bpy.context.active_object

        if not Condition_1 :

            message = [
                "Please select Target object",
            ]
            ShowMessageBox2(message=message, icon="COLORSET_02_VEC")

            return {"CANCELLED"}

        else:

            self.Target = context.active_object
            bpy.context.scene.tool_settings.snap_elements = {"FACE"}


            if context.space_data.type == "VIEW_3D":
                
                # Prepare scene  :
                ##########################################################

                bpy.context.space_data.overlay.show_outline_selected = False
                bpy.context.space_data.overlay.show_object_origins = False
                bpy.context.space_data.overlay.show_annotation = False
                bpy.context.space_data.overlay.show_text = False
                bpy.context.space_data.overlay.show_extras = False
                bpy.context.space_data.overlay.show_floor = False
                bpy.context.space_data.overlay.show_axis_x = False
                bpy.context.space_data.overlay.show_axis_y = False
                bpy.context.scene.tool_settings.use_snap = True
                bpy.context.scene.tool_settings.snap_elements = {"FACE"}
                bpy.context.scene.tool_settings.transform_pivot_point = (
                    "INDIVIDUAL_ORIGINS"
                )
                bpy.ops.wm.tool_set_by_id(name="builtin.cursor")
                bpy.ops.object.hide_view_set(unselected=True)

                ###########################################################
                self.TargetObject = bpy.context.active_object
                

                self.TargetPoints = []

            
                self.visibleObjects = bpy.context.visible_objects.copy()
                self.background_type = bpy.context.space_data.shading.background_type
                bpy.context.space_data.shading.background_type = "VIEWPORT"
                self.background_color = tuple(
                    bpy.context.space_data.shading.background_color
                )
                bpy.context.space_data.shading.background_color = (0.0, 0.0, 0.0)

                bpy.ops.screen.screen_full_area()
                Override, area3D, space3D = CtxOverride(context)
                bpy.ops.screen.region_toggle(Override, region_type="UI")
                bpy.ops.object.select_all(action='DESELECT')
#                bpy.ops.object.select_all(Override, action="DESELECT")
                context.window_manager.modal_handler_add(self)

                return {"RUNNING_MODAL"}

            else:

                self.report({"WARNING"}, "Active space must be a View3d")

                return {"CANCELLED"}


############################################################################
class BDENTAL_OT_OcclusalPlaneInfo(bpy.types.Operator):
    """ Add Align Refference points """

    bl_idname = "bdental.occlusalplaneinfo"
    bl_label = "INFO"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        message = [
            "\u2588 Deselect all objects,",
            "\u2588 Select the target Object,",
            "\u2588 Click < OCCLUSAL PLANE > button,",
            f"      Press <Left Click> to Place Cursor,",
            f"      <'R'> to Add Right Point,",
            f"      <'A'> to Add Anterior median Point,",
            f"      <'L'> to Add Left Point,",
            f"      Press <'DEL'> to delete Point,",
            f"      Press <'ESC'> to Cancel Operation,",
            f"      Press <'ENTER'> to Add Occlusal Plane.",
        ]
        ShowMessageBox(message=message, title="INFO", icon="INFO")

        return {"FINISHED"}

#######################################################################################
# Decimate model operator :


class BDENTAL_OT_decimate(bpy.types.Operator):
    """ Decimate to ratio """ 

    bl_idname = "bdental.decimate"
    bl_label = "Decimate Model"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        BDENTAL_Props = context.scene.BDENTAL_Props
        decimate_ratio = round(BDENTAL_Props.decimate_ratio, 2)

        ActiveObj = context.active_object
        condition = (ActiveObj and ActiveObj.type == 'MESH' and ActiveObj in bpy.context.selected_objects )

        if not condition :

            message = [" Please select the target object !"]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")

            return {"CANCELLED"}
        else:

            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.ops.object.modifier_add(type="DECIMATE")
            bpy.context.object.modifiers["Decimate"].ratio = decimate_ratio
            bpy.ops.object.modifier_apply(modifier="Decimate")

            return {"FINISHED"}


#######################################################################################
# Fill holes operator :


class BDENTAL_OT_fill(bpy.types.Operator):
    """fill edge or face """

    bl_idname = "bdental.fill"
    bl_label = "FILL"
    bl_options = {"REGISTER", "UNDO"}

    Fill_treshold : IntProperty(
        name="Hole Fill Treshold",
        description="Hole Fill Treshold",
        default=400,
    )

    def execute(self, context):

        Mode = self.ActiveObj.mode
        
        if not Mode == "EDIT":
            bpy.ops.object.mode_set(mode="EDIT")

        bpy.ops.mesh.edge_face_add()
        bpy.ops.mesh.subdivide(number_cuts=10)
        bpy.ops.mesh.subdivide(number_cuts=2)
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.select_non_manifold()
        bpy.ops.mesh.remove_doubles(threshold=0.1)

        bpy.ops.mesh.looptools_relax(
            input="selected",
            interpolation="cubic",
            iterations="3",
            regular=True,
        )
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.fill_holes(sides=self.Fill_treshold)
        bpy.ops.mesh.quads_convert_to_tris(
            quad_method="BEAUTY", ngon_method="BEAUTY"
        )
        bpy.ops.mesh.select_all(action="DESELECT")

        bpy.ops.object.mode_set(mode=Mode)

        return {"FINISHED"}

    def invoke(self, context, event):
        self.ActiveObj = context.active_object
        condition = (self.ActiveObj and self.ActiveObj.type == 'MESH' and self.ActiveObj in bpy.context.selected_objects )

        if not condition :

            message = [" Please select the target object !"]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")

            return {"CANCELLED"}

        else :
            wm = context.window_manager
            return wm.invoke_props_dialog(self)

#######################################################################################
# Retopo smooth operator :


class BDENTAL_OT_retopo_smooth(bpy.types.Operator):
    """Retopo sculpt for filled holes"""

    bl_idname = "bdental.retopo_smooth"
    bl_label = "Retopo Smooth"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        ActiveObj = context.active_object
        condition = (ActiveObj and ActiveObj.type == 'MESH' and ActiveObj in bpy.context.selected_objects )

        if not condition :

            message = [" Please select the target object !"]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")

            return {"CANCELLED"}

        else:

            # Prepare scene settings :
            bpy.context.tool_settings.mesh_select_mode = (True, False, False)

            bpy.ops.object.mode_set(mode="SCULPT")

            Model = bpy.context.view_layer.objects.active

            bpy.context.scene.tool_settings.sculpt.use_symmetry_x = False
            bpy.context.scene.tool_settings.unified_paint_settings.size = 50

            bpy.ops.wm.tool_set_by_id(name="builtin_brush.Simplify")
            bpy.data.brushes["Simplify"].cursor_color_add = (0.3, 0.0, 0.7, 0.4)
            bpy.data.brushes["Simplify"].strength = 0.5
            bpy.data.brushes["Simplify"].auto_smooth_factor = 0.5
            bpy.data.brushes["Simplify"].use_automasking_topology = True
            bpy.data.brushes["Simplify"].use_frontface = True

            if Model.use_dynamic_topology_sculpting == False:
                bpy.ops.sculpt.dynamic_topology_toggle()

            bpy.context.scene.tool_settings.sculpt.detail_type_method = "CONSTANT"
            bpy.context.scene.tool_settings.sculpt.constant_detail_resolution = 16
            bpy.ops.sculpt.sample_detail_size(mode="DYNTOPO")

            return {"FINISHED"}


#######################################################################################
# clean model operator :
class BDENTAL_OT_clean_mesh(bpy.types.Operator):
    """ Fill small and medium holes and remove small parts"""

    bl_idname = "bdental.clean_mesh"
    bl_label = "CLEAN MESH"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ####### Get model to clean #######
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="MEDIAN")
        Model = bpy.context.view_layer.objects.active
        self.Model_name = Model.name
        bpy.ops.object.select_all(action="DESELECT")
        Model.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.context.tool_settings.mesh_select_mode = (True, False, False)

        ####### Fill Holes #######

        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.select_non_manifold()
        bpy.ops.mesh.fill_holes(sides=100)
        bpy.ops.mesh.quads_convert_to_tris(
            quad_method="BEAUTY", ngon_method="BEAUTY"
        )

        ############ clean non_manifold borders ##############
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.select_non_manifold()
        bpy.ops.mesh.select_more()
        bpy.ops.mesh.select_less()
        bpy.ops.mesh.delete(type="FACE")

        bpy.ops.mesh.select_non_manifold()
        bpy.ops.mesh.select_less()
        bpy.ops.mesh.delete(type="VERT")

        ####### Fill Holes #######

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.select_non_manifold()
        bpy.ops.mesh.fill_holes(sides=10)
        bpy.ops.mesh.quads_convert_to_tris(
            quad_method="BEAUTY", ngon_method="BEAUTY"
        )
        ####### Relax borders #######
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.select_non_manifold()
        bpy.ops.mesh.remove_doubles(threshold=0.1)

        bpy.ops.mesh.looptools_relax(
            input="selected", interpolation="cubic", iterations="3", regular=True
        )

        ####### Make mesh consistent (face normals) #######

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        obj = bpy.data.objects.get(self.Model_name)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        print("Clean Mesh finished.")

        return {"FINISHED"}


#######################################################################################
###################################### Cutters ########################################
#######################################################################################
# CurveCutter_01
class BDENTAL_OT_CurveCutterAdd(bpy.types.Operator):
    """ description of this Operator """

    bl_idname = "bdental.curvecutteradd"
    bl_label = "CURVE CUTTER ADD"
    bl_options = {"REGISTER", "UNDO"}

    def modal(self, context, event):

        if not event.type in {
            "DEL",
            "LEFTMOUSE",
            "RET",
            "ESC",
        }:
            # allow navigation

            return {"PASS_THROUGH"}

        elif event.type == ("DEL"):
            if event.value == ("PRESS"):

                DeleteLastCurvePoint()

            return {"RUNNING_MODAL"}

        elif event.type == ("LEFTMOUSE"):

            if event.value == ("PRESS"):

                return {"PASS_THROUGH"}

            if event.value == ("RELEASE"):

                ExtrudeCurvePointToCursor(context, event)

        elif event.type == "RET":

            if event.value == ("PRESS"):
                CurveCutterName = bpy.context.scene.BDENTAL_Props.CurveCutterNameProp
                CurveCutter = bpy.data.objects[CurveCutterName]
                CurveCutter.select_set(True)
                bpy.context.view_layer.objects.active = CurveCutter

                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.curve.cyclic_toggle()

                bpy.ops.object.mode_set(mode="OBJECT")

                # bpy.ops.object.modifier_apply(apply_as="DATA", modifier="Shrinkwrap")

                bpy.context.object.data.bevel_depth = 0
                bpy.context.object.data.extrude = 1.5
                bpy.context.object.data.offset = 0

                bpy.ops.wm.tool_set_by_id(name="builtin.select")
                bpy.context.scene.tool_settings.use_snap = False
                bpy.context.space_data.overlay.show_outline_selected = True

                return {"FINISHED"}

        elif event.type == ("ESC"):

            if event.value == ("PRESS"):

                CurveCutterName = bpy.context.scene.BDENTAL_Props.CurveCutterNameProp
                CurveCutter = bpy.data.objects[CurveCutterName]
                bpy.ops.object.mode_set(mode="OBJECT")

                bpy.ops.object.select_all(action="DESELECT")
                CurveCutter.select_set(True)
                bpy.context.view_layer.objects.active = CurveCutter
                bpy.ops.object.delete(use_global=False, confirm=False)

                CuttingTargetName = context.scene.BDENTAL_Props.CuttingTargetNameProp
                CuttingTarget = bpy.data.objects[CuttingTargetName]

                bpy.ops.object.select_all(action="DESELECT")
                CuttingTarget.select_set(True)
                bpy.context.view_layer.objects.active = CuttingTarget

                bpy.ops.wm.tool_set_by_id(name="builtin.select")
                bpy.context.scene.tool_settings.use_snap = False
                bpy.context.space_data.overlay.show_outline_selected = True

                return {"CANCELLED"}

        return {"RUNNING_MODAL"}

    def invoke(self, context, event):

        if bpy.context.selected_objects == []:

            message = [" Please select the target object !"]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")

            return {"CANCELLED"}

        else:

            if context.space_data.type == "VIEW_3D":

                # Assign Model name to CuttingTarget property :
                CuttingTarget = bpy.context.view_layer.objects.active
                bpy.context.scene.BDENTAL_Props.CuttingTargetNameProp = CuttingTarget.name

                bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.hide_view_clear()
                bpy.ops.object.select_all(action="DESELECT")

                # for obj in bpy.data.objects:
                #     if "CuttingCurve" in obj.name:
                #         obj.select_set(True)
                #         bpy.ops.object.delete(use_global=False, confirm=False)

                bpy.ops.object.select_all(action="DESELECT")
                CuttingTarget.select_set(True)
                bpy.context.view_layer.objects.active = CuttingTarget
                # Hide everything but model :
                bpy.ops.object.hide_view_set(unselected=True)

                CuttingCurveAdd()

                context.window_manager.modal_handler_add(self)

                return {"RUNNING_MODAL"}

            else:

                self.report({"WARNING"}, "Active space must be a View3d")

                return {"CANCELLED"}


class BDENTAL_OT_CurveCutterCut(bpy.types.Operator):
    " Performe Curve Cutting Operation"

    bl_idname = "bdental.curvecuttercut"
    bl_label = "CURVE CUTTER CUT"

    def execute(self, context):

        # Get CuttingTarget :
        CuttingTargetName = bpy.context.scene.BDENTAL_Props.CuttingTargetNameProp
        CuttingTarget = bpy.data.objects[CuttingTargetName]

        # Get CurveCutter :
        CurveCutterName = bpy.context.scene.BDENTAL_Props.CurveCutterNameProp
        CurveCutter = bpy.data.objects[CurveCutterName]

        bpy.context.tool_settings.mesh_select_mode = (True, False, False)
        bpy.context.scene.tool_settings.use_snap = False
        bpy.ops.view3d.snap_cursor_to_center()

        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        CurveCutter.select_set(True)
        bpy.context.view_layer.objects.active = CurveCutter
        # remove material :
        for mat_slot in CurveCutter.material_slots:
            bpy.ops.object.material_slot_remove()

        # Change CurveCutter setting   :
        bpy.context.object.data.bevel_depth = 0
        bpy.context.object.data.offset = 0

        # subdivide curve points :
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.curve.select_all(action="SELECT")
        bpy.ops.curve.subdivide()

        # convert CurveCutter to mesh :
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.convert(target="MESH")

        # Make vertex group :
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_mode(type="VERT")
        bpy.ops.mesh.select_all(action="SELECT")
        curve_vgroup = CurveCutter.vertex_groups.new(name="curve_vgroup")
        bpy.ops.object.vertex_group_assign()
        bpy.ops.object.mode_set(mode="OBJECT")

        # select CuttingTarget :
        bpy.ops.object.select_all(action="DESELECT")
        CuttingTarget.select_set(True)
        bpy.context.view_layer.objects.active = CuttingTarget

        # delete old vertex groups :
        CuttingTarget.vertex_groups.clear()

        # deselect all vertices :
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_mode(type="VERT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")

        # Join CurveCutter to CuttingTarget :
        CurveCutter.select_set(True)
        bpy.ops.object.join()
        bpy.ops.object.hide_view_set(unselected=True)

        # intersect make vertex group :
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_mode(type="VERT")
        bpy.ops.mesh.intersect()

        intersect_vgroup = CuttingTarget.vertex_groups.new(name="intersect_vgroup")
        CuttingTarget.vertex_groups.active_index = intersect_vgroup.index
        bpy.ops.object.vertex_group_assign()

        # OtherObjList = [obj for obj in bpy.data.objects if obj!= CuttingTarget]
        # hide all but object
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.hide_view_set(unselected=True)

        # delete curve_vgroup :
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        curve_vgroup = CuttingTarget.vertex_groups["curve_vgroup"]

        CuttingTarget.vertex_groups.active_index = curve_vgroup.index
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.delete(type="FACE")

        bpy.ops.ed.undo_push()       
        # 1st methode :
        SplitSeparator(CuttingTarget=CuttingTarget)
        for obj in bpy.context.visible_objects:
            obj.vertex_groups.clear()

        print("Cutting done with first method")

        # Filtring loose parts :
        # resulting_parts = PartsFilter()
        
        

        # if resulting_parts > 1:
        #     for obj in bpy.context.visible_objects:
        #         obj.vertex_groups.clear()

        #     print("Cutting done with first method")

        # else:
        #     pass
            # # bpy.ops.ed.undo()
            # # Get CuttingTarget :
            # CuttingTargetName = bpy.context.scene.BDENTAL_Props.CuttingTargetNameProp
            # CuttingTarget = bpy.data.objects[CuttingTargetName]
            # CuttingTarget.select_set(True)
            # bpy.context.view_layer.objects.active = CuttingTarget

            # bol = True

            # while bol:
            #     bol = IterateSeparator()

            # # Filtring loose parts :
            # resulting_parts = PartsFilter()
            # print("Cutting done with second method")

            # bpy.ops.object.select_all(action="DESELECT")
            # ob = bpy.context.visible_objects[-1]
            # ob.select_set(True)
            # bpy.context.view_layer.objects.active = ob
            # bpy.ops.wm.tool_set_by_id(name="builtin.select")

        return {"FINISHED"}


#######################################################################################
# CurveCutter_02
class BDENTAL_OT_CurveCutterAdd2(bpy.types.Operator):
    """ description of this Operator """

    bl_idname = "bdental.curvecutteradd2"
    bl_label = "CURVE CUTTER ADD"
    bl_options = {"REGISTER", "UNDO"}

    def modal(self, context, event):

        if not event.type in {
            "DEL",
            "LEFTMOUSE",
            "RET",
            "ESC",
        }:
            # allow navigation

            return {"PASS_THROUGH"}

        elif event.type == ("DEL"):
            if event.value == ("PRESS"):

                DeleteLastCurvePoint()

            return {"RUNNING_MODAL"}

        elif event.type == ("LEFTMOUSE"):

            if event.value == ("PRESS"):

                return {"PASS_THROUGH"}

            if event.value == ("RELEASE"):

                ExtrudeCurvePointToCursor(context, event)

        elif event.type == "RET":

            if event.value == ("PRESS"):
                CurveCutterName = bpy.context.scene.BDENTAL_Props.CurveCutterNameProp
                CurveCutter = bpy.data.objects[CurveCutterName]
                CurveCutter.select_set(True)
                bpy.context.view_layer.objects.active = CurveCutter

                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.curve.cyclic_toggle()

                bpy.ops.object.mode_set(mode="OBJECT")

                # bpy.ops.object.modifier_apply(apply_as="DATA", modifier="Shrinkwrap")

                bpy.ops.wm.tool_set_by_id(name="builtin.select")
                bpy.context.scene.tool_settings.use_snap = False
                bpy.context.space_data.overlay.show_outline_selected = True

                return {"FINISHED"}

        elif event.type == ("ESC"):

            if event.value == ("PRESS"):

                CurveCutterName = bpy.context.scene.BDENTAL_Props.CurveCutterNameProp
                CurveCutter = bpy.data.objects[CurveCutterName]
                bpy.ops.object.mode_set(mode="OBJECT")

                bpy.ops.object.select_all(action="DESELECT")
                CurveCutter.select_set(True)
                bpy.context.view_layer.objects.active = CurveCutter
                bpy.ops.object.delete(use_global=False, confirm=False)

                CuttingTargetName = context.scene.BDENTAL_Props.CuttingTargetNameProp
                CuttingTarget = bpy.data.objects[CuttingTargetName]

                bpy.ops.object.select_all(action="DESELECT")
                CuttingTarget.select_set(True)
                bpy.context.view_layer.objects.active = CuttingTarget

                bpy.ops.wm.tool_set_by_id(name="builtin.select")
                bpy.context.scene.tool_settings.use_snap = False
                bpy.context.space_data.overlay.show_outline_selected = True

                return {"CANCELLED"}

        return {"RUNNING_MODAL"}

    def invoke(self, context, event):

        if bpy.context.selected_objects == []:

            message = [" Please select the target object !"]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")

            return {"CANCELLED"}

        else:

            if context.space_data.type == "VIEW_3D":

                # Assign Model name to CuttingTarget property :
                CuttingTarget = bpy.context.view_layer.objects.active
                bpy.context.scene.BDENTAL_Props.CuttingTargetNameProp = CuttingTarget.name

                bpy.ops.object.mode_set(mode="OBJECT")
                bpy.ops.object.hide_view_clear()
                bpy.ops.object.select_all(action="DESELECT")

                # for obj in bpy.data.objects:
                #     if "CuttingCurve" in obj.name:
                #         obj.select_set(True)
                #         bpy.ops.object.delete(use_global=False, confirm=False)

                bpy.ops.object.select_all(action="DESELECT")
                CuttingTarget.select_set(True)
                bpy.context.view_layer.objects.active = CuttingTarget
                # Hide everything but model :
                bpy.ops.object.hide_view_set(unselected=True)

                CuttingCurveAdd()
                bpy.context.object.data.bevel_depth = 0.1
                bpy.context.object.data.extrude = 0
                bpy.context.object.data.offset = 0

                context.window_manager.modal_handler_add(self)

                return {"RUNNING_MODAL"}

            else:

                self.report({"WARNING"}, "Active space must be a View3d")

                return {"CANCELLED"}


class BDENTAL_OT_CurveCutter2_ShortPath(bpy.types.Operator):
    " Shortpath Curve Cutting tool"

    bl_idname = "bdental.curvecutter2_shortpath"
    bl_label = "ShortPath"

    def execute(self, context):

        
        t0 = Tcounter()
        ###########################################################################
        # Get CuttingTarget :
        CuttingTargetName = bpy.context.scene.BDENTAL_Props.CuttingTargetNameProp
        CuttingTarget = bpy.data.objects[CuttingTargetName]

        # Get CurveCutter :
        CurveCutterName = bpy.context.scene.BDENTAL_Props.CurveCutterNameProp
        CurveCutter = bpy.data.objects[CurveCutterName]

        if bpy.context.mode != 'OBJECT' :
            bpy.ops.object.mode_set(mode="OBJECT")

        bpy.ops.object.select_all(action="DESELECT")
        CurveCutter.select_set(True)
        bpy.context.view_layer.objects.active = CurveCutter

        # subdivide curve points :
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.curve.select_all(action="SELECT")
        bpy.ops.curve.subdivide()
        bpy.ops.object.mode_set(mode="OBJECT")

        bpy.ops.object.select_all(action="DESELECT")
        CuttingTarget.select_set(True)
        bpy.context.view_layer.objects.active = CuttingTarget
        bpy.ops.object.hide_view_set(unselected=True)

        # curve control points coordinates relative to mesh obj local coord :
        CurveCoList = CutterPointsList(CurveCutter, CuttingTarget)
        # list of mesh verts IDs that are closest to curve points :
        Closest_VIDs = [
            ClosestVerts(i, CurveCoList, CuttingTarget)
            for i in range(len(CurveCoList))
        ]

        path = Closest_VIDs.copy()
        path.append(Closest_VIDs[0])
        n = len(Closest_VIDs)
        loop = []

        for i in range(n):

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_mode(type="VERT")
            bpy.ops.mesh.select_all(action="DESELECT")
            bpy.ops.object.mode_set(mode="OBJECT")

            V0 = CuttingTarget.data.vertices[path[i]]
            V1 = CuttingTarget.data.vertices[path[i + 1]]
            V0.select = True
            V1.select = True
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.shortest_path_select()
            bpy.ops.object.mode_set(mode="OBJECT")
            Selected_Verts = [
                v.index
                for v in CuttingTarget.data.vertices
                if v.select and v.index != path[i + 1]
            ]
            loop.extend(Selected_Verts)

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")

        for v_id in loop:
            CuttingTarget.data.vertices[v_id].select = True

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.looptools_relax(
            input="selected", interpolation="cubic", iterations="5", regular=True
        )
        # delete old vertex groups :
        CuttingTarget.vertex_groups.clear()
        intersect_vgroup = CuttingTarget.vertex_groups.new(name="intersect_vgroup")
        bpy.ops.object.vertex_group_assign()

                # 1st methode :
        SplitSeparator(CuttingTarget=CuttingTarget)

        # # Filtring loose parts :
        # resulting_parts = PartsFilter()
        # print(resulting_parts)

        # if resulting_parts > 1:
        #     for obj in bpy.context.visible_objects:
        #         obj.vertex_groups.clear()

        #     print("Cutting done with first method")

        # else:
        
        #     # Get CuttingTarget :
        #     CuttingTargetName = bpy.context.scene.BDENTAL_Props.CuttingTargetNameProp
        #     CuttingTarget = bpy.data.objects[CuttingTargetName]
        #     CuttingTarget.select_set(True)
        #     bpy.context.view_layer.objects.active = CuttingTarget

        #     bol = True

        #     while bol:
        #         bol = IterateSeparator()

        #     # Filtring loose parts :
        #     resulting_parts = PartsFilter()
        #     print("Cutting done with second method")

        #     bpy.ops.object.select_all(action="DESELECT")
        #     ob = bpy.context.visible_objects[-1]
        #     ob.select_set(True)
        #     bpy.context.view_layer.objects.active = ob
        #     bpy.ops.wm.tool_set_by_id(name="builtin.select")

        return {"FINISHED"}

    #     bol = True

    #     while bol:
    #         bol = IterateSeparator()

    #     # Filtring loose parts :
    #     resulting_parts = PartsFilter()
    #     print("Cutting done with second method")

    #     bpy.ops.object.select_all(action="DESELECT")
    #     ob = bpy.context.visible_objects[-1]
    #     ob.select_set(True)
    #     bpy.context.view_layer.objects.active = ob
    #     bpy.ops.wm.tool_set_by_id(name="builtin.select")

    #     t1 = Tcounter()
    #     print(f"FINISHED in {t1-t0} secondes")

    # return {"FINISHED"}

#######################################################################################
# Square cut modal operator :


class BDENTAL_OT_square_cut(bpy.types.Operator):
    """Square Cutting Tool add"""

    bl_idname = "bdental.square_cut"
    bl_label = "Square Cut"
    bl_options = {"REGISTER", "UNDO"}

    def modal(self, context, event):

        if event.type == "RET":
            if event.value == ("PRESS"):

                add_square_cutter(context)

            return {"FINISHED"}

        elif event.type == ("ESC"):

            return {"CANCELLED"}

        else:

            # allow navigation
            return {"PASS_THROUGH"}

        return {"RUNNING_MODAL"}

    def invoke(self, context, event):

        if bpy.context.selected_objects == []:

            message = [" Please select the target object !"]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")

            return {"CANCELLED"}

        else:

            if context.space_data.type == "VIEW_3D":

                CuttingTarget = context.scene.BDENTAL_Props.CuttingTargetNameProp

                # Hide everything but model :

                bpy.ops.object.mode_set(mode="OBJECT")

                Model = bpy.context.view_layer.objects.active
                bpy.ops.object.select_all(action="DESELECT")
                Model.select_set(True)

                CuttingTarget = Model.name

                bpy.ops.object.hide_view_set(unselected=True)

                bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="MEDIAN")
                bpy.context.scene.tool_settings.use_snap = False

                message = [" Please align Model to the Cutting View and click 'ENTER' !"]
                ShowMessageBox(message=message, icon="COLORSET_02_VEC")

                context.window_manager.modal_handler_add(self)

                return {"RUNNING_MODAL"}

            else:

                self.report({"WARNING"}, "Active space must be a View3d")

                return {"CANCELLED"}


#######################################################################################
# Square cut confirm operator :


class BDENTAL_OT_square_cut_confirm(bpy.types.Operator):
    """confirm Square Cut operation"""

    bl_idname = "bdental.square_cut_confirm"
    bl_label = "Tirm"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        if bpy.context.selected_objects == []:

            message = [" Please select the target object !"]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")

            return {"CANCELLED"}

        else:
            try:
                cutting_mode = context.scene.BDENTAL_Props.cutting_mode

                bpy.context.tool_settings.mesh_select_mode = (True, False, False)
                bpy.ops.wm.tool_set_by_id(name="builtin.select")
                bpy.ops.object.mode_set(mode="OBJECT")
                frame = bpy.data.objects["my_frame_cutter"]

                bpy.ops.object.select_all(action="DESELECT")
                frame.select_set(True)
                bpy.context.view_layer.objects.active = frame
                bpy.ops.object.select_all(action="INVERT")
                Model = bpy.context.selected_objects[0]
                bpy.context.view_layer.objects.active = Model

                # Make Model normals consitent :

                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.mesh.select_all(action="SELECT")
                bpy.ops.mesh.normals_make_consistent(inside=False)
                bpy.ops.mesh.fill_holes()
                bpy.ops.mesh.select_all(action="DESELECT")
                bpy.ops.object.mode_set(mode="OBJECT")

                # ....Add undo history point...:
                bpy.ops.ed.undo_push()

                # Add Boolean Modifier :
                bpy.ops.object.select_all(action="DESELECT")
                Model.select_set(True)
                bpy.context.view_layer.objects.active = Model

                bpy.ops.object.modifier_add(type="BOOLEAN")
                bpy.context.object.modifiers["Boolean"].show_viewport = False
                bpy.context.object.modifiers["Boolean"].operation = "DIFFERENCE"
                bpy.context.object.modifiers["Boolean"].object = frame

                # Apply boolean modifier :
                if cutting_mode == "Cut inner":
                    bpy.ops.object.modifier_apply(modifier="Boolean")

                if cutting_mode == "Keep inner":
                    bpy.context.object.modifiers["Boolean"].operation = "INTERSECT"
                    bpy.ops.object.modifier_apply(modifier="Boolean")

                # Delete resulting loose geometry :

                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.mesh.select_all(action="SELECT")
                bpy.ops.mesh.delete_loose()
                bpy.ops.mesh.select_all(action="DESELECT")
                bpy.ops.object.mode_set(mode="OBJECT")

                bpy.ops.object.select_all(action="DESELECT")
                frame.select_set(True)
                bpy.context.view_layer.objects.active = frame

            except Exception:
                pass

            return {"FINISHED"}


#######################################################################################
# Square cut exit operator :


class BDENTAL_OT_square_cut_exit(bpy.types.Operator):
    """Square Cutting Tool Exit"""

    bl_idname = "bdental.square_cut_exit"
    bl_label = "Exit"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        # Delete frame :
        try:

            frame = bpy.data.objects["my_frame_cutter"]
            bpy.ops.object.select_all(action="DESELECT")
            frame.select_set(True)

            bpy.ops.object.select_all(action="INVERT")
            Model = bpy.context.selected_objects[0]

            bpy.ops.object.select_all(action="DESELECT")
            frame.select_set(True)
            bpy.context.view_layer.objects.active = frame

            bpy.ops.object.delete(use_global=False, confirm=False)

            bpy.ops.object.select_all(action="DESELECT")
            Model.select_set(True)
            bpy.context.view_layer.objects.active = Model

        except Exception:
            pass

        return {"FINISHED"}



#################################################################################################
# Registration :
#################################################################################################

classes = [
    BDENTAL_OT_JoinObjects,
    BDENTAL_OT_SeparateObjects,
    BDENTAL_OT_Parent,
    BDENTAL_OT_Unparent,
    BDENTAL_OT_align_to_front,
    BDENTAL_OT_to_center,
    BDENTAL_OT_center_cursor,
    BDENTAL_OT_OcclusalPlane,
    BDENTAL_OT_OcclusalPlaneInfo,
    BDENTAL_OT_decimate,
    BDENTAL_OT_clean_mesh,
    BDENTAL_OT_fill,
    BDENTAL_OT_retopo_smooth,
    BDENTAL_OT_CurveCutterAdd,
    BDENTAL_OT_CurveCutterAdd2,
    BDENTAL_OT_CurveCutterCut,
    BDENTAL_OT_CurveCutter2_ShortPath,
    BDENTAL_OT_square_cut,
    BDENTAL_OT_square_cut_confirm,
    BDENTAL_OT_square_cut_exit,

]


def register():

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


