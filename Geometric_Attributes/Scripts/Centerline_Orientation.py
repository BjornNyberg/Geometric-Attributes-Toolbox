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

import arcpy
from math import sqrt

def main(infc,Depo_Dir,Calc_AD):

    fields = ["id","Distance","RDistance","DCoordx","DCoordy",'RDCoordx','RDCoordy','NEAR_FID','NEAR_DIST','AlongDist','SHAPE@','OID@']
    fields2 = ['OID@','SHAPE@','Distance']
    if Calc_AD == 'false':
        fields2.remove('Distance')
        
    curfields = curfields = [f.name for f in arcpy.ListFields(infc)]   
    if 'AlongDist' not in curfields:
            arcpy.AddField_management(infc,'AlongDist',"DOUBLE")
        
    comparisonA, comparisonB, change,DistData = {},{},[],{}
    
    arcpy.Near_analysis(infc,Depo_Dir)

    arcpy.AddMessage('Orienting Centerlines (1/2)')
    sr=arcpy.Describe(Depo_Dir).spatialReference
    data = {f[0]:f for f in arcpy.da.SearchCursor(Depo_Dir,fields2)}
    with arcpy.da.UpdateCursor(infc,fields) as cursor:
        for feature in cursor:
            try:
       
                ID = feature[0]
                
                if ID in comparisonA and ID in comparisonB:
                    continue
                else:    
                    pnt = arcpy.PointGeometry(arcpy.Point(feature[3],feature[4]),sr)
                    geom = feature[-2]
                    if round(geom.length,2) == round(feature[1],2) or round(geom.length,2) == round(feature[2],2):   
                        dist = 100000000000.0
                        
                        for f2 in data:
                            feature2 = data[f2]
                            value = feature2[1].distanceTo(pnt)
                            if value < dist:
                                dist = value
                                if Calc_AD != 'false':
                                    AlongDist = feature2[2]
                        if Calc_AD != 'false':
                            dist = AlongDist
                                
                        if round(geom.length,2) == round(feature[1],2):
                            comparisonA[ID] = dist
                        else:
                            comparisonB[ID] = dist
                            
                        if ID in comparisonA and ID in comparisonB:
                            if comparisonB[ID] < comparisonA[ID]:
                                change.append(ID)
                                
                if Calc_AD == 'true':
                    values = data[feature[-5]]
                    feature[-3] = values[-1]
                else:
                    feature[-3] = feature[-4]
                    
                cursor.updateRow(feature) 
                    
            except Exception,e:
                arcpy.AddError('%s'%(e))
                continue
    del data

    if change:
        arcpy.AddMessage('Updating Centerlines (2/2)')
        with arcpy.da.UpdateCursor(infc,fields) as cursor:
            for feature in cursor:
                try:
                    if feature[0] in change:
                        D = feature[1]
                        D2 = feature[2]
                        sx = feature[3] 
                        sy = feature[4] 
                        ex = feature[5] 
                        ey = feature[6]
                        
                        feature[1] = D2
                        feature[2] = D
                        
                        feature[3] = ex
                        feature[4] = ey
                        feature[5] = sx
                        feature[6] = sy

                        cursor.updateRow(feature)
                except Exception,e:
                    arcpy.AddError('%s'%(e))
                    continue
    try:
        arcpy.DeleteField_management(infc,['NEAR_DIST','NEAR_FID'])
    except Exception, e:
        arcpy.AddMessage('%s'%(e))
    
if __name__ == "__main__":        

    #==================================

    #Definition of inputs and outputs
    #==================================
    inFC=arcpy.GetParameterAsText(0)
    direction=arcpy.GetParameterAsText(1)
    calc=arcpy.GetParameterAsText(2)

    main(inFC,direction,calc)
