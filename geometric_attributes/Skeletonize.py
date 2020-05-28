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

import os,string,random,math, tempfile
import processing as st
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import *
from qgis.PyQt.QtGui import QIcon

class Skeletonize(QgsProcessingAlgorithm):

    Centerlines = 'Centerlines'
    Raster = 'Raster'
    inv = 'Invert Image'
    SkelMethod = 'Skeletonize Method'

    def __init__(self):
        super().__init__()

    def name(self):
        return "Skeletonize"

    def tr(self, text):
        return QCoreApplication.translate("Raster Tools", text)

    def displayName(self):
        return self.tr("Centerlines (Skeletonize)")

    def group(self):
        return self.tr("Raster Tools")

    def shortHelpString(self):
        return self.tr("Create centerlines from a raster image by skeletonizing a binary raster image.\n Based on the scikit image package - more information available at https://scikit-image.org/docs/dev/auto_examples/edges/plot_skeleton.html. \n Use the Help button for more information.")

    def groupId(self):
        return "Raster Tools"

    def helpUrl(self):
        return "https://github.com/BjornNyberg/Geometric-Attributes-Toolbox/wiki"

    def createInstance(self):
        return type(self)()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.Raster,
            self.tr("Raster"), None, False))

        self.addParameter(QgsProcessingParameterBoolean(self.inv, self.tr("Invert Image"),False))

        self.addParameter(QgsProcessingParameterVectorDestination(
            self.Centerlines,
            self.tr("Centerlines"),
            QgsProcessing.TypeVectorLine))

        self.addParameter(QgsProcessingParameterEnum(self.SkelMethod,
                                self.tr('Select Skeletonize Method'), options=[self.tr("lee"),self.tr("medial axis")],defaultValue=0))

    def processAlgorithm(self, parameters, context, feedback):

        try:
            import networkx as nx
            from osgeo import gdal as osgdal
            from skimage.morphology import medial_axis, skeletonize
            from skimage.io import imread
            from skimage.util import invert
        except Exception as e:
            feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
            feedback.reportError(QCoreApplication.translate('Error',' '))
            feedback.reportError(QCoreApplication.translate('Error','Error loading modules - please install the scikit-image python module'))
            return {}

        rlayer = self.parameterAsRasterLayer(parameters, self.Raster, context)
        sMethod  = self.parameterAsInt(parameters, self.SkelMethod, context)
        inv = parameters[self.inv]

        fname = ''.join(random.choice(string.ascii_lowercase) for i in range(10))

        outFname = os.path.join(tempfile.gettempdir(),'%s.tif'%(fname))
        rect = rlayer.extent()
        dp = rlayer.dataProvider()
        raster = dp.dataSourceUri()

        xres = rlayer.rasterUnitsPerPixelX()
        yres = rlayer.rasterUnitsPerPixelY()

        img = imread(raster)
        stats = dp.bandStatistics(1,QgsRasterBandStats.All,rect,0)

        if dp.bandCount() != 1 or stats.maximumValue > 1:
            feedback.reportError(QCoreApplication.translate('Error','Tool requires a binary raster input - please run the Thresholding tool prior to calculating centerlines.'))
            return {}

        nrows,ncols = img.shape

        if inv:
            img = invert(img)

        if sMethod  == 0:
            skeleton = skeletonize(img, method='lee').astype(float)
        elif sMethod  == 1:
            skeleton = medial_axis(img).astype(float)

        driver = osgdal.GetDriverByName('GTiff')
        dataset = driver.Create(outFname, ncols, nrows, 1, osgdal.GDT_Float32,)

        dataset.SetGeoTransform((rect.xMinimum(),xres, 0, rect.yMaximum(), 0, -yres))

        wkt_prj = rlayer.crs().toWkt()
        dataset.SetProjection(wkt_prj)
        band = dataset.GetRasterBand(1)
        band.SetNoDataValue(0)
        band.WriteArray(skeleton)
        dataset,band = None,None

        outSHP = os.path.join(tempfile.gettempdir(),'%s.shp'%(fname))

        params = {'input':outFname,'type':0,'column':'value','-s':False,'-v':False,'-z':False,'-b':False,'-t':False,'output':outSHP,'GRASS_REGION_PARAMETER':None,'GRASS_REGION_CELLSIZE_PARAMETER':0,'GRASS_OUTPUT_TYPE_PARAMETER':2,'GRASS_VECTOR_DSCO':'','GRASS_VECTOR_LCO':'','GRASS_VECTOR_EXPORT_NOCAT':False}
        templines = st.run("grass7:r.to.vect",params,context=context,feedback=feedback)
        params = {'INPUT':templines['output'],'LINES':templines['output'],'OUTPUT':'memory:'}
        tempOut = st.run('native:splitwithlines',params,context=context,feedback=None)

        params = {'INPUT':tempOut['OUTPUT'],'OUTPUT':'memory:'}
        explodeOut = st.run("native:explodelines",params,context=context,feedback=None)

        G = nx.Graph()
        for feature in explodeOut['OUTPUT'].getFeatures(QgsFeatureRequest()):
            try:
                geom = feature.geometry().asPolyline()
                start,end = geom[0],geom[-1]
                startx,starty=start
                endx,endy=end
                length = feature.geometry().length()
                branch = [(startx,starty),(endx,endy)]
                G.add_edge(branch[0],branch[1],weight=length)
            except Exception as e:
                feedback.reportError(QCoreApplication.translate('Node Error','%s'%(e)))

        fields = QgsFields()
        prj = QgsCoordinateReferenceSystem(wkt_prj)
        (writer, dest_id) = self.parameterAsSink(parameters, self.Centerlines, context,
                                               fields, QgsWkbTypes.LineString, prj)
        fet = QgsFeature()
        skip_edges = []
        minD = xres*1.1

        for circle in nx.cycle_basis(G): #Fix x node intersections
            start,curDist,end2 = None,None,None
            cLen = len(circle)
            if cLen <= 4:
                skip = []
                for enum,end in enumerate(circle):
                    if G.degree(end) != 3:
                        cLen = -1
                    if start == None:
                        start = end
                        start1 = end
                        continue
                    elif enum == 1:
                        start2 = end
                    elif enum == 2:
                        end1 = end
                    else:
                        end2 = end

                    dx,dy = start[0]-end[0],start[1]-end[1]
                    dist = math.sqrt((dx**2)+(dy**2))
                    if curDist == None:
                        curDist = dist
                    if dist > minD or dist != curDist:
                        cLen == -1
                        break
                    curDist = dist
                    skip.extend([(start,end),(end,start)])
                    start = end
                if end2:
                    dx,dy = start[0]-start1[0],start[1]-start1[1]
                    dist = math.sqrt((dx**2)+(dy**2))
                    if dist > minD or dist != curDist:
                        cLen == -1
                    skip.extend([(start,start1),(start1,start)]) #Close circle

                    if cLen == 4:
                        skip_edges.extend(skip)
                        polylines = [[QgsPointXY(start1[0],start1[1]),QgsPointXY(end1[0],end1[1])],[QgsPointXY(start2[0],start2[1]),QgsPointXY(end2[0],end2[1])]]
                        for points in polylines:
                            outGeom = QgsGeometry.fromPolylineXY(points)
                            fet.setGeometry(outGeom)
                            writer.addFeature(fet,QgsFeatureSink.FastInsert)

        for edge in G.edges(data=True):
            if edge not in skip_edges:
                L = edge[2]['weight']
                start = edge[0]
                end = edge[1]
                vertices = [G.degree(start),G.degree(end)]
                points = [QgsPointXY(start[0],start[1]),QgsPointXY(end[0],end[1])]
                outGeom = QgsGeometry.fromPolylineXY(points)
                fet.setGeometry(outGeom)
                writer.addFeature(fet,QgsFeatureSink.FastInsert)

        return {self.Centerlines:dest_id}

if __name__ == '__main__':
    pass
