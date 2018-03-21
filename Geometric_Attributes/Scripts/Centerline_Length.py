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


#Algorithm body
import arcpy
import networkx as nx

def main(infc):

    curfields = curfields = [f.name for f in arcpy.ListFields(infc)]

    fields = ["Distance","RDistance","DCoordx","DCoordy","RDCoordx","RDCoordy"]
    for field in fields:
        if field not in curfields:
            arcpy.AddField_management(infc,field,"DOUBLE")


    edges = {}
    arcpy.AddMessage('Calculating Edges (1/2)')

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

    fields.extend(['id','SHAPE@'])
    Lengths = {}
    arcpy.AddMessage('Updating Features (2/2)')
    with arcpy.da.UpdateCursor(infc,fields) as cursor:
        for feature in cursor:
            try:
                start = feature[-1].firstPoint
                end = feature[-1].lastPoint
                startx,starty =(start.X,start.Y)
                endx,endy =(end.X,end.Y)
        
                ID = feature[6]
                if ID not in Lengths:
                    G = edges[ID]
                    Source = G.nodes()[0]
                    for n in range(2):
                        Length,Path = nx.single_source_dijkstra(G,Source,weight='weight')
                        Index = max(Length,key=Length.get)
                        Source = Path[Index][-1]
                    Lengths[ID] = [Length]
                    Length,Path = nx.single_source_dijkstra(G,Source,weight='weight')
                    G.clear()
                    Lengths[ID].append(Length)
                    
                L = [Lengths[ID][0][(endx,endy)],Lengths[ID][0][(startx,starty)]]
                if L[0] > L[1]:
                    sx = startx
                    sy = starty
                    ex = endx
                    ey = endy
                else:
                    sx = endx
                    sy = endy
                    ex = startx
                    ey = starty
                L2 = [Lengths[ID][1][(endx,endy)],Lengths[ID][1][(startx,starty)]]

                feature[0]=max(L)
                feature[1]=max(L2)
                feature[2]=ex 
                feature[3]=ey
                feature[4]=sx
                feature[5]=sy

                cursor.updateRow(feature)
            except Exception,e: #No Connection?
                arcpy.AddError('%s'%(e))
                continue

if __name__ == "__main__":        

    #==================================

    #Definition of inputs and outputs
    #==================================
    inFC=arcpy.GetParameterAsText(0)

    main(inFC)
