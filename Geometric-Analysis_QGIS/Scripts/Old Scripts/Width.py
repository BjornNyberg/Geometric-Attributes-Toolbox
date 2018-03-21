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
##Calculate_Width_By=field Centerline
##Calculate_Distance_By_Optional=string
##Custom_Distance_Field_Optional=string 
##Distance=number 1000
##Width=output vector

#Algorithm body
#==================================
from qgis.core import *
from PyQt4.QtCore import *
import networkx as nx
import processing as st
from math import sqrt

Lengths = {}
layer = st.getobject(Centerline)

if layer.fieldNameIndex("Distance") == -1:
    layer.dataProvider().addAttributes([QgsField("Distance",QVariant.Double)])
if layer.fieldNameIndex("RDistance") == -1:
    layer.dataProvider().addAttributes([QgsField("RDistance",QVariant.Double)])

edges = {}

layer.startEditing()
layer.commitChanges() #Force creation of fields mentioned above
Total = layer.featureCount()

if Calculate_Distance_By_Optional:
	progress.setText('Calculating Edges')
	for enum,feature in enumerate(layer.getFeatures()):
	    progress.setPercentage(int((100 * enum)/Total))
	    try:
		points = feature.geometry().asPolyline()
		pnts1 = points[0][0],points[0][1]
		pnts2 = points[-1][0],points[-1][1]
		if Custom_Distance_Field_Optional:
		    Length = float(feature[Custom_Distance_Field_Optional])
		else:
		    Length = feature.geometry().length()
		ID = feature[Calculate_Distance_By_Optional]
		if ID in edges:
		    edges[ID].append((pnts1,pnts2,Length))
		else:
		    edges[ID] = [(pnts1,pnts2,Length)]
	    except Exception:
		continue ##Possible Collapsed Polyline?

fields= layer.pendingFields()

writer = QgsVectorFileWriter(Width, "CP1250", fields, layer.dataProvider().geometryType(),layer.crs(), "ESRI Shapefile")

fet = QgsFeature(fields)

G = nx.Graph()
ID = None

progress.setText('Calculating Perpendicular Lines')
for enum,feature in enumerate(layer.getFeatures()):
	try:
		progress.setPercentage(int((100 * enum)/Total))
		pnt = feature.geometry().asPolyline()
		curID = feature[Calculate_Width_By]
		if ID != curID:
		    startx,starty = pnt[0][0],pnt[0][1]
		    midx,midy = pnt[-1][0],pnt[-1][1]
		    ID = feature[Calculate_Width_By]
		    continue

		endx,endy = pnt[-1][0],pnt[-1][1]
		m = ((starty - endy)/(startx - endx)) #Slope
		nr = -1*((startx - endx)/(starty - endy))#Negative Reciprocal
			
		if starty==endy or startx==endx: #if horizontal or vertical
		    if starty == endy:
			y1 = midx + Distance
			x1 = midx
		    if startx == endx:
			y1 = midy
			x1 = midx + Distance
		else:
		    if m > 0: #Transpose line depending on quadrant based on m
			if m >= 1:
			    y1 = nr*(Distance)+ midy
			    x1 = midx + Distance
			if m < 1:
			    y1 = midy + Distance
			    x1 = (Distance/nr) + midx
		    if m < 0:
			if m >= -1:
			    y1 = midy + Distance
			    x1 = (Distance/nr) + midx
			if m < -1:
			    y1 = nr*(Distance)+ midy
			    x1 = midx + Distance

		if starty==endy or startx==endx: #if horizontal or vertical
		    if starty == endy:
			y2 = midy - Distance
			x2 = midx
		    if startx == endx:
			y2 = midy
			x2 = midx - Distance
		else:
		    if m > 0: #Transpose line depending on quadrant based on m
			if m >= 1:
			    y2 = nr*(-Distance) + midy
			    x2 = midx - Distance
			if m < 1:
			    y2 = midy - Distance
			    x2 = (-Distance/nr)+ midx
		    if m < 0:
			if m >= -1:
			    y2 = midy - Distance
			    x2 = (-Distance/nr)+ midx
			if m < -1:
			    y2 = nr*(-Distance) + midy
			    x2 = midx - Distance

		geom = QgsGeometry.fromPolyline([QgsPoint(x1,y1),QgsPoint(midx,midy),QgsPoint(x2,y2)]) #Create line
		fet.setGeometry(geom)
		for field in fields:
		    fet[field.name()] = feature[field.name()]
		if Calculate_Distance_By_Optional:
			FID = feature[Calculate_Distance_By_Optional]
			FID2 = '%sB'%(FID)
			if FID not in Lengths:
			    G.add_weighted_edges_from(edges[FID])
			    Source = G.nodes()[0]
			    for n in range(2):
				Length,Path = nx.single_source_dijkstra(G,Source,weight='weight')
				Index = max(Length,key=Length.get)
				Source = Path[Index][-1]
			    Lengths[FID] = Length
			    Length,Path = nx.single_source_dijkstra(G,Source,weight='weight')
			    Lengths[FID2] = Length

			    G.clear()
			try:
				fet["Distance"]=Lengths[FID][(midx,midy)]   
				fet["RDistance"]=Lengths[FID2][(midx,midy)] 
			except Exception:
				pass
		
		startx,starty = midx,midy
		midx,midy = endx,endy
		writer.addFeature(fet)

	except Exception,error:
		progress.setText('%s'%(error))

del writer
