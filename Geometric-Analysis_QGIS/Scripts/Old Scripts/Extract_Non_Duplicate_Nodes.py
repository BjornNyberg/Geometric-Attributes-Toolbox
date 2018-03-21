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
##Polygon=vector
##Precision=number 2
##Output=output vector

#Algorithm body
#==================================
from qgis.core import *
from PyQt4.QtCore import *
from itertools import chain
import processing as st

keepNodes = set([])
layer = st.getobject(Polygon)

fields = QgsFields()
fields.append( QgsField( "id", QVariant.Int ))
crs = layer.crs()

writer = QgsVectorFileWriter(Output, "CP1250", fields, 1,layer.crs(), "ESRI Shapefile")
fet = QgsFeature()
Total = layer.featureCount()
progress.setText('Extracting Nodes')
for enum,feature in enumerate(layer.getFeatures()):
    progress.setPercentage(int((100 * enum)/Total))
    geomType = feature.geometry()
    if geomType.type() == QGis.Polygon:
        if geomType.isMultipart():
            geom = geomType.asMultiPolygon()
            geom = list(chain(*chain(*geom)))
        else:
            geom = geomType.asPolygon()
            geom = list(chain(*geom))
    elif geomType.type() == QGis.Line:
        if geomType.isMultipart():
            geom = geomType.asMultiPolyline()
            geom = list(chain(*geom))
        else:
            geom = geomType.asPolyline()
    for points in geom:
        if (round(points.x(),Precision),round(points.y(),Precision)) not in keepNodes:   
                pnt = QgsGeometry.fromPoint(QgsPoint(points.x(),points.y()))
                fet.setGeometry(pnt)
                writer.addFeature(fet)
                keepNodes.update([(round(points.x(),Precision),round(points.y(),Precision))])

del writer
            
