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

from collections import OrderedDict
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsField, QgsFeature, QgsRaster,QgsProcessingParameterBoolean, QgsPointXY, QgsSpatialIndex, QgsProcessingParameterRasterLayer, QgsProcessingParameterFolderDestination, QgsProcessingParameterField, QgsProcessingParameterNumber, QgsProcessing,QgsWkbTypes, QgsGeometry, QgsProcessingAlgorithm, QgsProcessingParameterFeatureSource, QgsProcessingParameterFeatureSink,QgsProcessingParameterNumber,QgsFeatureSink,QgsFeatureRequest,QgsFields,QgsProperty,QgsVectorLayer)
from qgis.PyQt.QtGui import QIcon
import os,tempfile

class Tortuosity(QgsProcessingAlgorithm):

    Centerline = 'Centerline'
    Tortuosity ='Tortuosity Line'
    Weight = 'Weight Field'
    Sources = 'Source Points'
    Targets = 'Target Points'

    def __init__(self):
        super().__init__()

    def name(self):
        return "Tortuosity"

    def tr(self, text):
        return QCoreApplication.translate("Tortuosity", text)

    def displayName(self):
        return self.tr("Tortuosity")

    def group(self):
        return self.tr("Line Tools")

    def shortHelpString(self):
        return self.tr("Measure the tortuosity or shorest pathways between source points and optional target locations. Input requires a linestring, a source point layer with a ID field and a corresponding target point layer with a ID field. If the 'Weight' option is supplied, the cost distance calculator will be weighted to the given field.")

    def groupId(self):
        return "1. Line Tools"

    def helpUrl(self):
        return "https://github.com/BjornNyberg/Geometric-Attributes-Toolbox/wiki"

    def createInstance(self):
        return type(self)()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Centerline,
            self.tr("Line String"),
            [QgsProcessing.TypeVectorLine]))

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Sources,
            self.tr("Source Points"),
            [QgsProcessing.TypeVectorPoint]))

        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Targets,
            self.tr("Target Points"),
            [QgsProcessing.TypeVectorPoint], optional=True))

        self.addParameter(QgsProcessingParameterField(self.Weight,
                                self.tr('Weight Field'), parentLayerParameterName=self.Centerline, type=QgsProcessingParameterField.Numeric, optional=True))

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.Tortuosity,
            self.tr("Tortuosity"),
            QgsProcessing.TypeVectorLine))

    def processAlgorithm(self, parameters, context, feedback):

        try:
            import math, random, string
            import pandas as pd
            import processing as st
            import networkx as nx
            import numpy as np
        except Exception as e:
            feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
            feedback.reportError(QCoreApplication.translate('Error',' '))
            feedback.reportError(QCoreApplication.translate('Error','Error loading modules - please install the necessary dependencies'))
            return {}

        Network = self.parameterAsLayer(parameters, self.Centerline, context)
        Sources = self.parameterAsLayer(parameters, self.Sources, context)
        Targets = self.parameterAsLayer(parameters, self.Targets, context)

        Precision = 6

        explode = st.run("native:explodelines",{'INPUT':Network,'OUTPUT':'memory:'},context=context,feedback=feedback)

        wF = parameters[self.Weight]

        fet = QgsFeature()
        fs = QgsFields()

        fs = QgsFields()
        fs.append(QgsField("ID", QVariant.Int))
        field_names = ['Distance', 'SP_Dist']

        for name in field_names:
            fs.append(QgsField(name, QVariant.Double))

        (writer, dest_id) = self.parameterAsSink(parameters, self.Tortuosity, context,
                                            fs, QgsWkbTypes.LineString, Network.sourceCrs())

        index = QgsSpatialIndex(explode['OUTPUT'].getFeatures())
        orig_data = {feature.id():feature for feature in explode['OUTPUT'].getFeatures()}

        srcs,tgts = {},{}

        field_check = Sources.fields().indexFromName('ID')

        if field_check == -1:
            feedback.reportError(QCoreApplication.translate('Error','No ID attribute in Source layer'))
            return {}
        if Targets:
            field_check2 = Targets.fields().indexFromName('ID')
            if field_check2 == -1:
                feedback.reportError(QCoreApplication.translate('Error','No ID attribute in Targets layer'))
                return {}

        feedback.pushInfo(QCoreApplication.translate('Model','Defining Source Nodes'))
        total = 100.0/Sources.featureCount()
        c = 0
        for enum,feature in enumerate(Sources.getFeatures()): #Find source node
            try:
                if total > 0:
                    feedback.setProgress(int(enum*total))
                pnt = feature.geometry().asPoint()
                startx,starty = (round(pnt.x(),Precision),round(pnt.y(),Precision))
                featFIDs = index.nearestNeighbor(QgsPointXY(startx,starty), 2)
                d = 1e10
                ID = None
                for FID in featFIDs:
                    feature2 = orig_data[FID]
                    testGeom = QgsGeometry.fromPointXY(QgsPointXY(startx,starty))
                    dist = QgsGeometry.distance(testGeom,feature2.geometry())

                    if dist < d: #Find closest vertex in graph to source point

                        ID = feature['ID']
                        d = dist
                        geom = feature2.geometry()

                        start,end = geom.asPolyline()

                        startx2,starty2 = (round(start.x(),Precision),round(start.y(),Precision))
                        endx2,endy2 = (round(end.x(),Precision),round(end.y(),Precision))

                        testGeom2 = QgsGeometry.fromPointXY(QgsPointXY(startx2,starty2))
                        testGeom3 = QgsGeometry.fromPointXY(QgsPointXY(endx2,endy2))
                        near = QgsGeometry.distance(testGeom2,testGeom)
                        near2 = QgsGeometry.distance(testGeom3,testGeom)
                        if near < near2:
                            x,y = startx2,starty2
                        else:
                            x,y = endx2,endy2
                if ID:
                    if ID in srcs:
                        srcs[ID].append((x,y))
                    else:
                        srcs[ID] = [(x,y)]
                    c+=1

            except Exception as e:
                feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))

        if Targets:
            total = 100.0/Targets.featureCount()

            feedback.pushInfo(QCoreApplication.translate('Model','Defining Target Nodes'))
            for enum,feature in enumerate(Targets.getFeatures()): #Find source node
                try:
                    if total > 0:
                        feedback.setProgress(int(enum*total))
                    pnt = feature.geometry().asPoint()

                    startx,starty = (round(pnt.x(),Precision),round(pnt.y(),Precision))

                    featFIDs = index.nearestNeighbor(QgsPointXY(startx,starty), 2)

                    d = 1e10
                    ID = None
                    for FID in featFIDs:
                        feature2 = orig_data[FID]
                        testGeom = QgsGeometry.fromPointXY(QgsPointXY(startx,starty))
                        dist = QgsGeometry.distance(testGeom,feature2.geometry())

                        if dist < d: #Find closest vertex in graph to source point
                            ID = feature['ID']
                            d = dist
                            geom = feature2.geometry()

                            start,end = geom.asPolyline()

                            startx2,starty2 = (round(start.x(),Precision),round(start.y(),Precision))
                            endx2,endy2 = (round(end.x(),Precision),round(end.y(),Precision))

                            testGeom2 = QgsGeometry.fromPointXY(QgsPointXY(startx2,starty2))
                            testGeom3 = QgsGeometry.fromPointXY(QgsPointXY(endx2,endy2))
                            near = QgsGeometry.distance(testGeom2,testGeom)
                            near2 = QgsGeometry.distance(testGeom3,testGeom)
                            if near < near2:
                                x,y = startx2,starty2
                            else:
                                x,y = endx2,endy2
                    if ID:
                        if ID in tgts:
                            tgts[ID].append((x,y))
                        else:
                            tgts[ID] = [(x,y)]
                        c+=1

                except Exception as e:
                    feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))

        total = 100.0/Network.featureCount()

        G = nx.Graph()

        feedback.pushInfo(QCoreApplication.translate('Model','Building Graph'))
        for enum,feature in enumerate(explode['OUTPUT'].getFeatures()): #Build Graph
            try:
                if total > 0:
                    feedback.setProgress(int(enum*total))

                geom = feature.geometry()
                if geom.isMultipart():
                    start,end = geom.asMultiPolyline()[0]
                else:
                    start,end = geom.asPolyline()

                startx,starty = (round(start.x(),Precision),round(start.y(),Precision))
                endx,endy = (round(end.x(),Precision),round(end.y(),Precision))

                if wF:
                    w = feature[wF]
                    if type(w) == int or type(w) == float:
                        pass
                    else:
                        feedback.reportError(QCoreApplication.translate('Error','Weight field contains non numeric values - check for null values'))
                        return {}
                    w = float(W)*feature.geometry().length()
                else:
                    w = feature.geometry().length()

                G.add_edge((startx,starty),(endx,endy),weight=w)
                #G.add_edge((endx,endy),(startx,starty),weight=w)

            except Exception as e:
                feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))

        feedback.pushInfo(QCoreApplication.translate('Model','Creating Fracture Network'))
        try:
            for FID in srcs:
                sources = srcs[FID]
                for source in sources:
                    if G.has_node(source):
                        if FID in tgts:
                            targets = tgts[FID]
                            for target in targets:
                                try:
                                    path = nx.single_source_dijkstra(G, source, target, weight='weight')
                                except Exception:
                                    feedback.reportError(QCoreApplication.translate('Error','No connection found between source and target of ID %s'%(FID)))
                                    continue

                                length = nx.single_source_dijkstra_path_length(G,source)
                                sx = None

                                Index = 1
                                for p in path[Index]:
                                    if sx == None:
                                        sx, sy = p[0], p[1]
                                        continue
                                    ex, ey = p[0], p[1]
                                    D = max([length[(sx, sy)], length[(ex, ey)]])
                                    dx = path[Index][0][0] - ex
                                    dy = path[Index][0][1] - ey
                                    dx2 = path[Index][0][0] - sx
                                    dy2 = path[Index][0][1] - sy
                                    SP = max([math.sqrt((dx ** 2) + (dy ** 2)), math.sqrt((dx2 ** 2) + (dy2 ** 2))])

                                    points = [QgsPointXY(sx, sy), QgsPointXY(ex, ey)]
                                    fet.setGeometry(QgsGeometry.fromPolylineXY(points))
                                    fet.setAttributes([FID, D, SP])
                                    writer.addFeature(fet)
                                    sx, sy = ex, ey

                        else:
                            length, path = nx.single_source_dijkstra(G, source, weight='weight')
                            sx = None
                            Index = max(length, key=length.get)
                            source = path[Index][-1]
                            for p in path[Index]:
                                if sx == None:
                                    sx, sy = p[0], p[1]
                                    continue
                                ex, ey = p[0], p[1]
                                D = max([length[(sx, sy)], length[(ex, ey)]])
                                dx = path[Index][0][0] - ex
                                dy = path[Index][0][1] - ey
                                dx2 = path[Index][0][0] - sx
                                dy2 = path[Index][0][1] - sy
                                SP = max([math.sqrt((dx ** 2) + (dy ** 2)), math.sqrt((dx2 ** 2) + (dy2 ** 2))])

                                points = [QgsPointXY(sx, sy), QgsPointXY(ex, ey)]
                                fet.setGeometry(QgsGeometry.fromPolylineXY(points))
                                fet.setAttributes([FID, D, SP])
                                writer.addFeature(fet)
                                sx, sy = ex, ey

        except Exception as e:
            feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))

        return {self.Tortuosity:dest_id}
