#==================================

#Author Bjorn Burr Nyberg
#University of Bergen
#Contact bjorn.nyberg@uib.no
#Copyright 2013

#==================================

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

import os, sys, math, string, random,tempfile
import processing as st
import networkx as nx
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import *
from itertools import combinations,chain
from math import sqrt, degrees,atan,radians,tan

class sampleTransects(QgsProcessingAlgorithm):

    Centerlines = 'Centerlines'
    Raster = 'Raster'
    Output='Output'

    def __init__(self):
        super().__init__()

    def name(self):
        return "Sample Transects"

    def tr(self, text):
        return QCoreApplication.translate("Sample Transects", text)

    def displayName(self):
        return self.tr("Sample Transects")

    def group(self):
        return self.tr("Raster Tools")

    def shortHelpString(self):
        return self.tr('''Sample Transects tool will sample the endpoint of each line corresponding to the Distance field used by the centerline creation tools.''')

    def groupId(self):
        return "Raster Tools"

    def helpUrl(self):
        return "https://github.com/BjornNyberg/Geometric-Attributes-Toolbox/wiki"

    def createInstance(self):
        return type(self)()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Centerlines,
            self.tr("Transects"),
            [QgsProcessing.TypeVectorLine]))

        self.addParameter(QgsProcessingParameterRasterLayer(
            self.Raster,
            self.tr("Raster"), None, False))

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.Output,
            self.tr("Sampled Transects"),
            QgsProcessing.TypeVectorLine))

    def processAlgorithm(self, parameters, context, feedback):

        layer = self.parameterAsVectorLayer(parameters, self.Centerlines, context)
        rlayer = self.parameterAsRasterLayer(parameters, self.Raster, context)

        fs = QgsFields()
        for field in layer.fields():
            fs.append(QgsField(field.name(),field.type()))

        bands = rlayer.bandCount()

        for n in range(bands):
            fs.append(QgsField('rvalue_'+ str(n+1),6))

        (writer, dest_id) = self.parameterAsSink(parameters,self.Output,context,fs,2,layer.sourceCrs())

        rProv = rlayer.dataProvider()

        fet = QgsFeature()
        W = True
        for feature in layer.getFeatures(QgsFeatureRequest()):
            try:
                geom = feature.geometry()
                if geom.isMultipart():
                    geomFeat = geom.asMultiPolyline()[0]
                    W = True
                else:
                    geomFeat = geom.asPolyline()
                end = geomFeat[-1]
                rows = []
                for field in layer.fields():
                    rows.append(feature[field.name()])

                for n in range(bands):
                    val,res = rProv.sample(QgsPointXY(end[0], end[1]), n+1)
                    if res:
                        rows.append(val)
                    else:
                        rows.append(-1)
    
                fet.setGeometry(geom)
                fet.setAttributes(rows)
                writer.addFeature(fet,QgsFeatureSink.FastInsert)

            except Exception as e:
                feedback.reportError(QCoreApplication.translate('Node Error','%s'%(e)))

        if W:
            feedback.reportError(QCoreApplication.translate('Node Error','Warning: Multipart polylines are not supported'))

        return {self.Output:dest_id}
