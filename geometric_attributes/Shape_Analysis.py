#==================================
#Author Bjorn Burr Nyberg
#University of Bergen
#Contact bjorn.nyberg@uib.no
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

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsVectorLayer, QgsSpatialIndex, QgsField,QgsVectorFileWriter,QgsProcessingParameterBoolean, QgsProcessingParameterField, QgsFeature, QgsPointXY, QgsProcessingParameterNumber, QgsProcessingParameterString, QgsProcessing,QgsWkbTypes, QgsGeometry, QgsProcessingAlgorithm, QgsProcessingParameterFeatureSource, QgsProcessingParameterFeatureSink,QgsFeatureSink,QgsFeatureRequest,QgsFields,QgsProperty)

class Shape(QgsProcessingAlgorithm):

    Polygons='Polygons'
    Width = 'Geometric Attributes'
    Directional = 'Directional'
    Output = 'Output'

    def __init__(self):
        super().__init__()

    def name(self):
        return "Shape Analysis"

    def tr(self, text):
        return QCoreApplication.translate("Shape Analysis", text)

    def displayName(self):
        return self.tr("Shape Analysis")

    def group(self):
        return self.tr("Polygon Tools")

    def shortHelpString(self):
        return self.tr("Calculate the shape of a polygon as crescentric, sinuous or ellipsoidal/rectangular with a symmetrical or asymmetrical shape.\n Use the Help button for more information.")

    def groupId(self):
        return "2. Polygon Tools"

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
            self.Width,
            self.tr("Geometric Attributes"),
            [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterBoolean(self.Directional,
                    self.tr("Directional"),False))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.Output,
            self.tr("Output"),
            QgsProcessing.TypeVectorPolygon))

    def processAlgorithm(self, parameters, context, feedback):

        try:
            import processing as st
            import networkx as nx
            from scipy import stats
            from math import fabs
        except Exception as e:
            feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
            feedback.reportError(QCoreApplication.translate('Error',' '))
            feedback.reportError(QCoreApplication.translate('Error','Error loading modules - please install the necessary python module'))
            return {}

        layer = self.parameterAsVectorLayer(parameters, self.Width, context)
        layer2 = self.parameterAsVectorLayer(parameters, self.Polygons, context)
        Directional = parameters[self.Directional]

        context.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)

        '''Input thresholds - for more detail refer to
        Nyberg, B., Buckley, S.J., Howell, J.A., Nanson, R.A. (2015). Geometric attribute and shape characterization of modern
        depositional elements: A quantitative GIS method for empirical analysis, Computers & Geosciences, Vo. 82, 2015, p. 191-204. '''

        Crescentric_Threshold = 1
        Sinuous_Threshold = 0.2
        Symmetry_Threshold = 0.2
        Linear_Threshold = 0.5
        Precision = 3 #Point precision

        D,W,DW,SP = {},{},{},{}
        IDs = set([])

        fields = ['ID','Distance','Width','Deviation','SP_Dist']
        for field in fields:
            field_check =layer.fields().indexFromName(field)
            if field_check == -1:
                feedback.reportError(QCoreApplication.translate('Error','Width measurements feature class do not have the required fields of ID, Distance, Width, Deviation and SP_Dist'))
                return {}

        field_check = layer2.fields().indexFromName('ID')
        if field_check == -1:
            feedback.reportError(QCoreApplication.translate('Error','Polygons feature class does not have an ID field!'))
            return {}

        for total,feature in enumerate(layer.getFeatures()):
            ID = feature['ID']
            IDs.update([ID])
            if ID in D:
                D[ID].append(feature['Distance'])
                W[ID].append(feature['Width'])
                DW[ID].append(feature['Deviation'])
                SP[ID].append(feature['SP_Dist'])
            else:
                D[ID] = [feature['Distance']]
                W[ID] = [feature['Width']]
                DW[ID] = [feature['Deviation']]
                SP[ID] = [feature['SP_Dist']]

        fields = QgsFields()

        field_names = ['Length','Sinuosity','Width','Deviation','Shape']

        fields.append( QgsField('ID', QVariant.Int ))

        for name in field_names[:-1]:
            fields.append( QgsField(name, QVariant.Double ))

        fields.append(QgsField(field_names[-1], QVariant.String ))

        fet = QgsFeature(fields)

        (writer, dest_id) = self.parameterAsSink(parameters, self.Output, context,
                                               fields, QgsWkbTypes.Polygon, layer.sourceCrs())

        data = {}
        Total = len(IDs)
        Counter = 0

        feedback.pushInfo(QCoreApplication.translate('Update','Calculating Fields'))
        for ID in IDs:
            try:
                feedback.setProgress(int((100 * Counter)/Total))
                Counter += 1

                Distance = max(D[ID])
                Width = max(W[ID])
                SPv = max(SP[ID])

                x = [n/Distance for n in D[ID]]
                y = [n/Width for n in W[ID]]

                m, intercept, r_value, p_value, std_err = stats.linregress(x,y)
                r2=r_value**2

                xMax = max(DW[ID])
                x = [n/xMax for n in DW[ID] if n > 0]
                x2 = [-(n/-xMax) for n in DW[ID] if n < 0]

                mm = [float(len(x)),float(len(x2))] #min and max values
                mm = min(mm)/max(mm)
                c=xMax/(Width/2.0)

                Class = ''

                if c > Crescentric_Threshold:
                    if mm < Sinuous_Threshold:
                        if fabs(m) > Symmetry_Threshold:
                            Class = "C AS"
                        elif r2 > Linear_Threshold:
                            Class = "C L"
                        else:
                            Class = "C S"
                    else:
                        if fabs(m) > Symmetry_Threshold:
                            Class = "S AS"
                        elif r2 > Linear_Threshold:
                            Class = "S L"
                        else:
                            Class = "S S"
                else:
                    if fabs(m) > Symmetry_Threshold:
                        Class = "E AS"
                    elif r2 > Linear_Threshold:
                        Class = "E L"
                    else:
                        Class= "E S"

                if Directional:
                    if fabs(m) > Symmetry_Threshold:
                        if m > 0:
                            Class = ' '.join([Class,'1'])
                        else:
                            Class = ' '.join([Class,'0'])

                data[ID] = (round(Distance,Precision),round((Distance/SPv),Precision),round(Width,Precision),round(xMax,Precision),Class)

            except Exception as e:
                feedback.reportError(QCoreApplication.translate('Error','%s'%(e)))
                continue

        total = 100.0/float(total)

        feedback.pushInfo(QCoreApplication.translate('Update','Creating Output'))
        for enum,feature in enumerate(layer2.getFeatures()): #Update features
            if total != -1:
                feedback.setProgress(int(enum*total))
            ID = feature['ID']
            if ID in data:
                rows = [ID]
                values = data[ID]
                rows.extend(values)
                fet.setAttributes(rows)
                fet.setGeometry(feature.geometry())
                writer.addFeature(fet)

        return {self.Output:dest_id}
