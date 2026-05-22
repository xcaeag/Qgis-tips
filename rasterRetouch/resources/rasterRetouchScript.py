"""
Script QGis pour retouche MNT raster.

Propose une barre d'outils pour travailler le relief d'un raster (DEM). Elévation, baisse du relief, floutage, copie ect... à l'aide de 'pinceaux'.

Ressources
- https://stackoverflow.com/questions/69687798/generating-a-soft-circluar-mask-using-numpy-python-3

"""

import os
from tools import tools
import numpy as np
from scipy.ndimage import gaussian_filter

from osgeo import gdal
from pathlib import Path

from qgis.gui import QgsRubberBand, QgsMapTool
from qgis.utils import iface
from qgis.core import (
    Qgis,
    QgsProject,
    QgsWkbTypes,
    QgsGeometry,
    QgsAnnotationPointTextItem,
    QgsPointXY,
    QgsRasterLayer,
)

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtCore import Qt


def disk(r1=5, r2=10, fx=1, fy=1, curve=True):
    size = 2 * r2 + 1
    x = np.arange(0, size, 1, float)
    y = x[:, np.newaxis][::-1]
    x0 = y0 = size // 2
    a = np.sqrt(((x - x0) / fx) ** 2 + ((y - y0) / fy) ** 2)
    a = np.maximum(
        np.minimum(((a - r1) / (r2 - r1)), np.full(a.shape, 1)), np.full(a.shape, 0)
    )
    a = 1 - a
    if curve:
        a = 0.5 + np.sin(a * np.pi - np.pi / 2) / 2

    return a


class BrushTool(QgsMapTool):
    _instance = None

    MODE_MONTER = 1
    MODE_DESCENDRE = 2
    MODE_FLOUTER = 3
    MODE_COPIER = 4  # copie depuis un deuxième mnt
    MODE_COPIE2 = 5  # copie au sein du même mnt
    MODE_APLATIR = 6
    MODE_TRAINER = 7
    MODE_ACCENTUER = 8
    MODE_ERODER = 9

    def __init__(self, rastLayer, canvas):
        self._canvas = canvas
        QgsMapTool.__init__(self, self._canvas)

        self.DIR = Path(os.path.dirname(os.path.realpath(__file__)))

        self.rb = QgsRubberBand(self._canvas, QgsWkbTypes.PolygonGeometry)
        self.rb.setStrokeColor(QColor(150, 30, 80, 200))
        self.rb.setWidth(2)
        self.rbblur = QgsRubberBand(self._canvas, QgsWkbTypes.PolygonGeometry)
        self.rbblur.setStrokeColor(QColor(150, 30, 80, 200))
        self.rbblur.setWidth(1)
        self.rbfrom = QgsRubberBand(self._canvas, QgsWkbTypes.PolygonGeometry)
        self.rbfrom.setStrokeColor(QColor(150, 30, 80, 200))
        self.rbfrom.setWidth(1)
        self.label = None

        self.fromPointXY = None
        self.fromPointDX = None
        self.fromPointDY = None
        self.currentPointXY = None
        self.drawing = False
        self.mode = None
        self.actions = {}

        self.brush = None
        self.brushR = self._canvas.extent().width() / 50
        self.brushBlurSize = 0.6
        self.brushAlpha = 0.6

        self.toCopyLayer = None
        self.dsToCopy = None
        self.npaToCopy = None

        self.rlayer = rastLayer
        self.ds = gdal.Open(rastLayer.dataProvider().dataSourceUri(), gdal.GA_Update)
        self.npa = self.ds.ReadAsArray()
        # self.npa2 = None
        self.firstZone = None

        self.shiftKey = False
        self.ctrlKey = False
        self.key = 0

        self.initToolbar()

        BrushTool._instance = self

    @classmethod
    def getInstance(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = cls(*args, **kwargs)

        return cls._instance

    def __del__(self):
        print("del")
        self.closeToolbar()

    def changeMode(self):
        oldmode = self.mode
        newmode = self.sender().data()

        if oldmode == newmode:
            self.actions[oldmode].setChecked(False)
            self.mode = None
            self.hide()
            return

        if newmode == BrushTool.MODE_COPIER:
            toCopyLayer = iface.mapCanvas().currentLayer()
            if toCopyLayer == self.rlayer:
                self.toCopyLayer = None
                newmode = oldmode

            if toCopyLayer is not None and toCopyLayer != self.toCopyLayer:
                self.toCopyLayer = toCopyLayer
                self.dsToCopy = gdal.Open(self.toCopyLayer.dataProvider().dataSourceUri())
                self.npaToCopy = self.dsToCopy.ReadAsArray()

        self.mode = newmode
        for k, a in self.actions.items():
            a.setChecked(k == self.mode)

    def initToolbar(self):
        self.actions[BrushTool.MODE_MONTER] = QAction(
            QIcon(str(self.DIR / "rasterRetouchMode1.svg")),
            "Monter",
            iface.mainWindow(),
        )
        self.actions[BrushTool.MODE_DESCENDRE] = QAction(
            QIcon(str(self.DIR / "rasterRetouchMode2.svg")),
            "Descendre",
            iface.mainWindow(),
        )
        self.actions[BrushTool.MODE_FLOUTER] = QAction(
            QIcon(str(self.DIR / "rasterRetouchMode3.svg")),
            "Flouter",
            iface.mainWindow(),
        )
        self.actions[BrushTool.MODE_COPIER] = QAction(
            QIcon(str(self.DIR / "rasterRetouchMode4.svg")),
            "Copier",
            iface.mainWindow(),
        )
        self.actions[BrushTool.MODE_COPIE2] = QAction(
            QIcon(str(self.DIR / "rasterRetouchMode5.svg")),
            "Dupliquer",
            iface.mainWindow(),
        )
        self.actions[BrushTool.MODE_APLATIR] = QAction(
            QIcon(str(self.DIR / "rasterRetouchMode6.svg")),
            "Emousser",
            iface.mainWindow(),
        )
        self.actions[BrushTool.MODE_ACCENTUER] = QAction(
            QIcon(str(self.DIR / "rasterRetouchMode8.svg")),
            "Accentuer",
            iface.mainWindow(),
        )

        self.actions[BrushTool.MODE_TRAINER] = QAction(
            QIcon(str(self.DIR / "rasterRetouchMode7.svg")),
            "Trainer",
            iface.mainWindow(),
        )

        self.toolbar = iface.addToolBar("Retouche raster")

        for k, a in self.actions.items():
            a.setCheckable(True)
            a.setData(k)
            a.triggered.connect(lambda: self.changeMode())
            self.toolbar.addAction(a)

        closeAction = QAction(
            QIcon(str(self.DIR / "close.svg")),
            "Fin",
            iface.mainWindow(),
        )
        closeAction.triggered.connect(lambda: close())
        self.toolbar.addAction(closeAction)

    def closeToolbar(self):
        print("close Toolbar")
        for a in self.actions.values():
            self.toolbar.removeAction(a)

        self.toolbar = None

    def setLabel(self, text=None):
        ptXY = QgsPointXY(
            self.rb.asGeometry().centroid().asPoint().x(),
            self.rb.asGeometry().boundingBox().yMaximum(),
        )
        if self.label is None and text is not None:
            self.label = QgsAnnotationPointTextItem("", ptXY)
            annotation_layer = QgsProject.instance().mainAnnotationLayer()
            annotation_layer.addItem(self.label)

        if self.label is not None and text is not None:
            self.label.setText(text)
            self.label.setPoint(ptXY)
            QgsProject.instance().mainAnnotationLayer().triggerRepaint()

        if text is None and self.label is not None:
            self.label.setText("")
            self.label = None
            QgsProject.instance().mainAnnotationLayer().reset()

    def buildRubberBand(self):
        if self.currentPointXY is None or self.mode is None:
            self.hide()
        else:
            geom = QgsGeometry.fromPointXY(self.currentPointXY).buffer(self.brushR, 5)
            self.rb.setToGeometry(geom)
            geom = QgsGeometry.fromPointXY(self.currentPointXY).buffer(
                self.brushBlurSize * self.brushR, 5
            )
            self.rbblur.setToGeometry(geom)
            self.rb.setFillColor(QColor(200, 200, 240, round(self.brushAlpha * 200)))

            if self.mode == BrushTool.MODE_COPIE2 and self.fromPointXY is not None:
                geom = QgsGeometry.fromPointXY(self.fromPointXY).buffer(self.brushR, 5)
                self.rbfrom.setToGeometry(geom)

    def draw(self):
        if self.brush is None:
            return

        xmin, _, _, ymax = self.rlayer.extent().toRectF().getCoords()
        xpix = round(
            (self.currentPointXY.x() - xmin) / self.rlayer.rasterUnitsPerPixelX()
        )
        ypix = round(
            (ymax - self.currentPointXY.y()) / self.rlayer.rasterUnitsPerPixelY()
        )

        # zone de la brosse à retenir (clip si sur la bordure du raster)
        bxmin = max(0, self.brushsize2 - xpix)
        if bxmin >= self.brushsize2:
            return

        bxmax = (
            min(
                self.brushsize,
                self.brushsize - (xpix + self.brushsize2 - self.rlayer.width()),
            )
            - 1
        )
        if bxmin >= bxmax:
            return

        bymin = max(0, self.brushsize2 - ypix)
        if bymin >= self.brushsize2:
            return

        bymax = (
            min(
                self.brushsize,
                self.brushsize - (ypix + self.brushsize2 - self.rlayer.height()),
            )
            - 1
        )
        if bymin >= bymax:
            return

        rxmin = max(xpix - self.brushsize2, 0)
        rymin = max(ypix - self.brushsize2, 0)
        rxmax = min(xpix + self.brushsize2, self.rlayer.width())
        rymax = min(ypix + self.brushsize2, self.rlayer.height())

        abrush = self.brush[bymin:bymax, bxmin:bxmax]
        zon = self.npa[rymin:rymax, rxmin:rxmax]

        delta = 100
        newBrush = abrush * self.brushAlpha
        if self.mode == BrushTool.MODE_MONTER:
            self.npa[rymin:rymax, rxmin:rxmax] = zon + delta * newBrush
        elif self.mode == BrushTool.MODE_DESCENDRE:
            self.npa[rymin:rymax, rxmin:rxmax] = zon - delta * newBrush
        elif self.mode == BrushTool.MODE_APLATIR:
            average = np.copy(zon)
            average.fill(np.average(zon))
            self.npa[rymin:rymax, rxmin:rxmax] = zon + (average - zon) * newBrush * 0.1
        elif self.mode == BrushTool.MODE_ACCENTUER:
            average = np.copy(zon)
            average.fill(np.average(zon))
            self.npa[rymin:rymax, rxmin:rxmax] = zon + (zon - average) * newBrush * 0.1
        elif self.mode == BrushTool.MODE_TRAINER:
            if self.firstZone is None:
                self.firstZone = np.copy(zon)
            self.npa[rymin:rymax, rxmin:rxmax] = zon + (self.firstZone - zon) * newBrush
        elif self.mode == BrushTool.MODE_FLOUTER:
            znull = zon
            zon[zon > 99999] = 0
            blurred = gaussian_filter(zon, sigma=1)
            blurred[zon == np.NaN] = 0
            blurred[zon > 99999] = 0
            r = zon + (blurred - zon) * newBrush
            r[znull == np.NaN] = np.NaN
            self.npa[rymin:rymax, rxmin:rxmax] = r
        elif self.mode == BrushTool.MODE_COPIER:
            xminBck, _, _, ymaxBck = self.toCopyLayer.extent().toRectF().getCoords()
            xpixBck = round(
                (self.currentPointXY.x() - xminBck)
                / self.toCopyLayer.rasterUnitsPerPixelX()
            )
            ypixBck = round(
                (ymaxBck - self.currentPointXY.y())
                / self.toCopyLayer.rasterUnitsPerPixelY()
            )
            bckxmin = max(xpixBck - self.brushsize2, 0)
            bckymin = max(ypixBck - self.brushsize2, 0)
            bckxmax = min(xpixBck + self.brushsize2, self.toCopyLayer.width())
            bckymax = min(ypixBck + self.brushsize2, self.toCopyLayer.height())

            self.npa[rymin:rymax, rxmin:rxmax] = zon + (
                (self.npaToCopy[bckymin:bckymax, bckxmin:bckxmax] - zon) * newBrush
            )
        elif self.mode == BrushTool.MODE_COPIE2:
            xminBck, _, _, ymaxBck = self.rlayer.extent().toRectF().getCoords()
            xpixBck = round(
                (self.fromPointXY.x() - xminBck) / self.rlayer.rasterUnitsPerPixelX()
            )
            ypixBck = round(
                (ymaxBck - self.fromPointXY.y()) / self.rlayer.rasterUnitsPerPixelY()
            )
            bckxmin = max(xpixBck - self.brushsize2, 0)
            bckymin = max(ypixBck - self.brushsize2, 0)
            bckxmax = min(xpixBck + self.brushsize2, self.rlayer.width())
            bckymax = min(ypixBck + self.brushsize2, self.rlayer.height())

            if rymax - rymin == bckymax - bckymin and rxmax - rxmin == bckxmax - bckxmin:
                self.npa[rymin:rymax, rxmin:rxmax] = zon + (
                    (self.npa[bckymin:bckymax, bckxmin:bckxmax] - zon) * newBrush
                )

    def canvasPressEvent(self, event):
        if self.mode is None:
            return

        if self.mode == BrushTool.MODE_COPIE2 and self.ctrlKey:
            self.fromPointXY = self._canvas.getCoordinateTransform().toMapCoordinates(
                event.pos().x(), event.pos().y()
            )
            self.fromPointDX = None
            self.fromPointDY = None
            return

        self.currentPointXY = self._canvas.getCoordinateTransform().toMapCoordinates(
            event.pos().x(), event.pos().y()
        )
        self.drawing = True

        if (
            self.mode == BrushTool.MODE_COPIE2
            and self.fromPointXY is not None
            and self.fromPointDX is None
        ):
            self.fromPointDX = self.fromPointXY.x() - self.currentPointXY.x()
            self.fromPointDY = self.fromPointXY.y() - self.currentPointXY.y()

        rx = self.brushR / self.rlayer.rasterUnitsPerPixelX()
        ry = self.brushR / self.rlayer.rasterUnitsPerPixelY()
        fx = fy = 1.0
        if rx > ry:
            fy = rx / ry
        if ry > rx:
            fx = ry / rx

        self.brushsize2 = max(round(rx), round(ry))  # rayon
        self.brushsize = 1 + 2 * self.brushsize2  # diamètre
        self.brush = disk(
            r1=self.brushBlurSize * self.brushsize2, r2=self.brushsize2, fx=fx, fy=fy
        )

        try:
            self.draw()
        except Exception:
            pass

    def canvasMoveEvent(self, event):
        if self.mode is None:
            return

        self.currentPointXY = self._canvas.getCoordinateTransform().toMapCoordinates(
            event.pos().x(), event.pos().y()
        )
        if self.mode == BrushTool.MODE_COPIE2 and self.fromPointDX is not None:
            self.fromPointXY.set(
                self.currentPointXY.x() + self.fromPointDX,
                self.currentPointXY.y() + self.fromPointDY,
            )

        self.buildRubberBand()

        if self.drawing:
            try:
                self.draw()
            except Exception:
                pass

    def canvasReleaseEvent(self, event):
        if self.mode is None:
            return

        self.currentPointXY = None
        self.buildRubberBand()

        self.drawing = False
        self.firstZone = None

        tools.updateGeotiff(self.ds, self.npa)

        iface.mapCanvas().refreshAllLayers()
        iface.mapCanvas().waitWhileRendering()
        self.rlayer.dataProvider().reloadData()
        self.rlayer.triggerRepaint()

    def wheelEvent(self, e):
        if not self.drawing and (self.ctrlKey or self.shiftKey):
            d = e.angleDelta().y()
            if d > 0 and not self.shiftKey and self.ctrlKey:
                self.brushR = self.brushR + self.brushR / 20
            elif d < 0 and not self.shiftKey and self.ctrlKey:
                self.brushR = self.brushR - self.brushR / 20
            elif d > 0 and self.shiftKey and not self.ctrlKey:
                self.brushBlurSize = min(self.brushBlurSize * 1.1, 1)
            elif d < 0 and self.shiftKey and not self.ctrlKey:
                self.brushBlurSize = self.brushBlurSize * 0.9
            elif d > 0 and self.shiftKey and self.ctrlKey:
                self.brushAlpha = min(self.brushAlpha + 0.01, 1)
                self.setLabel("{:0d}".format(round(100 * self.brushAlpha)))
            elif d < 0 and self.shiftKey and self.ctrlKey:
                self.brushAlpha = max(self.brushAlpha - 0.01, 0)
                self.setLabel("{:0d}".format(round(100 * self.brushAlpha)))

            self.buildRubberBand()
            e.accept()

    def keyPressEvent(self, e):
        if self.mode is None:
            return

        self.key = e.modifiers()
        if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.shiftKey = True
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.ctrlKey = True

    def keyReleaseEvent(self, e):
        if self.mode is None:
            return

        self.key = e.modifiers()
        self.shiftKey = e.modifiers() & Qt.KeyboardModifier.ShiftModifier
        self.ctrlKey = e.modifiers() & Qt.KeyboardModifier.ControlModifier
        self.setLabel(None)

    def activate(self):
        pass

    def deactivate(self):
        self.ds = None
        self.npa = None

    def hide(self):
        self.rb.reset()
        self.rbblur.reset()
        self.rbfrom.reset()

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True


def close():
    rasterBrushTool = BrushTool.getInstance()
    rasterBrushTool.hide()
    iface.mapCanvas().unsetMapTool(rasterBrushTool)
    rasterBrushTool.closeToolbar()


r = iface.mapCanvas().currentLayer()
if type(r) is QgsRasterLayer:
    rasterBrushTool = BrushTool(r, iface.mapCanvas())
    iface.mapCanvas().setMapTool(rasterBrushTool)
else:
    iface.messageBar().pushMessage(
        "Raster Retouch",
        "Sélectionnez une couche raster au préalable",
        level=Qgis.MessageLevel.Warning,
    )
