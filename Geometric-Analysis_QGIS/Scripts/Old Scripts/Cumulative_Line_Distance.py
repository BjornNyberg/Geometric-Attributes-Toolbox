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
##Groupby_Field=field Centerline
##Custom_Weight_Field_Optional=string

#Algorithm body
#==================================
from qgis.core import *
from PyQt4.QtCore import QVariant
import networkx as nx
import processing as st

layer = st.getobject(Centerline)
if layer.fieldNameIndex("Distance") == -1:
    layer.dataProvider().addAttributes([QgsField("Distance",QVariant.Double)])
if layer.fieldNameIndex("RDistance") == -1:
    layer.dataProvider().addAttributes([QgsField("RDistance",QVariant.Double)])
if layer.fieldNameIndex("Length") == -1:
    layer.dataProvider().addAttributes([QgsField("RDistance",QVariant.Double)])
Total = layer.featureCount()
edges = {}
progress.setText('Calculating Edges')
layer.startEditing()
for enum,feature in enumerate(layer.getFeatures()):
    try:
        progress.setPercentage(int((100 * enum)/Total))
        points = feature.geometry().asPolyline()
        pnts1 = points[0][0],points[0][1]
        pnts2 = points[-1][0],points[-1][1]
        if Custom_Weight_Field_Optional:
            Length = float(feature[Custom_Weight_Field_Optional])
        else:
            Length = feature.geometry().length()
        ID = feature[Groupby_Field]
        if ID in edges:
            edges[ID].add_edge(pnts1,pnts2,weight=Length)
        else:
            Graph = nx.Graph()
            Graph.add_edge(pnts1,pnts2,weight=Length)
            edges[ID] = Graph
    except Exception:
        continue ##Possible Collapsed Polyline?
        layer.updateFeature(feature)


layer.commitChanges()
Lengths = {}
progress.setText('Updating Features')
layer.startEditing()
for enum,feature in enumerate(layer.getFeatures()):
    try:
        progress.setPercentage(int((100 * enum)/Total))
        points = feature.geometry().asPolyline()
        startx,starty = points[0][0],points[0][1]
        endx,endy = points[-1][0],points[-1][1]
        ID = feature[Groupby_Field]
        if ID not in Lengths:
            G = edges[ID]
            Source = G.nodes()[0]
            for n in range(2):
                Length,Path = nx.single_source_dijkstra(G,Source,weight='weight')
                Index = max(Length,key=Length.get)
                Source = Path[Index][-1]
            Lengths[ID] = [Length]
            Length,Path = nx.single_source_dijkstra(G,Source,weight='weight')
            Lengths[ID].append(Length)
            L = max([Lengths[ID][0][(endx,endy)],Lengths[ID][0][(startx,starty)]])
            L2 = max([Lengths[ID][1][(endx,endy)],Lengths[ID][1][(startx,starty)]])
            feature["Distance"]=L
            feature["RDistance"]=L2
            G.clear()
        else:
            L = max([Lengths[ID][0][(endx,endy)],Lengths[ID][0][(startx,starty)]])
            L2 = max([Lengths[ID][1][(endx,endy)],Lengths[ID][1][(startx,starty)]])
            feature["Distance"]=L
            feature["RDistance"]=L2
        layer.updateFeature(feature)
    except Exception: #No Connection?
        continue

layer.commitChanges()
