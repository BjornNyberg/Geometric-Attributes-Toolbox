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
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.'''

#==================================

#Definition of inputs and outputs
#==================================
##[SAFARI]=group
##Centerline=vector
##Mask=vector
##Calculate_Width_By=field Centerline
##Calculate_Distance_By=field Centerline
##Custom_Weight_Field_Optional=string
##Distance=number 10000
##Threshold=number 100
##Original=output vector
##Output=output vector

#Algorithm body
#==================================
from qgis.core import *
from PyQt4.QtCore import *
import networkx as nx
import processing as st
import math

keepNodes,Lengths = set([]), {}
layer = st.getobject(Centerline)
if layer.fieldNameIndex("Length") == -1:
    layer.dataProvider().addAttributes([QgsField("Length",QVariant.Double)])
if layer.fieldNameIndex("Distance") == -1:
    layer.dataProvider().addAttributes([QgsField("Distance",QVariant.Double)])
if layer.fieldNameIndex("RDistance") == -1:
    layer.dataProvider().addAttributes([QgsField("RDistance",QVariant.Double)])
edges = {}
layer.startEditing()
layer.commitChanges() #Force creation of fields mentioned above
Total = layer.featureCount()
progress.setText('Calculating Edges')
for enum,feature in enumerate(layer.getFeatures()):
    progress.setPercentage(int((100 * enum)/Total))
    try:
        points = feature.geometry().asPolyline()
        pnts1 = points[0][0],points[0][1]
        pnts2 = points[-1][0],points[-1][1]
        if Custom_Weight_Field_Optional:
            Length = float(feature[Custom_Weight_Field_Optional])
        else:
            Length = feature.geometry().length()
        ID = feature[Calculate_Distance_By]
        if ID in edges:
            edges[ID].append((pnts1,pnts2,Length))
        else:
            edges[ID] = [(pnts1,pnts2,Length)]
    except Exception:
        continue ##Possible Collapsed Polyline?

fields= layer.pendingFields()
crs = layer.crs()

writer = QgsVectorFileWriter(Original, "CP1250", fields, layer.dataProvider().geometryType(),layer.crs(), "ESRI Shapefile")

fet = QgsFeature(fields)
G = nx.Graph()
midx = False

Distance = Distance/2
progress.setText('Calculating Perpendicular Lines')
for enum,feature in enumerate(layer.getFeatures()):

    progress.setPercentage(int((100 * enum)/Total))
    pnt = feature.geometry().asPolyline()
    if midx == False:
        startx,starty = pnt[0][0],pnt[0][1]
        midx,midy = pnt[-1][0],pnt[-1][1]
        ID = feature[Calculate_Width_By]
        keepNodes.update([(midx,midy)])
        continue
    endx,endy = pnt[-1][0],pnt[-1][1]
    if starty==endy or startx==endx: #if horizontal or vertical
        if starty == endy:
            y1 = midx + Distance
            y2 = midy - Distance
            x1 = midx
            x2 = midx
        if startx == endx:
            y1 = midy
            y2 = midy
            x1 = midx + Distance
            x2 = midx - Distance
    else:
        m = ((starty - endy)/(startx - endx)) #Slope
        nr = -1*((startx - endx)/(starty - endy))#Negative Reciprocal
        if m > 0: #Transpose line depending on quadrant based on m
            if m >= 1:
                y1 = nr*(Distance)+ midy
                y2 = nr*(-Distance) + midy
                x1 = midx + Distance
                x2 = midx - Distance
            if m < 1:
                y1 = midy + Distance
                y2 = midy - Distance
                x1 = (Distance/nr) + midx
                x2 = (-Distance/nr)+ midx
        if m < 0:
            if m >= -1:
                y1 = midy + Distance
                y2 = midy - Distance
                x1 = (Distance/nr) + midx
                x2 = (-Distance/nr)+ midx
            if m < -1:
                y1 = nr*(Distance)+ midy
                y2 = nr*(-Distance) + midy
                x1 = midx + Distance
                x2 = midx - Distance
    geom1 = QgsGeometry.fromPolyline([QgsPoint(x1,y1),QgsPoint(midx,midy),QgsPoint(x2,y2)])
    fet.setGeometry(geom1)
    for field in fields:
        fet[field.name()] = feature[field.name()]
    keepNodes.update([(midx,midy)])
    FID = feature[Calculate_Distance_By]
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
        fet["Distance"]=Lengths[FID][(midx,midy)]
        fet["RDistance"]=Lengths[FID2][(midx,midy)]
        G.clear()
    else:
        fet["Distance"]=Lengths[FID][(midx,midy)]
        fet["RDistance"]=Lengths[FID2][(midx,midy)]
    startx,starty = midx,midy
    midx,midy = endx,endy
    writer.addFeature(fet)

del writer
progress.setText('Intersecting With Mask')
Inter=st.runalg("qgis:intersection",Original,Mask,None)
st.runalg("qgis:multiparttosingleparts",Inter["OUTPUT"],Output)
layer = QgsVectorLayer(Output, "Line_Mesh", "ogr")

if layer.fieldNameIndex('Width') == -1:
    layer.dataProvider().addAttributes([QgsField("Width",QVariant.Double)])

Total = layer.featureCount()
progress.setText('Calculating Widths')
layer.startEditing()
for enum,feature in enumerate(layer.getFeatures()):
    progress.setPercentage(int((100 * enum)/Total))
    points = feature.geometry().asPolyline()
    if len(points) != 3: #Check to make sure that two lines have been made
        layer.deleteFeature(feature.id())
        continue
    mid = (float(points[1][0]),float(points[1][1]))
    if mid in keepNodes:
        startx,starty = float(points[0][0]),float(points[0][1])
        endx,endy = float(points[2][0]),float(points[2][1])
        midx,midy = mid[0],mid[1]
        d = [math.sqrt(((startx-midx)**2)+((starty-midy)**2)),math.sqrt(((endx-midx)**2)+((endy-midy)**2))] #Distances
        e = 100-((min(d)/max(d)) * 100)
        if e > Threshold:
            layer.deleteFeature(feature.id())
        else:
            feature["Width"]=feature.geometry().length()
            layer.updateFeature(feature)
    else:
        layer.deleteFeature(feature.id())

layer.commitChanges()
