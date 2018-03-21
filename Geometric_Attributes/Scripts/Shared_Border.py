#==================================
#Author Bjorn Burr Nyberg 
#University of Bergen
#Contact bjorn.nyberg@uni.no
#Copyright 2014
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
import networkx as nx
from collections import defaultdict

def main(infc,Class_Name):

    names = set()

    arcpy.AddMessage('Determining Unique Class Names (1/2)')
    for feature in arcpy.da.SearchCursor(infc,['%s'%Class_Name]):
        try:
            fName = str(feature[0]).replace(' ','')
            names.add(fName[:10]) #Field name < 10 characters

        except Exception,e:
            arcpy.AddError('%s'%(e))

    curfields = [f.name for f in arcpy.ListFields(infc)]     
    new_fields = []

    for name in names:
        if name not in curfields:
            arcpy.AddField_management(infc,name,"DOUBLE")
        new_fields.append(name)
            
    new_fields.extend(['%s'%(Class_Name),'OID@','SHAPE@'])
    cursor2 = {f[-2]:f for f in arcpy.da.SearchCursor(infc,new_fields)}
    arcpy.AddMessage('Calculating Shared Border Percentages (2/2)')
    lengths = {} #Store lengths of unique oid pairs
    with arcpy.da.UpdateCursor(infc,new_fields) as cursor:
        for feature in cursor:
            try:
                data = defaultdict(float)

                for feature_key in cursor2.keys():
		    
                    if feature_key != feature[-2]: #Do not intersect with same geometry
                        if (feature[-2],feature_key)in lengths:
                            values = lengths[(feature[-2],feature_key)]
                            try:
                                data[values[1]] += values[0]
                            except Exception,e:
                                arcpy.AddError('%s'%(e))
                                continue
                        else:    
                            feature2 = cursor2[feature_key]
                            if not feature[-1].disjoint(feature2[-1]): #Check if they intersect

                                if feature[-1].area < feature2[-1].area:
                                    geom = feature[-1].buffer(0.1).intersect(feature2[-1],4) #Get geometry - if topologically correct dataset use feature[-1].buffer(0.1).intersect(feature2[-1],2)
                                else:
                                    geom = feature2[-1].buffer(0.1).intersect(feature[-1],4) #Get geometry - if topologically correct dataset use feature[-1].intersect(feature2[-1],2)
                                fName = str(feature2[-3]).replace(' ','')
                                Class = fName[:10]

                                fName2 = str(feature[-3]).replace(' ','')
                                Class2 = fName2[:10]
                                try:
                                    length = geom.length/2 	#if topologically correct dataset use geom.length
                                    data[Class] += length
                                    lengths[(feature_key,feature[-2])] = (length,Class2) 
                                except Exception,e: # No length? possible collapsed polygon/point
                                    arcpy.AddError('%s'%(e))
                                    continue
                
                datasum = feature[-1].length
                for k,v in data.iteritems():
                    FID = new_fields.index(k)
                    feature[FID]=round(float(v/datasum)*100,2)

                diff = names - set(data.keys())

                for k in diff:
                    FID = new_fields.index(k)
                    feature[FID]= 0.0
                cursor.updateRow(feature)

            except Exception,e:
                arcpy.AddError('%s'%(e))
                continue
    del cursor2
if __name__ == "__main__":        

    #==================================

    #Definition of inputs and outputs
    #==================================

    infc=arcpy.GetParameterAsText(0)
    Class_Name=arcpy.GetParameterAsText(1)
    
    main(infc,Class_Name)
