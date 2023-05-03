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
from PyQt5.QtWidgets import QMessageBox,QComboBox

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
        If the tool fails, manual installation will be required using 'pip install segment-geospatial'. In addition, the SAM checkpoint files
        will need to be downloaded and placed within the Geometric Attributes plugin.''')

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
                 'Attempting to download pre-trained SAM checkpoint file (~4gb). Note this may take some time and QGIS will not be responsive during the download! Do you wish to continue?', QMessageBox.Yes, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                from samgeo import common
                checkpoints = ['sam_vit_h_4b8939.pth','sam_vit_l_0b3195.pth','sam_vit_b_01ec64.pth']
                for checkpoint in checkpoints:
                    url = 'https://dl.fbaipublicfiles.com/segment_anything/{}'.format(checkpoint)
                    dirname = os.path.dirname(__file__)
                    outName = os.path.join(dirname, checkpoint)
                    common.download_checkpoint(url,outName,overwrite=True,quiet=True)
            except Exception:
                feedback.reportError(QCoreApplication.translate('Warning','''Failed to download {} dataset. Consider downloading manually and place the file within the Geometric Attributes plugin at ~QGIS3\profiles\default\python\plugins\geometric_attributes. Check the user guide for more information.'''.format(checkpoint)))
                return {}
        else:
            feedback.reportError(QCoreApplication.translate('Warning','''Consider downloading checkpoint files manually and place the file within the Geometric Attributes plugin at ~QGIS3\profiles\default\python\plugins\geometric_attributes. Check the user guide for more information.'''))

        return {}

if __name__ == '__main__':
    pass
