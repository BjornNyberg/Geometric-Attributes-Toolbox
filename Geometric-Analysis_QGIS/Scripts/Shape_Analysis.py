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
##Width_Symmetry=vector
##Update_Feature=vector
##Name_Field_Optional=string
##Sinuous_Threshold=string 0.2
##Symmetry_Threshold=string 0.2
##Linear_Threshold=string 0.5
##Crescentric_Threshold=string 1
##Directional=boolean True

#==================================
import processing as st
import pysal as ps
import numpy as np
from scipy import stats
from itertools import izip
from math import fabs
from pandas import DataFrame
from qgis.core import *
from PyQt4.QtCore import *

dbf = Width_Symmetry.replace('.shp','.dbf')
dbf = ps.open(dbf)
d = {col: dbf.by_col(col) for col in dbf.header}
df = DataFrame(d)

data = {}
Groups = df.groupby("FID")
Total = len(Groups)
Counter = 0
progress.setText('Calculating Fields')
for name,g in Groups:
    try:
        progress.setPercentage(int((100 * Counter)/Total))
        Counter += 1

        x = [n/g.Distance.max() for n in g.Distance]
        y = [n/g.Width.max() for n in g.Width]
        
        m, intercept, r_value, p_value, std_err = stats.linregress(x,y)
        r2=r_value**2
        
        xMax = g.Deviation.abs().max()     
        x = [n/xMax for n in g.Deviation if n > 0]
        x2 = [-(n/-xMax) for n in g.Deviation if n < 0] 
        
        mm = [float(len(x)),float(len(x2))] #min and max values
        mm = min(mm)/max(mm)  
        c=xMax/(g.Width.max()/2)

        Class = ''

        if c > eval(Crescentric_Threshold): 
            if mm < eval(Sinuous_Threshold):
                if fabs(m) > eval(Symmetry_Threshold):
                    Class = "C AS"
                elif r2 > eval(Linear_Threshold):
                    Class = "C L"    
                else:
                    Class = "C S"
            else:
                if fabs(m) > eval(Symmetry_Threshold):
                    Class = "S AS"
                elif r2 > eval(Linear_Threshold):
                    Class = "S L"    
                else:
                    Class = "S S"
        else:
            if fabs(m) > eval(Symmetry_Threshold):
                Class = "E AS"
            elif r2 > eval(Linear_Threshold):
                Class = "E L"               
            else:
                Class= "E S"

        if Directional:
            if fabs(m) > eval(Symmetry_Threshold):
		    if m > 0:
			Class = ' '.join([Class,'1'])
		    else:
			Class = ' '.join([Class,'0'])
    
        data[name] = (g.Width.max(),c,mm,g.Centerline.max(),g.Sinuosity.max(),g.Angle.max(),fabs(m),r2,xMax,Class)

    except Exception,e:
        progress.setText('%s'%(e))
        continue

del df

layer = st.getObject(Update_Feature)
field_names = [('Max_Width',QVariant.Double),('CRatio',QVariant.Double),('CProp',QVariant.Double),('Length',QVariant.Double),('Sinuosity',QVariant.Double),('Angle',QVariant.Double),('Slope',QVariant.Double),('r2',QVariant.Double),('Deviation',QVariant.Double),('Class_Name',QVariant.String)]
for name,type in field_names:
    if layer.fieldNameIndex(name) == -1:
        layer.dataProvider().addAttributes([QgsField(name,type)])

layer.startEditing()
Total = layer.featureCount()
for enum,feature in enumerate(layer.getFeatures()):
    try:
        progress.setPercentage(int((100 * Counter)/Total))
        values = data[feature["FID"]]
        for d,v in zip(field_names[:-1],values[:-1]):
            feature[d[0]]=float(v)
            layer.updateFeature(feature)
        feature[field_names[-1][0]]=values[-1]
        layer.updateFeature(feature)
    except Exception,e:
        progress.setText('%s'%(e))
        continue
layer.commitChanges()
