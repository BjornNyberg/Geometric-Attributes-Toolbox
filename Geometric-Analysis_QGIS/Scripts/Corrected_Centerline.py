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
##Centerline=vector
##Depositional_Direction=vector
##Distance_Field=string
##Output=output vector

#Algorithm body
#==================================
from qgis.core import *
from PyQt4.QtCore import *
import processing as st
from math import sqrt

layer = st.getObject(Centerline)
layer2 = st.getObject(Depositional_Direction)

if layer.fieldNameIndex("AlongDist") == -1:
    layer.dataProvider().addAttributes([QgsField("AlongDist",QVariant.String)])
    layer.startEditing()
    layer.commitChanges()
data = {f.id():f for f in layer2.getFeatures()}

index = QgsSpatialIndex()
map(index.insertFeature, layer2.getFeatures())

fields= layer.pendingFields()

writer = QgsVectorFileWriter(Output, "CP1250", fields, layer.dataProvider().geometryType(),layer.crs(), "ESRI Shapefile")
fet = QgsFeature(fields)

progress.setText('Determining Start Node')
Total = layer.featureCount()
for enum,feature in enumerate(layer.getFeatures()):
    try:
        progress.setPercentage(int((100 * enum)/Total))
        geom = feature.geometry().asPolyline()
        start,end = geom[0],geom[-1]
        startx,starty=start
        endx,endy=end
        if Distance_Field:
            ids= index.nearestNeighbor(QgsPoint(startx,starty), 1)
            nearest = index.nearestNeighbor(QgsPoint(endx,endy), 1)
            ids.extend(nearest)
            if len(ids)==2:
                dist,dist2 = [data[ids[0]][Distance_Field],data[ids[1]][Distance_Field]]
            else: #if more that 2 nearest points exist
                value,value2 = None,None
                for id in ids:
                    midx,midy = data[id].geometry().centroid().asPoint()
                    dx,dy = startx-midx,starty-midy
                    dx2,dy2 = endx-midx,endy-midy
                    shortestPath = sqrt((dx**2)+(dy**2))
                    shortestPath2 = sqrt((dx2**2)+(dy2**2))
                    if shortestPath < value or value == None:
                        value = shortestPath
                        dist = data[id][Distance_Field]
                    if shortestPath2 < value2 or value2 == None:
                        value2= shortestPath2
                        dist2 = data[id][Distance_Field]
            
        else:
            f = data[ids[0]]
            midx,midy = f.geometry().centroid().asPoint()
            dx,dy = startx-midx,starty-midy
            dx2,dy2 = endx-midx,endy-midy
            dist = sqrt((dx**2)+(dy**2))
            dist2 = sqrt((dx2**2)+(dy2**2))

        if dist > dist2:
            geom.reverse()
            dist = dist2

        newgeom = QgsGeometry.fromPolyline(geom)
       
        for field in fields:
            fet[field.name()] = feature[field.name()]
        fet["AlongDist"]=float(dist)
        fet.setGeometry(newgeom)
        writer.addFeature(fet)
    except Exception:
        continue
    
del writer
