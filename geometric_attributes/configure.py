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

import os,sys, subprocess
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import *
from qgis.utils import iface
from PyQt5.QtWidgets import QMessageBox, QFileDialog,QInputDialog,QLineEdit

class configureSAM(QgsProcessingAlgorithm):

    def __init__(self):
        super().__init__()

    def name(self):
        return "Configure SAM"

    def tr(self, text):
        return QCoreApplication.translate("Configure SAM", text)

    def displayName(self):
        return self.tr("Configure Segment Anything Model (SAM)")

    def group(self):
        return self.tr("Raster Tools")

    def shortHelpString(self):
        return self.tr('''This script will attempt to install the dependencies required for the Segment Anything Model (SAM) tool for Windows users.
        If the tool fails, manual installation will be required using 'python3 -m pip install segment-geospatial'. In addition, the SAM checkpoint file
        will need to be downloaded from https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth and placed within the Geometric Attributes plugin folder
        located at ~QGIS3\profiles\default\python\plugins\geometric_attributes.''')

    def groupId(self):
        return "Raster Tools"

    def helpUrl(self):
        return "https://github.com/BjornNyberg/Geometric-Attributes-Toolbox/wiki"

    def createInstance(self):
        return type(self)()

    def initAlgorithm(self, config=None):
        pass

    def processAlgorithm(self, parameters, context, feedback):

        if os.name == 'nt': ##GUI for python installer via subprocess module
            reply = QMessageBox.question(iface.mainWindow(), 'Install SAM Dependencies',
                 'Attempting to install segment-geospatial package. Do you wish to continue?', QMessageBox.Yes, QMessageBox.No)

            if reply == QMessageBox.Yes:
                try:
                    is_admin = os.getuid() == 0
                except AttributeError:
                    import ctypes
                    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

                modules = ['segment-geospatial']

                for module in modules:
                    try:
                        if is_admin:
                            status = subprocess.check_call(['python3','-m', 'pip', 'install', module])
                        else:
                            status = subprocess.check_call(['python3','-m', 'pip', 'install', module,'--user'])

                        if status != 0:
                            feedback.reportError(QCoreApplication.translate('Warning','Failed to install %s - consider installing manually'%(module)))
                    except Exception:
                        feedback.reportError(QCoreApplication.translate('Warning','Failed to install %s - consider installing manually'%(module)))
                        continue

            if os.name != 'nt':
                feedback.reportError(QCoreApplication.translate('Warning','macOS and Linux users - manually install the segment-geospatial python package.'))
                return {}

        reply = QMessageBox.question(iface.mainWindow(), 'Install SAM Dependencies',
                 'Attempting to download pre-trained SAM checkpoint file (~2.5gb). Note this may take some time and QGIS will not be responsive during the download! Do you wish to continue?', QMessageBox.Yes, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                import requests
                url = 'https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth'
                dirname = os.path.dirname(__file__)
                outName = os.path.join(dirname, 'sam_vit_h_4b8939.pth')
                with open(outName, "wb") as f:
                    response = requests.get(url, stream=True)
                    for data in response.iter_content(chunk_size=10000):
                        f.write(data)
            except Exception:
                feedback.reportError(QCoreApplication.translate('Warning','''Failed to download checkpoint dataset. Consider downloading manually from
                https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth and place the file within the Geometric Attributes plugin folder at at ~QGIS3\profiles\default\python\plugins\geometric_attributes.'''))
                return {}
        else:
            feedback.reportError(QCoreApplication.translate('Warning','''Consider downloading manually from
            https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth and place the file within the Geometric Attributes plugin folder at at ~QGIS3\profiles\default\python\plugins\geometric_attributes.'''))

        return {}

if __name__ == '__main__':
    pass
