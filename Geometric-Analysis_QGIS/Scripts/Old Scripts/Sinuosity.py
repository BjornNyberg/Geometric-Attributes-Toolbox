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
#Algorithm
#==================================
import processing as st
from PyQt4.QtCore import QVariant
from qgis.core import *
from math import sqrt

layer = st.getobject(Centerline)
if layer.fieldNameIndex("Sinuosity") == -1:
    layer.dataProvider().addAttributes([QgsField("Sinuosity",QVariant.Double)])
Total = layer.featureCount()
layer.startEditing()
progress.setText('Calculating Sinuosity')
for enum,feature in enumerate(layer.getFeatures()):
    progress.setPercentage(int((100 * enum)/Total))
    points= feature.geometry().asPolyline()

    startx,starty = float(points[0][0]),float(points[0][1])
    endx,endy = float(points[-1][0]),float(points[-1][1])
                    
    dx = endx - startx
    dy =  endy - starty
                    
    shortestPath = sqrt((dx**2)+(dy**2))

    Sinuosity = feature.geometry().length()/shortestPath
    feature["Sinuosity"] = Sinuosity

    layer.updateFeature(feature)

layer.commitChanges()

