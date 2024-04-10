"""
A piece of demo code for QGis macro... project specific code
The toolbar is built when the project is opened 
Allows, by a simple drag-and-drop on the map, a copy of the marked modifiable attributes between two polygons.

# To be placed in the 'macros' block of the QGis project
# This MyTool.py script must be located next to the QGis project

from MyTool import *
myTool = None

def openProject():
    global myTool
    if myTool is None:
        myTool = MyTool(iface.mapCanvas()) 

def closeProject():
    global myTool
    myTool.closeToolbar()
    myTool = None
    
def saveProject():
    pass

"""

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.utils import iface
from qgis.core import QgsCoordinateTransform, QgsWkbTypes, QgsApplication, QgsProject, QgsSpatialIndex, QgsGeometry
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.PyQt.QtCore import Qt

           
class MyTool(QgsMapTool): 
    """
    'Tool' class, displays the button bar, controls mouse events on the map (selection...)
    """
    
    ACTION_COPY = "A"
    ACTION_UNDO = "B"
    MODE_COPY = "COPY"
   
    def __init__(self, canvas):
        """
        Initilizations

        rubber band...
        """
        QgsMapTool.__init__(self, canvas) 

        self._canvas = canvas 
        self.x = self._canvas.getCoordinateTransform()
        self.actions = {}
        self.currentLayer = None
        self.mode = None
        self.workingLayer = None
        self.history = []

        self.fromPointXY = self.currentPointXY = None
        self.rb = QgsRubberBand(self._canvas, QgsWkbTypes.LineGeometry)
        self.rb.setStrokeColor(QColor(150, 30, 80, 200))
        self.rb.setWidth(2)

        # build the toolbar
        self.initToolbar()

    def deactivate(self):
        for _, a in self.actions.items():
            a.setChecked(False)
        self.rb.reset()

    def initToolbar(self):
        """
        Build toolbar 
        """
        self.actions[self.ACTION_COPY] = QAction(QIcon(str(QgsProject.instance().absolutePath()+"/MyTool.A.svg")), "Copy Attribute", iface.mainWindow())
        self.actions[self.ACTION_COPY].setCheckable(True)
        self.actions[self.ACTION_COPY].triggered.connect(lambda : self.modeCopy())

        self.actions[self.ACTION_UNDO] = QAction(QgsApplication.getThemeIcon("mActionUndo.svg"), "Undo", iface.mainWindow())
        self.actions[self.ACTION_UNDO].setEnabled(False)
        self.actions[self.ACTION_UNDO].triggered.connect(lambda : self.undo())

        self.toolbar = iface.addToolBar("MyToolBar")

        for a in self.actions.values():
            self.toolbar.addAction(a)

    def buildIndex(self):
        """
        Build index for features search
        """
        if self.workingLayer != self._canvas.currentLayer():
            self.workingLayer = self._canvas.currentLayer()

            self.xMap2Layer = QgsCoordinateTransform(self._canvas.mapSettings().destinationCrs(), self.workingLayer.crs(), QgsProject.instance())

            self.geoIndex = QgsSpatialIndex()
            for f in self.workingLayer.getFeatures():
                self.geoIndex.addFeature(f)

    def modeCopy(self):
        """
        Switch to copy attribute mode
        """
        if self.actions[self.ACTION_COPY].isChecked():
            self.mode = MyTool.MODE_COPY
            self._canvas.setMapTool(self)
        else:
            self.mode = None
            self._canvas.unsetMapTool(self)

        self.rb.reset()

    def undo(self):
        """
        Restore attributes
        """
        oldValues = self.history.pop()

        for field_idx, v in oldValues["values"].items():
            self.workingLayer.changeAttributeValue(oldValues["fid"], field_idx, v)

        self.actions[self.ACTION_UNDO].setEnabled(len(self.history) > 0)
        self.workingLayer.triggerRepaint()

    def closeToolbar(self):
        for _, a in self.actions.items():
            self.toolbar.removeAction(a)

        self.toolbar = None

    def buildRubberBand(self):
        """
        Build line - from feature -> to feature
        """
        if self.currentPointXY is None or self.mode is None or self.fromPointXY is None:
            self.rb.reset()
        else:
            if self.mode == MyTool.MODE_COPY:
                geom = QgsGeometry.fromPolylineXY([self.fromPointXY, self.currentPointXY])
                self.rb.setToGeometry(geom)

    def doActionA(self):
        """
        Identify features, copy attributes
        """
        fromPointInLayer = self.xMap2Layer.transform(self.fromPointXY)
        toPointInLayer = self.xMap2Layer.transform(self.currentPointXY)

        fromId = self.geoIndex.nearestNeighbor(fromPointInLayer, 1)
        toId = self.geoIndex.nearestNeighbor(toPointInLayer, 1)

        fromFeat = None
        for id in fromId:
            fromFeat = self.workingLayer.getFeature(id)
            if fromFeat.geometry().contains(fromPointInLayer):
                break

        toFeat = None
        for id in toId:
            toFeat = self.workingLayer.getFeature(id)
            if toFeat.geometry().contains(toPointInLayer):
                break

        if fromFeat is None or toFeat is None:
            return

        # copy attributes, save old values 
        form_config = self.workingLayer.editFormConfig()
        oldValues = {"fid":toFeat.id(), "values":{}}
        for field in self.workingLayer.fields():
            field_idx = self.workingLayer.fields().indexOf(field.name())
            if form_config.readOnly(field_idx) or field_idx in self.workingLayer.primaryKeyAttributes():
                continue

            oldValues["values"][field_idx] = toFeat[field.name()]
            self.workingLayer.changeAttributeValue(toFeat.id(), field_idx, fromFeat[field.name()])

        self.history.append(oldValues)
        self.actions[self.ACTION_UNDO].setEnabled(True)

        self.workingLayer.triggerRepaint()
        
    def canvasPressEvent(self, event):
        """
        Begining
        """
        if self.mode is None:
            return

        self.fromPointXY = self.x.toMapCoordinates(event.pos().x(), event.pos().y())
        self.currentPointXY = self.x.toMapCoordinates(event.pos().x(), event.pos().y())

        self.buildIndex()
        self.workingLayer.startEditing()

    def canvasMoveEvent(self, event):
        """
        Rebuild rubber band (then line)
        """
        if self.mode is None:
            return

        self.currentPointXY = self.x.toMapCoordinates(event.pos().x(), event.pos().y())
        self.buildRubberBand()


    def canvasReleaseEvent(self, event):
        """
        mouse button release : do action
        """
        if self.mode is None:
            return

        self.rb.reset()
        if self.mode == MyTool.MODE_COPY:
            self.doActionA()

        self.fromPointXY = self.currentPointXY = None


