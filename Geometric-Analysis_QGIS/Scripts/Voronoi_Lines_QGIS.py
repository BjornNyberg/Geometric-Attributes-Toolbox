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
    DensifyGeometriesInterval.py by Anita Graser, Dec 2012
    based on DensifyGeometries.py
    ---------------------
    Date                 : October 2012
    Copyright            : (C) 2012 by Victor Olaya
    Email                : volayaf at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

#==================================
#Definition of inputs and outputs
#==================================

##[SAFARI]=group
##Polygons=vector
##Densify_Interval=number 0
##Tile_Size=number 0
##Output=output vector

#Algorithm body
#==================================

import processing as st
import os
from qgis.core import *
from PyQt4.QtCore import *
from itertools import combinations,chain
from math import sqrt

Precision=5
keepNodes=set([])

progress.setText('Extracting Nodes')
layer2 = st.getobject(Polygons)
Total = layer2.featureCount()

def densify(polyline, interval): #based on DensifyGeometriesInterval.py
    output = []
    for i in xrange(len(polyline) - 1):
        p1 = polyline[i]
        p2 = polyline[i + 1]
        output.append(p1)

        # Calculate necessary number of points between p1 and p2
        pointsNumber = sqrt(p1.sqrDist(p2)) / interval
        if pointsNumber > 1:
            multiplier = 1.0 / float(pointsNumber)
        else:
            multiplier = 1
        for j in xrange(int(pointsNumber)):
            delta = multiplier * (j + 1)
            x = p1.x() + delta * (p2.x() - p1.x())
            y = p1.y() + delta * (p2.y() - p1.y())
            output.append(QgsPoint(x, y))
            if j + 1 == pointsNumber:
                break
    output.append(polyline[len(polyline) - 1])
    return output
    
fields = QgsFields()

tempFile = os.path.join(os.path.dirname(Output),'temp.shp')
writer = QgsVectorFileWriter(tempFile, "CP1250", fields, 1,layer2.crs(), "ESRI Shapefile")
fet = QgsFeature()
selection = layer2.selectedFeatures()
if len(selection)== 0:
    selection = [f for f in layer2.getFeatures()]
    Total = layer2.featureCount()
else:
    Total = len(selection)

for enum,feature in enumerate(selection):
    progress.setPercentage(int((100 * enum)/Total))
    geomType = feature.geometry()
    geom = []
    if geomType.type() == QGis.Polygon:
        if geomType.isMultipart():
            polygons = geomType.asMultiPolygon()
            if Densify_Interval == 0 : 
                geom = chain(*chain(*polygons))
            else:
                for poly in polygons:
                    p = []
                    for ring in poly:
                       p.extend(densify(ring, Densify_Interval))
                    geom.extend(p)
		
        else:
            polygon = geomType.asPolygon()
            if Densify_Interval == 0 : 
                geom = chain(*polygon)
            else:
                for ring in polygon:
                    geom.extend(densify(ring, Densify_Interval))
    for points in geom:
        if (round(points.x(),Precision),round(points.y(),Precision)) not in keepNodes:   
                pnt = QgsGeometry.fromPoint(QgsPoint(points.x(),points.y()))
                fet.setGeometry(pnt)
                writer.addFeature(fet)
                keepNodes.update([(round(points.x(),Precision),round(points.y(),Precision))])
rect = layer2.extent()
extent = [rect.xMinimum(),rect.xMaximum(),rect.yMinimum(),rect.yMaximum()]
combo = combinations(extent,2)

for points in combo:
    pnt = QgsGeometry.fromPoint(QgsPoint(points[0],points[1]))
    fet.setGeometry(pnt)
    writer.addFeature(fet)
del writer

if Tile_Size > 0:
    progress.setText('Tiling Dataset')
    width = (rect.xMaximum() - rect.xMinimum()) / Tile_Size
    height = (rect.yMaximum() - rect.yMinimum()) / Tile_Size
    grid = st.runalg("saga:creategraticule",Polygons,None,width,height,1,None)
    pInter = st.runalg("qgis:intersection",Polygons,grid["GRATICULE"],None)
 
    layer2 = st.getobject(pInter["OUTPUT"])
    selection = [f for f in layer2.getFeatures()]

data = {f.id():f for f in selection}

progress.setText('Creating Voronoi Polygons')
Voronoi = st.runalg("saga:thiessenpolygons",tempFile,None)

field_names = [(field.name(),field.type()) for field in layer2.pendingFields()]
for name,type in field_names:
    fields.append( QgsField(name,type))
    
try:
    os.remove(tempFile) #Remove split centerline data
except Exception:
    pass

progress.setText('Intersecting Lines')
layer = st.getobject(Voronoi["POLYGONS"])

keepNodes=set([])
Total = layer.featureCount()
    
fet = QgsFeature(fields)
writer = QgsVectorFileWriter(Output, "CP1250", fields,2,layer.crs(), "ESRI Shapefile")

index = QgsSpatialIndex()
map(index.insertFeature, selection)

for enum,feature in enumerate(layer.getFeatures()):
    try:
        progress.setPercentage(int((100 * enum)/Total))
	startx = None
	pnts = feature.geometry().asPolygon()
	for point in pnts[0]: #No rings exist in a thiessen polygons
		if startx == None:	
			startx,starty = (round(point[0],Precision),round(point[1],Precision))
			continue
		endx,endy = (round(point[0],Precision),round(point[1],Precision))
		geom = QgsGeometry.fromPolyline([QgsPoint(startx,starty),QgsPoint(endx,endy)])
                if ((startx,starty),(endx,endy)) in keepNodes:
                    startx,starty = endx,endy
                    continue
                keepNodes.update([((endx,endy),(startx,starty))])
                bbox = geom.boundingBox()
                feats = index.intersects(bbox)
		
		for FID in feats:
		    inter = data[FID]
                    try:
                        if geom.within(inter.geometry()): #Reduces the number of lines but will not extent to the edge of the polygon
                            for name,type in field_names:
				fet[name] = inter[name]
                            fet.setGeometry(geom)
                            writer.addFeature(fet)
  
                        elif geom.intersects(inter.geometry()):
                            geom_line = geom.intersection(inter.geometry())
                            for name,type in field_names:
				fet[name] = inter[name]
                            fet.setGeometry(geom_line)
                            writer.addFeature(fet)  
		    except Exception:
			continue

		startx,starty = endx,endy
    except Exception,e:
	progress.setText('%s'%(e))

del writer
