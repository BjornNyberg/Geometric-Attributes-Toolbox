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

"""
***************************************************************************
    Densify script based on DensifyGeometriesInterval.py by Anita Graser and 
    DensifyGeometries.py by Victor Olaya
    ---------------------
***************************************************************************
"""
    
import os, sys, math
import processing as st
import networkx as nx
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsVectorLayer, QgsSpatialIndex, QgsField,QgsVectorFileWriter, QgsProcessingParameterBoolean, QgsFeature, QgsPointXY, QgsProcessingParameterNumber, QgsProcessingParameterString, QgsProcessing,QgsWkbTypes, QgsGeometry, QgsProcessingAlgorithm, QgsProcessingParameterFeatureSource, QgsProcessingParameterFeatureSink,QgsFeatureSink,QgsFeatureRequest,QgsFields,QgsProperty)
from itertools import combinations,chain
from math import sqrt

class Centerlines(QgsProcessingAlgorithm):

    Polygons='Polygons'
    Method='Method'
    Densify='Line Spacing'
    Output='Centerlines'
    
    def __init__(self):
        super().__init__()
        
    def name(self):
        return "Centerlines"

    def tr(self, text):
        return QCoreApplication.translate("Centerlines", text)

    def displayName(self):
        return self.tr("Centerlines")
 
    def group(self):
        return self.tr("Algorithms")
    
    def shortHelpString(self):
        return self.tr('Calculate centerlines of each polygon. Available methods: 1. Centerlines, 2. All, 3. Circles, 4. A number (e.g., 5)')

    def groupId(self):
        return "Algorithms"
    
    def helpUrl(self):
        return "https://github.com/BjornNyberg/Geometric-Attributes-Toolbox/blob/master/Datasets/README.pdf"
    
    def createInstance(self):
        return type(self)()
    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Polygons,
            self.tr("Polygons"),
            [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterString(
            self.Method,
            self.tr("Method"),'Centerlines'))
        self.addParameter(QgsProcessingParameterNumber(
            self.Densify,
            self.tr("Line Spacing"),
            QgsProcessingParameterNumber.Double,
            0.0))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.Output,
            self.tr("Centerlines"),
            QgsProcessing.TypeVectorLine))
    

    def processAlgorithm(self, parameters, context, feedback):
        
        layer = self.parameterAsVectorLayer(parameters, self.Polygons, context)
        Method = parameters[self.Method]
        
        def densify(polyline, interval): #based on DensifyGeometriesInterval.py
            output = []
            for i in range(len(polyline) - 1):
                p1 = polyline[i]
                p2 = polyline[i + 1]
                output.append(p1)

                # Calculate necessary number of points between p1 and p2
                pointsNumber = math.sqrt(p1.sqrDist(p2)) / interval
                if pointsNumber > 1:
                    multiplier = 1.0 / float(pointsNumber)
                else:
                    multiplier = 1
                for j in range(int(pointsNumber)):
                    delta = multiplier * (j + 1)
                    x = p1.x() + delta * (p2.x() - p1.x())
                    y = p1.y() + delta * (p2.y() - p1.y())
                    output.append(QgsPointXY(x, y))
                    if j + 1 == pointsNumber:
                        break
            output.append(polyline[len(polyline) - 1])
            return output
            
        field_check =layer.fields().indexFromName('ID')
            
        if field_check == -1:   
            pr = layer.dataProvider()
            pr.addAttributes([QgsField("ID", QVariant.Int)])
            layer.updateFields() 
            
        layer.startEditing()
        for feature in layer.getFeatures():
            feature['ID'] = feature.id()
            layer.updateFeature(feature)
        layer.commitChanges()
            
        fet = QgsFeature()
        fields = QgsFields()
        fields.append(QgsField("ID", QVariant.Int))  
        field_names = ['Distance','RDistance','SP_Dist','SP_RDist']

        for name in field_names:
            fields.append( QgsField(name, QVariant.Double ))

        fet2 = QgsFeature(fields)
        (writer2, dest_id) = self.parameterAsSink(parameters, self.Output, context,
                                               fields, QgsWkbTypes.LineString, layer.sourceCrs())
                                       
        if dest_id.endswith('.shp'):
            dirname = dest_id[:-4]
        else:
            dirname = dest_id
        infc = r'%s%s'%(dirname,'P.shp')
        layer2 = QgsVectorLayer(infc)
        Densify_Interval = parameters[self.Densify]
        
        Precision=5
    
        keepNodes= set([])
        fields = QgsFields()
        fields.append(QgsField("ID", QVariant.Int))  
        writer = QgsVectorFileWriter(infc, "CP1250", fields, QgsWkbTypes.Point, layer.sourceCrs(), "ESRI Shapefile") #.shp requirement of SAGA
        
        feedback.pushInfo(QCoreApplication.translate('Update','Creating Vertices'))
        total = 100.0/layer.featureCount()
        
        for enum,feature in enumerate(layer.getFeatures()):
            if total != -1: 
                feedback.setProgress(int(enum*total))

            geomType = feature.geometry()
            geom = []
            if geomType.wkbType() == QgsWkbTypes.Polygon:
                polygon = geomType.asPolygon()
                if Densify_Interval == 0 : 
                    geom = chain(*polygon)
                else:
                    for ring in polygon:
                        geom.extend(densify(ring, Densify_Interval))  
            else:
                polygons = geomType.asMultiPolygon()
                if Densify_Interval == 0 : 
                    geom = chain(*chain(*polygons))
                else:
                    for poly in polygons:
                        p = []
                        for ring in poly:
                           p.extend(densify(ring, Densify_Interval))
                        geom.extend(p)
            for points in geom:
                if (round(points.x(),Precision),round(points.y(),Precision)) not in keepNodes:   
                    pnt = QgsGeometry.fromPointXY(QgsPointXY(points.x(),points.y()))
                    fet.setGeometry(pnt)
                    fet.setAttributes([feature['ID']])
                    writer.addFeature(fet)
                    keepNodes.update([(round(points.x(),Precision),round(points.y(),Precision))])

        feedback.pushInfo(QCoreApplication.translate('Update','Creating Voronoi Polygons'))
        del writer
        
        tempVP = r'%s%s'%(dirname,'VL.shp') #.shp requirement of SAGA

        param = {'POINTS':infc,'POLYGONS':tempVP,'FRAME':10.0}  
        Voronoi = st.run("saga:thiessenpolygons",param,context=context,feedback=feedback)   
        
        del keepNodes
        edges = {}
        
        feedback.pushInfo(QCoreApplication.translate('Update','Calculating Edges'))

        param = {'INPUT':Voronoi['POLYGONS'],'OUTPUT':'memory:'}
        lines = st.run("qgis:polygonstolines",param,context=context,feedback=feedback)
        param = {'INPUT':lines['OUTPUT'],'OUTPUT':'memory:'}
        exploded = st.run("native:explodelines",param,context=context,feedback=feedback)
        param = {'INPUT':exploded['OUTPUT'],'PREDICATE':6,'INTERSECT':layer,'METHOD':0}
        st.run("native:selectbylocation",param,context=context,feedback=feedback)              
        total = 100.0/exploded['OUTPUT'].featureCount()
        
        for enum,feature in enumerate(exploded['OUTPUT'].selectedFeatures()):
            try:
                if total != -1: 
                    feedback.setProgress(int(enum*total))
                part = feature.geometry().asPolyline()
                startx = None
                for point in part: 
                    if startx == None:	
                        startx,starty = (round(point.x(),Precision),round(point.y(),Precision))
                        continue
                    endx,endy = (round(point.x(),Precision),round(point.y(),Precision))
                    geom = QgsGeometry.fromPolylineXY([QgsPointXY(startx,starty),QgsPointXY(endx,endy)])
                    ID = feature['ID']
                    Length = geom.length()
                    if ID in edges:
                        edges[ID].add_edge((startx,starty),(endx,endy),weight=Length)
                    else:
                        Graph = nx.Graph()
                        Graph.add_edge((startx,starty),(endx,endy),weight=Length)
                        edges[ID] = Graph
                    startx,starty = endx,endy
                    
            except Exception as e:
                feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
                
            try:
                os.remove(tempVP)
                os.remove(P)
            except Exception:
                pass

        feedback.pushInfo(QCoreApplication.translate('Update','Calculating %s Centerlines' %(len(edges))))

        if edges:
            total = 100.0/len(edges)
            for enum,FID in enumerate(edges):
        
                feedback.setProgress(int(enum*total))
                G = edges[FID]
                G=max(nx.connected_component_subgraphs(G), key=len) #Largest Connected Graph
                
                if Method.isdigit():
                    Threshold = int(Method)
                    G2 = G.copy()
                    G3 = G.copy()
                    for n in range(int(Threshold)):      
                        removeNodes  = [k for k,v in G2.degree() if v == 1]
                        G2.remove_nodes_from(removeNodes)
  
                    endPoints = [k for k,v in G2.degree() if v == 1] 
        
                    G3.remove_edges_from(G2.edges)
                    
                    for source in endPoints:
                        length,path = nx.single_source_dijkstra(G3,source,weight='weight')
                        Index = max(length,key=length.get)
                        sx = None
                        G2.add_path(path[Index])
                        
                    del G3
                    
                    source = list(G2.nodes())[0] #Get length along all paths
                    for n in range(2):
                        length,path = nx.single_source_dijkstra(G,source,weight='weight')
                        Index = max(length,key=length.get)
                        source = path[Index][-1] 
                    length2,path2 = nx.single_source_dijkstra(G,source,weight='weight')
                    
                    for p in G2.edges:
                        points = []
                        points.append(QgsPointXY(p[0][0],p[0][1]))
                        points.append(QgsPointXY(p[1][0],p[1][1]))
                        
                        D = max([length[(p[0][0],p[0][1])],length[(p[1][0],p[1][1])]])
                        D2= max([length2[(p[0][0],p[0][1])],length2[(p[1][0],p[1][1])]])
                        
                        dx = path[Index][0][0] - p[1][0]
                        dy =  path[Index][0][1] - p[1][1]
                        dx2 = path[Index][0][0] - p[0][0]
                        dy2 =  path[Index][0][1] - p[0][1]
                        SP = max([math.sqrt((dx**2)+(dy**2)),math.sqrt((dx2**2)+(dy2**2))])

                        dx = path[Index][-1][0] - p[1][0]
                        dy =  path[Index][-1][1] - p[1][1]
                        dx2 = path[Index][-1][0] - p[0][0]
                        dy2 =  path[Index][-1][1] - p[0][1]
                        SP2 = max([math.sqrt((dx**2)+(dy**2)),math.sqrt((dx2**2)+(dy2**2))])

                        fet2.setGeometry(QgsGeometry.fromPolylineXY(points))
                        fet2.setAttributes([FID,D,D2,SP,SP2])
                        writer2.addFeature(fet2)
   
                    del G2    
              
                elif Method == 'All':
                       
                    curLen = 0
                    G2 = G.copy()
                    while len(G2) != curLen:
                        curLen = len(G2)
                        removeNodes = [k for k,v in G2.degree() if v == 1]
                        G2.remove_nodes_from(removeNodes)
              
                    source = list(G.nodes())[0]
                    for n in range(2):
                        length,path = nx.single_source_dijkstra(G,source,weight='weight')
                        Index = max(length,key=length.get)
                        source = path[Index][-1]  

                    G2.add_path(path[Index])
                    
                    source = list(G2.nodes())[0] #Get length along all paths
                    for n in range(2):
                        length,path = nx.single_source_dijkstra(G,source,weight='weight')
                        Index = max(length,key=length.get)
                        source = path[Index][-1] 
                    length2,path2 = nx.single_source_dijkstra(G,source,weight='weight')
                    
                    for p in G2.edges:
                        points = []
                        points.append(QgsPointXY(p[0][0],p[0][1]))
                        points.append(QgsPointXY(p[1][0],p[1][1]))
                        
                        D = max([length[(p[0][0],p[0][1])],length[(p[1][0],p[1][1])]])
                        D2= max([length2[(p[0][0],p[0][1])],length2[(p[1][0],p[1][1])]])
                        
                        dx = path[Index][0][0] - p[1][0]
                        dy =  path[Index][0][1] - p[1][1]
                        dx2 = path[Index][0][0] - p[0][0]
                        dy2 =  path[Index][0][1] - p[0][1]
                        SP = max([math.sqrt((dx**2)+(dy**2)),math.sqrt((dx2**2)+(dy2**2))])

                        dx = path[Index][-1][0] - p[1][0]
                        dy =  path[Index][-1][1] - p[1][1]
                        dx2 = path[Index][-1][0] - p[0][0]
                        dy2 =  path[Index][-1][1] - p[0][1]
                        SP2 = max([math.sqrt((dx**2)+(dy**2)),math.sqrt((dx2**2)+(dy2**2))])

                        fet2.setGeometry(QgsGeometry.fromPolylineXY(points))
                        fet2.setAttributes([FID,D,D2,SP,SP2])
                        writer2.addFeature(fet2)
                     
                    del G2       
                  
                
                elif Method == 'Circles':
                       
                    curLen = 0
                    G2 = G.copy()
                    while len(G2) != curLen:
                        curLen = len(G2)
                        degree = G2.degree()
                        removeNodes = [k for k,v in G2.degree() if v == 1]
                        G2.remove_nodes_from(removeNodes)

                    for p in G2.edges:
                        points = []
                        points.append(QgsPointXY(p[0][0],p[0][1]))
                        points.append(QgsPointXY(p[1][0],p[1][1]))

                        fet2.setGeometry(QgsGeometry.fromPolylineXY(points))
                        fet2.setAttributes([FID])
                        writer2.addFeature(fet2)
                     
                    del G2       
     
   
                else:
                    source = list(G.nodes())[0]
                    for n in range(2):
                        length,path = nx.single_source_dijkstra(G,source,weight='weight')
                        Index = max(length,key=length.get)
                        source = path[Index][-1] 
                    length2,path2 = nx.single_source_dijkstra(G,source,weight='weight')
                    sx = None
                    for p in path[Index]:
                        if sx == None:
                            sx,sy = p[0], p[1]
                            continue
                        ex,ey = p[0],p[1]    
                        D = max([length[(sx,sy)],length[(ex,ey)]])
                        D2= max([length2[(sx,sy)],length2[(ex,ey)]])
                        dx = path[Index][0][0] - ex
                        dy =  path[Index][0][1] - ey
                        dx2 = path[Index][0][0] - sx
                        dy2 =  path[Index][0][1] - sy
                        SP = max([math.sqrt((dx**2)+(dy**2)),math.sqrt((dx2**2)+(dy2**2))])

                        dx = path[Index][-1][0] - ex
                        dy =  path[Index][-1][1] - ey
                        dx2 = path[Index][-1][0] - sx
                        dy2 =  path[Index][-1][1] - sy
                        SP2 = max([math.sqrt((dx**2)+(dy**2)),math.sqrt((dx2**2)+(dy2**2))])
                        
                        points = [QgsPointXY(sx,sy),QgsPointXY(ex,ey)]
                        fet2.setGeometry(QgsGeometry.fromPolylineXY(points))
                        fet2.setAttributes([FID,D,D2,SP,SP2])
                        writer2.addFeature(fet2)
                        sx,sy = ex,ey
               
                G.clear()

            
        del writer2,edges
        
        return {self.Output:dest_id}
