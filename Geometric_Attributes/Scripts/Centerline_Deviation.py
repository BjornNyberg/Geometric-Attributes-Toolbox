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



import networkx as nx
import os
from math import sqrt


def main(infc):

    curfields = [f.name for f in arcpy.ListFields(infc)]
    for field in curfields:
        if 'Deviation' not in curfields:
            arcpy.AddField_management(infc,'Deviation',"DOUBLE")
    fields = ['id','Distance','RDistance','RDCoordx','RDCoordy','DCoordx','DCoordy','SHAPE@','Deviation']
    SP = {}
    SP2 = {}
    arcpy.AddMessage('Calculating ShortestPath (1/2)')
    for feature in arcpy.da.SearchCursor(infc, fields):
        try:
            geom = feature[7].length
            if round(geom,2) == round(feature[1],2): 
                SP[feature[0]]=[feature[3],feature[4]]
            if round(geom,2) == round(feature[2],2):
                SP2[feature[0]]=[feature[5],feature[6]]
                
        except Exception,e:
            arcpy.AddError('%s'%(e))
            continue
      
    arcpy.AddMessage('Calculating Centerline Deviation (2/2)')
    with arcpy.da.UpdateCursor(infc,fields) as cursor:
        for feature in cursor:
            try:
                midx,midy = feature[5],feature[6]

                startx,starty=(SP[feature[0]][0],SP[feature[0]][1])
                endx,endy =(SP2[feature[0]][0],SP2[feature[0]][1])

                dx = startx-endx
                dy = starty-endy

                m = (dx**2)+ (dy**2)

                u = ((midx - startx) * (endx - startx) + (midy - starty) * (endy - starty))/(m)
                x = startx + u * (endx - startx)
                y = starty + u * (endy - starty)
                d = ((endx-startx)*(midy-starty) - (endy - starty)*(midx - startx)) #Determine which side of the SP the symmetry occurs

                if u > 1:
                    u = 1
                elif u < 0:
                    u = 0

                dx = x - midx
                dy =  y - midy
                
                dist = sqrt((dx**2)+(dy**2))

                if d < 0:
                    DW = -(dist)
                else:
                    DW = dist
                feature[-1]=DW
                cursor.updateRow(feature)


            except Exception,e:
                arcpy.AddError('%s'%(e))
                continue


if __name__ == "__main__":        

    #==================================

    #Definition of inputs and outputs
    #==================================
    inFC=arcpy.GetParameterAsText(0)
    
    main(inFC)
