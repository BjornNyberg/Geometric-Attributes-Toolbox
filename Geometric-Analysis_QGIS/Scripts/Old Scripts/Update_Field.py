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
##Feature=vector
##Update_Field=string NewField
##Expression=string rolling_mean(df.Field_Name,5)
##Groupby_Optional=string 
##Sortby_Optional=string 

#Algorithm
#==================================
import pysal as ps
import processing as st
from itertools import izip
from pandas import *
from qgis.core import *
from PyQt4.QtCore import QVariant

dbf = Feature.replace('.shp','.dbf')
dbf = ps.open(dbf)
d = {col: dbf.by_col(col) for col in dbf.header}
df = DataFrame(d)
layer = st.getobject(Feature)

progress.setText('Calculating Fields to Update')
if Groupby_Optional:
    data = {}
    for n,g in df.groupby(Groupby_Optional.split(',')):   
        if Sortby_Optional:
            g.sort(columns=Sortby_Optional,inplace=True)
        data.update(dict(izip(g.index,eval(Expression))))
else:
    if Sortby_Optional:
         df.sort(columns=Sortby_Optional,inplace=True)
    data = dict(izip(df.index,eval(Expression)))

if layer.fieldNameIndex(Update_Field) == -1:
    layer.dataProvider().addAttributes([QgsField(Update_Field,QVariant.Double)])

progress.setText('Updating Fields')
Total = layer.featureCount()
layer.startEditing()
for enum,feature in enumerate(layer.getFeatures()):
    progress.setPercentage(int((100 * enum)/Total))
    if feature.id() in data:
        value = data[feature.id()]   
        feature[Update_Field]=float(value)
        layer.updateFeature(feature)

layer.commitChanges() 
