#==================================
#Author Bjorn Burr Nyberg 
#University of Bergen
#Contact bjorn.nyberg@uni.no
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
import networkx as nx
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsVectorLayer, QgsSpatialIndex, QgsField,QgsVectorFileWriter, QgsProcessingParameterField, QgsFeature, QgsPointXY, QgsProcessingParameterNumber, QgsProcessingParameterString, QgsProcessing,QgsWkbTypes, QgsGeometry, QgsProcessingAlgorithm, QgsProcessingParameterFeatureSource, QgsProcessingParameterFeatureSink,QgsFeatureSink,QgsFeatureRequest,QgsFields,QgsProperty)

class Overlap(QgsProcessingAlgorithm):

    Polygons='Polygons'
    Tolerance = 'Tolerance'
    Output = 'Output'
    
    def __init__(self):
        super().__init__()
        
    def name(self):
        return "Topologically Consistent Polygons"

    def tr(self, text):
        return QCoreApplication.translate("Topologically Consistent Polygons", text)

    def displayName(self):
        return self.tr("Topologically Consistent Polygons")
 
    def group(self):
        return self.tr("Algorithms")
    
    def shortHelpString(self):
        return self.tr("Create topologically consistent polygons")

    def groupId(self):
        return "Algorithms"
    
    def helpUrl(self):
        return "https://github.com/BjornNyberg/Geometric-Attributes-Toolbox/blob/master/Datasets/README.pdf"
    
    def createInstance(self):
        return type(self)()
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Polygons,
            self.tr("Polygons"),
            [QgsProcessing.TypeVectorPolygon]))
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

        layer = self.parameterAsVectorLayer(parameters, self.Polygons, context)
        distance = parameters[self.Tolerance]
        
        if distance <= 0.0:
            feedback.reportError(QCoreApplication.translate('Error','Tolerance must be greater than 0'))
            return {}
            
        fet = QgsFeature()
        fields = QgsFields()
        for field in layer.fields():
            fields.append (QgsField(field.name(), field.type()))

        (writer, dest_id) = self.parameterAsSink(parameters, self.Output, context,
                                               fields, QgsWkbTypes.Polygon, layer.sourceCrs())
        
        features = {}
        
        for total,f in enumerate(layer.getFeatures()):
            features[f.id()]=f.geometry()
        
        selected = [f.id() for f in layer.selectedFeatures()]
        
        if len(selected) == 0:
            selected = list(features.keys())
            total = len(selected)
        
        index = QgsSpatialIndex(layer.getFeatures())
        total = 100.0/float(total)
            
        fields = QgsFields()
        for field in layer.fields():
            fields.append (QgsField(field.name(), field.type()))
            
        fet = QgsFeature(fields)

        feedback.pushInfo(QCoreApplication.translate('Update','Creating topologically consistent polygons'))

        for enum,feature in enumerate(layer.getFeatures()): #Update features
            try:
                if total != -1: 
                    feedback.setProgress(int(enum*total))
                geom = feature.geometry()
                if feature.id() in selected:
                    geom = feature.geometry().buffer(float(distance),5)
                    bbox = geom.boundingBox()
                    feats = index.intersects(bbox) #Find geometries that intersect with bounding box
                    for FID in feats:
                        try:
                            if FID != feature.id(): #Do not intersect with same geometry
                                feat=features[FID]
                                if geom.overlaps(feat):
                                    geom = geom.difference(feat) #Ensure no overlap
                        except Exception as e:
                            feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
                            continue

                rows = []
                for field in layer.fields():
                    rows.append(feature[field.name()])
                    
                fet.setAttributes(rows)
                fet.setGeometry(geom)
                writer.addFeature(fet)
                
                features[feature.id()]=geom
                
            except Exception as e:
                feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
                continue

        return {self.Output:dest_id}

