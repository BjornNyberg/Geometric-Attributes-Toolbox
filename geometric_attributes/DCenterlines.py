#==================================

#Author Bjorn Burr Nyberg
#University of Bergen
#Contact bjorn.nyberg@uni.no
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


import os, sys, math
import processing as st
import networkx as nx
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsVectorLayer, QgsSpatialIndex, QgsField,QgsVectorFileWriter, QgsProcessingParameterBoolean, QgsFeature, QgsPointXY, QgsProcessingParameterNumber, QgsProcessingParameterString, QgsProcessing,QgsWkbTypes, QgsGeometry, QgsProcessingAlgorithm, QgsProcessingParameterFeatureSource, QgsProcessingParameterFeatureSink,QgsFeatureSink,QgsFeatureRequest,QgsFields,QgsProperty)
from itertools import combinations,chain
from math import sqrt

class DCenterlines(QgsProcessingAlgorithm):

    Centerline='Centerline'
    Direction='Direction'
    Output = 'Directional Centerlines'

    def __init__(self):
        super().__init__()

    def name(self):
        return "Directional Centerline"

    def tr(self, text):
        return QCoreApplication.translate("Directional Centerline", text)

    def displayName(self):
        return self.tr("Directional Centerline")

    def group(self):
        return self.tr("Line Tools")

    def shortHelpString(self):
        return self.tr('''The directional centerline script will reverse the distance field based on the proximity to another feature class line to indicate the start point of each centerline. \n
        Alternatively, the algorithm will reverse and calculate the distance in relation to another centerline by assigning the start point of each centerline as the shortest Distance attribute to the Direction feature class.''')

    def groupId(self):
        return "Line Tools"

    def helpUrl(self):
        return "https://github.com/BjornNyberg/Geometric-Attributes-Toolbox/wiki"

    def createInstance(self):
        return type(self)()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Centerline,
            self.tr("Centerlines"),
            [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Direction,
            self.tr("Direction"),
            [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.Output,
            self.tr("Directional Centerlines"),
            QgsProcessing.TypeVectorLine))

    def processAlgorithm(self, parameters, context, feedback):

        layer = self.parameterAsVectorLayer(parameters, self.Centerline, context)
        layer2 = self.parameterAsVectorLayer(parameters, self.Direction, context)

        context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)

        index = QgsSpatialIndex(layer2.getFeatures())

        fet = QgsFeature()
        fields = QgsFields()
        fields.append(QgsField("ID", QVariant.Int))
        field_names = ['Distance','RDistance','SP_Dist','SP_RDist']

        for name in field_names:
            fields.append( QgsField(name, QVariant.Double ))

        AD = False
        if layer2.fields().indexFromName('Distance') != -1:
            AD = True
            fields.append( QgsField('AlongDist', QVariant.Double ))

        (writer, dest_id) = self.parameterAsSink(parameters, self.Output, context,
                                               fields, QgsWkbTypes.LineString, layer.sourceCrs())

        Precision = 5
        SPS = {}
        SPE = {}
        values = {}
        values2 = {}
        data = {feature.id():feature for feature in layer2.getFeatures()}
        total = 0
        feedback.pushInfo(QCoreApplication.translate('Update','Defining Centerline Paths'))
        for enum,feature in enumerate(layer.getFeatures()):
            total += 1
            try:
                pnt = feature.geometry()
                if pnt.isMultipart():
                    pnt = pnt.asMultiPolyline()[0]
                else:
                    pnt = pnt.asPolyline()

                startx,starty = round(pnt[0][0],Precision),round(pnt[0][1],Precision)
                endx,endy = round(pnt[-1][0],Precision),round(pnt[-1][1],Precision)
                ID = feature['ID']
                c =  feature['Distance']
                if ID in SPS: #Get start and endpoint of each centerline
                    v = values[ID]
                    v2 = values2[ID]

                    if c > v:
                        SPS[ID] = [(startx,starty),(endx,endy)]
                        values[ID] = c
                    if c < v2:
                        SPE[ID] = [(startx,starty),(endx,endy)]
                        values2[ID] = c

                else:
                    SPS[ID] = [(startx,starty),(endx,endy)]
                    values[ID] = c
                    SPE[ID] = [(startx,starty),(endx,endy)]
                    values2[ID] = c

            except Exception as e:
                #feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
                continue ##Possible Collapsed Polyline?

        del values,values2
        feedback.pushInfo(QCoreApplication.translate('Update','Correcting Centerline Direction'))
        total = 100.0/float(total)
        ID = None

        for enum,feature in enumerate(layer.getFeatures()):

            if total != -1:
                feedback.setProgress(int(enum*total))
            try:
                try:
                    geom = feature.geometry().asPolyline()
                except Exception:
                    geom = feature.geometry().asMultiPolyline()[0]
                start,end = geom[0],geom[-1]
                startx,starty=start
                endx,endy=end
                curID = feature['ID']
                if curID != ID:
                    ID =curID
                    reverse = False

                    SP = SPS[curID]
                    EP = SPE[curID]

                    startx,starty = round(SP[0][0],Precision),round(SP[0][1],Precision)
                    v = index.nearestNeighbor(QgsPointXY(startx,starty), 1)

                    midx,midy = data[v[0]].geometry().centroid().asPoint()

                    dx,dy = startx-midx,starty-midy
                    if AD:
                        shortestPath = data[v[0]]['Distance'] + sqrt((dx**2)+(dy**2))
                        startx,starty = round(SP[1][0],Precision),round(SP[1][1],Precision)
                        v = index.nearestNeighbor(QgsPointXY(startx,starty), 1)
                        dx,dy = startx-midx,starty-midy
                        SPd = data[v[0]]['Distance']+ sqrt((dx**2)+(dy**2))
                        if SPd < shortestPath:
                            shortestPath = SPd
                    else:
                        shortestPath = sqrt((dx**2)+(dy**2))

                    startx,starty = round(EP[0][0],Precision),round(EP[0][1],Precision)

                    v = index.nearestNeighbor(QgsPointXY(startx,starty), 1)

                    midx,midy = data[v[0]].geometry().centroid().asPoint()
                    dx,dy = startx-midx,starty-midy

                    if AD:
                        shortestPath2 = data[v[0]]['Distance'] + sqrt((dx**2)+(dy**2))
                        startx,starty = round(SP[1][0],Precision),round(SP[1][1],Precision)
                        v = index.nearestNeighbor(QgsPointXY(startx,starty), 1)
                        dx,dy = startx-midx,starty-midy
                        SPd = data[v[0]]['Distance']+ sqrt((dx**2)+(dy**2))
                        if SPd < shortestPath2:
                            shortestPath2 = SPd
                    else:
                        shortestPath2 = sqrt((dx**2)+(dy**2))

                    if shortestPath2 > shortestPath:
                        reverse = True
                        dist = shortestPath
                    else:
                        dist = shortestPath2

                D = feature['Distance']
                D2 = feature['RDistance']
                SP = feature['SP_Dist']
                SP2 = feature['SP_RDist']
                if reverse:
                    rows = [curID,D2,D,SP2,SP]

                else:
                    rows = [curID,D,D2,SP,SP2]
                    D2 = D
                if AD:
                    rows.append(float(dist)+D2)

                fet.setGeometry(feature.geometry())
                fet.setAttributes(rows)
                writer.addFeature(fet)

            except Exception as e:
                feedback.pushInfo(QCoreApplication.translate('Update','%s'%(e)))
                continue

        return {self.Output:dest_id}
