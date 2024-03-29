# -*- coding: utf-8 -*-

"""
/***************************************************************************
 GeometricAttributes
                                 A QGIS plugin
 A set of tools for the automated and objective classification of geometry and shape of modern depositional elements
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-08-26
        copyright            : (C) 2019 by Bjorn Nyberg
        email                : bjorn.nyberg@uib.no
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Bjorn Nyberg'
__date__ = '2019-08-26'
__copyright__ = '(C) 2019 by Bjorn Nyberg'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
from .Adjacency import Connected
from .Centerlines import Centerlines
from .DCenterlines import DCenterlines
from .GA import GA
from .Overlap import Overlap
from .Shape_Analysis import Shape
from .mergeLines import mergeLines
from .Sinuosity import Sinuosity
from .Centerline_Lengths import centDist
from .Transects import Transects
from .Sample_Transects import sampleTransects
from .Thresholding import Thresholding
from .Skeletonize import Skeletonize
from .Tortuosity import Tortuosity
from .SAM import SAM
from .SAM_predictor import SAM_Pred
from .configure import configureSAM


class GeometricAttributesProvider(QgsProcessingProvider):

    def __init__(self):
        """
        Default constructor.
        """
        QgsProcessingProvider.__init__(self)

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        self.addAlgorithm(Connected())
        self.addAlgorithm(Centerlines())
        self.addAlgorithm(DCenterlines())
        self.addAlgorithm(GA())
        self.addAlgorithm(Overlap())
        self.addAlgorithm(Shape())
        self.addAlgorithm(mergeLines())
        self.addAlgorithm(Sinuosity())
        self.addAlgorithm(centDist())
        self.addAlgorithm(Transects())
        self.addAlgorithm(sampleTransects())
        self.addAlgorithm(Thresholding())
        self.addAlgorithm(Skeletonize())
        self.addAlgorithm(Tortuosity())
        self.addAlgorithm(SAM())
        self.addAlgorithm(SAM_Pred())
        self.addAlgorithm(configureSAM())


    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return 'Algorithms'

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return self.tr('Geometric Attributes')

    def icon(self):
        """
        Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        iconPath = os.path.join( os.path.dirname(__file__), 'icon.jpg')
        return QIcon(iconPath)

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.name()
