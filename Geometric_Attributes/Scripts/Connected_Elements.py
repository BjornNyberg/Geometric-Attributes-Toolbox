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

def main(infc):

    curfields = [f.name for f in arcpy.ListFields(infc)]      
    new_fields = ['Connection','Neighbour']
    for field in new_fields:
        if field not in curfields:
            if field == 'Connection':
                arcpy.AddField_management(infc,field,"SHORT")
            else:
                arcpy.AddField_management(infc,field,"TEXT")

    new_fields.extend(['OID@','SHAPE@'])
    
    arcpy.AddMessage('Calculating Connected Elements (1/2)')
    Graph = nx.Graph()
    cursor = {f[-2]:f for f in arcpy.da.SearchCursor(infc,new_fields)}
    
    for feature in arcpy.da.SearchCursor(infc,new_fields):
        try:

             Graph.add_edge(feature[-2],feature[-2])

             for feature_key in cursor.keys():
                 if feature_key != feature[-2]: #Do not intersect with same geometry
                    feature2 = cursor[feature_key]
                    if not feature[-1].disjoint(feature2[-1]): #Check if they intersect
                        Graph.add_edge(feature[-2],feature2[-2])

        except Exception,e:
             arcpy.AddError('%s'%(e))
             continue
    del cursor
    subGraphs = nx.connected_component_subgraphs(Graph)

    Graphs = list(subGraphs)

    arcpy.AddMessage('Updating Features (2/2)')

    with arcpy.da.UpdateCursor(infc,['OID@','Connection','Neighbour']) as cursor2:
        for feature3 in cursor2:
            for enum,G in enumerate(Graphs): #Update features    
                 if feature3[0] in G:
                     feature3[1]=enum+1
                     nbs = G.neighbors(feature3[0])
                     nbs.remove(feature3[0])
                     feature3[2]= ','.join(str(n) for n in nbs)
                     cursor2.updateRow(feature3)
                     break

if __name__ == "__main__":        

    #==================================

    #Definition of inputs and outputs
    #==================================
    infc=arcpy.GetParameterAsText(0)
    
    main(infc)
