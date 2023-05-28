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

          Parameters

          Image: 8 bit 3-Band (RGB) image to classify
          Training Points: Training points used to train the SAM model. Requires an "id" field with a 1 value that indicates a foreground, and a 0 value that indicates a background. If id field is not available all points will be given a value of 1.
          Checkpoint: Checkpoint file to use for classification.
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

        # self.addParameter(QgsProcessingParameterBoolean(self.multiple,
        #             self.tr("Multiple Mask Output"),False))

        self.addParameter(QgsProcessingParameterBoolean(self.logits,
                    self.tr("Apply Logits"),False))

        self.addParameter(QgsProcessingParameterRasterDestination(
        self.Mask,
        self.tr("Image Mask"), None, False))


    def processAlgorithm(self, parameters, context, feedback):

        if sys.version_info.minor < 8:
            feedback.reportError(QCoreApplication.translate('Warning',"Please install a newer version of QGIS as SAM requires python version 3.8=>"))
            return {}

        try: ##Imports
            from samgeo import SamGeo
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

        crs = str(rlayer.crs()).split(' ')[1][:-1] #TO DO cleanup

        field_check = vlayer.fields().indexFromName('id')

        if '.tif' not in outputRaster: ##To do - add other formats
            feedback.reportError(QCoreApplication.translate('Warning','Please save the raster layer as a .tif file.'))
            return {}

        ##Get trained checkpoint file from Geometric Attributes plugin folder
        checkpoints = self.cValues()
        cName = checkpoints[parameters[self.ckpoint]]
        dirname = os.path.dirname(__file__)
        checkpoint = os.path.join(dirname,cName)
        ##multiple = parameters[self.multiple] ##TO DO - add multiple mask output
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

        for feature in vlayer.getFeatures(QgsFeatureRequest()):
            geom = feature.geometry()
            if field_check == -1:
                label = 1
            else:
                label = feature['id']
                if label not in [0,1]: #If label is not 0 (background) or 1 (foreground), then return 1
                    label = 1

            if QgsWkbTypes.isSingleType(geom.wkbType()): #Check for multipart polyline
                x,y = geom.asPoint()
                labels.append(label)
                points.append([x,y])
            else:
                for x,y in geom.asMultiPoint():
                    labels.append(label)
                    points.append([x,y])

        ##Load SamGeo Model
        sam = SamGeo(
                model_type=m,
                checkpoint=checkpoint,
                automatic=False,
                sam_kwargs=None,
            )

        ## Run SamGeoPredictor
        sam.set_image(inRaster)

        if logits:
            masks, scores ,logits = sam.predict(src_fp=inRaster,point_coords=points,point_labels=labels,point_crs=crs,return_logits=True,return_results=True)
            mask_input = logits[np.argmax(scores), :, :]  # Choose the model's best mask
            sam.predict(src_fp=inRaster,mask_input=mask_input[None, :, :],point_coords=points,point_labels=labels,point_crs=crs,output=outputRaster)
        else:
            sam.predict(src_fp=inRaster,point_coords=points,point_labels=labels,point_crs=crs,output=outputRaster)

        ##Return Output to QGIS
        return {self.Mask:outputRaster}

if __name__ == '__main__':
    pass
