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

import os, sys
import processing as st
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsField, QgsFeature,QgsSpatialIndex, QgsPointXY, QgsProcessing,QgsWkbTypes, QgsGeometry,QgsProcessingParameterBoolean, QgsProcessingAlgorithm, QgsProcessingParameterFeatureSource,QgsProcessingParameterNumber, QgsProcessingParameterFeatureSink,QgsFeatureSink,QgsFeatureRequest,QgsFields,QgsProperty)
from itertools import combinations,chain
from math import sqrt,degrees,atan2,atan,radians,tan,fabs

class GA(QgsProcessingAlgorithm):

    Centerline='Centerline'
    Polygons='Polygons'
    Samples = 'Number of Samples'
    Distance = 'Distance'
    FC = 'Fast Compute'
    Output='Geometric Attributes'

    def __init__(self):
        super().__init__()

    def name(self):
        return "Geometric Attributes"

    def tr(self, text):
        return QCoreApplication.translate("Geometric Attributes", text)

    def displayName(self):
        return self.tr("Geometric Attributes")

    def group(self):
        return self.tr("Polygon Tools")

    def shortHelpString(self):
        return self.tr('''Calculate geometric attributes of width and centerline deviation along a centerline of a polygon. Make sure to use the 'Explode Tool' prior to executing the tool for MultiLineString geometries. \n
        Inputs -  'Samples' is the number of width measurements to take for a given centerline taken as centerline length / number of samples. If 'sample by distance' is selected, width measurement are taken along a centerline if the distance exceeds the given 'Samples' number. Keep 'Samples' equal to 0 to take width measurements at each vertex.
        \n The fast compute option will define width as the distance from the Centerlines end vertex to the closest vertex that defines the polygon multipled by 2. \n Use the Help button for more information.''')

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
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.Centerline,
            self.tr("Centerlines"),
            [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterNumber(
            self.Samples,
            self.tr("Samples"),
            QgsProcessingParameterNumber.Double,
            100.0))
        self.addParameter(QgsProcessingParameterBoolean(self.Distance,
                    self.tr("Sample By Distance"),False))
        self.addParameter(QgsProcessingParameterBoolean(self.FC,
                    self.tr("Fast Compute"),False))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.Output,
            self.tr("Geometric Attributes"),
            QgsProcessing.TypeVectorLine))


    def processAlgorithm(self, parameters, context, feedback):

        layer = self.parameterAsSource(parameters, self.Centerline, context)
        layer2 = self.parameterAsVectorLayer(parameters, self.Polygons, context)
        samples = parameters[self.Samples]
        distance = parameters[self.Distance]
        FC = parameters[self.FC]

        context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)

        if layer.sourceCrs() != layer2.sourceCrs():
            feedback.reportError(QCoreApplication.translate('Error','WARNING: Centerline and Polygon input do not have the same projection'))

        Precision=5
        if FC:
            field_names = ['Distance','SP_Dist','Width','Deviation','DWidthL','DWidthR']
        else:
            field_names = ['Distance','SP_Dist','Width','Deviation','DWidthL','DWidthR','Diff']

        fields = QgsFields()
        fields.append( QgsField('ID', QVariant.Int ))

        for name in field_names:
            fields.append( QgsField(name, QVariant.Double ))

        (writer, dest_id) = self.parameterAsSink(parameters, self.Output, context,
                                               fields, QgsWkbTypes.LineString, layer.sourceCrs())

        fet = QgsFeature()

        field_check =layer.fields().indexFromName('ID')
        field_check2 =layer2.fields().indexFromName('ID')
        if field_check == -1 or field_check2 == -1:
            feedback.reportError(QCoreApplication.translate('Error','Centerline and Polygon input feature require a matching ID field!'))
            return {}

        total = 0
        counts = {}
        if FC:
            vertices = st.run("native:extractvertices", {'INPUT':layer2,'OUTPUT':'memory:'})
            index = QgsSpatialIndex(vertices['OUTPUT'].getFeatures())
            data = {feature.id():feature for feature in vertices['OUTPUT'].getFeatures()}
        SPS = {}
        SPE = {}
        values = {}
        values2 = {}
        feats = {f["ID"]:f for f in layer2.getFeatures()}
        feedback.pushInfo(QCoreApplication.translate('Update','Defining Centerline Paths'))
        for enum,feature in enumerate(layer.getFeatures()):
            total += 1
            try:
                pnt = feature.geometry()
                if pnt.isMultipart():
                    pnt = pnt.asMultiPolyline()[0]
                else:
                    pnt = pnt.asPolyline()

                startx,starty = round(pnt[0][0],Precision),round(pnt[0][1],Precision)
                endx,endy = round(pnt[-1][0],Precision),round(pnt[-1][1],Precision)
                ID = feature['ID']
                c =  feature['Distance']
                if ID in SPS: #Get start and endpoint of each centerline
                    v = values[ID]
                    v2 = values2[ID]
                    v3 = counts[ID] + 1
                    if c > v:
                        SPS[ID] = [(startx,starty),(endx,endy)]
                        values[ID] = c
                    if c < v2:
                        SPE[ID] = [(startx,starty),(endx,endy)]
                        values2[ID] = c
                    counts[ID] = v3
                else:
                    SPS[ID] = [(startx,starty),(endx,endy)]
                    values[ID] = c
                    SPE[ID] = [(startx,starty),(endx,endy)]
                    values2[ID] = c
                    counts[ID] = 1

            except Exception as e:
                feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
                continue ##Possible Collapsed Polyline?

        del values,values2
        total = 100.0/float(total)
        ID = None
        feedback.pushInfo(QCoreApplication.translate('Update','Creating Width Measurements'))
        report = True
        for enum,feature in enumerate(layer.getFeatures()):
            try:
                if total != -1:
                    feedback.setProgress(int(enum*total))
                pnt = feature.geometry()
                L = pnt.length()
                if pnt.isMultipart():
                    pnt = pnt.asMultiPolyline()[0]
                else:
                    pnt = pnt.asPolyline()

                curID = feature["ID"]
                if ID != curID:
                    startx,starty = round(pnt[0][0],Precision),round(pnt[0][1],Precision)
                    midx,midy = round(pnt[-1][0],Precision),round(pnt[-1][1],Precision)

                    ID = curID
                    if samples > 0:
                        if distance:
                            Counter = L
                            Limit = float(samples)
                        else:
                            Counter = 1
                            Limit = round((counts[ID]/float(samples)),0)

                    continue

                endx,endy = round(pnt[-1][0],Precision),round(pnt[-1][1],Precision)

                if samples > 0:
                    if distance:
                        Counter += L
                    else:
                        Counter += 1
                    if Counter < Limit:
                        startx,starty = midx,midy
                        midx,midy = endx,endy
                        continue
                if FC:
                    startx,starty = round(pnt[0][0],Precision),round(pnt[0][1],Precision)
                    near = index.nearestNeighbor(QgsPointXY(startx,starty), 1)
                    SPv = 1e12

                    midx,midy = data[near[0]].geometry().asPoint()

                    dx,dy = startx-midx,starty-midy
                    shortestPath = sqrt((dx**2)+(dy**2))
                    if shortestPath < SPv:
                        SPv = shortestPath

                    near = index.nearestNeighbor(QgsPointXY(endx,endy), 1)
                    midx,midy = data[near[0]].geometry().asPoint()
                    dx,dy = endx-midx,endy-midy

                    shortestPath = sqrt((dx**2)+(dy**2))
                    if shortestPath < SPv:
                        SP = shortestPath

                else:

                    m = ((starty - endy)/(startx - endx)) #Slope
                    inter = feats[curID]
                    Distance = inter.geometry().boundingBox().width()/2

                    if startx==endx: #if vertical
                        x1,y1 = midx+Distance,midy
                        x2,y2 = midx - Distance,midy
                    else:
                        m = ((starty - endy)/(startx - endx)) #Slope
                        angle = degrees(atan(m)) + 90

                        m = tan(radians(angle)) #Angle to Slope
                        c,s = (1/sqrt(1+m**2),m/sqrt(1+m**2)) #cosine and sin
                        x1,y1 = (midx + Distance*(c),midy + Distance*(s))
                        x2,y2 = (midx - Distance*(c),midy - Distance*(s))

                    geom = QgsGeometry.fromPolylineXY([QgsPointXY(x1,y1),QgsPointXY(midx,midy),QgsPointXY(x2,y2)])

                    geom = geom.intersection(inter.geometry())

                    if geom.isMultipart():
                        polyline = geom.asMultiPolyline()
                        if len(polyline) == 0:
                            startx,starty = midx,midy
                            midx,midy = endx,endy
                            continue

                        for line in polyline:
                            if len(line)==3:
                                t=1
                                start,mid,end = line
                                geom1 = QgsGeometry.fromPolylineXY([QgsPointXY(start[0],start[1]),QgsPointXY(mid[0],mid[1])])
                                geom2 = QgsGeometry.fromPolylineXY([QgsPointXY(mid[0],mid[1]),QgsPointXY(end[0],end[1])])
                                geom = QgsGeometry.fromPolylineXY([QgsPointXY(start[0],start[1]),QgsPointXY(mid[0],mid[1]),QgsPointXY(end[0],end[1])])
                                break

                    else:
                        try:
                            line = geom.asPolyline()
                        except Exception as e:
                            startx,starty = midx,midy
                            midx,midy = endx,endy
                            if report:
                                report = False
                                feedback.reportError(QCoreApplication.translate('Error','Width measurement along centerline does not intersect with input polygons. Check 1. ID fields corresponds between centerline and polygons 2. Geometry of centerline and polygon inputs by using the "Fix Geometries" tool'))
                            continue
                        geom1 = QgsGeometry.fromPolylineXY([QgsPointXY(line[0][0],line[0][1]),QgsPointXY(line[1][0],line[1][1])])
                        geom2 = QgsGeometry.fromPolylineXY([QgsPointXY(line[1][0],line[1][1]),QgsPointXY(line[2][0],line[2][1])])
                    Widths = [geom1.length(),geom2.length()]


                SP = list(SPS[curID])
                SP.extend(list(SPE[curID]))
                D = 0

                for start,end in combinations(SP,2):
                    dx = start[0] - end[0]
                    dy =  start[1] - end[1]
                    shortestPath = sqrt((dx**2)+(dy**2))
                    if shortestPath > D:
                        D = shortestPath
                        s = QgsPointXY(start[0],start[1])
                        e = QgsPointXY(end[0],end[1])

                m = s.sqrDist(e)

                u = ((midx - s.x()) * (e.x() - s.x()) + (midy - s.y()) * (e.y() - s.y()))/(m)
                x = s.x() + u * (e.x() - s.x())
                y = s.y() + u * (e.y() - s.y())
                d = ((e.x()-s.x())*(midy-s.y()) - (e.y() - s.y())*(midx - s.x())) #Determine which side of the SP the symmetry occurs

                dx = s.x() - e.x()
                dy =  s.y() - e.y()
                shortestPath = sqrt((dx**2)+(dy**2))

                dx = s.x() - x
                dy =  s.y() - y
                shortestPath1 = sqrt((dx**2)+(dy**2))

                if shortestPath < shortestPath1:
                    sym = QgsGeometry.fromPolylineXY([QgsPointXY(e.x(),e.y()),QgsPointXY(midx,midy)])
                else:
                    sym = QgsGeometry.fromPolylineXY([QgsPointXY(x,y),QgsPointXY(midx,midy)])

                if d < 0:
                    DW = -(sym.length())
                else:
                    DW = sym.length()

                if FC:
                    W = SPv*2
                    rows = [curID,feature['Distance'],feature['SP_Dist'],W,DW,(W/2)+DW,-(W/2)+DW]
                    geom = feature.geometry()
                else:
                    W = geom.length()

                    rows = [curID,feature['Distance'],feature['SP_Dist'],W,DW,(W/2)+DW,-(W/2)+DW,(min(Widths)/max(Widths))*100]

                startx,starty = midx,midy
                midx,midy = endx,endy

                fet.setGeometry(geom)
                fet.setAttributes(rows)
                writer.addFeature(fet)

                if distance:
                    Counter -= samples
                else:
                    Counter = 0

            except Exception as e:
                #feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
                startx,starty = midx,midy
                midx,midy = endx,endy
                continue
        del writer
        if FC:
            del data

        del SPS,SPE

        return {self.Output:dest_id}
