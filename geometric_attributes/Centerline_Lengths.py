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
from math import sqrt

class centDist(QgsProcessingAlgorithm):

    Centerlines = 'Centerlines'
    explode = 'Explode'
    Densify = 'Densify'
    Output='Output'

    def __init__(self):
        super().__init__()

    def name(self):
        return "Distance Along Centerline"

    def tr(self, text):
        return QCoreApplication.translate("Distance Along Centerline", text)

    def displayName(self):
        return self.tr("Distance Along Centerline")

    def group(self):
        return self.tr("Line Tools")

    def shortHelpString(self):
        return self.tr('''Calculate the the distance (Distance), reverse distance (RDistance), shortest path distance (SP_Dist) and reverse shortest path distance (SP_RDist) from the centerline(s) startpoint. 'Explode lines' option will split the line at each vertex. Use the 'Vertex Density' option to split the centerline at a given distance. \n For more options refer to the tortuosity and shortest pathway tools found in the NetworkGT plugin.
        \n Use the Help button for more information.''')

    def groupId(self):
        return "1. Line Tools"

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
            self.Densify,
            self.tr("Vertex Density"),
            QgsProcessingParameterNumber.Double,
            0.0, minValue = 0.0))

        self.addParameter(QgsProcessingParameterBoolean(self.explode,
                    self.tr("Explode Lines"),False))

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.Output,
            self.tr("Centerline Distance"),
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
        explode = parameters[self.explode]
        densify = parameters[self.Densify]

        fet = QgsFeature()
        fs = QgsFields()
        field_names = ['ID','Distance','RDistance','SP_Dist','SP_RDist']

        fields = layer.fields()
        for field in fields:
            if field.name() not in field_names:
                fs.append(QgsField(field.name(),field.type()))

        for field in field_names:
            fs.append(QgsField(field,6))

        (writer, dest_id) = self.parameterAsSink(parameters, self.Output, context,
                                               fs, QgsWkbTypes.LineString, layer.sourceCrs())

        Precision, W = 6, False
        Graph = nx.Graph()

        if densify > 0:
            params = {'INPUT':layer, 'INTERVAL':densify,'OUTPUT':'memory:'}
            out = st.run("native:densifygeometriesgivenaninterval",params,context=context,feedback=None)
            layer = out['OUTPUT']
            explode = True

        if explode:
            params  = {'INPUT':layer,'OUTPUT':'memory:'}
            explode = st.run("native:explodelines",params,context=context,feedback=feedback)
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

                rows = []
                for field in fields:
                    if field.name() not in field_names:
                        rows.append(feature[field.name()])

                start,end = geom[0],geom[-1]
                startx,starty = round(start[0],6),round(start[1],6)
                endx,endy = round(end[0],6),round(end[1],6)
                Graph.add_edge((startx,starty),(endx,endy),weight=feature.geometry().length(),rows=rows,feat=feature.geometry())

            except Exception as e:
                feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
        if W:
            feedback.reportError(QCoreApplication.translate('Error','Multipart polylines are not supported'))

        feedback.pushInfo(QCoreApplication.translate('Update','Calculating Centerlines Distances'))

        for enum,maxG in enumerate(list(nx.connected_components(Graph))):
            G = Graph.subgraph(maxG)
            source = list(G.nodes())[0]

            length,path = nx.single_source_dijkstra(G,source,weight='weight')
            Index = max(length,key=length.get)
            source = path[Index][-1]

            length,path = nx.single_source_dijkstra(G,source,weight='weight')

            Index = max(length,key=length.get)
            source = path[Index][-1]

            length2,path2 = nx.single_source_dijkstra(G,source,weight='weight')

            for p in G.edges(data=True):
                dx = path[Index][0][0] - p[1][0]
                dy =  path[Index][0][1] - p[1][1]
                dx2 = path[Index][0][0] - p[0][0]
                dy2 =  path[Index][0][1] - p[0][1]
                SP = max([math.sqrt((dx**2)+(dy**2)),math.sqrt((dx2**2)+(dy2**2))])

                dx = path[Index][-1][0] - p[1][0]
                dy =  path[Index][-1][1] - p[1][1]
                dx2 = path[Index][-1][0] - p[0][0]
                dy2 =  path[Index][-1][1] - p[0][1]
                SP2 = max([math.sqrt((dx**2)+(dy**2)),math.sqrt((dx2**2)+(dy2**2))])

                D = max([length[(p[0][0],p[0][1])],length[(p[1][0],p[1][1])]])
                D2= max([length2[(p[0][0],p[0][1])],length2[(p[1][0],p[1][1])]])

                rows,geom = p[2]['rows'],p[2]['feat']
                rows.extend([enum,D,D2,SP,SP2])

                fet.setGeometry(geom)
                fet.setAttributes(rows)
                writer.addFeature(fet)

        return {self.Output:dest_id}
