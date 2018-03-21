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
##Voronoi_Lines=vector
##Method=string ShortestPath
##Threshold=number 0
##Groupby_Field=field Voronoi_Lines
##Output=output vector

#Algorithm body
#==================================
import networkx as nx
import os
import processing as st
from qgis.core import *
from PyQt4.QtCore import QVariant

layer = st.getobject(Voronoi_Lines)
Point_Precision=5
Total = layer.featureCount()
edges = {}
progress.setText('Calculating Edges')
for enum,feature in enumerate(layer.getFeatures()):
    try:
        progress.setPercentage(int((100 * enum)/Total))
        points = feature.geometry().asPolyline()
        pnts1 = (round(points[0][0],Point_Precision),round(points[0][1],Point_Precision))
        pnts2 = (round(points[-1][0],Point_Precision),round(points[-1][1],Point_Precision))
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

fields = QgsFields()
fields.append( QgsField('FID', QVariant.Int ))

writer = QgsVectorFileWriter(Output, "CP1250", fields, layer.dataProvider().geometryType(),layer.crs(), "ESRI Shapefile")

progress.setText('Calculating Shortest Paths')
Total2 = len(edges)
data = {}
fet = QgsFeature(fields)
for enum,FID in enumerate(edges):
    progress.setPercentage(int((100 * enum)/Total2))
    G = edges[FID]
    G=nx.connected_component_subgraphs(G)[0] #Largest Connected Graph
    
    if Threshold !=0:
        G2 = G.copy()
        for n in range(int(Threshold)):      
            degree = G2.degree()
            removeNodes  = [k for k,v in degree.iteritems() if v == 1]
            G2.remove_nodes_from(removeNodes)
        endPoints = [k for k,v in degree.iteritems() if v == 1]   
        data[FID]= set(G2.nodes())
        G.remove_nodes_from(G2.nodes())
        for source in endPoints:
            length,path = nx.single_source_dijkstra(G,source,weight='weight')
            Index = max(length,key=length.get)
            data[FID].update(path[Index])
        del G2
        
    else:
        if Method == 'Loop' or Method == 'Combine':
            curLen = 0
	    G2 = G.copy()
            while len(G2) != curLen:
                curLen = len(G2)
                degree = G2.degree()
                removeNodes = [k for k,v in degree.iteritems() if v == 1]
                G2.remove_nodes_from(removeNodes)
            data[FID]= set(G2.nodes())
            if Method == 'Combine':
		    source = G.nodes()[0]
		    for n in range(2):
			length,path = nx.single_source_dijkstra(G,source,weight='weight')
			Index = max(length,key=length.get)
			source = path[Index][-1]  
		    data[FID].update(path[Index])
	    del G2         

        else:
            source = G.nodes()[0]
            for n in range(2):
                length,path = nx.single_source_dijkstra(G,source,weight='weight')
                Index = max(length,key=length.get)
                source = path[Index][-1]  
            points = [QgsPoint(p[0],p[1]) for p in path[Index]]
            fet.setGeometry(QgsGeometry.fromPolyline(points))
            fet["FID"] = FID
            writer.addFeature(fet)                   
    G.clear()

if Method in ['Loop','Combine'] or Threshold != 0:
	progress.setText('Creating Centerline Segments')
	for enum,feature in enumerate(layer.getFeatures()):
	    try:
		progress.setPercentage(int((100 * enum)/Total))
		FID = feature[Groupby_Field]
		points = feature.geometry().asPolyline()
		
		pnts1 = (round(points[0][0],Point_Precision),round(points[0][1],Point_Precision))
		pnts2 = (round(points[-1][0],Point_Precision),round(points[-1][1],Point_Precision))
		values = data[FID]
		if pnts1 in values and pnts2 in values:
		    fet.setGeometry(feature.geometry())
		    fet["FID"]= FID
		    writer.addFeature(fet)
	    except:
		continue

del writer,edges,data
