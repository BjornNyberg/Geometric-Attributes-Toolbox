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

import arcpy,os
arcpy.env.overwriteOutput= True

def main(inFC,Output):
    try:
 
        fields = [f.name for f in arcpy.ListFields(inFC)]

        if 'id' not in fields:
	    try:
            	arcpy.AddField_management(inFC,"id",'LONG')
            	arcpy.CalculateField_management(inFC, 'id', "!FID!", "PYTHON_9.3", "")
	    except:
		pass
            
        #Variables
        temp = 'in_memory\\tempdata'
        temp2 = 'in_memory\\tempdata2'
        arcpy.AddMessage('Converting Features to Points (1/5)')
        arcpy.FeatureVerticesToPoints_management(inFC,temp, "ALL")
        arcpy.AddMessage('Calculating Thiessen Polygons (2/5)')
        arcpy.CreateThiessenPolygons_analysis(temp, temp2, "ONLY_FID")
        arcpy.AddMessage('Converting Polygons to Lines (3/5)')
        arcpy.PolygonToLine_management(temp2, temp)

        arcpy.AddMessage('Intersecting Features (4/5)')
        arcpy.Intersect_analysis([temp, inFC], temp2, "ALL")
        arcpy.AddMessage('Creating Singlepart Features (5/5)')
        arcpy.MultipartToSinglepart_management(temp2, Output)


        fieldNames = []
        for field in arcpy.ListFields(Output):
            if not field.required and field.name != 'id':
                fieldNames.append(field.name)
        arcpy.DeleteField_management(Output,fieldNames)

    except Exception,e:
        arcpy.AddError('%s'%(e))


if __name__ == "__main__":        
    ###Inputs###
    inFC = arcpy.GetParameterAsText(0)
    Output = arcpy.GetParameterAsText(1)

    main(inFC,Output)
