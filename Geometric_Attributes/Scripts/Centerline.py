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
import os,arcpy

def main(infc,Threshold,outfc):

    edges = {}
    arcpy.AddMessage('Calculating Edges (1/3)')
    for feature in arcpy.da.SearchCursor(infc,['SHAPE@','id']):
        try:
            start = feature[0].firstPoint
            end = feature[0].lastPoint
            pnts1,pnts2 = [(start.X,start.Y),(end.X,end.Y)]
            Length = feature[0].length
            ID = feature[1]
            if ID in edges:
                edges[ID].add_edge(pnts1,pnts2,weight=Length)
            else:
                Graph = nx.Graph()
                Graph.add_edge(pnts1,pnts2,weight=Length)
                edges[ID] = Graph
        except Exception,e:
            arcpy.AddError('%s'%(e))
    data = {}

    arcpy.AddMessage('Calculating Shortest Paths (2/3)')
    Threshold = int(Threshold)
    
    for FID in edges:
        try:
            G = edges[FID]
            G = max(nx.connected_component_subgraphs(G),key=len) #Largest Connected Graph

            source = G.nodes()[0]
            for n in range(2):
                length,path = nx.single_source_dijkstra(G,source,weight='weight')          
                Index = max(length,key=length.get)
                source = path[Index][-1]
            data[FID]=path[Index]
            
            if Threshold > 0:
                G2 = G.copy()
                for n in range(int(Threshold)):      
                    degree = G2.degree()
                    removeNodes  = [k for k,v in degree.iteritems() if v == 1]
                    G2.remove_nodes_from(removeNodes)
                endPoints = [k for k,v in degree.iteritems() if v == 1]   
                data[FID]= set(G2.nodes())
                G.remove_nodes_from(G2.nodes())
                for source in endPoints:
                    length,path = nx.single_source_dijkstra(G,source,weight='weight')
                    Index = max(length,key=length.get)
                    data[FID].update(path[Index])
                del G2
                
        except Exception,e:
            arcpy.AddError('%s'%(e))  
 
    
    if data:

        dirname = os.path.dirname(outfc)
        basename = os.path.basename(outfc)
        if len(dirname) == 0:
            dirname = arcpy.env.scratchWorkspace
        
        arcpy.CreateFeatureclass_management(dirname,basename,"POLYLINE",'','','',infc)

            
        fields= ['id','SHAPE@']
        cursor = arcpy.da.InsertCursor(outfc,fields)
        
    
        curfields = [field.name for field in arcpy.ListFields(outfc)]

    	fields = ['id','Distance','RDistance','DCoordx','DCoordy','RDCoordx','RDCoordy','Deviation','Width', 'AlongDist']

    	for field in fields:
            if field not in curfields:
		try:
                    arcpy.AddField_management(outfc,field,"DOUBLE")
		except Exception,e:
		    arcpy.AddError('%s'%(e))
                    pass
                

        arcpy.AddMessage('Creating Centerline Segments (3/3)')
        for feature in arcpy.da.SearchCursor(infc,['SHAPE@','id']):
            try:
                FID = feature[1]
                if FID in data:
                    start = feature[0].firstPoint
                    end = feature[0].lastPoint
                    pnts = [(start.X,start.Y),(end.X,end.Y)]
                    pnts1,pnts2 = pnts
                
                    if pnts1 in data[FID] and pnts2 in data[FID]:
                        update_data = [FID,pnts]
                        cursor.insertRow(update_data)
            except Exception,e:
                arcpy.AddError('%s'%(e))
                continue 


if __name__ == "__main__":        

    #==================================

    #Definition of inputs and outputs
    #==================================
    inFC=arcpy.GetParameterAsText(0)
    Threshold=arcpy.GetParameterAsText(1)
    Output=arcpy.GetParameterAsText(2)

    main(inFC,Threshold,Output)


