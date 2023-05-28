'''This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.'''

import os,sys
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import *

class SAM(QgsProcessingAlgorithm):

    Raster = 'Raster'
    Mask = 'Mask'
    Polygons = 'Polygons'
    ckpoint = 'Checkpoints'
    unique = 'unique'
    batch = 'batch'
    p1 = 'points_per_side'
    p2 = 'points_per_batch'
    p3 = 'pred_iou_thresh'
    p4 = 'stability_score_thresh'
    p5 = 'stability_score_offset'
    p6 = 'box_nms_thresh'
    p7 = 'crop_n_layers'
    p8 = 'crop_nms_thresh'
    p9 = 'crop_overlap_ratio'
    p10 = 'crop_n_points_downscale_factor'
    p12 = 'min_mask_region_area'

    def __init__(self):
        super().__init__()

    def name(self):
        return "SAM"

    def tr(self, text):
        return QCoreApplication.translate("SAM", text)

    def displayName(self):
        return self.tr("Segment Anything Model (SAM)")

    def group(self):
        return self.tr("Raster Tools")

    def shortHelpString(self):
        return self.tr('''Meta's Segment Anything model that will classify objects automatically based on a series of points and parameters.

          Warpper to the segment-geospatial python package, the script requires the installation of the segment-geospatial python package as well as downloading the SAM checkpoints - refer to the 'Configure' tool for more help.

          Parameters

          Image: 8 bit 3-Band (RGB) image to classify
          Checkpoint: Checkpoint file to use for classification.
          Automatic Mask Generator: Generate unique output classifications.
          Batch Processing: Process image in batches (tiles) for better performance.

          Advanced Parameters


          Points Per Side: The number of points to be sampled along one side of the image. The total number of points is points_per_side**2.

          Points Per Batch: Sets the number of points run simultaneously by the model. Higher numbers may be faster but use more GPU memory.

          Pred Iou Thresh: A filtering threshold in [0,1], using the model's predicted mask quality.

          Stability Score Thres: A filtering threshold in [0,1], using the stability of the mask under changes to the cutoff used to binarize the model's mask predictions.

          Stability Score Offset: The amount to shift the cutoff when calculated the stability score.

          Box Nms Thresh: The box IoU cutoff used by non-maximalsuppression to filter duplicate masks.

          Crop N Layers: If >0, mask prediction will be run again on crops of the image. Sets the number of layers to run, where each layer has 2**i_layer number of image crops.

          Crop Nms Thresh: The box IoU cutoff used by non-maximal suppression to filter duplicate masks between different crops.

          Crop Overlap Ratio: Sets the degree to which crops overlap. In the first crop layer, crops will overlap by this fraction of the image length. Later layers with more crops scale down this overlap.

          Crop N Points Downscale Factor: The number of points-per-side sampled in layer n is scaled down by 'crop n points downscale factor'**n.

          Min Mask Region Area: If >0, postprocessing will be applied to remove disconnected regions and holes in masks with area smaller than min_mask_region_area.''')

    def groupId(self):
        return "3. Raster Tools"

    def helpUrl(self):
        return "https://github.com/BjornNyberg/Geometric-Attributes-Toolbox/wiki"

    def createInstance(self):
        return type(self)()

    def cValues(self):
        dirname = os.path.dirname(__file__)  # directory to scripts
        values = [p for p in os.listdir(dirname) if p.endswith('.pth')]
        return values

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.Raster,
            self.tr("Image"), None, False))

        self.addParameter(QgsProcessingParameterEnum(self.ckpoint,
                                                     self.tr('Checkpoint File'),
                                                     options=self.cValues(), defaultValue=0))

        self.addParameter(QgsProcessingParameterBoolean(self.unique,
                    self.tr("Automatic Mask Generator"),False))

        self.addParameter(QgsProcessingParameterBoolean(self.batch,
                    self.tr("Batch Processing"),False))

        self.addParameter(QgsProcessingParameterVectorDestination(
            self.Polygons,
            self.tr("Polygons"),
            QgsProcessing.TypeVectorPolygon))

        self.addParameter(QgsProcessingParameterRasterDestination(
        self.Mask,
        self.tr("Image Mask"), None, False))

        param1 = QgsProcessingParameterNumber(self.p1,self.tr("Points Per Side"),QgsProcessingParameterNumber.Integer,None,minValue=1,optional=True)
        param2 = QgsProcessingParameterNumber(self.p2,self.tr("Points Per Batch"),QgsProcessingParameterNumber.Integer,None,minValue=1.0,optional=True)
        param3 = QgsProcessingParameterNumber(self.p3,self.tr("Pred Iou Thresh"),QgsProcessingParameterNumber.Double,None,minValue=0.0,maxValue=1.0,optional=True)
        param4 = QgsProcessingParameterNumber(self.p4,self.tr("Stability Score Thresh"),QgsProcessingParameterNumber.Double,None,minValue=0.0,maxValue=1.0,optional=True)
        param5 = QgsProcessingParameterNumber(self.p5,self.tr("Stability Score Offset"),QgsProcessingParameterNumber.Double,None,minValue=0.0,maxValue=1.0,optional=True)
        param6 = QgsProcessingParameterNumber(self.p6,self.tr("Box Nms Thresh"),QgsProcessingParameterNumber.Double,None,minValue=0.0,optional=True)
        param7 = QgsProcessingParameterNumber(self.p7,self.tr("Crop N Layers"),QgsProcessingParameterNumber.Integer,None,minValue=0,optional=True)
        param8 = QgsProcessingParameterNumber(self.p8,self.tr("Crop Nms Thresh"),QgsProcessingParameterNumber.Double,None,minValue=0.0,optional=True)
        param9 = QgsProcessingParameterNumber(self.p9,self.tr("Crop Overlap Ratio"),QgsProcessingParameterNumber.Double,None,minValue=0.01,optional=True)
        param10 = QgsProcessingParameterNumber(self.p10,self.tr("Crop N Points Downscale Factor"),QgsProcessingParameterNumber.Integer,None,minValue=0,optional=True)
        param12 = QgsProcessingParameterNumber(self.p12,self.tr("Min Mask Region Area"),QgsProcessingParameterNumber.Integer,None,minValue=0,optional=True)

        ## param11 - point_grids ## not implemented

        param1.setFlags(param1.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        param2.setFlags(param2.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        param3.setFlags(param3.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        param4.setFlags(param1.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        param5.setFlags(param2.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        param6.setFlags(param3.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        param7.setFlags(param1.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        param8.setFlags(param2.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        param9.setFlags(param3.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        param10.setFlags(param1.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        param12.setFlags(param3.flags() | QgsProcessingParameterDefinition.FlagAdvanced)

        self.addParameter(param1)
        self.addParameter(param2)
        self.addParameter(param3)
        self.addParameter(param4)
        self.addParameter(param5)
        self.addParameter(param6)
        self.addParameter(param7)
        self.addParameter(param8)
        self.addParameter(param9)
        self.addParameter(param10)
        self.addParameter(param12)

    def processAlgorithm(self, parameters, context, feedback):

        if sys.version_info.minor < 8:
            feedback.reportError(QCoreApplication.translate('Warning',"Please install a newer version of QGIS as SAM requires python version 3.8=>"))
            return {}

        try: ##Imports
            import torch
            from samgeo import SamGeo
        except Exception as e:
            feedback.reportError(QCoreApplication.translate('Warning','Failed to load python modules for SAM predictions. Try using the configure tool or manually install the segment-geospatial package using pip install segment-geospatial. '))
            return {}

        ##Get inputs
        rlayer = self.parameterAsRasterLayer(parameters, self.Raster, context)
        unique = parameters[self.unique]
        batch = parameters[self.batch]
        outputRaster = self.parameterAsOutputLayer(parameters, self.Mask, context)
        outputVector = self.parameterAsOutputLayer(parameters, self.Polygons, context)

        if '.tif' not in outputRaster: ##To do - add other formats
            feedback.reportError(QCoreApplication.translate('Warning','Please save the raster layer as a .tif file.'))
            return {}
        if '.gpkg' not in outputVector:
            feedback.reportError(QCoreApplication.translate('Warning','Please save the vector layer as a geopackage (.gpkg) file.'))
            return {}

        ##Get trained checkpoint file from Geometric Attributes plugin folder
        checkpoints = self.cValues()
        cName = checkpoints[parameters[self.ckpoint]]
        dirname = os.path.dirname(__file__)
        checkpoint = os.path.join(dirname,cName)

        ##Get mode type
        mt = {'sam_vit_h_4b8939.pth':'vit_h','sam_vit_l_0b3195.pth':'vit_l','sam_vit_b_01ec64.pth':'vit_b'}
        m = mt[cName]

        ##Get advanced parameters
        params = {'points_per_side':parameters[self.p1],'points_per_batch':parameters[self.p2],'pred_iou_thresh':parameters[self.p3],
        'stability_score_thresh':parameters[self.p4],'stability_score_offset':parameters[self.p5],'box_nms_thresh':parameters[self.p6],
        'crop_n_layers':parameters[self.p7],'crop_nms_thresh':parameters[self.p8],'crop_overlap_ratio':parameters[self.p9],
        'crop_n_points_downscale_factor':parameters[self.p10],'min_mask_region_area':parameters[self.p12]}

        params = {k:v for k,v in params.items() if v is not None} #Delete None values

        ##Get raster input data provider to check band count
        dp = rlayer.dataProvider()

        if dp.bandCount() != 3:
            feedback.reportError(QCoreApplication.translate('Error','Tool requires a 3 band RGB image.'))
            return {}

        if dp.dataType(1) != 1: ## Convert image to 8bit if required based on band 1 stats
            feedback.reportError(QCoreApplication.translate('Error','WARNING! Input needs to be an 8 bit image. Use the gdal translate tool to convert to a byte image prior to SAM processing.'))
            return {}
        else:
            inRaster = dp.dataSourceUri()

        ##Check GPU driver and provide user warning
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

        if device == 'cpu':
            feedback.reportError(QCoreApplication.translate('Warning','WARNING! No GPU detected, reverting to CPU which may be slow...'))

        ##Run SamGeo model
        sam = SamGeo(
            checkpoint=checkpoint,
            model_type=m,
            automatic=True,
            device=device,
            sam_kwargs=params,
        )

        if unique: #Automatic Mask Generator
            #Generate Mask
            sam.generate(source=inRaster,unique=True,batch=batch)

            ##Save masks
            sam.save_masks(outputRaster,unique=True)

        else: #Segment Anything
            #Generate Mask
            sam.generate(source=inRaster, output=outputRaster,batch=batch)

        ##Export to Geopackage
        sam.tiff_to_gpkg(outputRaster, outputVector, simplify_tolerance=None)

        ##Return Output to QGIS
        return {self.Polygons:outputVector,self.Mask:outputRaster}

if __name__ == '__main__':
    pass
