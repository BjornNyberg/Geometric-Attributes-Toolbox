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
##Segment_Angle=boolean False

#Algorithm
#==================================
import processing as st
import numpy as np
from math import *
#from cmath import phase,rect
from PyQt4.QtCore import QVariant
from qgis.core import *

layer = st.getobject(Centerline)

if layer.fieldNameIndex("Angle") == -1:
    layer.dataProvider().addAttributes([QgsField("Angle",QVariant.Double)])
if Segment_Angle:
    if layer.fieldNameIndex("Mean_Angle") == -1:
        layer.dataProvider().addAttributes([QgsField("Mean_Angle",QVariant.Double)])
   # if layer.fieldNameIndex("Std_Angle") == -1: #Standard deviation of Angle?
     #   layer.dataProvider().addAttributes([QgsField("Std_Angle",QVariant.Double)])

layer.startEditing()
Total = layer.featureCount()
progress.setText('Calculating Angles')
   
for enum,feature in enumerate(layer.getFeatures()):
    progress.setPercentage(int((100 * enum)/Total))
    points = feature.geometry().asPolyline()
    B_S = []
    startx,starty = None,None
    if Segment_Angle:
        for pnt in points:
            if startx == None:
                startx,starty = pnt[0],pnt[1]
                continue
            endx,endy = pnt[0],pnt[1]
            dx = endx - startx
            dy =  endy - starty
            angle = degrees(atan2(dy,dx))
            B_S.append((90 - angle) % 360)
            startx,starty = pnt[0],pnt[1]
    startx,starty = float(points[0][0]),float(points[0][1])
    endx,endy = float(points[-1][0]),float(points[-1][1])                  
    dx = endx - startx
    dy =  endy - starty
    angle = degrees(atan2(dy,dx))
    Bearing = (90 - angle) % 360
    feature["Angle"] = Bearing
    if Segment_Angle:
        #mean = degrees(phase(sum(rect(1,radians(d)) for d in B_S)/len(B_S))) #Alternative mean angle?
        #if mean < 0: #How to handle negatives?
          #  mean = 360 - fabs(mean)
        x=[]
        y=[]
        for n in B_S:
            x.append(cos(radians(n)))
            y.append(sin(radians(n)))       
        v1,v3 = np.mean(x),np.std(x)
        v2,v4 = np.mean(y),np.std(y)
        if v1 >0 and v2 > 0:
            mean = degrees(atan2(v2,v1))
        elif v1 <0 and v2 > 0:
            mean= fabs(degrees(atan2(v2,v1)))
        elif  v1 < 0 and v2 < 0:
            mean=360 + degrees(atan2(v2,v1))
        else:
            mean= 360-fabs(degrees(atan2(v2,v1)))
        #if v3 >0 and v4 > 0: #Standard Deviation of Angle?
          #  std = degrees(atan2(v4,v3))
        #elif v3 <0 and v4 > 0:
          #  std= fabs(degrees(atan2(v4,v3)))
        #elif  v3 < 0 and v4 < 0:
          #  std=360 + degrees(atan2(v4,v3))
        #else:
        #    std= 360-fabs(degrees(atan2(v4,v3)))
        feature["Mean_Angle"] = float(mean)
      #  feature["Std_Angle"] = float(std)
    layer.updateFeature(feature)
layer.commitChanges()

