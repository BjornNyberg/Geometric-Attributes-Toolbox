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
from osgeo import gdal
import numpy as np

class SAM_Pred(QgsProcessingAlgorithm):

    Raster = 'Raster'
    Mask = 'Mask'
    Points = 'Points'
    multiple = 'multiple'
    logits = 'logits'
    ckpoint = 'Checkpoints'

    def __init__(self):
        super().__init__()

    def name(self):
        return "SAM Prediction"

    def tr(self, text):
        return QCoreApplication.translate("SAM", text)

    def displayName(self):
        return self.tr("Segment Anything Model (SAM) - Training Points")

    def group(self):
        return self.tr("Raster Tools")

    def shortHelpString(self):
        return self.tr('''Meta's Segment Anything model that will classify objects based on a series of training points describing the foreground (1) and background (0).

          Warpper to the segment-geospatial python package, the script requires the installation of the segment-geospatial python package as well as downloading the SAM checkpoints - refer to the 'Configure' tool for more help.

          Parameters

          Image: 8 bit 3-Band (RGB) image to classify
          Training Points: Training points used to train the SAM model. Requires an "id" field with a 1 value that indicates a foreground, and a 0 value that indicates a background.
          Checkpoint: Checkpoint file to use for classification.
          Multiple: Create 3 bands showing the different confidence levels of the SAM prediction.
          Logits: Apply an extra iteration of logits to determine the final prediction.

          ''')

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

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Points,
            self.tr("Training Points"),
            [QgsProcessing.TypeVectorPoint]))

        self.addParameter(QgsProcessingParameterBoolean(self.multiple,
                    self.tr("Multiple Mask Output"),False))

        self.addParameter(QgsProcessingParameterBoolean(self.logits,
                    self.tr("Apply Logits"),False))

        self.addParameter(QgsProcessingParameterRasterDestination(
        self.Mask,
        self.tr("Image Mask"), None, False))


    def processAlgorithm(self, parameters, context, feedback):

        def coords(gt,x,y):
            c, a, b, f, d, e = gt
            col = int((x - c) / a)
            row = int((y - f) / e)
            return (col,row)

        if float(sys.version[:3]) <= 3.7:
            feedback.reportError(QCoreApplication.translate('Warning',"Please install a newer version of QGIS as SAM requires python version 3.8=>"))
            return {}

        try: ##Imports
            import cv2
            from samgeo import SamGeo, SamGeoPredictor
            from segment_anything import sam_model_registry
        except Exception as e:
            feedback.reportError(QCoreApplication.translate('Warning','Failed to load python modules for SAM predictions. Try using the configure tool or manually install the segment-geospatial package using pip install segment-geospatial. '))
            return {}

        ##Get inputs
        rlayer = self.parameterAsRasterLayer(parameters, self.Raster, context)
        vlayer = self.parameterAsSource(parameters, self.Points, context)
        outputRaster = self.parameterAsOutputLayer(parameters, self.Mask, context)

        ##Check parameters
        if rlayer.crs() != vlayer.sourceCrs():
            feedback.reportError(QCoreApplication.translate('Error','Error! Raster image and training points do not have the same coordinate projection system.'))
            return {}

        if 'EPSG:4326' not in str(rlayer.crs()): #TO DO remove and add support for multiple proejctions
            feedback.reportError(QCoreApplication.translate('Error',str(rlayer.crs())))
            feedback.reportError(QCoreApplication.translate('Error','Error! This tool is currently only supported for an EPS:4326 coordinate projection.'))
            return {}

        field_check = vlayer.fields().indexFromName('id')
        if field_check == -1:
             feedback.reportError(QCoreApplication.translate('Error','Error! Training points do not have an "id" field for labelling outputs.'))
             return {}

        if '.tif' not in outputRaster: ##To do - add other formats
            feedback.reportError(QCoreApplication.translate('Warning','Please save the raster layer as a .tif file.'))
            return {}

        ##Get trained checkpoint file from Geometric Attributes plugin folder
        checkpoints = self.cValues()
        cName = checkpoints[parameters[self.ckpoint]]
        dirname = os.path.dirname(__file__)
        checkpoint = os.path.join(dirname,cName)
        multiple = parameters[self.multiple]
        logits = parameters[self.logits]

        ##Get mode type
        mt = {'sam_vit_h_4b8939.pth':'vit_h','sam_vit_l_0b3195.pth':'vit_l','sam_vit_b_01ec64.pth':'vit_b'}
        m = mt[cName]

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

        ##Get point data
        labels =  []
        points = []
        layer = gdal.Open(inRaster)
        gt = layer.GetGeoTransform()

        for feature in vlayer.getFeatures(QgsFeatureRequest()):
            geom = feature.geometry()
            label = int(feature['id'])
            if label not in [0,1]:
                feedback.reportError(QCoreApplication.translate('Error','Error! Training data must have value of either 0 for background or 1 for foreground.'))
                return {}
            if QgsWkbTypes.isSingleType(geom.wkbType()):
                x,y = geom.asPoint()
                col,row = coords(gt,x,y)
                labels.append(label)
                points.append([col,row])
            else:
                for x,y in geom.asMultiPoint(): #Check for multipart polyline
                    col,row = coords(gt,x,y)
                    labels.append(label)
                    points.append([col,row])

        labels = np.array(labels)
        points = np.array(points)

        ##Load SamGeo Model
        sam = sam_model_registry[m](checkpoint=checkpoint)

        ## Run SamGeoPredictor
        predictor = SamGeoPredictor(sam)
        img_arr = cv2.imread(inRaster)
        predictor.set_image(img_arr)

        ext = rlayer.extent()
        x_min, x_max, y_min, y_max = ext.xMinimum(),ext.yMaximum(),ext.xMaximum(),ext.yMinimum()
        box = [x_min,y_max,x_max,y_min]

        if logits:
            masks, scores ,logits = predictor.predict(src_fp=inRaster,geo_box=box,point_coords=points,point_labels=labels,multimask_output=True,return_logits=True)
            mask_input = logits[np.argmax(scores), :, :]  # Choose the model's best mask
            masks, _, _ = predictor.predict(src_fp=inRaster,geo_box=box,mask_input=mask_input[None, :, :],point_coords=points,point_labels=labels,multimask_output=multiple)
        else:
            masks, _, _ = predictor.predict(src_fp=inRaster,point_coords=points,point_labels=labels,multimask_output=multiple,geo_box=box)

        #Masks to geotiff
        predictor.masks_to_geotiff(inRaster, outputRaster, masks.astype("uint8"))

        ##Return Output to QGIS
        return {self.Mask:outputRaster}

if __name__ == '__main__':
    pass
