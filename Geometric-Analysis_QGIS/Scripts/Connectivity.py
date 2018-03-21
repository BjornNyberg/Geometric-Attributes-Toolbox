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
##Class_Name=field Polygons

#Algorithm body
#==================================

import processing as st
import networkx as nx
from qgis.core import *
from PyQt4.QtCore import QVariant
from collections import defaultdict

names = set()
layer = st.getobject(Polygons)
Total = layer.featureCount()
progress.setText('Determining Unique Class Names')
features = {f.id():f for f in layer.getFeatures()}
selected = set([f.id() for f in layer.selectedFeatures()])

for enum,feature in enumerate(layer.getFeatures()): #Find unique values & Connection
    try:
        progress.setPercentage(int((100 * enum)/Total))
        fName = str(feature[Class_Name]).replace(' ','')
        names.add(fName[:10]) #Field name < 10 characters

    except Exception,e:
	progress.setText('%s'%(e))

if layer.fieldNameIndex("Connection") == -1:
    layer.dataProvider().addAttributes([QgsField("Connection",QVariant.Int)])
if layer.fieldNameIndex("Neighbour") == -1:
    layer.dataProvider().addAttributes([QgsField("Neighbour",QVariant.String)])
if layer.fieldNameIndex("Perimeter") == -1:
    layer.dataProvider().addAttributes([QgsField("Perimeter",QVariant.String)])

fieldIndex = layer.fieldNameIndex("Connection")

for name in names:
	if layer.fieldNameIndex(name) == -1:
	    layer.dataProvider().addAttributes([QgsField(name,QVariant.Double)])
        
Graph = nx.Graph()

index = QgsSpatialIndex()
map(index.insertFeature, layer.getFeatures())

progress.setText('Calculating Shared Border Percentages')
layer.startEditing()
for enum,feature in enumerate(layer.getFeatures()): #Update features
    try:
	data = defaultdict(float)
        progress.setPercentage(int((100 * enum)/Total))
	if Buffer_Distance:
	    curGeom = feature.geometry().buffer(float(Buffer_Distance),5)
	else:
	    curGeom = feature.geometry()

	bbox = feature.geometry().boundingBox()
	feats = index.intersects(bbox) #Find geometries that intersect with bounding box
	if feature.id() in selected:
            Graph.add_edge(feature.id(),feature.id())
        Connected = []
	
	for FID in feats:
	    if FID != feature.id(): #Do not intersect with same geometry
		feat=features[FID]

                if curGeom.intersects(feat.geometry()): #Check if they intersect
                    if FID in selected and feature.id() in selected: #Reservoir to Reservoir Element Connection
                        Graph.add_edge(feature.id(),FID)
                        Connected.append(str(FID))

                    geom = curGeom.intersection(feat.geometry()) #Get geometry
                    fName = str(feat[Class_Name]).replace(' ','')
                    Class = fName[:10]
                    try:
			if curGeom.overlaps(feat.geometry()):	    
			    length = geom.length()/2 #Estimate as half the perimeter of polygon
			else: 
                            length = geom.length() #Topologically correct data with no overlap
                        data[Class] += length
                    except Exception,e:# No length? possible collapsed polygon/point
                        continue
        for k,v in data.iteritems():
            feature[k]=float(v)
        Neighbours = ','.join(Connected).replace('L','')
        feature["Neighbour"]= Neighbours
        feature["Perimeter"]= float(curGeom.length())
        layer.updateFeature(feature)

    except Exception,e:
        progress.setText('%s'%(e))
	continue
subGraphs = H=nx.connected_component_subgraphs(Graph)

progress.setText('Calculating Connectivity')
for enum,G in enumerate(subGraphs): #Update features
    progress.setPercentage(int((100 * enum)/len(subGraphs)))
    for node in G:
        layer.changeAttributeValue(node,fieldIndex,int(enum))
layer.commitChanges()
