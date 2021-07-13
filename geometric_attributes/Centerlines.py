#==================================

#Author Bjorn Burr Nyberg
#University of Bergen
#Contact bjorn.nyberg@uib.no
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

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import *
from itertools import combinations,chain
from math import sqrt,fabs

class Centerlines(QgsProcessingAlgorithm):

    Polygons='Polygons'
    Method='Method'
    Densify='Line Spacing'
    Simplify = 'Simplify'
    T = 'Trim Iterations'
    tField ='Trim Field'
    dField ='Densify Field'
    sField = 'Simplify Field'
    Output='Centerlines'

    def __init__(self):
        super().__init__()

    def name(self):
        return "Centerlines"

    def tr(self, text):
        return QCoreApplication.translate("Centerlines", text)

    def displayName(self):
        return self.tr("Centerlines")

    def group(self):
        return self.tr("Polygon Tools")

    def shortHelpString(self):
        return self.tr('''Calculate centerline(s) of each polygon. Available methods: 1. 'Centerlines' will calculate the shortest path between start and endpoint. 2. 'All' will calculate all shortest path(s) between start and endpoint. 3. 'Circles' will calculate all circles (or loops) within a polygon.
        Alternatively a number (e.g., 50) can be provided in the 'Trim Iterations' option which will calculate all shortest paths from all the start points generated after trimming dangles from the voronoi lines by N iterations.
        Simplify Vertex Spacing will simplify the input polygon geometry by applying the Douglas-Peucker algorithm. A simplified polygon will reduce the accuracy for the centerline in favor of processing time. Densify Vertex Spacing will densify vertices along the input polygon geometry to create a more accurate centerline at the expensive of computational time. Hint - apply a simplify and densify option to produce a simplified and smoothed centerline representation.
        Output will calculate the distance (Distance), reverse distance (RDistance), shortest path distance (SP_Dist) and reverse shortest path distance (SP_RDist) from the centerline(s) startpoint.
        Use the Help button for more information.
        ''')

    def groupId(self):
        return "Polygon Tools"

    def helpUrl(self):
        return "https://github.com/BjornNyberg/Geometric-Attributes-Toolbox/wiki"

    def createInstance(self):
        return type(self)()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Polygons,
            self.tr("Polygons"),
            [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterEnum(self.Method,
                                self.tr('Centerlines'), options=[self.tr("Centerlines"),self.tr("All"),self.tr("Circles")],defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            self.T,
            self.tr("Trim Iterations"),
            QgsProcessingParameterNumber.Double,
            0.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.Simplify,
            self.tr("Simplify Vertex Spacing"),
            QgsProcessingParameterNumber.Double,
            0.0,minValue=0.0,optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            self.Densify,
            self.tr("Densify Vertex Spacing"),
            QgsProcessingParameterNumber.Double,
            0.0,minValue=0.0,optional=True))
        param1 = QgsProcessingParameterField(self.tField,
                                self.tr('Trim Iterations By Field'), parentLayerParameterName=self.Polygons, type=QgsProcessingParameterField.Numeric, optional=True)
        param2 = QgsProcessingParameterField(self.sField,
                                self.tr('Simplify Vertex Spacing By Field'), parentLayerParameterName=self.Polygons, type=QgsProcessingParameterField.Numeric, optional=True)
        param3 = QgsProcessingParameterField(self.dField,
                                self.tr('Densify Vertex Spacing By Field'), parentLayerParameterName=self.Polygons, type=QgsProcessingParameterField.Numeric, optional=True)

        param1.setFlags(param1.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        param2.setFlags(param2.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        param3.setFlags(param3.flags() | QgsProcessingParameterDefinition.FlagAdvanced)

        self.addParameter(param1)
        self.addParameter(param2)
        self.addParameter(param3)

        self.addParameter(QgsProcessingParameterFeatureSink(
            self.Output,
            self.tr("Centerlines"),
            QgsProcessing.TypeVectorLine))


    def processAlgorithm(self, parameters, context, feedback):

        try:
            import os, sys, math, string, random,tempfile
            import processing as st
            import networkx as nx
        except Exception as e:
            feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
            feedback.reportError(QCoreApplication.translate('Error',' '))
            feedback.reportError(QCoreApplication.translate('Error','Error loading modules - please install the necessary python module'))
            return {}

        layer = self.parameterAsVectorLayer(parameters, self.Polygons, context)

        if layer == None:
            feedback.reportError(QCoreApplication.translate('Error','Do not use the "Selected features only" option when applying the algorithm to selected features'))
            return {}

        aMethod = parameters[self.Method]
        Threshold = parameters[self.T]
        tField = self.parameterAsString(parameters, self.tField, context)
        sField = self.parameterAsString(parameters, self.sField, context)
        dField = self.parameterAsString(parameters, self.dField, context)

        mDict = {0:"Centerlines",1:"All",2:"Circles"}
        Method = mDict[aMethod]

        context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)

        field_check =layer.fields().indexFromName('ID')

        if field_check == -1:
            pr = layer.dataProvider()
            pr.addAttributes([QgsField("ID", QVariant.Int)])
            layer.updateFields()

        layer.startEditing()
        for feature in layer.getFeatures():
            feature['ID'] = feature.id()
            layer.updateFeature(feature)
        layer.commitChanges()

        fet = QgsFeature()
        fields = QgsFields()
        fields.append(QgsField("ID", QVariant.Int))
        field_names = ['Distance','RDistance','SP_Dist','SP_RDist']

        for name in field_names:
            fields.append( QgsField(name, QVariant.Double ))

        fet2 = QgsFeature(fields)
        (writer2, dest_id) = self.parameterAsSink(parameters, self.Output, context,
                                               fields, QgsWkbTypes.LineString, layer.sourceCrs())

        outDir = os.path.join(tempfile.gettempdir(),'GA')
        if not os.path.exists(outDir):
            os.mkdir(outDir)

        fname = ''.join(random.choice(string.ascii_lowercase) for i in range(10))
        infc = os.path.join(outDir,'%s.shp'%(fname))
        Densify_Interval = parameters[self.Densify]
        s = parameters[self.Simplify]

        Precision,tol = 6, 1e-6

        keepNodes= set([])
        fields = QgsFields()
        fields.append(QgsField("ID", QVariant.Int))
        writer = QgsVectorFileWriter(infc, "CP1250", fields, QgsWkbTypes.Point, layer.sourceCrs(), "ESRI Shapefile") #.shp requirement of SAGA

        features = layer.selectedFeatures()
        total = layer.selectedFeatureCount()
        if len(features) == 0:
            features = layer.getFeatures()
            total = layer.featureCount()

        total = 100.0/total

        feedback.pushInfo(QCoreApplication.translate('Update','Creating Vertices'))
        thresholds = {}

        for enum,feature in enumerate(features):
            if total != -1:
                feedback.setProgress(int(enum*total))

            geomType = feature.geometry()
            if sField:
                s = feature[sField]
            if dField:
                Densify_Interval = feature[dField]
            if s:
                if s > 0:
                    geomType = geomType.simplify(s)
            if Densify_Interval:
                if Densify_Interval > 0:
                    geomType = geomType.densifyByDistance(Densify_Interval)

            ID = feature['ID']
            geom = []
            if geomType.wkbType() == QgsWkbTypes.Polygon:
                polygon = geomType.asPolygon()
                geom = chain(*polygon)
            else:
                polygons = geomType.asMultiPolygon()
                geom = chain(*chain(*polygons))

            for points in geom:
                if (round(points.x(),Precision),round(points.y(),Precision)) not in keepNodes:
                    pnt = QgsGeometry.fromPointXY(QgsPointXY(points.x(),points.y()))
                    fet.setGeometry(pnt)
                    fet.setAttributes([ID])
                    writer.addFeature(fet)
                    keepNodes.update([(round(points.x(),Precision),round(points.y(),Precision))])
            if tField:
                tValue = feature[tField]
                try:
                    thresholds[ID] = int(tValue)
                except Exception as e:
                    feedback.reportError(QCoreApplication.translate('Error','Non-numeric value found in field for trim iteration function.'))
                    return {}

        feedback.pushInfo(QCoreApplication.translate('Update','Creating Voronoi Polygons'))
        del writer

        tempVP = os.path.join(outDir,'VL.shp') #.shp requirement of SAGA

        param = {'POINTS':infc,'POLYGONS':tempVP,'FRAME':10.0}
        Voronoi = st.run("saga:thiessenpolygons",param,context=context,feedback=None)

        del keepNodes
        edges = {}

        feedback.pushInfo(QCoreApplication.translate('Update','Calculating Edges'))

        param = {'INPUT':Voronoi['POLYGONS'],'OUTPUT':'memory:'}
        lines = st.run("qgis:polygonstolines",param,context=context,feedback=feedback)

        param = {'INPUT':lines['OUTPUT'],'OUTPUT':'memory:'}
        exploded = st.run("native:explodelines",param,context=context,feedback=feedback)
        param = {'INPUT':exploded['OUTPUT'],'PREDICATE':6,'INTERSECT':layer,'METHOD':0}
        st.run("native:selectbylocation",param,context=context,feedback=None)
        total = 100.0/exploded['OUTPUT'].selectedFeatureCount()

        for enum,feature in enumerate(exploded['OUTPUT'].selectedFeatures()):
            try:
                if total != -1:
                    feedback.setProgress(int(enum*total))
                part = feature.geometry().asPolyline()
                startx = None
                for point in part:
                    if startx == None:
                        startx,starty = (round(point.x(),Precision),round(point.y(),Precision))
                        continue
                    endx,endy = (round(point.x(),Precision),round(point.y(),Precision))
                    geom = QgsGeometry.fromPolylineXY([QgsPointXY(startx,starty),QgsPointXY(endx,endy)])
                    ID = feature['ID']
                    Length = geom.length()
                    if Length > tol:
                        if ID in edges:
                            edges[ID].add_edge((startx,starty),(endx,endy),weight=Length)
                        else:
                            Graph = nx.Graph()
                            Graph.add_edge((startx,starty),(endx,endy),weight=Length)
                            edges[ID] = Graph
                    startx,starty = endx,endy

            except Exception as e:
                feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))

        feedback.pushInfo(QCoreApplication.translate('Update','Calculating %s Centerlines' %(len(edges))))

        if edges:
            total = 100.0/len(edges)
            for enum,FID in enumerate(edges):

                feedback.setProgress(int(enum*total))
                G = edges[FID]
                maxG=max(nx.connected_components(G), key=len) #Largest Connected Graph
                G = G.subgraph(maxG)
                try:
                    if Threshold > 0 or tField:
                        if tField:
                            Threshold = thresholds[FID]
                        else:
                            Threshold = int(Threshold)
                        G2 = G.copy()
                        G3 = G.copy()
                        for n in range(int(Threshold)):
                            degree = G2.degree()
                            removeNodes  = [k for k,v in degree if v == 1]
                            G2.remove_nodes_from(removeNodes)

                        degree = G2.degree()
                        if len(G2) < 2:
                            feedback.reportError(QCoreApplication.translate('Update','No centerline found after trimming dangles for polygon ID %s - skipping' %(FID)))
                            continue

                        endPoints = [k for k,v in degree if v == 1]

                        G3.remove_edges_from(G2.edges)

                        for source in endPoints:
                            length,path = nx.single_source_dijkstra(G3,source,weight='weight')
                            Index = max(length,key=length.get)
                            nx.add_path(G2,path[Index])

                        del G3

                        source = list(G2.nodes())[0] #Get length along all paths
                        for n in range(2):
                            length,path = nx.single_source_dijkstra(G,source,weight='weight')
                            Index = max(length,key=length.get)
                            source = path[Index][-1]
                        length2,path2 = nx.single_source_dijkstra(G,source,weight='weight')

                        for p in G2.edges:
                            points = []
                            points.append(QgsPointXY(p[0][0],p[0][1]))
                            points.append(QgsPointXY(p[1][0],p[1][1]))

                            D = max([length[(p[0][0],p[0][1])],length[(p[1][0],p[1][1])]])
                            D2= max([length2[(p[0][0],p[0][1])],length2[(p[1][0],p[1][1])]])

                            dx = path[Index][0][0] - p[1][0]
                            dy =  path[Index][0][1] - p[1][1]
                            dx2 = path[Index][0][0] - p[0][0]
                            dy2 =  path[Index][0][1] - p[0][1]
                            SP = max([math.sqrt((dx**2)+(dy**2)),math.sqrt((dx2**2)+(dy2**2))])

                            dx = path[Index][-1][0] - p[1][0]
                            dy =  path[Index][-1][1] - p[1][1]
                            dx2 = path[Index][-1][0] - p[0][0]
                            dy2 =  path[Index][-1][1] - p[0][1]
                            SP2 = max([math.sqrt((dx**2)+(dy**2)),math.sqrt((dx2**2)+(dy2**2))])

                            fet2.setGeometry(QgsGeometry.fromPolylineXY(points))
                            fet2.setAttributes([FID,D,D2,SP,SP2])
                            writer2.addFeature(fet2)

                        del G2

                    elif Method == 'All':

                        curLen = 0
                        G2 = G.copy()
                        while len(G2) != curLen:
                            curLen = len(G2)
                            degree = G2.degree()
                            removeNodes = [k for k,v in degree if v == 1]
                            G2.remove_nodes_from(removeNodes)

                        source = list(G.nodes())[0]
                        for n in range(2):
                            length,path = nx.single_source_dijkstra(G,source,weight='weight')
                            Index = max(length,key=length.get)
                            source = path[Index][-1]

                        nx.add_path(G2,path[Index])

                        source = list(G2.nodes())[0] #Get length along all paths
                        for n in range(2):
                            length,path = nx.single_source_dijkstra(G,source,weight='weight')
                            Index = max(length,key=length.get)
                            source = path[Index][-1]
                        length2,path2 = nx.single_source_dijkstra(G,source,weight='weight')

                        for p in G2.edges:
                            points = []
                            points.append(QgsPointXY(p[0][0],p[0][1]))
                            points.append(QgsPointXY(p[1][0],p[1][1]))

                            D = max([length[(p[0][0],p[0][1])],length[(p[1][0],p[1][1])]])
                            D2= max([length2[(p[0][0],p[0][1])],length2[(p[1][0],p[1][1])]])

                            dx = path[Index][0][0] - p[1][0]
                            dy =  path[Index][0][1] - p[1][1]
                            dx2 = path[Index][0][0] - p[0][0]
                            dy2 =  path[Index][0][1] - p[0][1]
                            SP = max([math.sqrt((dx**2)+(dy**2)),math.sqrt((dx2**2)+(dy2**2))])

                            dx = path[Index][-1][0] - p[1][0]
                            dy =  path[Index][-1][1] - p[1][1]
                            dx2 = path[Index][-1][0] - p[0][0]
                            dy2 =  path[Index][-1][1] - p[0][1]
                            SP2 = max([math.sqrt((dx**2)+(dy**2)),math.sqrt((dx2**2)+(dy2**2))])

                            fet2.setGeometry(QgsGeometry.fromPolylineXY(points))
                            fet2.setAttributes([FID,D,D2,SP,SP2])
                            writer2.addFeature(fet2)

                        del G2

                    elif Method == 'Circles':

                        curLen = 0
                        G2 = G.copy()
                        while len(G2) != curLen:
                            curLen = len(G2)
                            degree = G2.degree()
                            removeNodes = [k for k,v in degree if v == 1]
                            G2.remove_nodes_from(removeNodes)

                        for p in G2.edges:
                            points = []
                            points.append(QgsPointXY(p[0][0],p[0][1]))
                            points.append(QgsPointXY(p[1][0],p[1][1]))

                            fet2.setGeometry(QgsGeometry.fromPolylineXY(points))
                            fet2.setAttributes([FID])
                            writer2.addFeature(fet2)

                        del G2


                    else:
                        source = list(G.nodes())[0]
                        for n in range(2):
                            length,path = nx.single_source_dijkstra(G,source,weight='weight')
                            Index = max(length,key=length.get)
                            source = path[Index][-1]
                        length2,path2 = nx.single_source_dijkstra(G,source,weight='weight')
                        sx = None
                        for p in path[Index]:
                            if sx == None:
                                sx,sy = p[0], p[1]
                                continue
                            ex,ey = p[0],p[1]
                            D = max([length[(sx,sy)],length[(ex,ey)]])
                            D2= max([length2[(sx,sy)],length2[(ex,ey)]])
                            dx = path[Index][0][0] - ex
                            dy =  path[Index][0][1] - ey
                            dx2 = path[Index][0][0] - sx
                            dy2 =  path[Index][0][1] - sy
                            SP = max([math.sqrt((dx**2)+(dy**2)),math.sqrt((dx2**2)+(dy2**2))])

                            dx = path[Index][-1][0] - ex
                            dy =  path[Index][-1][1] - ey
                            dx2 = path[Index][-1][0] - sx
                            dy2 =  path[Index][-1][1] - sy
                            SP2 = max([math.sqrt((dx**2)+(dy**2)),math.sqrt((dx2**2)+(dy2**2))])

                            points = [QgsPointXY(sx,sy),QgsPointXY(ex,ey)]
                            fet2.setGeometry(QgsGeometry.fromPolylineXY(points))
                            fet2.setAttributes([FID,D,D2,SP,SP2])
                            writer2.addFeature(fet2)
                            sx,sy = ex,ey

                except Exception as e:
                    feedback.reportError(QCoreApplication.translate('Update','%s'%(e)))
                    feedback.reportError(QCoreApplication.translate('Update','No centerline found for polygon ID %s - skipping' %(FID)))
                    continue


        del writer2,edges

        return {self.Output:dest_id}
