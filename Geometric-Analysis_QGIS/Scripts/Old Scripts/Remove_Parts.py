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

#==================================

#Definition of inputs and outputs
#==================================
##[SAFARI]=group
##Polygon=vector
##Singlepart=boolean True
##Area_Threshold=number 0
##Output=output vector

#Algorithm body
#==================================

from qgis.core import *
from PyQt4.QtCore import *
import processing as st

layer = st.getobject(Polygon)

fields= layer.pendingFields()
crs = layer.crs()

writer = QgsVectorFileWriter(Output, "CP1250", fields, 3,layer.crs(), "ESRI Shapefile")
fet = QgsFeature(fields)
Total = layer.featureCount()
progress.setText('Extracting Parts')
for enum,feature in enumerate(layer.getFeatures()):
    progress.setPercentage(int((100 * enum)/Total))
    geomType = feature.geometry()
    if geomType.isMultipart():
        multiPart = geomType.asMultiPolygon()
        geomTotal = []
        for part in multiPart:
            geom = [[QgsPoint(pnt.x(),pnt.y()) for pnt in part[0]]]
            if len(part) == 1:
                polygon = QgsGeometry.fromPolygon(geom)
                for field in fields:
                    fet[field.name()] = feature[field.name()]
                fet.setGeometry(polygon)
            for ring in part[1:]:            
                part_ring = [[QgsPoint(pnt.x(), pnt.y()) for pnt in ring]]
                polygon = QgsGeometry.fromPolygon(part_ring)
                area = polygon.area()
                if area < Area_Threshold or Area_Threshold == 0:
                    continue
                geom.append(part_ring[0])   
            if Singlepart:
                for field in fields:
                    fet[field.name()] = feature[field.name()]
                polygon = QgsGeometry.fromPolygon(geom)  
                fet.setGeometry(polygon)
                writer.addFeature(fet)
            else:
                geomTotal.append(geom)
        if len(geomTotal) > 0:
            for field in fields:
                fet[field.name()] = feature[field.name()]
            polygon = QgsGeometry.fromMultiPolygon(geomTotal)  
            fet.setGeometry(polygon)
            writer.addFeature(fet)
    else:
        part = geomType.asPolygon()
        geom = [[QgsPoint(pnt.x(),pnt.y()) for pnt in part[0]]]
        if len(part) == 1:
            polygon = QgsGeometry.fromPolygon(geom)
            for field in fields:
                fet[field.name()] = feature[field.name()]
            fet.setGeometry(polygon)
        for ring in part[1:]:
            part_ring = [[QgsPoint(pnt.x(), pnt.y()) for pnt in ring]]
            polygon = QgsGeometry.fromPolygon(part_ring)
            area = polygon.area()
            if area < Area_Threshold or Area_Threshold == 0:
                continue
            geom.append(part_ring[0])
        for field in fields:
            fet[field.name()] = feature[field.name()]
        polygon = QgsGeometry.fromPolygon(geom)
        fet.setGeometry(polygon)
        writer.addFeature(fet)

del writer
