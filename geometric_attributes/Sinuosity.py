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
from qgis.core import (QgsVectorLayer, QgsSpatialIndex,QgsProcessingParameterEnum, QgsField,QgsVectorFileWriter, QgsProcessingParameterBoolean, QgsFeature, QgsPointXY, QgsProcessingParameterNumber, QgsProcessingParameterString, QgsProcessing,QgsWkbTypes, QgsGeometry, QgsProcessingAlgorithm, QgsProcessingParameterFeatureSource, QgsProcessingParameterFeatureSink,QgsFeatureSink,QgsFeatureRequest,QgsFields,QgsProperty)
from itertools import combinations,chain
from math import sqrt

class Sinuosity(QgsProcessingAlgorithm):

    Centerlines = 'Centerlines'

    def __init__(self):
        super().__init__()

    def name(self):
        return "Sinuosity"

    def tr(self, text):
        return QCoreApplication.translate("Sinuosity", text)

    def displayName(self):
        return self.tr("Sinuosity")

    def group(self):
        return self.tr("Algorithms")

    def shortHelpString(self):
        return self.tr('''Calculate sinuosity of a line as feature length / shortest path distance.''')

    def groupId(self):
        return "Algorithms"

    def helpUrl(self):
        return "https://github.com/BjornNyberg/Geometric-Attributes-Toolbox/wiki"

    def createInstance(self):
        return type(self)()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Centerlines,
            self.tr("Centerlines"),
            [QgsProcessing.TypeVectorLine]))

    def processAlgorithm(self, parameters, context, feedback):

        layer = self.parameterAsVectorLayer(parameters, self.Centerlines, context)

        context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)

        field_check =layer.fields().indexFromName('Sinuosity')

        if field_check == -1:
            pr = layer.dataProvider()
            pr.addAttributes([QgsField("Sinuosity", QVariant.Double)])
            layer.updateFields()

        layer.startEditing()
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom.isMultipart():
                geom = geom.asMultiPolyline()[0]
            else:
                geom = geom.asPolyline()

            start,end = geom[0],geom[-1]
            try:
                dx = start.x() - end.x()
                dy =  start.y() - end.y()
                shortestPath = math.sqrt((dx**2)+(dy**2))
                featLen = feature.geometry().length()
                s = float(featLen/shortestPath)
            except Exception:
                s = -1
            feature['Sinuosity'] = s
            layer.updateFeature(feature)
        layer.commitChanges()

        return {}
