#==================================
#Author Bjorn Burr Nyberg
#University of Bergen
#Contact bjorn.nyberg@uni.no
#Copyright 2013
#Modified from http://ceg-sense.ncl.ac.uk/geoanorak/code/pythontransects.html
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
##Mask_Nodes=vector
##Output=output vector


#Algorithm body
#==================================
from qgis.core import *
from PyQt4.QtCore import *
import processing as st
from math import sqrt

Point_Precision=5
Lengths = {}

layer = st.getobject(Centerline)
layer2 = st.getobject(Mask_Nodes)

fields= layer.pendingFields()
fields.append( QgsField( "Width", QVariant.Double ))
crs = layer.crs()
fet = QgsFeature(fields)

Total = layer.featureCount()

if layer.fieldNameIndex("Width") == -1:
    layer.dataProvider().addAttributes([QgsField("Width",QVariant.Double)])
    
    
data = {f.id():f for f in layer2.getFeatures()}
index = QgsSpatialIndex()
map(index.insertFeature, layer2.getFeatures())
                
writer = QgsVectorFileWriter(Output, "CP1250", fields, 1,layer.crs(), "ESRI Shapefile")
progress.setText('Calculating Width')

layer.startEditing()

for enum,feature in enumerate(layer.getFeatures()):
    try:
        progress.setPercentage(int((100 * enum)/Total))
        geom = feature.geometry().asPolyline()
        start = geom[0]
        
        startx,starty=start

        id= index.nearestNeighbor(QgsPoint(startx,starty), 1)
        midx,midy = data[id[0]].geometry().asPoint()
        
        dx,dy = startx-midx,starty-midy
        shortestPath = sqrt((dx**2)+(dy**2))
        
        feature["Width"] = shortestPath*2
        pnt = QgsGeometry.fromPoint(QgsPoint(startx,starty))
        fet.setGeometry(pnt)
        for field in fields:
            fet[field.name()] = feature[field.name()]
        fet["Width"] = shortestPath*2
        writer.addFeature(fet)
        
        layer.updateFeature(feature)
        
    except Exception,e:
        progress.setText('%s'%(e))
        continue
layer.commitChanges()
