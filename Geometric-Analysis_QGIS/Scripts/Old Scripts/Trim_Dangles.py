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
##Polyline=vector
##Groupby_Field=field Polyline
##Loops=number 1
##Threshold=number 2
##Threshold_Field_Optional=string
##Output=output vector

#Algorithm body
#==================================
import networkx as nx
import processing as st
from qgis.core import *
from PyQt4.QtCore import QVariant

layer = st.getobject(Polyline)

Total = layer.featureCount()
edges = {}
progress.setText('Calculating Edges')
for enum,feature in enumerate(layer.getFeatures()):
    try:
        progress.setPercentage(int((100 * enum)/Total))
        points = feature.geometry().asPolyline()
        pnts1 = points[0][0],points[0][1]
        pnts2 = points[-1][0],points[-1][1]
        if Threshold_Field_Optional:
            Weight = feature[Threshold_Field_Optional]
        else:
            Weight = 1
        ID = feature[Groupby_Field]
        if ID in edges:
            edges[ID].add_edge(pnts1,pnts2,weight=Weight)
        else:
            Graph = nx.Graph()
            Graph.add_edge(pnts1,pnts2,weight=Weight)
            edges[ID] = Graph
    except Exception:
        continue ##Possible Collapsed Polyline?

fields= layer.pendingFields()
fet = QgsFeature(fields)
writer = QgsVectorFileWriter(Output, "CP1250", fields, layer.dataProvider().geometryType(),layer.crs(), "ESRI Shapefile")

progress.setText('Triming Lines')
Total2 = len(edges)
data = set([])
for enum,FID in enumerate(edges):
    progress.setPercentage(int((100 * enum)/Total2))
    G = edges[FID]
    for n in range(Loops):      
        degree = G.degree(weight='weight')
        keepNodes = [k for k,v in degree.iteritems() if v < Threshold]
        G.remove_nodes_from(keepNodes)
    data.update(G.nodes())  

    G.clear()

progress.setText('Creating Segments')
for enum,feature in enumerate(layer.getFeatures()):
    progress.setPercentage(int((100 * enum)/Total))
    points = feature.geometry().asPolyline()
    if len(points) < 2: #Possible Collapsed Polyline?
        continue
    pnts1 = points[0][0],points[0][1]
    pnts2 = points[-1][0],points[-1][1]
    if pnts1 in data and pnts2 in data:
        points = [QgsPoint(pnt.x(),pnt.y()) for pnt in points]
        fet.setGeometry(QgsGeometry.fromPolyline(points))
        for field in fields:
            fet[field.name()] = feature[field.name()]
        writer.addFeature(fet)

del writer
