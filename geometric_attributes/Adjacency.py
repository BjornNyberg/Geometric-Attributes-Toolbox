#==================================
#Author Bjorn Burr Nyberg
#University of Bergen
#Contact bjorn.nyberg@uib.no
#Copyright 2014
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


import os
import processing as st
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsVectorLayer, QgsSpatialIndex, QgsField,QgsVectorFileWriter, QgsProcessingParameterField, QgsFeature, QgsPointXY, QgsProcessingParameterNumber, QgsProcessingParameterString, QgsProcessing,QgsWkbTypes, QgsGeometry, QgsProcessingAlgorithm, QgsProcessingParameterFeatureSource, QgsProcessingParameterFeatureSink,QgsFeatureSink,QgsFeatureRequest,QgsFields,QgsProperty)

class Connected(QgsProcessingAlgorithm):

    Polygons='Polygons'
    Field = 'Field'
    Tolerance = 'Allowed Tolerance'
    Output = 'Output'

    def __init__(self):
        super().__init__()

    def name(self):
        return "Adjacency"

    def tr(self, text):
        return QCoreApplication.translate("Adjacency", text)

    def displayName(self):
        return self.tr("Adjacency")

    def group(self):
        return self.tr("Polygon Tools")

    def shortHelpString(self):
        return self.tr("Calculate adjacenct polygons and connected clusters. Tolerance specifies the distance by which to buffer each polygon to identify an adjacent polygon. An approximate perimeter shared between the polygons is taken as the perimenter of the overlapping area divided by two.\n Use the Help button for more information.")

    def groupId(self):
        return "Polygon Tools"

    def helpUrl(self):
        return "https://github.com/BjornNyberg/Geometric-Attributes-Toolbox/wiki"

    def createInstance(self):
        return type(self)()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Polygons,
            self.tr("Polygons"),
            [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterField(
            self.Field,
            self.tr("Field"),
            parentLayerParameterName=self.Polygons, optional=False))
        self.addParameter(QgsProcessingParameterNumber(
            self.Tolerance,
            self.tr("Tolerance"),
            QgsProcessingParameterNumber.Double,
            0.1))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.Output,
            self.tr("Output"),
            QgsProcessing.TypeVectorPolygon))

    def processAlgorithm(self, parameters, context, feedback):

        try:
            import networkx as nx
        except Exception as e:
            feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
            feedback.reportError(QCoreApplication.translate('Error',' '))
            feedback.reportError(QCoreApplication.translate('Error','Error loading modules - please install the necessary python module'))
            return {}

        layer = self.parameterAsVectorLayer(parameters, self.Polygons, context)
        features = {f.id():f for f in layer.getFeatures()}
        selected = [f.id() for f in layer.selectedFeatures()]

        context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)

        if len(selected) == 0:
            selected = list(features.keys())

        distance = parameters[self.Tolerance]
        Class_Name = parameters[self.Field]

        if distance <= 0.0:
            feedback.reportError(QCoreApplication.translate('Error','Tolerance must be greater than 0'))
            return {}

        names = set()
        update = {}
        skip = ['Connection','Adjacent','Perimeter','ORIG_FID']

        for total,feature in enumerate(layer.getFeatures()): #Find unique values & Connection
            try:
                fName = str(feature[Class_Name]).replace(' ','')
                names.add(fName[:10]) #Field name < 10 characters
                if fName[:10] in skip:
                    feedback.reportError(QCoreApplication.translate('Error','Attribute %s in %s field is a required field in resulting feature class - rename attribute or change field'% (fName[:10],Class_Name)))
                    return {}
            except Exception as e:
                feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))

        fet = QgsFeature()
        fields = QgsFields()
        fields.append(QgsField("Connection", QVariant.Int))

        orig_fields = []


        for field in layer.fields():
            if field.name() not in skip:
                orig_fields.append(field.name())
                fields.append (QgsField(field.name(), field.type()))

        for name in names:
            fields.append( QgsField(name, QVariant.Double ))

        fields.append (QgsField('Adjacent', QVariant.String ))
        fields.append (QgsField('Perimeter', QVariant.Double ))
        fields.append (QgsField('ORIG_ID', QVariant.Int ))

        (writer, dest_id) = self.parameterAsSink(parameters, self.Output, context,
                                               fields, QgsWkbTypes.Polygon, layer.sourceCrs())

        G = nx.Graph()

        index = QgsSpatialIndex(layer.getFeatures())
        total = 100.0/float(total)

        feedback.pushInfo(QCoreApplication.translate('Update','Calculating Shared Border Percentages'))
        for enum,feature in enumerate(layer.getFeatures()): #Update features
            try:
                if total != -1:
                    feedback.setProgress(int(enum*total))

                data = {name:0.0 for name in names}
                curGeom = feature.geometry().buffer(float(distance),5)
                bbox = curGeom.boundingBox()
                feats = index.intersects(bbox) #Find geometries that intersect with bounding box

                Connected = []

                for FID in feats:
                    if FID != feature.id(): #Do not intersect with same geometry
                        feat=features[FID]

                        if curGeom.intersects(feat.geometry()): #Check if they intersect

                            if FID in selected and feature.id() in selected: #Element to Element Connection
                                G.add_edge(feature.id(),FID)
                                Connected.append(str(FID))

                            geom = curGeom.intersection(feat.geometry()) #Get geometry
                            fName = str(feat[Class_Name]).replace(' ','')
                            Class = fName[:10]
                            try:
                                if curGeom.overlaps(feat.geometry()):
                                    length = geom.length()/2 #Estimate as half the perimeter of polygon
                                    if length < 0:
                                        length = 0.0
                                    data[Class] += length
                            except Exception as e:# No length? possible collapsed polygon/point
                                feedback.pushInfo(QCoreApplication.translate('Update','%s'%(e)))
                                continue

                G.add_edge(feature.id(),feature.id())

                rows = []
                for field in orig_fields:
                    rows.append(feature[field])

                for k,v in data.items():
                    rows.append(v)

                if len(Connected) != 0:
                    Neighbours = ','.join(Connected).replace('L','')
                else:
                    Neighbours = 'None'

                rows.append(Neighbours)
                rows.append(float(curGeom.length()))
                rows.append(feature.id())
                rows.append(feature.geometry())
                update[feature.id()] = rows

            except Exception as e:
                feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
                continue

        subGraphs = nx.connected_components(G)

        feedback.pushInfo(QCoreApplication.translate('Update','Creating Layer'))

        for enum,maxG in enumerate(subGraphs): #Update features
            sG = G.subgraph(maxG)
            for node in sG:
                rows = [enum]
                v = update[node]
                rows.extend(v[:-1])

                fet.setAttributes(rows)
                fet.setGeometry(v[-1])
                writer.addFeature(fet)

        return {self.Output:dest_id}
