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
        geom = []
        for part in multiPart:
            if len(part) == 1:
                continue # No rings
            for ring in part[1:]:            
                data = [[QgsPoint(pnt.x(),pnt.y()) for pnt in ring]]   
                polygon = QgsGeometry.fromPolygon(data)
                area = polygon.area()
                if Area_Threshold != 0 and area < Area_Threshold:
                    continue
                if Singlepart:
                    for field in fields:
                        fet[field.name()] = feature[field.name()]
                    fet.setGeometry(polygon)
                    writer.addFeature(fet)
                else:
                    geom.append(data[0])
        if len(geom) > 0:
            polygon = QgsGeometry.fromPolygon(geom)
            for field in fields:
                fet[field.name()] = feature[field.name()]
            fet.setGeometry(polygon)
            writer.addFeature(fet)
    else:
        geom = []
        part = geomType.asPolygon()
        if len(part) == 1:
            continue # No rings
        for ring in part[1:]:
            data = [[QgsPoint(pnt.x(),pnt.y()) for pnt in ring]]
            polygon = QgsGeometry.fromPolygon(data)
            area = polygon.area()
            if Area_Threshold != 0 and area < Area_Threshold:
                continue
            if Singlepart:
                for field in fields:
                    fet[field.name()] = feature[field.name()]
                fet.setGeometry(polygon)
                writer.addFeature(fet)
            else:
                geom.append(data[0])
        if len(geom) > 0:
            polygon = QgsGeometry.fromPolygon(geom)
            for field in fields:
                fet[field.name()] = feature[field.name()]
            fet.setGeometry(polygon)
            writer.addFeature(fet)
del writer
