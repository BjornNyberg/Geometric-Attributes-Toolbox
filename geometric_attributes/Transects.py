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

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsVectorLayer, QgsSpatialIndex,QgsProcessingParameterEnum, QgsField,QgsVectorFileWriter, QgsProcessingParameterBoolean, QgsFeature, QgsPointXY, QgsProcessingParameterNumber, QgsProcessingParameterString, QgsProcessing,QgsWkbTypes, QgsGeometry, QgsProcessingAlgorithm, QgsProcessingParameterFeatureSource, QgsProcessingParameterFeatureSink,QgsFeatureSink,QgsFeatureRequest,QgsFields,QgsProperty)
from itertools import combinations,chain
from math import sqrt, degrees,atan,radians,tan

class Transects(QgsProcessingAlgorithm):

    Centerlines = 'Centerlines'
    Samples = 'Samples'
    Densify = 'Densify'
    Distance = 'Distance'
    Output='Output'

    def __init__(self):
        super().__init__()

    def name(self):
        return "Transects By Distance"

    def tr(self, text):
        return QCoreApplication.translate("Transects By Distance", text)

    def displayName(self):
        return self.tr("Transects By Distance")

    def group(self):
        return self.tr("Line Tools")

    def shortHelpString(self):
        return self.tr('''Transects by distance will define perpendicular transects along a centerline at a given distance. 'Transect Width' will define the length of each of the perpendicular transects. 'Sampling Distance' will specify the distance at which to create transects. Use the 'Vertex Density' option to add vertices along the centerline and thus increase the accuracy of the sampling distance at the cost of performance.''')

    def groupId(self):
        return "Line Tools"

    def helpUrl(self):
        return "https://github.com/BjornNyberg/Geometric-Attributes-Toolbox/wiki"

    def createInstance(self):
        return type(self)()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Centerlines,
            self.tr("Centerlines"),
            [QgsProcessing.TypeVectorLine]))

        self.addParameter(QgsProcessingParameterNumber(
            self.Distance,
            self.tr("Transect Width"),
            QgsProcessingParameterNumber.Double,
            100.0))

        self.addParameter(QgsProcessingParameterNumber(
            self.Samples,
            self.tr("Sampling Distance"),
            QgsProcessingParameterNumber.Double,
            100.0))

        self.addParameter(QgsProcessingParameterNumber(
            self.Densify,
            self.tr("Vertex Density"),
            QgsProcessingParameterNumber.Double,
            0.0, minValue = 0.0))

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.Output,
            self.tr("Transects"),
            QgsProcessing.TypeVectorLine))


    def processAlgorithm(self, parameters, context, feedback):

        try:
            import os, sys, math, string, random,tempfile
            import processing as st
            import networkx as nx
        except Exception as e:
            feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
            feedback.reportError(QCoreApplication.translate('Error',' '))
            feedback.reportError(QCoreApplication.translate('Error','Error loading modules - please install the necessary python module'))
            return {}

        layer = self.parameterAsVectorLayer(parameters, self.Centerlines, context)
        Distance = parameters[self.Distance]
        samples = parameters[self.Samples]
        densify = parameters[self.Densify]

        fet = QgsFeature()
        fs = QgsFields()

        field_check = layer.fields().indexFromName('Distance')

        fields = layer.fields()
        for field in fields:
            fs.append(QgsField(field.name(),field.type()))

        if field_check == -1:
            fs.append(QgsField('Distance',6))

        (writer, dest_id) = self.parameterAsSink(parameters, self.Output, context,
                                               fs, QgsWkbTypes.LineString, layer.sourceCrs())

        Precision, W = 6, False
        Graph = nx.Graph()

        if densify > 0:
            params = {'INPUT':layer, 'INTERVAL':densify,'OUTPUT':'memory:'}
            out = st.run("native:densifygeometriesgivenaninterval",params,context=context,feedback=None)
            layer = out['OUTPUT']

        params  = {'INPUT':layer,'OUTPUT':'memory:'}
        explode = st.run("native:explodelines",params,context=context,feedback=None)
        layer = explode['OUTPUT']

        total = 100.0/layer.featureCount()
        W = False
        for enum,feature in enumerate(layer.getFeatures()):
            try:
                if total != -1:
                    feedback.setProgress(int(enum*total))
                geom = feature.geometry()
                if geom.isMultipart():
                    geom = geom.asMultiPolyline()[0]
                    W = True
                else:
                    geom = geom.asPolyline()

                rows = {}
                for field in fields:
                    rows[field.name()] = feature[field.name()]

                start,end = geom[0],geom[-1]
                startx,starty = start
                endx,endy = end
                Graph.add_edge((startx,starty),(endx,endy),weight=feature.geometry().length(),rows=rows)

            except Exception as e:
                feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
        if W:
            feedback.reportError(QCoreApplication.translate('Error','Multipart polylines are not supported'))

        feedback.pushInfo(QCoreApplication.translate('Update','Calculating Transects'))
        Counter = 0
        for G in list(nx.connected_component_subgraphs(Graph)):
            v = 0
            if field_check != -1:
                for edge in G.edges(data=True):
                    values = edge[2]['rows']
                    v2 = values['Distance']
                    if v2 > v:
                        v = v2
                        source = edge[0]
            else:
                source = list(G.nodes())[0]

            for n in range(2):
                length,path = nx.single_source_dijkstra(G,source,weight='weight')
                Index = max(length,key=length.get)
                source = path[Index][-1]

            Counter = 0
            Limit = float(samples)

            start, midx = None,None
            for p in path[Index]:
                if start == None:
                    start = p
                    midx,midy = p
                    continue

                if midx == None:
                    midx,midy = p

                startx,starty = start
                endx,endy = p

                dx = startx - endx
                dy =  starty - endy
                L = math.sqrt((dx**2)+(dy**2))

                if samples > 0:
                    Counter += L

                    if Counter < Limit:
                        start = p
                        continue

                if midx==endx: #if vertical
                    x1,y1 = endx + Distance,endy
                    x2,y2 = endx - Distance,endy
                else:
                    m = ((midy - endy)/(midx - endx)) #Slope
                    angle = degrees(atan(m)) + 90

                    m = tan(radians(angle))
                    c,s = (1/sqrt(1+m**2),m/sqrt(1+m**2))
                    x1,y1 = (endx + Distance*(c),endy + Distance*(s))
                    x2,y2 = (endx - Distance*(c),endy - Distance*(s))

                Counter -= samples

                geom = QgsGeometry.fromPolylineXY([QgsPointXY(x1,y1),QgsPointXY(x2,y2)])

                data = G.get_edge_data((startx,starty), (endx,endy))

                rows = list(data['rows'].values())
                if field_check == -1:
                    D = max([length[(startx,starty)],length[(endx,endy)]])
                    rows.append(D)

                midx = None
                start = p

                fet.setGeometry(geom)
                fet.setAttributes(rows)
                writer.addFeature(fet)

        return {self.Output:dest_id}
