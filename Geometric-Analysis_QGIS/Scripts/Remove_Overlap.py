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

#==================================
#Definition of inputs and outputs
#==================================

##[SAFARI]=group
##Polygons=vector
##Buffer_Distance=string
##Output=output vector

#Algorithm body
#==================================

import processing as st
from qgis.core import *
from PyQt4.QtCore import QVariant
from collections import defaultdict

layer = st.getobject(Polygons)
Total = layer.selectedFeatureCount()

features = {f.id():f for f in layer.selectedFeatures()}
skip = set([])

index = QgsSpatialIndex()
map(index.insertFeature,layer.selectedFeatures())

fields= layer.pendingFields()
writer = QgsVectorFileWriter(Output, "CP1250", fields, 3,layer.crs(), "ESRI Shapefile")
fet = QgsFeature(fields)

progress.setText('Removing Overlap')

for enum,feature in enumerate(layer.selectedFeatures()): #Update features
    try:
        progress.setPercentage(int((enum)/Total))
        change=False
	if Buffer_Distance:
	    geom = feature.geometry().buffer(float(Buffer_Distance),5)
	else:
            geom = feature.geometry()
        bbox = geom.boundingBox()
        feats = index.intersects(bbox) #Find geometries that intersect with bounding box
        for FID in feats:
            try:
                if FID != feature.id(): #Do not intersect with same geometry
                    feat=features[FID].geometry()
                    if geom.overlaps(feat):
                        geom.makeDifference(feat) #Ensure no overlap
            except:
                continue

        fet.setGeometry(geom)
        for field in fields:
            fet[field.name()] = feature[field.name()]
        features[feature.id()]=fet
        writer.addFeature(fet)
    
    except Exception,e:
        progress.setText('%s'%(e))
        continue
