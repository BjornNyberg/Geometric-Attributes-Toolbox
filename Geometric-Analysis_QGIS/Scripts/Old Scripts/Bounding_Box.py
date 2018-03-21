#==================================
#Author Bjorn Burr Nyberg
#University of Bergen
#Contact bjorn.nyberg@uni.no
#Copyright 2013
#Modified from http://ceg-sense.ncl.ac.uk/geoanorak/code/pythontransects.html
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
##Feature=vector

#Algorithm body
#==================================
import processing as st
from qgis.core import *
from PyQt4.QtCore import *

layer = st.getobject(Feature)
if layer.fieldNameIndex("bbox_w") == -1:
    layer.dataProvider().addAttributes([QgsField("bbox_w",QVariant.Double)])
if layer.fieldNameIndex("bbox_h") == -1:
    layer.dataProvider().addAttributes([QgsField("bbox_h",QVariant.Double)])

Total = layer.featureCount()
progress.setText('Calculating Bounding Box')
layer.startEditing()
for enum,feature in enumerate(layer.getFeatures()):
        progress.setPercentage(int((100 * enum)/Total))
	bbox = feature.geometry().boundingBox()
	feature["bbox_w"]=bbox.width()
	feature["bbox_h"]=bbox.height()
	layer.updateFeature(feature)

layer.commitChanges()
