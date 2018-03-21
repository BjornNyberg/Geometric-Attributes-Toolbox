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

import arcpy
import numpy as np
import math
#from scipy import stats

def main(infc,polygons,Directional):

    #==================================

    #Advanced parameters
    Sinuous_Threshold= 0.2
    Symmetry_Threshold=0.2
    Linear_Threshold= 0.5
    Crescentric_Threshold= 1

    #==================================

    SampleN =  {}
    data_width = {}
    data_deviation = {}
    data_distance = {}
     
    Counter = 0
    arcpy.AddMessage('Grouping Fields (1/3)')
    with arcpy.da.SearchCursor(infc,['id','Width','Deviation','Distance']) as cursor:
	for feature in cursor:
            try:
                ID = feature[0]
                if ID not in data_width:
                    data_width[ID] = [feature[1]]
                    data_deviation[ID] = [feature[2]]
                    data_distance[ID] = [feature[3]]
                else:

                    data_width[ID].append(feature[1])
                    data_deviation[ID].append(feature[2])
                    data_distance[ID].append(feature[3])
                    
                Counter += 1

            except Exception,e:
                arcpy.AddError('%s'%(e))
                continue

    data= {}


    arcpy.AddMessage('Calculating Fields (2/3)')
    for name in data_width:
        try:

            x = [n/max(data_distance[name]) for n in data_distance[name]]

            y = [n/max(data_width[name]) for n in data_width[name]]

            #m, intercept, r_value, p_value, std_err = stats.linregress(x,y)
	    m,r_value = 1,0.5
            r2=r_value**2

            xMax = max(math.fabs(a) for a in data_deviation[name])
            
            x = [n/xMax for n in data_deviation[name] if n > 0]
            
            x2 = [-(n/-xMax) for n in data_deviation[name] if n < 0] 
     
            mm = [float(len(x)),float(len(x2))] #min and max values
            mm = min(mm)/max(mm)

            c=xMax/(max(data_width[name])/2)


            Class = ''

            if c > Crescentric_Threshold: 
                if mm < Sinuous_Threshold:
                    if math.fabs(m) > Symmetry_Threshold:
                        Class = "C AS"
                    elif r2 > Linear_Threshold:
                        Class = "C L"    
                    else:
                        Class = "C S"
                else:
                    if math.fabs(m) > Symmetry_Threshold:
                        Class = "S AS"
                    elif r2 > Linear_Threshold:
                        Class = "S L"    
                    else:
                        Class = "S S"
            else:
                if math.fabs(m) > Symmetry_Threshold:
                    Class = "E AS"
                elif r2 > Linear_Threshold:
                    Class = "E L"               
                else:
                    Class= "E S"

            if Directional == 'true':
                if math.fabs(m) > Symmetry_Threshold:
                        if m > 0:
                            Class = ' '.join([Class,'1'])
                        else:
                            Class = ' '.join([Class,'0'])
        
            data[name] = (max(data_width[name]),max(data_distance[name]),xMax,c,r2,math.fabs(m),mm,Class)

        except Exception,e:
            arcpy.AddError('%s'%(e))
            continue
            
    arcpy.AddMessage('Updating Fields (3/3)')    
    fields = ['MW','Length','MD','CT','LT','SymT','SinT','Class']

    curfields = [f.name for f in arcpy.ListFields(polygons)]
    for field in fields:
        if field not in curfields:
            if field == 'Class':
                arcpy.AddField_management(polygons,field,"TEXT")
            else:
                arcpy.AddField_management(polygons,field,"DOUBLE")

    arcpy.AddMessage('%s'%(fields))
      
    fields.append('id')
    with arcpy.da.UpdateCursor(polygons,fields) as cursor:
        for feature in cursor:
            try:
		if feature[-1] in data: 
                    values = data[feature[-1]]
                    for enum,v in enumerate(values[:-1]):
                        feature[enum]=float(v)
                    feature[7]=values[-1]
                    cursor.updateRow(feature)
 
            except Exception,e:
                arcpy.AddError('%s'%(e))
                continue


if __name__ == "__main__":        

    #==================================

    #Definition of inputs and outputs
    #==================================
    inFC=arcpy.GetParameterAsText(0)
    polygons=arcpy.GetParameterAsText(1)
    Directional=arcpy.GetParameterAsText(2)

    main(inFC,polygons,Directional)

