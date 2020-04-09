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

import os, math
import processing as st
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import *
from qgis.PyQt.QtGui import QIcon
from copy import deepcopy

class mergeLines(QgsProcessingAlgorithm):

    Centerline = 'Centerlines'
    Merged = 'Merged'
    Method = 'Method'
    computeAll = 'Compute All'

    def __init__(self):
        super().__init__()

    def name(self):
        return "Merge Linestrings"

    def tr(self, text):
        return QCoreApplication.translate("Merge Linestrings", text)

    def displayName(self):
        return self.tr("Merge Linestrings")

    def group(self):
        return self.tr("Algorithms")

    def shortHelpString(self):
        return self.tr('''Merge singlepart linestring geometries into a single oriented polyline if two endpoints are identical. The tool will split lines at intersections that contain more than two endpoints and calculate the statistics of each float attribute in the new line output. \n For additional topological editing visit the NetworkGT plugin.''')

    def groupId(self):
        return "Algorithms"

    def helpUrl(self):
        return "https://github.com/BjornNyberg/Geometric-Attributes-Toolbox/wiki"

    def createInstance(self):
        return type(self)()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Centerline,
            self.tr("Centerlines"),
            [QgsProcessing.TypeVectorLine]))

        self.addParameter(QgsProcessingParameterEnum(self.Method,
                                self.tr('Summary Method'), options=[self.tr("min"),self.tr("mean"),self.tr("max"),self.tr("sum"),self.tr("range"),self.tr("all")],defaultValue=2))

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.Merged,
            self.tr("Merged"),
            QgsProcessing.TypeVectorLine))

    def processAlgorithm(self, parameters, context, feedback):

        import networkx as nx
        import numpy as np

        layer = self.parameterAsLayer(parameters, self.Centerline, context)
        m = self.parameterAsInt(parameters, self.Method, context)

        Graph, dataOut = {},[]
        P = 1000000

        fields = QgsFields()
        stats = ['min_','mean_','max_', 'sum_', 'r_']
        for field in layer.fields():
            if m == 5 and field.type() == 6:
                for stat in stats:
                    name = stat + field.name()
                    fields.append(QgsField(name,field.type()))
            else:
                fields.append(QgsField(field.name(),field.type()))
            dataOut.append([])

        (writer, dest_id) = self.parameterAsSink(parameters, self.Merged, context,
                                               fields, QgsWkbTypes.LineString, layer.sourceCrs())

        total = layer.featureCount()
        total = 100.0/total

        for enum,feature in enumerate(layer.getFeatures(QgsFeatureRequest())):
            try:
                if total != -1:
                    feedback.setProgress(int(enum*total))

                geom = feature.geometry().asPolyline()

                start,end = geom[0],geom[-1]
                startx,starty=start
                endx,endy=end
                branch = [(math.ceil(startx*P)/P,math.ceil(starty*P)/P),(math.ceil(endx*P)/P,math.ceil(endy*P)/P)]

                for b in branch:
                    if b in Graph: #node count
                        Graph[b] += 1
                    else:
                        Graph[b] = 1

            except Exception as e:
                feedback.reportError(QCoreApplication.translate('Node Error','%s'%(e)))
                continue

        attrs = {}
        G = nx.Graph()
        feedback.pushInfo(QCoreApplication.translate('Create Lines','Creating V Node Graph'))

        total = layer.featureCount()
        total = 100.0/total

        features = layer.getFeatures(QgsFeatureRequest())
        for enum,feature in enumerate(features):
            try:
                geom = feature.geometry().asPolyline()
                if total != -1:
                    feedback.setProgress(int(enum*total))

                start,end = geom[0],geom[-1]
                startx,starty=start
                endx,endy=end
                branch = [(math.ceil(startx*P)/P,math.ceil(starty*P)/P),(math.ceil(endx*P)/P,math.ceil(endy*P)/P)]

                rows = []
                for field in layer.fields():
                    rows.append(feature[field.name()])

                vertices = [Graph[branch[0]],Graph[branch[1]]]

                if 2 in vertices:
                    G.add_edge(branch[0],branch[1])
                    attrs[(branch[0],branch[1])] = rows #Keep attributes of feature
                    continue

                points = []
                for pnt in geom:
                    x,y = (math.ceil(pnt[0]*P)/P,math.ceil(pnt[1]*P)/P)
                    points.append(QgsPointXY(x,y))
                    geomFeat = QgsGeometry.fromPolylineXY(points)
                fet.setGeometry(geomFeat)
                fet.setAttributes(rows)
                writer.addFeature(fet,QgsFeatureSink.FastInsert)

            except Exception as e:
                feedback.pushInfo(QCoreApplication.translate('Create Lines','%s'%(e)))
                break

        enum = 0
        Graph2 = []
        polyline, data= [],[]
        if len(G) > 0:
            total = 100.0/len(G)

        feedback.pushInfo(QCoreApplication.translate('Create Lines','Merging V nodes'))
        for enum,node in enumerate(G.nodes()): #TO DO split polyline at Y node intersections
            feedback.setProgress(int(enum*total))
            start = node
            enum +=1
            points = []
            while start:
                c = False
                edges = G.edges(start)
                for edge in edges:
                    if edge[0] == start:
                        curEnd = edge[1]
                    else:
                        curEnd = edge[0]
                    line = (start,curEnd)
                    line2 = (curEnd,start)
                    if line in data or line2 in data:
                        continue
                    else:
                        data.extend([line,line2])
                        if not points:
                            end = curEnd
                            points = [QgsPointXY(curEnd[0],curEnd[1]),QgsPointXY(start[0],start[1])]
                            if G.degree(curEnd) > 2:
                                break
                            continue
                        points.append(QgsPointXY(curEnd[0],curEnd[1]))
                        start = curEnd

                        if G.degree(curEnd) > 2:
                            c = False
                            break
                        else:
                            c = True

                if not c:
                    start = None
            while end:
                c = False
                edges = G.edges(end)
                for edge in edges:
                    if edge[0] == end:
                        curStart = edge[1]
                    else:
                        curStart = edge[0]
                    line = (curStart,end)
                    line2 = (end,curStart)

                    if line in data or line2 in data:
                        continue
                    else:
                        data.extend([line,line2])
                        if not points:
                            points = [QgsPointXY(curStart[0],curStart[1]),QgsPointXY(end[0],end[1])]
                            if G.degree(curStart) > 2:
                                c = False
                                break
                            continue
                        end = curStart
                        points.insert(0,QgsPointXY(curStart[0],curStart[1]))
                        if G.degree(curStart) > 2:
                            c = False
                            break
                        c = True
                if not c:
                    end = None
            if points:
                polyline.append(points)

        feedback.pushInfo(QCoreApplication.translate('Create Lines','Creating Lines'))

        if len(polyline) > 0:
            total = 100.0/len(polyline)

        fet = QgsFeature()

        for enum,part in enumerate(polyline):

            if total != -1:
                feedback.setProgress(int(enum*total))
            try:
                if part:
                    outGeom = QgsGeometry.fromPolylineXY(part)
                    geom = outGeom.asPolyline()
                    outRows = []
                    rowData = deepcopy(dataOut)
    
                    startP = None
                    try:
                        for pnt in geom:
                            pnt = (math.ceil(pnt.x()*P)/P,math.ceil(pnt.y()*P)/P)
                            if startP == None:
                                startP = pnt
                                continue
                            else:
                                endP = pnt
                                rows = None
                                if (startP,endP) in attrs:
                                    rows = attrs[(startP,endP)]
                                elif (endP,startP) in attrs:
                                    rows = attrs[(endP,startP)]
                                if rows:
                                    for enum, row in enumerate(rows):
                                        rowData[enum].append(row)
                                startP = pnt
                    except Exception:
                        rowData, outRows = [[]],[] #Did not find attributes

                    if len(rowData[0]) > 0:
                        for row in rowData:
                            if type(row[0]) == float:
                                if m == 5:
                                    outRows.extend([float(np.min(row)),float(np.mean(row)),float(np.max(row)),float(np.sum(row)),float(np.max(row)-np.min(row))])
                                elif m == 0:
                                    outRows.append(float(np.min(row)))
                                elif m == 1:
                                    outRows.append(float(np.mean(row)))
                                elif m == 2:
                                    outRows.append(float(np.max(row)))
                                elif m == 3:
                                    outRows.append(float(np.sum(row)))
                                else:
                                    outRows.append(float(np.max(row)-np.min(row)))

                            else:
                                outRows.append(row[0])

                    fet.setGeometry(outGeom)
                    fet.setAttributes(outRows)
                    writer.addFeature(fet)

            except Exception as e:
                feedback.pushInfo(QCoreApplication.translate('Create Lines',str(e)))
                continue

        del G

        return {self.Merged:dest_id}
