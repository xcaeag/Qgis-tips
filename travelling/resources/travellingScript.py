"""
Using the temporal controller, the idea is to follow a 'camera' path defined by a linestring geometry.
Extent and orientation can be carried by the M and Z values ​​of the geometry.
Once 'connected' (the python object) to the controller, this piece of code will adapt the view (and save the map), according to the progress of the cursor in the temporal range.

# Usage : 
# Initialize object 
flight_layer = iface.mapCanvas().currentLayer()
cam = Travelling(
    flight_layer, 
    wdir=str(Path.home() / "tmp"), 
    filename="tmp-{:03d}.png", 
    w=640, h=480
)

# Connect the temporal controler
cam.connectTemporalControler()

# play with the temporal controler
# ...

# and then disconnect 
cam.disconnectTemporalControler()
"""

from qgis.utils import iface
from qgis.core import (
    QgsProject,
    QgsPointXY,
    QgsGeometry,
    QgsPoint,
    QgsRectangle,
    QgsMapRendererParallelJob,
    QgsMapSettings
)
from qgis.PyQt.QtGui import QImage
from qgis.PyQt.QtCore import QSize
import numpy as np
import math
import os


class Travelling:
    """
    Class allowing to react to the change of the temporal range (from temporal controler).
    
    And adapts the view by following a "linestring" which carries the values ​​M and Z: width and rotation of the view (prerequisites).
    """

    def __init__(self, path, w=1500, h=1000, wdir="/tmp", filename="tmp-{:03d}.png", saveImage=True):
        """
        Initialization

        Parameters:
        path (geometry): the linestring to follow. M values for widths, Z for azimuth.
        w (int): ouput image width
        f (int): ouput image height
        wdir (string): output dir
        filename (string): file name template
        saveImage (boolean): is images will be saved
        """
        self.canvas = iface.mapCanvas()
        self.wdir = wdir
        self.filename = filename
        self.fxy = w / h
        self.defaultWidth = self.canvas.extent().width()
        self.width = w
        self.height = h
        self.saveImage = saveImage

        # settings for image saving
        self.settings = self.canvas.mapSettings()
        self.settings.setOutputSize(QSize(self.width, self.height))
        self.settings.setFlag(QgsMapSettings.DrawLabeling, True)
        self.settings.setFlag(QgsMapSettings.Antialiasing, True)
        self.settings.setFlag(QgsMapSettings.UseAdvancedEffects, True)
        self.settings.setFlag(QgsMapSettings.UseRenderingOptimization, True)
        self.settings.setOutputImageFormat(QImage.Format_ARGB32)
        self.settings.setDpiTarget(96)

        # the temporal controler object
        self.tc = self.canvas.temporalController() 

        # works with the first feature (selected or not)
        feats = path.selectedFeatures()
        if len(feats) > 0:
            feat = feats[0]
        else:
            feat = next(path.getFeatures())

        # for pos interpolation
        self.flight = feat.geometry()
        self.flightposY = [self.flight.distanceToVertex(i) for i, _ in enumerate(self.flight.vertices())]
        self.flightposX = range(0, len(self.flightposY))

        # ffmpeg command exemple
        ffmpeg = """# ffmpeg command exemple :
ffmpeg -start_number 0 -filter_complex "[0:v] fps=10,split [o1] [o2];[o1] palettegen [p]; [o2] fifo [o3];[o3] [p] paletteuse" -i {wdir}{sep}tmp-%03d.png {wdir}{sep}out.gif""".format(
            wdir=self.wdir,
            filename=self.filename,
            sep=os.sep
        )
        print(ffmpeg)


    def connectTemporalControler(self):
        """
        Connect the temporal controler event "updateTemporalRange"
        """
        self.tc.updateTemporalRange.connect(self.onUpdateTemporalRange)

    def disconnectTemporalControler(self):
        """
        Disconnect the temporal controler event "updateTemporalRange"
        """
        try:
            self.tc.updateTemporalRange.disconnect(self.onUpdateTemporalRange)
        except Exception:
            pass

    def getViewBox(self, progress):
        """
        Calculate the position of the view according to the advancement of the temporal controler
        """
        # interpolation taking into account the distribution of nodes along the line
        interpolated_dist =  np.interp(len(self.flightposX)*progress, self.flightposX, self.flightposY)
        pt = self.flight.interpolate(interpolated_dist).vertices().next()
        # or linear interpolation based on distance only : pt = self.flight.interpolate(progress * self.flight.length()).vertices().next()
        x, y, z, m = pt.x(), pt.y(), pt.z(), pt.m()

        # if m value does not exists, use default value (map extent)
        if math.isnan(m):
            m = self.defaultWidth

        # if z value does not exists, no rotation to apply
        if math.isnan(z):
            z = 0.0

        # the bounding box
        rect = QgsGeometry(QgsPoint(x, y)).buffer(m / 2, 5).boundingBox()
        h2 = (rect.height() / 2) / self.fxy
        y0 = (rect.yMinimum() + rect.yMaximum()) / 2
        bbox = QgsRectangle(QgsPointXY(rect.xMinimum(), y0 + h2), QgsPointXY(rect.xMaximum(), y0 - h2))

        return z, bbox

    def onUpdateTemporalRange(self):
        """
        Update the view (extent and rotation) when the temporal range changes

        Refresh the canvas, saves the image according to the settings
        """
        try:
            # Calculate the position of the view
            progress = self.tc.currentFrameNumber() / self.tc.totalFrameCount()
            azimuth, bbox = self.getViewBox(progress)

            self.disconnectTemporalControler()

            self.canvas.setExtent(bbox, False)
            self.canvas.refreshAllLayers()
            self.canvas.setRotation(-azimuth)
            self.canvas.waitWhileRendering()

            if self.saveImage:
                self.settings.setExtent(bbox)
                self.settings.setRotation(-azimuth)
                self.settings.setLayers(QgsProject.instance().layerTreeRoot().checkedLayers())
                job = QgsMapRendererParallelJob(self.settings)
                job.start()
                job.waitForFinished()

                img = job.renderedImage()
                fullname = "{}/{}".format(self.wdir, self.filename.format(self.tc.currentFrameNumber()))
                print(fullname)
                img.save(fullname)

            self.connectTemporalControler()

        except Exception:
            print("# ERR")
            self.tc.pause()
            self.disconnectTemporalControler()
