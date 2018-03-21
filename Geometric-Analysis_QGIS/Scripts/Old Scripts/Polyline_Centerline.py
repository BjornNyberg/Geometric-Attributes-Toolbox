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
##Groupby_Field=field Voronoi_Lines
##Seed=number 1
##Output=output vector

#Algorithm body
#==================================
import networkx as nx
import processing as st
from qgis.core import *
from PyQt4.QtCore import QVariant

layer = st.getobject(Voronoi_Lines)

Total = layer.featureCount()
edges = {}
progress.setText('Calculating Edges')
for enum,feature in enumerate(layer.getFeatures()):
    try:
        progress.setPercentage(int((100 * enum)/Total))
        points = feature.geometry().asPolyline()
        pnts1 = (float(points[0][0]),float(points[0][1]))
        pnts2 = (float(points[-1][0]),float(points[-1][1]))
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
if Method == 'All':
    fields.append( QgsField('Code', QVariant.Int ))
crs = layer.crs()

writer = QgsVectorFileWriter(Output, "CP1250", fields, layer.dataProvider().geometryType(),layer.crs(), "ESRI Shapefile")

progress.setText('Calculating Shortest Paths')
Total2 = len(edges)
data = set([])
fet = QgsFeature(fields)
for enum,FID in enumerate(edges):
    G = edges[FID]
    progress.setPercentage(int((100 * enum)/Total2))
    if Method == 'InteriorLoop':
        curLen = 0
        while len(G) != curLen:
            curLen = len(G)
            degree = G.degree()
            keepNodes = [k for k,v in degree.iteritems() if v == 1]
            G.remove_nodes_from(keepNodes)
        data.update(G.nodes())
    else:
        if len(G.nodes()) < Seed:
            Seed == len(G.nodes())/2
        source = G.nodes()[Seed]
        for n in range(2):
            length,path = nx.single_source_dijkstra(G,source,weight='weight')
            Index = max(length,key=length.get)
            source = path[Index][-1]  
        if Method =='ShortestPath':
            points = [QgsPoint(p[0],p[1]) for p in path[Index]]
            fet.setGeometry(QgsGeometry.fromPolyline(points))
            fet[0] = FID
            writer.addFeature(fet)
        elif Method == 'LongestPath':
            paths=nx.all_simple_paths(G,path[Index][0],path[Index][-1])
            path = max(paths,key=len)
            points = [QgsPoint(p[0],p[1]) for p in path]
            fet.setGeometry(QgsGeometry.fromPolyline(points))
            fet[0] = FID
            writer.addFeature(fet)      
        elif Method == 'AllPaths':
            paths=nx.all_simple_paths(G,path[Index][0],path[Index][-1])
            for path in paths:
                points = [QgsPoint(p[0],p[1]) for p in path]
                fet.setGeometry(QgsGeometry.fromPolyline(points))
                fet[0] = FID
                writer.addFeature(fet) 
        else:
            paths=nx.all_simple_paths(G,path[Index][0],path[Index][-1])         
            paths = list(paths) #Extremely slow!!!
            s = [set(s) for s in paths]
            inter = set(path[Index]).intersection(*s)
            points = []
            if Method == 'Intersect':
                for p in path[Index]:
                    if p in inter:
                        points.append(QgsPoint(p[0],p[1]))
                    else:
                        if len(points) > 1:
                            fet.setGeometry(QgsGeometry.fromPolyline(points))
                            fet[0] = FID
                            writer.addFeature(fet)
                            points = []
                if len(points) > 1:
                    fet.setGeometry(QgsGeometry.fromPolyline(points))
                    fet[0] = FID
                    writer.addFeature(fet)
            elif Method == 'Difference':
                prevPnts = []
                for path in paths:
                    prevPnt = False
                    for p in path:
                        if p not in inter and p not in prevPnts:
                            if prevPnt:
                                points.append(prevPnt) #Add startpoint
                            points.append(QgsPoint(p[0],p[1]))
                            prevPnt = None
                            prevPnts.append(p)
                        else:
                            if prevPnt == None:
                                points.append(QgsPoint(p[0],p[1])) #Add endpoint
                            prevPnt = QgsPoint(p[0],p[1])
                            if len(points) > 1:
                                fet.setGeometry(QgsGeometry.fromPolyline(points))
                                fet[0] = FID
                                writer.addFeature(fet)            
                            points = []
                    if len(points) > 1:
                        fet.setGeometry(QgsGeometry.fromPolyline(points))
                        fet[0] = FID
                        writer.addFeature(fet)                      
                        points = [] 
            elif Method == 'All':
                prevPnts,prevPnts2 = [],[]
                prevPnt = False
                paths.append(path[Index]) #append rather than find minimum len of paths to retain the weight argument used in the graph
                for cycle,path in enumerate(reversed(paths)): #reverse list to start with the the ShortestPath
                    points,points2 = [],[]                   
                    for p in path:
                        if p not in inter and p not in prevPnts:
                            if len(points2) > 1:
                                fet.setGeometry(QgsGeometry.fromPolyline(points2))
                                fet[0] = FID
                                fet[1] = 0
                                writer.addFeature(fet)
                                points2 = []       
                            if prevPnt:
                                points.append(prevPnt) #Add startpoint
                            points.append(QgsPoint(p[0],p[1]))
                            prevPnt = None
                            prevPnts.append(p)
                        else:
                            if prevPnt == None:
                                points.append(QgsPoint(p[0],p[1])) #Add endpoint
                            prevPnt = QgsPoint(p[0],p[1])
                            if len(points) > 1:
                                fet.setGeometry(QgsGeometry.fromPolyline(points))
                                fet[0] = FID
                                if cycle == 0:
                                    fet[1] = 1
                                else:
                                    fet[1] = 2
                                writer.addFeature(fet)
                            points = []
                            if p not in prevPnts and p not in prevPnts2:
                                points2.append(prevPnt)
                                prevPnts2.append(p)
                    if len(points) > 1:
                        fet.setGeometry(QgsGeometry.fromPolyline(points))
                        fet[0] = FID
                        if cycle == 0:
                            fet[1] = 1
                        else:
                            fet[1] = 2
                        writer.addFeature(fet)
                        points = [] 
                    if len(points2) > 1:
                        fet.setGeometry(QgsGeometry.fromPolyline(points2))
                        fet[0] = FID
                        fet[1] = 0
                        writer.addFeature(fet)
                        points2 = []            
    G.clear()

if Method == 'InteriorLoop':
    progress.setText('Creating Centerline Segments')
    for enum,feature in enumerate(layer.getFeatures()):
        progress.setPercentage(int((100 * enum)/Total))
        points = feature.geometry().asPolyline()
        if len(points) != 2: #Possible Collapsed Polyline?
            continue
        pnts1 = (float(points[0][0]),float(points[0][1]))
        pnts2 = (float(points[-1][0]),float(points[-1][1]))
        if pnts1 in data and pnts2 in data:
            points = [QgsPoint(pnts1[0],pnts1[1]),QgsPoint(pnts2[0],pnts2[1])]
            fet.setGeometry(QgsGeometry.fromPolyline(points))
            fet[0] = feature[Groupby_Field]
            writer.addFeature(fet)

del writer
