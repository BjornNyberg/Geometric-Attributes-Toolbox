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
##Join_Features=vector
##Target_Feature=vector
##Target_Join_Field=field Target_Feature
##Field=string Field_Name.describe()
##Groupby_Fields=string Join_Field
##Sortby_Optional=string
##Aggregate_Function=string mean

#Algorithm
#==================================

import pysal as ps
import processing as st
from pandas import *
import numpy as np
from qgis.core import *
from PyQt4.QtCore import QVariant

dbf = Join_Features.replace('.shp','.dbf')
dbf = ps.open(dbf)
d = {col: dbf.by_col(col) for col in dbf.header}
df = DataFrame(d)
fields = set([])

progress.setText('Calculating Fields to Update')
data = {}
Groupby_Fields = Groupby_Fields.split(',')
for n,g in df.groupby(Groupby_Fields):  
    if Sortby_Optional:
        g.sort(columns=Sortby_Optional,inplace=True) 
    if type(n) is tuple:
        d = n[0]
        if len(n) == 2:
            FID = str(n[1]).strip('()').replace(',',"")
        else:
            FID = str(n[1]).strip('()').replace(','," ")
    else:
        d,FID = n,n
    if d not in data:
        if '.describe()' in Field:
            data[d] = [eval('g.%s.tolist()'%(Field))]
        else:
            data[d] = [(FID,eval('g.%s.tolist()'%(Field)))]
            if FID not in fields:
                fields.update(FID)
    else:
        if '.describe()' in Field:
            data[d].append(eval('g.%s.tolist()'%(Field)))
        else:
            data[d].append((FID,eval('g.%s.tolist()'%(Field))))
            if FID not in fields:
                fields.update(FID)

layer = st.getobject(Target_Feature)
if '.describe()' in Field:
    fields = [ "t_count","count","mean","std","25%","50%","75%","min","max"]

for field_name in fields:
    if layer.fieldNameIndex(field_name) == -1:
        layer.dataProvider().addAttributes([QgsField(field_name,QVariant.Double)])

layer.startEditing()
progress.setText('Updating Fields')
Total = layer.featureCount()
for enum,feature in enumerate(layer.getFeatures()):
    progress.setPercentage(int((100 * enum)/Total))
    ID = feature[Target_Join_Field]
    if feature[ID] in data:
        value = data[ID]
        if '.describe()' in Field:
            d = zip(*value)
            feature["t_count"]=float(np.sum(d[0]))
            for Count,field_name in enumerate(fields[1:]):
                feature[field_name]=float(eval('np.%s(%s)'%(Aggregate_Function,d[Count])))
        else:
            for d in value:
                feature[str(d[0])]=float(eval('np.%s(%s)'%(Aggregate_Function,d[1])))
        layer.updateFeature(feature)

layer.commitChanges() 
