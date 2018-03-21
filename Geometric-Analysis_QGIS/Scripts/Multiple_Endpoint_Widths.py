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
##Max_Width=number 2500
##Join_Mask_By=field Centerline
##Width=output vector

#Algorithm body
#==================================
from qgis.core import *
from PyQt4.QtCore import *
import networkx as nx
import processing as st
from math import sqrt,degrees,atan2,floor,atan,radians,tan,fabs

Point_Precision=5
Lengths = {}

layer = st.getobject(Centerline)
layer2 = st.getobject(Mask)
field_names = ['Distance','RDistance','Width','Diff']
fields = QgsFields()
fields.append( QgsField('FID', QVariant.Int ))
fields.append( QgsField('Mask_FID', QVariant.Int ))

for name in field_names:
    fields.append( QgsField(name, QVariant.Double ))

edges = {}
feats = {f["FID"]:f for f in layer2.getFeatures()} #Get Geometries of Mask Feature

layer.startEditing()
layer.commitChanges() #Force creation of fields mentioned above
Total = layer.featureCount()
progress.setText('Calculating Edges')
for enum,feature in enumerate(layer.getFeatures()):
    progress.setPercentage(int((100 * enum)/Total))
    try:
        points = feature.geometry().asPolyline()
        pnts1 = round(points[0][0],Point_Precision),round(points[0][1],Point_Precision)
        pnts2 = round(points[-1][0],Point_Precision),round(points[-1][1],Point_Precision)
        
        Length = feature.geometry().length()
        ID = feature[Join_Mask_By]
        if ID in edges:
            edges[ID].append((pnts1,pnts2,Length))
        else:
            edges[ID] = [(pnts1,pnts2,Length)]
    except Exception:
        continue ##Possible Collapsed Polyline?

writer = QgsVectorFileWriter(Width, "CP1250", fields, layer.dataProvider().geometryType(),layer.crs(), "ESRI Shapefile")

fet = QgsFeature(fields)

G = nx.Graph()

progress.setText('Calculating Width & Centerline Deviation')
for enum,feature in enumerate(layer.getFeatures()):
    try:
        progress.setPercentage(int((100 * enum)/Total))
        pnt = feature.geometry().asPolyline()
        startx,starty = round(pnt[0][0],Point_Precision),round(pnt[0][1],Point_Precision)
        midx,midy = round(pnt[-1][0],Point_Precision),round(pnt[-1][1],Point_Precision)
        
        geom1 = QgsGeometry.fromPoint(QgsPoint(midx,midy))
        geom2 = geom1
        
        m = ((starty - midy)/(startx - midx)) #Slope
        inter = feats[feature[Join_Mask_By]]

        Distance = Max_Width

        if startx==midx: #if vertical
            x1,y1 = midx+Distance,midy
            x2,y2 = midx - Distance,midy
        else:
            m = ((starty - midy)/(startx - midx)) #Slope
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

        L_ID = feature[Join_Mask_By]
        L_ID2 = '%sB'%(L_ID)
        if L_ID  not in Lengths:
            G.add_weighted_edges_from(edges[L_ID])
	    Source = G.nodes()[0]
            for n in range(2):
                Length,Path = nx.single_source_dijkstra(G,Source,weight='weight')
                Index = max(Length,key=Length.get)
                Source = Path[Index][-1]
            Lengths[L_ID] = Length
            Length,Path = nx.single_source_dijkstra(G,Source,weight='weight')
            Lengths[L_ID2] = Length
            G.clear()
            
        Widths = [geom1.length(),geom2.length()]   
            
        W = geom.length()

        D= Lengths[L_ID][(midx,midy)]
        D2=Lengths[L_ID2][(midx,midy)]    
        
        fet["FID"]=feature["FID"]
        fet["Mask_FID"]=L_ID
        fet["Width"]=W
        fet["Diff"]= 100-(min(Widths)/max(Widths))*100
        fet["Distance"]=D
        fet["RDistance"]=D2

        writer.addFeature(fet)

    except Exception,error:
        progress.setText('%s'%(error))
        continue
del writer
