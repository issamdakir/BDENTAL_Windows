import os, stat, sys, shutil, math, threading
from math import degrees, radians, pi
import numpy as np
from time import sleep, perf_counter as Tcounter
from queue import Queue
from os.path import join, dirname, abspath, exists, split
from importlib import reload  

# Blender Imports :
import bpy
import bmesh
from mathutils import Matrix, Vector, Euler, kdtree
from bpy.props import (
    StringProperty,
    IntProperty,
    FloatProperty,
    EnumProperty,
    FloatVectorProperty,
    BoolProperty,
)
import SimpleITK as sitk
import vtk
import cv2
# try :
#     cv2 = reload(cv2)
# except ImportError :
#     pass
from vtk.util import numpy_support
from vtk import vtkCommand

# Global Variables :

from . import BDENTAL_Utils
from .BDENTAL_Utils import *

addon_dir = dirname(dirname(abspath(__file__)))
ShadersBlendFile = join(
    addon_dir, "Resources", "BlendData", "BDENTAL_BlendData.blend")
GpShader = "VGS_Marcos_modified"  # "VGS_Marcos_01" "VGS_Dakir_01"
Wmin = -400
Wmax = 3000
ProgEvent = vtkCommand.ProgressEvent
#######################################################################################
########################### CT Scan Load : Operators ##############################
#######################################################################################
def rmtree(top):
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            filename = os.path.join(root, name)
            os.chmod(filename, stat.S_IWUSR)
            os.remove(filename)
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)  

# class BDENTAL_OT_Uninstall(bpy.types.Operator):
#     """ Uninstall Addon """

#     bl_idname = "bdental.uninstall"
#     bl_label = "UNINSTALL"

#     def execute(self, context):

#         # Disable Addon :
#         Addon_Enable(AddonName='BDENTAL', Enable=False)
#         try :
#             shutil.rmtree(addon_dir)
#             print('BDENTAL Addon uninstalled successfully.(shutil)')
#         except Exception as Er :
#             print(Er)
#             if sys.platform == 'win32':
#                 try :
#                     rmtree(addon_dir)
#                     if not exists(addon_dir):
#                         print('BDENTAL Addon uninstalled successfully.(rmtree)')
#                     else :
#                         print('BDENTAL Addon could not be uninstalled ! (Folder still exists wthout error)')
#                 except Exception as Er :
#                     print(f'BDENTAL Addon could not be uninstalled ! Error : {Er}')

#                 # try :
#                 #     os.chmod(addon_dir,stat.S_IWUSR)
#                 #     # os.chmod(addon_dir,stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
#                 #     shutil.rmtree(addon_dir)
#                 #     if not exists(addon_dir):
#                 #         print('BDENTAL Addon uninstalled successfully.(os.chmod)')
#                 #     else :
#                 #         print('BDENTAL Addon could not be uninstalled !')
#                 # except Exception as Er :
#                 #     print(Er)
#                 #     print('BDENTAL Addon could not be uninstalled !')
            
                
#         return {"FINISHED"}


def GetMaxSerie(UserDcmDir):

    SeriesDict = {}
    Series_reader = sitk.ImageSeriesReader()
    series_IDs = Series_reader.GetGDCMSeriesIDs(UserDcmDir)

    if not series_IDs:
        
        message = ["No valid DICOM Serie found in DICOM Folder ! "]
        print(message)
        ShowMessageBox(message=message, icon="COLORSET_01_VEC")
        return {"CANCELLED"}

    def GetSerieCount(sID):
        count = len(Series_reader.GetGDCMSeriesFileNames(UserDcmDir, sID))
        SeriesDict[count] = sID

    threads = [
        threading.Thread(
            target=GetSerieCount,
            args=[sID],
            daemon=True,
        )
        for sID in series_IDs
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()
    MaxCount = sorted(SeriesDict, reverse=True)[0]
    MaxSerie = SeriesDict[MaxCount]
    return MaxSerie, MaxCount

def Load_Dicom_funtion(context, q):

    ################################################################################################
    start = Tcounter()
    ################################################################################################
    BDENTAL_Props = context.scene.BDENTAL_Props
    UserProjectDir = AbsPath(BDENTAL_Props.UserProjectDir)
    UserDcmDir = AbsPath(BDENTAL_Props.UserDcmDir)

    ################################################################################################

    if not exists(UserProjectDir):

        message = ["The Selected Project Directory Path is not valid ! "]
        ShowMessageBox(message=message, icon="COLORSET_02_VEC")
        return {"CANCELLED"}

    elif not exists(UserDcmDir):

        message = [" The Selected Dicom Directory Path is not valid ! "]
        ShowMessageBox(message=message, icon="COLORSET_02_VEC")
        return {"CANCELLED"}

    elif not os.listdir(UserDcmDir):
        message = ["No valid DICOM Serie found in DICOM Folder ! "]
        ShowMessageBox(message=message, icon="COLORSET_02_VEC")
        return {"CANCELLED"}

    else:
        # Get Preffix and save file :
        DcmInfoDict = eval(BDENTAL_Props.DcmInfo)
        Preffixs = list(DcmInfoDict.keys())

        for i in range(1,100) :
            Preffix = f"BD{i:03}"
            if not Preffix in Preffixs :
                break
        
        Split = split(UserProjectDir)
        ProjectName = (Split[-1] or Split[-2])
        BlendFile = f"{ProjectName}_CT-SCAN.blend"
        Blendpath = join(UserProjectDir, BlendFile)
        
        if not exists(Blendpath) or bpy.context.blend_data.filepath == Blendpath:
            bpy.ops.wm.save_as_mainfile(filepath=Blendpath)
        else :
            bpy.ops.wm.save_mainfile()

        # Start Reading Dicom data :
        ######################################################################################
        Series_reader = sitk.ImageSeriesReader()
        MaxSerie, MaxCount = GetMaxSerie(UserDcmDir)
        DcmSerie = Series_reader.GetGDCMSeriesFileNames(UserDcmDir, MaxSerie)

        ##################################### debug_02 ###################################
        debug_01 = Tcounter()
        message = f"MaxSerie ID : {MaxSerie}, MaxSerie Count : {MaxCount} (Time : {round(debug_01-start,2)} secondes)"
        print(message)
        # q.put("Max DcmSerie extracted...")
        ####################################################################################

        # Get StudyInfo :
        reader = sitk.ImageFileReader()
        reader.SetFileName(DcmSerie[0])
        reader.LoadPrivateTagsOn()
        reader.ReadImageInformation()

        Image3D = sitk.ReadImage(DcmSerie)

        # Get Dicom Info :
        Sp = Spacing = Image3D.GetSpacing()
        Sz = Size = Image3D.GetSize()
        Dims = Dimensions = Image3D.GetDimension()
        Origin = Image3D.GetOrigin()
        Direction = Image3D.GetDirection()

        # calculate Informations :
        D = Direction
        O = Origin
        DirectionMatrix_4x4 = Matrix(
            (
                (D[0], D[1], D[2], 0.0),
                (D[3], D[4], D[5], 0.0),
                (D[6], D[7], D[8], 0.0),
                (0.0, 0.0, 0.0, 1.0),
            )
        )

        TransMatrix_4x4 = Matrix(
            (
                (1.0, 0.0, 0.0, O[0]),
                (0.0, 1.0, 0.0, O[1]),
                (0.0, 0.0, 1.0, O[2]),
                (0.0, 0.0, 0.0, 1.0),
            )
        )

        VtkTransform_4x4 = TransMatrix_4x4 @ DirectionMatrix_4x4
        P0 = Image3D.TransformContinuousIndexToPhysicalPoint((0, 0, 0))
        P_diagonal = Image3D.TransformContinuousIndexToPhysicalPoint(
            (Sz[0] - 1, Sz[1] - 1, Sz[2] - 1)
        )
        VCenter = (Vector(P0) + Vector(P_diagonal)) * 0.5

        C = VCenter

        TransformMatrix = Matrix(
            (
                (D[0], D[1], D[2], C[0]),
                (D[3], D[4], D[5], C[1]),
                (D[6], D[7], D[8], C[2]),
                (0.0, 0.0, 0.0, 1.0),
            )
        )

        # Set DcmInfo :

        DcmInfo = {
                "UserProjectDir":RelPath(UserProjectDir),
                "Preffix":Preffix,
                "RenderSz":Sz,
                "RenderSp":Sp,
                "PixelType": Image3D.GetPixelIDTypeAsString(),
                "Wmin": Wmin,
                "Wmax": Wmax,
                "Size": Sz,
                "Dims": Dims,
                "Spacing": Sp,
                "Origin": Origin,
                "Direction": Direction,
                "TransformMatrix": TransformMatrix,
                "DirectionMatrix_4x4": DirectionMatrix_4x4,
                "TransMatrix_4x4": TransMatrix_4x4,
                "VtkTransform_4x4": VtkTransform_4x4,
                "VolumeCenter": VCenter}

        tags = {
            "StudyDate": "0008|0020",
            "PatientName": "0010|0010",
            "PatientID": "0010|0020",
            "BirthDate": "0010|0030",
            "WinCenter": "0028|1050",
            "WinWidth": "0028|1051",
        }
        for k, tag in tags.items():

            if tag in reader.GetMetaDataKeys():
                v = reader.GetMetaData(tag)
                
            else:
                v = ""

            DcmInfo[k] = v
            Image3D.SetMetaData(tag, v)

        ###################################### debug_02 ##################################
        debug_02 = Tcounter()
        message = f"DcmInfo {Preffix} set (Time : {debug_02-debug_01} secondes)"
        print(message)
        # q.put("Dicom Info extracted...")
        ##################################################################################

        #######################################################################################
        # Add directories :
        SlicesDir = join(UserProjectDir, "Slices")
        if not exists(SlicesDir):
            os.makedirs(SlicesDir)
        DcmInfo["SlicesDir"] = RelPath(SlicesDir)

        PngDir = join(UserProjectDir, "PNG")
        if not exists(PngDir):
            os.makedirs(PngDir)

        Nrrd255Path = join(UserProjectDir, f"{Preffix}_Image3D255.nrrd")
       
        DcmInfo["Nrrd255Path"] = RelPath(Nrrd255Path)

        #######################################################################################
        # set IntensityWindowing  :
        Image3D_255 = sitk.Cast(
            sitk.IntensityWindowing(
                Image3D,
                windowMinimum=Wmin,
                windowMaximum=Wmax,
                outputMinimum=0.0,
                outputMaximum=255.0,
            ),
            sitk.sitkUInt8,
        )

        # Convert Dicom to nrrd file :
        # sitk.WriteImage(Image3D, NrrdHuPath)
        sitk.WriteImage(Image3D_255, Nrrd255Path)

        ################################## debug_03 ######################################
        debug_03 = Tcounter()
        message = (
            f"Nrrd255 Export done!  (Time : {debug_03-debug_02} secondes)"
        )
        print(message)
        # q.put("nrrd 3D image file saved...")
        ##################################################################################

        #############################################################################################
        # MultiThreading PNG Writer:
        #########################################################################################
        def Image3DToPNG(i, slices, PngDir, Preffix):
            img_Slice = slices[i]
            img_Name = f"{Preffix}_img{i:04}.png"
            image_path = join(PngDir, img_Name)
            cv2.imwrite(image_path, img_Slice)
            image = bpy.data.images.load(image_path)
            image.pack()
            # print(f"{img_Name} was processed...")

        #########################################################################################
        # Get slices list :
        MaxSp = max(Vector(Sp))
        if MaxSp < 0.25:
            SampleRatio = round(MaxSp / 0.25, 2)
            Image3D_255 = ResizeImage(sitkImage=Image3D_255, Ratio=SampleRatio)
            DcmInfo["RenderSz"] = Image3D_255.GetSize()
            DcmInfo["RenderSp"] = Image3D_255.GetSpacing()
            
        Array = sitk.GetArrayFromImage(Image3D_255)
        slices = [np.flipud(Array[i, :, :]) for i in range(Array.shape[0])]
        # slices = [Image3D_255[:, :, i] for i in range(Image3D_255.GetDepth())]
        
        threads = [
            threading.Thread(
                target=Image3DToPNG,
                args=[i, slices, PngDir, Preffix],
                daemon=True,
            )
            for i in range(len(slices))
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # os.removedirs(PngDir)
        shutil.rmtree(PngDir)
        DcmInfo["CT_Loaded"] = True
        # Set DcmInfo property :
        DcmInfoDict = eval(BDENTAL_Props.DcmInfo)
        DcmInfoDict[Preffix] = DcmInfo
        BDENTAL_Props.DcmInfo = str(DcmInfoDict)
        BDENTAL_Props.UserProjectDir = RelPath(BDENTAL_Props.UserProjectDir)
        bpy.ops.wm.save_mainfile()
        # #################################### debug_04 ####################################
        # debug_04 = Tcounter()
        # message = (
        #     f"PNG images exported (Time : {debug_04-debug_03} secondes)"
        # )
        # print(message)
        # # q.put("PNG images saved...")
        # ##################################################################################
        
        # #################################### debug_05 ####################################
        # debug_05 = Tcounter()
        # message = f"{Preffix}_CT-SCAN.blend saved (Time = {debug_05-debug_04} secondes)"
        # print(message)
        # q.put("Blender project saved...")
        ##################################################################################

        #############################################################################################
        finish = Tcounter()
        message = f"Data Loaded in {finish-start} secondes"
        print(message)
        # q.put(message)
        #############################################################################################
        message = ["DICOM loaded successfully. "]
        ShowMessageBox(message=message, icon="COLORSET_03_VEC")

        return DcmInfo
    ####### End Load_Dicom_fuction ##############



#######################################################################################
# BDENTAL CT Scan 3DImage File Load :

def Load_3DImage_function(context,q):

    BDENTAL_Props = context.scene.BDENTAL_Props
    UserProjectDir = AbsPath(BDENTAL_Props.UserProjectDir)
    UserImageFile = AbsPath(BDENTAL_Props.UserImageFile)

    #######################################################################################

    if not exists(UserProjectDir):

        message = ["The Selected Project Directory Path is not valid ! "]
        ShowMessageBox(message=message, icon="COLORSET_02_VEC")
        return {"CANCELLED"}

    if not exists(UserImageFile):
        message = [" The Selected Image File Path is not valid ! "]
        
        ShowMessageBox(message=message, icon="COLORSET_02_VEC")
        return {"CANCELLED"}

    reader = sitk.ImageFileReader()
    IO = reader.GetImageIOFromFileName(UserImageFile)
    FileExt = os.path.splitext(UserImageFile)[1]

    if not IO:
        message = [f"{FileExt} files are not Supported! for more info about supported files please refer to Addon wiki "]
        ShowMessageBox(message=message, icon="COLORSET_01_VEC")
        return {"CANCELLED"}

    Image3D = sitk.ReadImage(UserImageFile)
    Depth = Image3D.GetDepth()

    if Depth == 0:
        message = ["Can't Build 3D Volume from 2D Image !", "for more info about supported files,", "please refer to Addon wiki"]
        ShowMessageBox(message=message, icon="COLORSET_01_VEC")
        return {"CANCELLED"}

    ImgFileName = os.path.split(UserImageFile)[1]
    BDENTAL_nrrd = HU_Image = False
    if ImgFileName.startswith("BD") and ImgFileName.endswith("_Image3D255.nrrd") :
        BDENTAL_nrrd = True
    if Image3D.GetPixelIDTypeAsString() in [
        "32-bit signed integer",
        "16-bit signed integer"]:
        HU_Image = True

    if not BDENTAL_nrrd and not HU_Image :
        message = ["Only Images with Hunsfield data or BDENTAL nrrd images are supported !"]
        ShowMessageBox(message=message, icon="COLORSET_01_VEC")
        return {"CANCELLED"}
    ###########################################################################################################

    else:

        start = Tcounter()
        ####################################
        # Get Preffix and save file :
        DcmInfoDict = eval(BDENTAL_Props.DcmInfo)
        Preffixs = list(DcmInfoDict.keys())

        for i in range(1,100) :
            Preffix = f"BD{i:03}"
            if not Preffix in Preffixs :
                break
        ########################################################
        Split = split(UserProjectDir)
        ProjectName = (Split[-1] or Split[-2])
        BlendFile = f"{ProjectName}_CT-SCAN.blend"
        Blendpath = join(UserProjectDir, BlendFile)
        
        if not exists(Blendpath) or bpy.context.blend_data.filepath == Blendpath:
            bpy.ops.wm.save_as_mainfile(filepath=Blendpath)
        else :
            bpy.ops.wm.save_mainfile()
        Image3D = sitk.ReadImage(UserImageFile)

        # Start Reading Dicom data :
        ######################################################################################
        # Get Dicom Info :
        reader = sitk.ImageFileReader()
        reader.SetFileName(UserImageFile)
        reader.LoadPrivateTagsOn()
        reader.ReadImageInformation()

        Image3D = reader.Execute()

        Sp = Spacing = Image3D.GetSpacing()
        Sz = Size = Image3D.GetSize()
        Dims = Dimensions = Image3D.GetDimension()
        Origin = Image3D.GetOrigin()
        Direction = Image3D.GetDirection()

        # calculate Informations :
        D = Direction
        O = Origin
        DirectionMatrix_4x4 = Matrix(
            (
                (D[0], D[1], D[2], 0.0),
                (D[3], D[4], D[5], 0.0),
                (D[6], D[7], D[8], 0.0),
                (0.0, 0.0, 0.0, 1.0),
            )
        )

        TransMatrix_4x4 = Matrix(
            (
                (1.0, 0.0, 0.0, O[0]),
                (0.0, 1.0, 0.0, O[1]),
                (0.0, 0.0, 1.0, O[2]),
                (0.0, 0.0, 0.0, 1.0),
            )
        )

        VtkTransform_4x4 = TransMatrix_4x4 @ DirectionMatrix_4x4
        P0 = Image3D.TransformContinuousIndexToPhysicalPoint((0, 0, 0))
        P_diagonal = Image3D.TransformContinuousIndexToPhysicalPoint(
            (Sz[0] - 1, Sz[1] - 1, Sz[2] - 1)
        )
        VCenter = (Vector(P0) + Vector(P_diagonal)) * 0.5

        C = VCenter

        TransformMatrix = Matrix(
            (
                (D[0], D[1], D[2], C[0]),
                (D[3], D[4], D[5], C[1]),
                (D[6], D[7], D[8], C[2]),
                (0.0, 0.0, 0.0, 1.0),
            )
        )

        # Set DcmInfo :

        DcmInfo = {
            "UserProjectDir":RelPath(UserProjectDir),
            "Preffix":Preffix,
            "RenderSz":Sz,
            "RenderSp":Sp,
            "PixelType": Image3D.GetPixelIDTypeAsString(),
            "Wmin": Wmin,
            "Wmax": Wmax,
            "Size": Sz,
            "Dims": Dims,
            "Spacing": Sp,
            "Origin": Origin,
            "Direction": Direction,
            "TransformMatrix": TransformMatrix,
            "DirectionMatrix_4x4": DirectionMatrix_4x4,
            "TransMatrix_4x4": TransMatrix_4x4,
            "VtkTransform_4x4": VtkTransform_4x4,
            "VolumeCenter": VCenter}

        tags = {
            "StudyDate": "0008|0020",
            "PatientName": "0010|0010",
            "PatientID": "0010|0020",
            "BirthDate": "0010|0030",
            "WinCenter": "0028|1050",
            "WinWidth": "0028|1051",
        }

        for k, tag in tags.items():

            if tag in reader.GetMetaDataKeys():
                v = reader.GetMetaData(tag)
                
            else:
                v = ""

            DcmInfo[k] = v
            Image3D.SetMetaData(tag, v)

        #######################################################################################
        # Add directories :
        SlicesDir = join(UserProjectDir, "Slices")
        if not exists(SlicesDir):
            os.makedirs(SlicesDir)
        DcmInfo["SlicesDir"] = RelPath(SlicesDir)

        PngDir = join(UserProjectDir, "PNG")
        if not exists(PngDir):
            os.makedirs(PngDir)

        Nrrd255Path = join(UserProjectDir, f"{Preffix}_Image3D255.nrrd")
    
        DcmInfo["Nrrd255Path"] = RelPath(Nrrd255Path)
        
        if BDENTAL_nrrd :
            Image3D_255 = Image3D
            
        else :
        #######################################################################################
            # set IntensityWindowing  :
            Image3D_255 = sitk.Cast(
                sitk.IntensityWindowing(
                    Image3D,
                    windowMinimum=Wmin,
                    windowMaximum=Wmax,
                    outputMinimum=0.0,
                    outputMaximum=255.0,
                ),
                sitk.sitkUInt8,
            )

        # Convert Dicom to nrrd file :
        # sitk.WriteImage(Image3D, NrrdHuPath)
        sitk.WriteImage(Image3D_255, Nrrd255Path)

        #############################################################################################
        # MultiThreading PNG Writer:
        #########################################################################################
        def Image3DToPNG(i, slices, PngDir, Preffix):
            img_Slice = slices[i]
            img_Name = f"{Preffix}_img{i:04}.png"
            image_path = join(PngDir, img_Name)
            cv2.imwrite(image_path, img_Slice)
            image = bpy.data.images.load(image_path)
            image.pack()
            # print(f"{img_Name} was processed...")

        #########################################################################################
        # Get slices list :
        MaxSp = max(Vector(Sp))
        if MaxSp < 0.25:
            SampleRatio = round(MaxSp / 0.25, 2)
            Image3D_255 = ResizeImage(sitkImage=Image3D_255, Ratio=SampleRatio)
            DcmInfo["RenderSz"] = Image3D_255.GetSize()
            DcmInfo["RenderSp"] = Image3D_255.GetSpacing()
        
        Array = sitk.GetArrayFromImage(Image3D_255)
        slices = [np.flipud(Array[i, :, :]) for i in range(Array.shape[0])]
        # slices = [Image3D_255[:, :, i] for i in range(Image3D_255.GetDepth())]
        
        threads = [
            threading.Thread(
                target=Image3DToPNG,
                args=[i, slices, PngDir, Preffix],
                daemon=True,
            )
            for i in range(len(slices))
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # os.removedirs(PngDir)
        shutil.rmtree(PngDir)
        DcmInfo["CT_Loaded"] = True
        
        # Set DcmInfo property :
        DcmInfoDict = eval(BDENTAL_Props.DcmInfo)
        DcmInfoDict[Preffix] = DcmInfo
        BDENTAL_Props.DcmInfo = str(DcmInfoDict)
        BDENTAL_Props.UserProjectDir = RelPath(BDENTAL_Props.UserProjectDir)
        bpy.ops.wm.save_mainfile()

        #############################################################################################
        finish = Tcounter()
        print(f"Data Loaded in {finish-start} second(s)")
        #############################################################################################
        
        return DcmInfo

##########################################################################################
######################### BDENTAL Volume Render : ########################################
##########################################################################################
class BDENTAL_OT_Volume_Render(bpy.types.Operator):
    """ Volume Render """

    bl_idname = "bdental.volume_render"
    bl_label = "LOAD SCAN"

    q = Queue()


    def execute(self, context):

        Start = Tcounter()
        print("Data Loading START...")

        global ShadersBlendFile
        global GpShader

        BDENTAL_Props = context.scene.BDENTAL_Props
        
        DataType = BDENTAL_Props.DataType
        if DataType == "DICOM Series" :
            DcmInfo = Load_Dicom_funtion(context, self.q)
        if DataType == "3D Image File" :
            DcmInfo = Load_3DImage_function(context,self.q)
        
        UserProjectDir = AbsPath(BDENTAL_Props.UserProjectDir)
        Preffix = DcmInfo["Preffix"]
        Wmin = DcmInfo["Wmin"]
        Wmax = DcmInfo["Wmax"]
        # PngDir = AbsPath(BDENTAL_Props.PngDir)
        print("\n##########################\n")
        print("Voxel Rendering START...")
        VolumeRender(DcmInfo, GpShader, ShadersBlendFile)
        scn = bpy.context.scene
        scn.render.engine = "BLENDER_EEVEE"
        BDENTAL_Props.GroupNodeName = GpShader

        if GpShader == "VGS_Marcos_modified":
            GpNode = bpy.data.node_groups.get(f"{Preffix}_{GpShader}")
            Low_Treshold = GpNode.nodes["Low_Treshold"].outputs[0]
            Low_Treshold.default_value = 600
            WminNode = GpNode.nodes["WminNode"].outputs[0]
            WminNode.default_value = Wmin
            WmaxNode = GpNode.nodes["WmaxNode"].outputs[0]
            WmaxNode.default_value = Wmax

            # newdriver = Low_Treshold.driver_add("default_value")
            # newdriver.driver.type = "AVERAGE"
            # var = newdriver.driver.variables.new()
            # var.name = "Treshold"
            # var.type = "SINGLE_PROP"
            # var.targets[0].id_type = "SCENE"
            # var.targets[0].id = bpy.context.scene
            # var.targets[0].data_path = "BDENTAL_Props.Treshold"
            # newdriver.driver.expression = "Treshold"

        if GpShader == "VGS_Dakir_01":
            # Add Treshold Driver :
            GpNode = bpy.data.node_groups.get(f"{Preffix}_{GpShader}")
            value = (600-Wmin)/(Wmax-Wmin) 
            treshramp = GpNode.nodes["TresholdRamp"].color_ramp.elements[0] = value

        
            
            
            # newdriver = treshramp.driver_add("position")
            # newdriver.driver.type = "SCRIPTED"
            # var = newdriver.driver.variables.new()
            # var.name = "Treshold"
            # var.type = "SINGLE_PROP"
            # var.targets[0].id_type = "SCENE"
            # var.targets[0].id = bpy.context.scene
            # var.targets[0].data_path = "BDENTAL_Props.Treshold"
            # newdriver.driver.expression = f"(Treshold-{Wmin})/{Wmax-Wmin}"

        BDENTAL_Props.CT_Rendered = True
        bpy.ops.view3d.view_selected(use_all_regions=False)
        bpy.ops.wm.save_mainfile()

        # post_handlers = bpy.app.handlers.depsgraph_update_post
        # [
        #     post_handlers.remove(h)
        #     for h in post_handlers
        #     if h.__name__ == "BDENTAL_TresholdUpdate"
        # ]
        # post_handlers.append(BDENTAL_TresholdUpdate)


        # bpy.ops.wm.save_mainfile()

        Finish = Tcounter()

        print(f"Finished (Time : {Finish-Start}")

        return {"FINISHED"}

class BDENTAL_OT_TresholdUpdate(bpy.types.Operator):
    """ Add treshold Update Handler  """

    bl_idname = "bdental.tresholdupdate"
    bl_label = "Update Treshold"

    def execute(self, context):    
        post_handlers = bpy.app.handlers.depsgraph_update_post
        [
            post_handlers.remove(h)
            for h in post_handlers
            if h.__name__ == "BDENTAL_TresholdUpdate"
        ]
        post_handlers.append(BDENTAL_TresholdUpdate)

        return {"FINISHED"}
    

##########################################################################################
######################### BDENTAL Add Slices : ########################################
##########################################################################################

class BDENTAL_OT_AddSlices(bpy.types.Operator):
    """ Add Volume Slices """

    bl_idname = "bdental.addslices"
    bl_label = "SLICE VOLUME"

    def execute(self, context):
        BDENTAL_Props = bpy.context.scene.BDENTAL_Props

        Active_Obj = bpy.context.view_layer.objects.active
        
        if not Active_Obj :                
            message = [" Please select CTVOLUME or SEGMENTATION ! "]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")
            return {"CANCELLED"}
        else :
            Conditions = [  
                            not Active_Obj.name.startswith("BD"),
                            not Active_Obj.name.endswith(("_CTVolume", "SEGMENTATION")),
                            Active_Obj.select_get() == False,
                                                                     ]
            if Conditions[0] or Conditions[1] or Conditions[2] :
                message = [" Please select CTVOLUME or SEGMENTATION ! "]
                ShowMessageBox(message=message, icon="COLORSET_02_VEC")
                return {"CANCELLED"}    
            else :
                Vol = Active_Obj
                Preffix = Vol.name[:5]
                DcmInfoDict = eval(BDENTAL_Props.DcmInfo)
                DcmInfo = DcmInfoDict[Preffix]

                # SLICES_Coll = bpy.context.scene.collection.children.get('SLICES')
                # if SLICES_Coll :
                #     SLICES_Coll.hide_viewport = False

                AxialPlane = AddAxialSlice(Preffix, DcmInfo)
                MoveToCollection(obj=AxialPlane, CollName="SLICES")

                CoronalPlane = AddCoronalSlice(Preffix, DcmInfo)
                MoveToCollection(obj=CoronalPlane, CollName="SLICES")

                SagitalPlane = AddSagitalSlice(Preffix, DcmInfo)
                MoveToCollection(obj=SagitalPlane, CollName="SLICES")
                
                # Add Cameras :

                bpy.context.scene.render.resolution_x = 512
                bpy.context.scene.render.resolution_y = 512

                [bpy.data.cameras.remove(cam) for cam in  bpy.data.cameras if f"{AxialPlane.name}_CAM" in cam.name]
                AxialCam = Add_Cam_To_Plane(AxialPlane, CamDistance = 100, ClipOffset=1)
                MoveToCollection(obj=AxialCam, CollName="SLICES-CAMERAS")

                [bpy.data.cameras.remove(cam) for cam in  bpy.data.cameras if f"{CoronalPlane.name}_CAM" in cam.name]
                CoronalCam = Add_Cam_To_Plane(CoronalPlane, CamDistance = 100, ClipOffset=1)
                MoveToCollection(obj=CoronalCam, CollName="SLICES-CAMERAS")


                [bpy.data.cameras.remove(cam) for cam in  bpy.data.cameras if f"{SagitalPlane.name}_CAM" in cam.name]
                SagitalCam = Add_Cam_To_Plane(SagitalPlane, CamDistance = 100, ClipOffset=1)
                MoveToCollection(obj=SagitalCam, CollName="SLICES-CAMERAS")


                for obj in bpy.data.objects :
                    if obj.name == f"{Preffix}_SLICES_POINTER" :
                        bpy.data.objects.remove(obj)

                bpy.ops.object.empty_add(type='PLAIN_AXES', align='WORLD', location=AxialPlane.location, scale=(1, 1, 1))
                SLICES_POINTER = bpy.context.object
                SLICES_POINTER.empty_display_size = 20
                SLICES_POINTER.show_name = True
                SLICES_POINTER.show_in_front = True
                SLICES_POINTER.name = f"{Preffix}_SLICES_POINTER"

                Override, _, _ = CtxOverride(bpy.context)

                bpy.ops.object.select_all(Override,action='DESELECT')
                AxialPlane.select_set(True)
                CoronalPlane.select_set(True)
                SagitalPlane.select_set(True)
                SLICES_POINTER.select_set(True)
                bpy.context.view_layer.objects.active = SLICES_POINTER
                bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
                bpy.ops.object.select_all(Override,action='DESELECT')
                SLICES_POINTER.select_set(True)
                bpy.context.view_layer.objects.active = SLICES_POINTER
                MoveToCollection(obj=SLICES_POINTER, CollName="SLICES_POINTERS")

                return {"FINISHED"}

###############################################################################
####################### BDENTAL VOLUME to Mesh : ################################
##############################################################################
class BDENTAL_OT_TreshSegment(bpy.types.Operator):
    """ Add a mesh Segmentation using Treshold """

    bl_idname = "bdental.tresh_segment"
    bl_label = "SEGMENTATION"

    SegmentName: StringProperty(
        name="Segmentation Name",
        default="TEST",
        description="Segmentation Name",
    )
    SegmentColor: FloatVectorProperty(
        name="Segmentation Color",
        description="Segmentation Color",
        default=[0.44, 0.4, 0.5, 1.0],  # (0.8, 0.46, 0.4, 1.0),
        soft_min=0.0,
        soft_max=1.0,
        size=4,
        subtype="COLOR",
    )

    TimingDict = {}

    def invoke(self, context, event):

        BDENTAL_Props = bpy.context.scene.BDENTAL_Props

        Active_Obj = bpy.context.view_layer.objects.active

        if not Active_Obj :
            message = [" Please select CTVOLUME for segmentation ! "]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")
            return {"CANCELLED"}
        else :
            Conditions = [  
                            not Active_Obj.name.startswith("BD"),
                            not Active_Obj.name.endswith("_CTVolume"),
                            Active_Obj.select_get() == False ]
            
            if Conditions[0] or Conditions[1] or Conditions[2] :                
                message = [" Please select CTVOLUME for segmentation ! "]
                ShowMessageBox(message=message, icon="COLORSET_02_VEC")
                return {"CANCELLED"}
                    
                    
            else :
                self.Vol = Active_Obj
                self.Preffix = self.Vol.name[:5]
                DcmInfoDict = eval(BDENTAL_Props.DcmInfo)
                self.DcmInfo = DcmInfoDict[self.Preffix]
                self.Nrrd255Path = AbsPath(self.DcmInfo["Nrrd255Path"])
                self.Treshold = BDENTAL_Props.Treshold
            
                if exists(self.Nrrd255Path):
                    if GpShader == "VGS_Marcos_modified":
                        GpNode = bpy.data.node_groups.get(f"{self.Preffix}_{GpShader}")
                        ColorPresetRamp = GpNode.nodes["ColorPresetRamp"].color_ramp
                        value = (self.Treshold - Wmin) / (Wmax - Wmin)
                        TreshColor = [
                            round(c, 2) for c in ColorPresetRamp.evaluate(value)[0:3]
                        ]
                        self.SegmentColor = TreshColor + [1.0]
                    self.q = Queue()
                    wm = context.window_manager
                    return wm.invoke_props_dialog(self)

                else:
                    message = [" Image File not Found in Project Folder ! "]
                    ShowMessageBox(message=message, icon="COLORSET_01_VEC")
                    return {"CANCELLED"}

    def DicomToMesh(self):
        counter_start = Tcounter()
        
        self.q.put(["GuessTime", "PROGRESS : Extracting mesh...", "", 0.01, 0.1, 2])
        # Load Infos :
        #########################################################################
        BDENTAL_Props = bpy.context.scene.BDENTAL_Props
        # NrrdHuPath = BDENTAL_Props.NrrdHuPath
        Nrrd255Path = self.Nrrd255Path
        print(Nrrd255Path)
        UserProjectDir = AbsPath(BDENTAL_Props.UserProjectDir)
        DcmInfo = self.DcmInfo
        Origin = DcmInfo["Origin"]
        VtkTransform_4x4 = DcmInfo["VtkTransform_4x4"]
        VtkMatrix = list(np.array(VtkTransform_4x4).ravel())
        Treshold = self.Treshold

        StlPath = join(UserProjectDir, f"{self.SegmentName}_SEGMENTATION.stl")
        Thikness = 1
        # Reduction = 0.9
        SmoothIterations = SmthIter = 5

        ############### step 1 : Reading DICOM #########################
        # self.q.put(["GuessTime", "PROGRESS : Reading DICOM...", "", 0, 0.1, 1])

        Image3D = sitk.ReadImage(Nrrd255Path)
        Sz = Image3D.GetSize()
        Sp = Image3D.GetSpacing()
        MaxSp = max(Vector(Sp))
        if MaxSp < 0.3:
            SampleRatio = round(MaxSp / 0.3, 2)
            ResizedImage = ResizeImage(sitkImage=Image3D, Ratio=SampleRatio)
            Image3D = ResizedImage
            # print(f"Image DOWN Sampled : SampleRatio = {SampleRatio}")

        # Convert Hu treshold value to 0-255 UINT8 :
        Treshold255 = HuTo255(Hu=Treshold, Wmin=Wmin, Wmax=Wmax)
        if Treshold255 == 0:
            Treshold255 = 1
        elif Treshold255 == 255:
            Treshold255 = 254

        step1 = Tcounter()
        self.TimingDict["Read DICOM"] = step1 - counter_start
        # print(f"step 1 : Read DICOM ({step1-start})")

        ############### step 2 : Extracting mesh... #########################
        # self.q.put(["GuessTime", "PROGRESS : Extracting mesh...", "", 0.0, 0.1, 2])

        # print("Extracting mesh...")
        vtkImage = sitkTovtk(sitkImage=Image3D)

        ExtractedMesh = vtk_MC_Func(vtkImage=vtkImage, Treshold=Treshold255)
        Mesh = ExtractedMesh

        polysCount = Mesh.GetNumberOfPolys()
        polysLimit = 800000

        # step1 = Tcounter()
        # print(f"before reduction finished in : {step1-start} secondes")
        step2 = Tcounter()
        self.TimingDict["extract mesh"] = step2 - step1
        # print(f"step 2 : extract mesh ({step2-step1})")
        
        ############### step 3 : mesh Reduction... #########################
        if polysCount > polysLimit:
            # print(f"Hight polygons count, : ({polysCount}) Mesh will be reduced...")
            Reduction = round(1 - (polysLimit / polysCount), 2)
            # print(f"MESH REDUCTION: Ratio = ({Reduction}) ...")
            
            ReductedMesh = vtkMeshReduction(
                q=self.q,
                mesh=Mesh,
                reduction=Reduction,
                step="Mesh Reduction",
                start=0.11,
                finish=0.75,
            )
            Mesh = ReductedMesh
            # print(f"Reduced Mesh polygons count : {Mesh.GetNumberOfPolys()} ...")
            # step2 = Tcounter()
            # print(f"reduction finished in : {step2-step1} secondes")
        # else:
        # print(f"Original mesh polygons count is Optimal : ({polysCount})...")
        step3 = Tcounter()
        self.TimingDict["Reduct mesh"] = step3 - step2
        # print(f"step 3 : Reduct mesh ({step3-step2})")

        ############### step 4 : mesh Smoothing... #########################
        # print("SMOOTHING...")
        SmoothedMesh = vtkSmoothMesh(
            q=self.q,
            mesh=Mesh,
            Iterations=SmthIter,
            step="Mesh Orientation",
            start=0.76,
            finish=0.78,
        )
        step3 = Tcounter()
        # try:
        #     print(f"SMOOTHING finished in : {step3-step2} secondes...")
        # except Exception:
        #     print(f"SMOOTHING finished in : {step3-step1} secondes (no Reduction!)...")
        step4 = Tcounter()
        self.TimingDict["Smooth mesh"] = step4 - step3
        # print(f"step 4 : Smooth mesh ({step4-step3})")

        ############### step 5 : Set mesh orientation... #########################
        # print("SET MESH ORIENTATION...")
        TransformedMesh = vtkTransformMesh(
            mesh=SmoothedMesh,
            Matrix=VtkMatrix,
        )
        step5 = Tcounter()
        self.TimingDict["Mesh Transform"] = step5 - step4
        # print(f"step 5 : set mesh orientation({step5-step4})")

        ############### step 6 : exporting mesh stl... #########################
        self.q.put(
            [
                "GuessTime",
                "PROGRESS : exporting mesh stl...",
                "",
                0.79,
                0.83,
                2,
            ]
        )

        # print("WRITING...")
        writer = vtk.vtkSTLWriter()
        writer.SetInputData(TransformedMesh)
        writer.SetFileTypeToBinary()
        writer.SetFileName(StlPath)
        writer.Write()

        # step4 = Tcounter()
        # print(f"WRITING finished in : {step4-step3} secondes")
        step6 = Tcounter()
        self.TimingDict["Export mesh"] = step6 - step5
        # print(f"step 6 : Export mesh ({step6-step5})")

        ############### step 7 : Importing mesh to Blender... #########################
        self.q.put(["GuessTime", "PROGRESS : Importing mesh...", "", 0.84, 0.97, 8])

        # print("IMPORTING...")
        # import stl to blender scene :
        bpy.ops.import_mesh.stl(filepath=StlPath)
        obj = bpy.context.object
        obj.name = f"{self.Preffix}_{self.SegmentName}_SEGMENTATION"
        obj.data.name = f"{self.Preffix}_{self.SegmentName}_mesh"

        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="MEDIAN")

        step7 = Tcounter()
        self.TimingDict["Import mesh"] = step7 - step6
        # print(f"step 7 : Import mesh({step7-step6})")
        ############### step 8 : Add material... #########################
        self.q.put(["GuessTime", "PROGRESS : Add material...", "", 0.98, 0.99, 1])

        # print("ADD COLOR MATERIAL")
        mat = bpy.data.materials.get(obj.name) or bpy.data.materials.new(obj.name)
        mat.diffuse_color = self.SegmentColor
        obj.data.materials.append(mat)
        MoveToCollection(obj=obj, CollName="SEGMENTS")
        bpy.ops.object.shade_smooth()

        bpy.ops.object.modifier_add(type="CORRECTIVE_SMOOTH")
        bpy.context.object.modifiers["CorrectiveSmooth"].iterations = 3
        bpy.context.object.modifiers["CorrectiveSmooth"].use_only_smooth = True

        # step5 = Tcounter()
        # print(f"Blender importing finished in : {step5-step4} secondes")

        step8 = Tcounter()
        self.TimingDict["Add material"] = step8 - step7
        # print(f"step 8 : Add material({step8-step7})")

        self.q.put(["End"])
        counter_finish = Tcounter()
        self.TimingDict["Total Time"] = counter_finish - counter_start

    def execute(self, context):
        counter_start = Tcounter()
        # TerminalProgressBar = BDENTAL_Utils.TerminalProgressBar
        CV2_progress_bar = BDENTAL_Utils.CV2_progress_bar
        # t1 = threading.Thread(
        #     target=TerminalProgressBar, args=[self.q, counter_start], daemon=True
        # )
        t2 = threading.Thread(
            target=CV2_progress_bar, args=[self.q], daemon=True
        )

        # t1.start()
        t2.start()
        self.DicomToMesh()
        # t1.join()
        t2.join()
        # print("\n")
        # print(self.TimingDict)

        return {"FINISHED"}

class BDENTAL_OT_MultiView(bpy.types.Operator):
    """ MultiView Toggle """

    bl_idname = "bdental.multiview"
    bl_label = "MULTI-VIEW"

    def execute(self, context):

        BDENTAL_Props = bpy.context.scene.BDENTAL_Props

        Active_Obj = bpy.context.view_layer.objects.active
        
        if not Active_Obj :                
            message = [" Please select CTVOLUME or SEGMENTATION ! "]
            ShowMessageBox(message=message, icon="COLORSET_02_VEC")
            return {"CANCELLED"}
        else :
            Conditions = [  
                            not Active_Obj.name.startswith("BD"),
                            not Active_Obj.name.endswith(("_CTVolume", "SEGMENTATION", "_SLICES_POINTER")),
                            Active_Obj.select_get() == False,
                                                                     ]
            if Conditions[0] or Conditions[1] or Conditions[2] :
                message = [" Please select CTVOLUME or SEGMENTATION or _SLICES_POINTER ! "]
                ShowMessageBox(message=message, icon="COLORSET_02_VEC")
                return {"CANCELLED"}    
            else :
                Preffix = Active_Obj.name[:5]
                AxialPlane = bpy.data.objects.get(f"1_{Preffix}_AXIAL_SLICE")
                CoronalPlane = bpy.data.objects.get(f"2_{Preffix}_CORONAL_SLICE")
                SagitalPlane = bpy.data.objects.get(f"3_{Preffix}_SAGITAL_SLICE")
                SLICES_POINTER = bpy.data.objects.get(f"{Preffix}_SLICES_POINTER")

                if not AxialPlane or not CoronalPlane or not SagitalPlane :
                    message = [ "To Add Multi-View Window :",
                                "1 - Please select CTVOLUME or SEGMENTATION",
                                "2 - Click on < SLICE VOLUME > button",
                                "AXIAL, CORONAL and SAGITAL slices will be added",
                                "3 - Click <MULTI-VIEW> button",
                                ]
                    ShowMessageBox(message=message, icon="COLORSET_02_VEC")
                    return {"CANCELLED"}

                else :

                    bpy.context.scene.unit_settings.scale_length = 0.001
                    bpy.context.scene.unit_settings.length_unit = 'MILLIMETERS'
                    
                    MultiView_Window, OUTLINER, PROPERTIES, AXIAL, CORONAL, SAGITAL, VIEW_3D = BDENTAL_MultiView_Toggle(Preffix)
                    MultiView_Screen = MultiView_Window.screen
                    AXIAL_Space3D = [Space for Space in AXIAL.spaces if Space.type == "VIEW_3D"][0]
                    AXIAL_Region = [reg for reg in AXIAL.regions if reg.type == "WINDOW"][0]

                    CORONAL_Space3D = [Space for Space in CORONAL.spaces if Space.type == "VIEW_3D"][0]
                    CORONAL_Region = [reg for reg in CORONAL.regions if reg.type == "WINDOW"][0]

                    SAGITAL_Space3D = [Space for Space in SAGITAL.spaces if Space.type == "VIEW_3D"][0]
                    SAGITAL_Region = [reg for reg in SAGITAL.regions if reg.type == "WINDOW"][0]
                    # AXIAL Cam view toggle :

                    AxialCam = bpy.data.objects.get(f"{AxialPlane.name}_CAM")
                    AXIAL_Space3D.use_local_collections = True
                    AXIAL_Space3D.use_local_camera = True
                    AXIAL_Space3D.camera = AxialCam
                    Override = {"window":MultiView_Window, 'screen':MultiView_Screen, 'area':AXIAL,'space_data':AXIAL_Space3D, 'region':AXIAL_Region}
                    bpy.ops.view3d.view_camera(Override)

                    # CORONAL Cam view toggle :
                    CoronalCam = bpy.data.objects.get(f"{CoronalPlane.name}_CAM")
                    CORONAL_Space3D.use_local_collections = True
                    CORONAL_Space3D.use_local_camera = True
                    CORONAL_Space3D.camera = CoronalCam
                    Override = {"window":MultiView_Window, 'screen':MultiView_Screen, 'area':CORONAL,'space_data':CORONAL_Space3D, 'region':CORONAL_Region}
                    bpy.ops.view3d.view_camera(Override)

                    # AXIAL Cam view toggle :
                    SagitalCam = bpy.data.objects.get(f"{SagitalPlane.name}_CAM")
                    SAGITAL_Space3D.use_local_collections = True
                    SAGITAL_Space3D.use_local_camera = True
                    SAGITAL_Space3D.camera = SagitalCam
                    Override = {"window":MultiView_Window, 'screen':MultiView_Screen, 'area':SAGITAL,'space_data':SAGITAL_Space3D, 'region':SAGITAL_Region}
                    bpy.ops.view3d.view_camera(Override)

                    bpy.ops.object.select_all(Override,action='DESELECT')
                    SLICES_POINTER.select_set(True)
                    bpy.context.view_layer.objects.active = SLICES_POINTER


        return {"FINISHED"}

#################################################################################################
# Registration :
#################################################################################################

classes = [
    BDENTAL_OT_Volume_Render,
    BDENTAL_OT_TresholdUpdate,
    BDENTAL_OT_AddSlices,
    BDENTAL_OT_TreshSegment,
    BDENTAL_OT_MultiView,
]

def register():

    for cls in classes:
        bpy.utils.register_class(cls)
    post_handlers = bpy.app.handlers.depsgraph_update_post
    MyPostHandlers = ["BDENTAL_TresholdUpdate", "AxialSliceUpdate", "CoronalSliceUpdate", "SagitalSliceUpdate"]

    # Remove old handlers : 
    handlers_To_Remove =  [ h for h in post_handlers if h.__name__ in MyPostHandlers ]
    if handlers_To_Remove :
        for h in handlers_To_Remove :
            bpy.app.handlers.depsgraph_update_post.remove(h)

    handlers_To_Add = [BDENTAL_TresholdUpdate, AxialSliceUpdate, CoronalSliceUpdate, SagitalSliceUpdate]
    for h in handlers_To_Add :
        post_handlers.append(h)
    # post_handlers.append(BDENTAL_TresholdUpdate)
    # post_handlers.append(AxialSliceUpdate)
    # post_handlers.append(CoronalSliceUpdate)
    # post_handlers.append(SagitalSliceUpdate)
    
def unregister():

    post_handlers = bpy.app.handlers.depsgraph_update_post
    MyPostHandlers = ["BDENTAL_TresholdUpdate", "AxialSliceUpdate", "CoronalSliceUpdate", "SagitalSliceUpdate"]
    handlers_To_Remove =  [ h for h in post_handlers if h.__name__ in MyPostHandlers ]

    if handlers_To_Remove :
        for h in handlers_To_Remove :
            bpy.app.handlers.depsgraph_update_post.remove(h)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
