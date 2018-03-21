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
##Output_Folder=folder

#Algorithm body
#==================================
import utm,os
import processing as st
from qgis.core import *
from PyQt4.QtCore import *
from processing.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException as pError

south = ['C','D','E','F','G','H','J','K','L','M']

layer = st.getobject(Polygon)

crs = layer.crs()

if crs.authid() != 'EPSG:4326':
    raise pError('%s Coordinate System is not supported - only EPSG:4326 (WGS84) Coordinate System is accepted!'%(crs.authid()))

projections = []
if layer.fieldNameIndex("id") == -1:
    layer.dataProvider().addAttributes([QgsField("id",QVariant.Int)])
if layer.fieldNameIndex("UTM") == -1:
    layer.dataProvider().addAttributes([QgsField("UTM",QVariant.String)])
if layer.fieldNameIndex("Lat_Long") == -1:
    layer.dataProvider().addAttributes([QgsField("Lat_Long",QVariant.String)])

if not os.path.exists(Output_Folder):
    os.mkdir(Output_Folder)

Total = layer.featureCount()
layer.startEditing()
progress.setText('Calculating UTMs')
for enum,feature in enumerate(layer.getFeatures()):
    try:  
        progress.setPercentage(int((100 * enum)/Total))
        pnt = feature.geometry().centroid().asPoint()
        lat,long=pnt.y(),pnt.x()
        lat_long = utm.from_latlon(lat,long)
        if lat_long[3] in south:
            hemisphere = 'S'
        else:
            hemisphere = 'N'
        UTM = '%s%s'%(lat_long[2],hemisphere)
        feature["UTM"] = UTM
        feature["Lat_Long"] = '%s,%s'%(lat,long)
        feature["id"]=enum
        projections.append(UTM)
        layer.updateFeature(feature)
    except Exception:
        continue

layer.commitChanges()
Total = len(projections) 
progress.setText('Repojecting Shapefile(s)')
Count = 0
for UTM in projections:
    try:
        progress.setPercentage(int((100 * Count)/Total))
        Count +=1
        hemisphere = UTM[-1]
        if hemisphere =='S':
            prj = '+proj=utm +zone=%s +ellps=WGS84 +datum=WGS84 +south +units=m +no_defs +towgs84=0,0,0'%(UTM[:2])
        else:
            prj = '+proj=utm +zone=%s +ellps=WGS84 +datum=WGS84 +units=m +no_defs +towgs84=0,0,0'%(UTM[:2])
        crs = QgsCoordinateReferenceSystem()
        crs.createFromProj4(prj)
        crs = crs.authid()

        Out = os.path.join(Output_Folder,'%s.shp'%(UTM))   
        st.runalg("qgis:selectbyattribute",Polygon,"UTM",0,UTM)
        st.runalg("qgis:reprojectlayer",Polygon,crs,Out)
    except Exception:
        continue
