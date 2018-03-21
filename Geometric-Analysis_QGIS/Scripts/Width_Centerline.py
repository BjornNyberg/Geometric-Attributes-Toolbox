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
##Mask=vector
##Split_by_Distance=string 1000
##Cutoff_Limit=string
##Width=output vector
##Symmetry=output vector

#Algorithm body
#==================================
from qgis.core import *
from PyQt4.QtCore import *
import networkx as nx
import processing as st
from math import sqrt,degrees,atan2,floor,atan,radians,tan,fabs

Point_Precision=5
Lengths = {}

progress.setText('Splitting Lines')
    
SC = st.runalg("grass:v.split.length",Centerline,eval(Split_by_Distance),None,None,None,2,None) #Split Centerlines

layer = st.getobject(SC["output"])
layer2 = st.getobject(Mask)
layer3 = st.getobject(Centerline)

field_names = ['Distance','RDistance','SP_Dist','SP_RDist','Width','Deviation','DWidth','DWidth2','Diff','Angle','Sinuosity','Centerline']
fields = QgsFields()
fields.append( QgsField('FID', QVariant.Int ))

for name in field_names:
    fields.append( QgsField(name, QVariant.Double ))

edges = {}
feats = {f["FID"]:f for f in layer2.getFeatures()} #Get Geometries of Mask Feature
ShortestPaths = {f["FID"]:f for f in layer3.getFeatures()} #Get Geometries of Original Centerline

Total = layer.featureCount()
progress.setText('Calculating Edges')
for enum,feature in enumerate(layer.getFeatures()):
    progress.setPercentage(int((100 * enum)/Total))
    try:
        points = feature.geometry().asPolyline()
        pnts1 = round(points[0][0],Point_Precision),round(points[0][1],Point_Precision)
        pnts2 = round(points[-1][0],Point_Precision),round(points[-1][1],Point_Precision)
        
        Length = feature.geometry().length()
        ID = feature["FID"]
        if ID in edges:
            edges[ID].append((pnts1,pnts2,Length))
        else:
            edges[ID] = [(pnts1,pnts2,Length)]
    except Exception:
        continue ##Possible Collapsed Polyline?
        

writer = QgsVectorFileWriter(Width, "CP1250", fields, layer.dataProvider().geometryType(),layer.crs(), "ESRI Shapefile")
fields2 = QgsFields()
fields2.append( QgsField('FID', QVariant.Int ))

field_names2 = ['Distance','RDistance','Width']
for name in field_names2:
    fields2.append( QgsField(name, QVariant.Double ))
    
writer2 = QgsVectorFileWriter(Symmetry, "CP1250", fields2, layer.dataProvider().geometryType(),layer.crs(), "ESRI Shapefile")

fet = QgsFeature(fields)
fet2 = QgsFeature(fields2)

G = nx.Graph()
ID = None

progress.setText('Calculating Width & Centerline Deviation')
for enum,feature in enumerate(layer.getFeatures()):
    try:
        progress.setPercentage(int((100 * enum)/Total))
        pnt = feature.geometry().asPolyline()
        curID = feature["FID"]
        if ID != curID:
            startx,starty = round(pnt[0][0],Point_Precision),round(pnt[0][1],Point_Precision)
            midx,midy = round(pnt[-1][0],Point_Precision),round(pnt[-1][1],Point_Precision)
            ID = curID
            Reverse_Test = True #Should a reverse test be performed?
            if Cutoff_Limit:
                Counter = 1
                Limit = floor((len(edges[curID]))/float(Cutoff_Limit))
            continue
        
        endx,endy = round(pnt[-1][0],Point_Precision),round(pnt[-1][1],Point_Precision)
        if Cutoff_Limit:
            if Counter <= Limit:
                startx,starty = midx,midy
                midx,midy = endx,endy
                Counter += 1
                continue

        m = ((starty - endy)/(startx - endx)) #Slope

        inter = feats[curID]
        
        Distance = inter.geometry().boundingBox().width()/2

        if startx==endx: #if vertical
            x1,y1 = midx+Distance,midy
            x2,y2 = midx - Distance,midy
        else:
            m = ((starty - endy)/(startx - endx)) #Slope
            angle = degrees(atan(m)) + 90

            m = tan(radians(angle)) #Angle to Slope
            c,s = (1/sqrt(1+m**2),m/sqrt(1+m**2)) #cosine and sin
            x1,y1 = (midx + Distance*(c),midy + Distance*(s))
            x2,y2 = (midx - Distance*(c),midy - Distance*(s))
        geom = QgsGeometry.fromPolyline([QgsPoint(x1,y1),QgsPoint(midx,midy),QgsPoint(x2,y2)])
        geom= geom.intersection(inter.geometry())
        if geom.isMultipart():
            polyline = geom.asMultiPolyline()
            for line in polyline:
                if len(line)==3: 
                    start,mid,end = line
                    geom1 = QgsGeometry.fromPolyline([QgsPoint(start[0],start[1]),QgsPoint(mid[0],mid[1])])
                    geom2 = QgsGeometry.fromPolyline([QgsPoint(mid[0],mid[1]),QgsPoint(end[0],end[1])])
                    geom = QgsGeometry.fromPolyline([QgsPoint(start[0],start[1]),QgsPoint(mid[0],mid[1]),QgsPoint(end[0],end[1])])
                    break
        else:
            line = geom.asPolyline()
            geom1 = QgsGeometry.fromPolyline([QgsPoint(line[0][0],line[0][1]),QgsPoint(line[1][0],line[1][1])])
            geom2 = QgsGeometry.fromPolyline([QgsPoint(line[1][0],line[1][1]),QgsPoint(line[2][0],line[2][1])])		

        fet.setGeometry(geom)        
        curID2 = '%sB'%(curID)
        if curID not in Lengths:
            G.add_weighted_edges_from(edges[curID])
            Source = G.nodes()[0]
            for n in range(2):
                Length,Path = nx.single_source_dijkstra(G,Source,weight='weight')
                Index = max(Length,key=Length.get)
                Source = Path[Index][-1]
            Lengths[curID] = Length
            Length,Path = nx.single_source_dijkstra(G,Source,weight='weight')
            Lengths[curID2] = Length
            G.clear()

        Widths = [geom1.length(),geom2.length()]   
        Centerline_Geom = ShortestPaths[curID].geometry()

	if Centerline_Geom.isMultipart():
		SP_Points = Centerline_Geom.asMultiPolyline()
		s=QgsPoint(SP_Points[0][0])
		e=QgsPoint(SP_Points[-1][-1])
	else:
		SP_Points = Centerline_Geom.asPolyline()
		s=QgsPoint(SP_Points[0])
		e=QgsPoint(SP_Points[-1])

        m = s.sqrDist(e)
        u = ((midx - s.x()) * (e.x() - s.x()) + (midy - s.y()) * (e.y() - s.y()))/(m)
        x = s.x() + u * (e.x() - s.x())
        y = s.y() + u * (e.y() - s.y())
        d = ((e.x()-s.x())*(midy-s.y()) - (e.y() - s.y())*(midx - s.x())) #Determine which side of the SP the symmetry occurs
        sym = QgsGeometry.fromPolyline([QgsPoint(x,y),QgsPoint(midx,midy)]) 
        
	dx = s.x() - e.x()
        dy =  s.y() - e.y()
        shortestPath = sqrt((dx**2)+(dy**2))

	dx = s.x() - x
        dy =  s.y() - y
        shortestPath1 = sqrt((dx**2)+(dy**2))

	dx = e.x() - x
        dy =  e.y() - y
        shortestPath2 = sqrt((dx**2)+(dy**2))

	if shortestPath < shortestPath1:
		sym = QgsGeometry.fromPolyline([QgsPoint(e.x(),e.y()),QgsPoint(midx,midy)]) 		

        angle = degrees(atan2(dy,dx))
        Bearing = (90 - angle) % 360

        fet2.setGeometry(sym)

        if d < 0:
            DW = -(geom2.length())
        else:
            DW = geom2.length()
            
        W = geom.length()
        Centerline_Dist = Centerline_Geom.length()
        
        if Reverse_Test: #Apply Centerline Correction
            D= Lengths[curID2][(midx,midy)]
            D2=Lengths[curID][(midx,midy)]
            d_diff=  fabs(D - shortestPath1) #Difference between centerline and SP distances
            d_diff1=  fabs(D2 - shortestPath2)
            if d_diff < d_diff1: #Reverse Centerline Distances if needed to match SP Distances
                Reverse = True
            else:
                Reverse = False
        
        if Reverse:
            D= Lengths[curID2][(midx,midy)]
            D2=Lengths[curID][(midx,midy)]
        else:
            D= Lengths[curID][(midx,midy)]
            D2=Lengths[curID2][(midx,midy)]    
        
        fet["FID"]=curID
        fet["Width"]=W
        fet["DWidth"]=(W/2)+DW
        fet["DWidth2"]=-(W/2)+DW
        fet["Deviation"]=DW
        fet["Diff"]= 100-(min(Widths)/max(Widths))*100
        fet["Distance"]=D
        fet["RDistance"]=D2
        fet["Angle"]=round(Bearing,2)
        fet["Sinuosity"]=Centerline_Dist/shortestPath
        fet["Centerline"]=Centerline_Dist
        fet["SP_Dist"]= round(shortestPath1,2)
        fet["SP_RDist"]= round(shortestPath2,2)

        fet2["FID"]=curID
        fet2["Width"]= round(W,2)
        fet2["Distance"]= round(shortestPath1,2)
        fet2["RDistance"]= round(shortestPath2,2)

        startx,starty = midx,midy
        midx,midy = endx,endy
        writer.addFeature(fet)
        writer2.addFeature(fet2)
        
        Reverse_Test = False # One reverse test per curID
        Counter = 1
    except Exception,e:
        startx,starty = midx,midy
        midx,midy = endx,endy
        progress.setText('%s'%(e))
        continue
del writer,writer2