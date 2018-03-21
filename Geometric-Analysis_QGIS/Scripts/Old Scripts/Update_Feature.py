#==================================
#Author Bjorn Burr Nyberg / bjorn.nyberg@uni.no
#University of Bergen
#==================================

#Definition of inputs and outputs
#==================================
##[SAFARI]=group
##Join_Features=vector
##Target_Feature=vector
##Target_Join_Field=field Target_Feature
##Update_Field=string New/Update Field
##Expression=string Field_Name.mean()
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
        d=n[0]
    else: 
        d= n
    value = eval('g.%s.tolist()'%(Expression))
    if d not in data:  
        if type(value) == float:
            data[d]=[value]
        else:
            data[d] = value
    else:
        if type(value) == float:
            data[d].append(value)
        else:
            data[d].extend(value)

layer = st.getobject(Target_Feature)

if layer.fieldNameIndex(Update_Field) == -1:
    layer.dataProvider().addAttributes([QgsField(Update_Field,QVariant.Double)])
Total = layer.featureCount()
progress.setText('Updating Fields')
layer.startEditing()
for enum,feature in enumerate(layer.getFeatures()):
    progress.setPercentage(int((100 * enum)/Total))
    if feature[Target_Join_Field] in data:
        value = data[feature[Target_Join_Field]]
        feature[Update_Field]=float(eval('np.%s(%s)'%(Aggregate_Function,value)))
        layer.updateFeature(feature)
layer.commitChanges() 
