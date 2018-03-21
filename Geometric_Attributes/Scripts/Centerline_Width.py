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

import arcpy,os
from math import sqrt

def main(infc,mask):

    arcpy.FeatureToLine_management([mask],'in_memory\\templines',
                               "0.001 Meters", "ATTRIBUTES")
    dname = os.path.dirname(infc)
    arcpy.CreateFeatureclass_management('in_memory','temppoints',"POINT",'','','',infc)
    arcpy.AddField_management('in_memory\\temppoints','FID',"LONG")
    
    cursor = arcpy.da.InsertCursor('in_memory\\temppoints',['SHAPE@','FID'])
    fields = ['id','DCoordx','DCoordy','OID@']
    for row in arcpy.da.SearchCursor(infc,fields):
        data = [[row[1],row[2]],row[-1]]
        cursor.insertRow(data)
    
    arcpy.Near_analysis('in_memory\\temppoints', 'in_memory\\templines')

   
    curfields = [f.name for f in arcpy.ListFields(infc)]
    if 'Width' not in curfields:
        arcpy.AddField_management(infc,'Width',"DOUBLE")
    fields.append('Width')
   
    data = {f[0]:f[1] for f in arcpy.da.SearchCursor('in_memory\\temppoints',['FID','NEAR_DIST'])}

    sr=arcpy.Describe(mask).spatialReference
    with arcpy.da.UpdateCursor(infc,fields) as cursor:
        for feature in cursor:
            try:
                feature[-1] = data[feature[-2]] * 2
                cursor.updateRow(feature)
            except Exception,e: #No Connection?
                arcpy.AddError('%s'%(e))
                continue

if __name__ == "__main__":        

    #==================================

    #Definition of inputs and outputs
    #==================================
    inFC=arcpy.GetParameterAsText(0)
    mask=arcpy.GetParameterAsText(1)

    main(inFC,mask)

    
