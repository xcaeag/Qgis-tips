"""
Help script for displaying and editing project and layers variables.

This script creates a widget that allows users to view and modify variables
"""

from qgis.core import QgsProject, QgsExpressionContextUtils, QgsMapLayer
from qgis.gui import QgsDoubleSpinBox, QgsSpinBox, QgsColorButton

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QLabel,
    QWidget,
    QGridLayout,
    QLineEdit,
    QDockWidget,
    QSizePolicy,
)


class VarWidget(QWidget):
    """Widget for displaying and editing project and layers variables."""

    def updateVariable(self, obj, key, stringValue):
        """Update the variable in the project or layer scope."""
        if isinstance(obj, QgsProject):
            QgsExpressionContextUtils.setProjectVariable(obj, key, stringValue)

        if isinstance(obj, QgsMapLayer):
            QgsExpressionContextUtils.setLayerVariable(obj, key, stringValue)

        self.iface.mapCanvas().refreshAllLayers()

    def addIntWidget(self, pk, obj, v, min=0, max=10000, step=1):
        """Create a spin box widget for integer variables."""
        wdgt = QgsSpinBox()
        wdgt.setMinimum(min)
        wdgt.setMaximum(max)
        wdgt.setSingleStep(step)

        try:
            wdgt.setClearValue(int(v), v)
        except ValueError:
            wdgt.setClearValue(0, "0")

        wdgt.valueChanged.connect(
            lambda value, key=pk: self.updateVariable(obj, key, f"{value}")
        )

        return wdgt

    def addDoubleWidget(self, pk, obj, v, min=0.0, max=10000.0, step=1.0):
        """Create a double spin box widget for float variables."""
        wdgt = QgsDoubleSpinBox()
        wdgt.setMinimum(min)
        wdgt.setMaximum(max)
        wdgt.setSingleStep(step)
        try:
            wdgt.setValue(float(v))
        except ValueError:
            wdgt.setValue(0.0)
        wdgt.valueChanged.connect(
            lambda value, key=pk: self.updateVariable(obj, key, f"{value}")
        )
        return wdgt

    def addColorWidget(self, v):
        """Create a color button widget for color variables."""
        wdgt = QgsColorButton()
        wdgt.setAllowOpacity(True)
        wdgt.setColor(QColor(v))
        return wdgt

    def addLineEditWidget(self, pk, obj, v):
        """Create a line edit widget for string variables."""
        wdgt = QLineEdit()
        try:
            wdgt.setText(str(v))
        except ValueError:
            wdgt.setText("")
        wdgt.textChanged.connect(
            lambda value, key=pk: self.updateVariable(obj, key, value)
        )
        return wdgt

    def addWidget(self, wdgt, label, x, y):
        """Add a widget to the variable bar layout."""

        # Create a label for the widget
        label = QLabel(label)
        label.setAlignment(Qt.AlignRight)
        label.setBuddy(wdgt)
        self._varBarLayout.addWidget(label, y, x)
        self._varBarLayout.addWidget(wdgt, y, x + 1)

    def addProjectWidgets(self):
        """Add widgets for project-specific data

        for now : background color.
        todo : project colors
        """
        label = QLabel("Project")
        label.setAlignment(Qt.AlignLeft)
        self._varBarLayout.addWidget(label, self.y, 0)

        v = QgsProject.instance().backgroundColor().name(QColor.HexArgb)
        wdgt = self.addColorWidget(v)
        wdgt.colorChanged.connect(
            lambda value: QgsProject.instance().setBackgroundColor(value)
        )
        self.addWidget(wdgt, "Background Color", 1, self.y)
        self.y = self.y + 1

    def addVarWidgets(self, conf, obj, scope):
        """Add widgets for the variables of the given object (project or layer)."""
        variables = scope.filteredVariableNames()
        x = 0

        # check if var exists
        varExists = False
        for pk in variables:
            if scope.isReadOnly(pk):
                continue
            varExists = True

        if not varExists:
            return

        if isinstance(obj, QgsProject):
            title = "Project variables"
        elif isinstance(obj, QgsMapLayer):
            title = f"'{obj.name()}' layer variables"

        label = QLabel(title)
        label.setAlignment(Qt.AlignLeft)
        self._varBarLayout.addWidget(label, self.y, x)
        x = x + 1

        for pk in variables:
            if scope.isReadOnly(pk):
                continue
            wdgt = None
            v = scope.variable(pk)

            if pk in conf.keys():
                variable = conf[pk]

                if variable["type"] == "integer":
                    wdgt = self.addIntWidget(
                        pk,
                        obj,
                        v,
                        min=variable["min"],
                        max=variable["max"],
                        step=variable["step"],
                    )
                elif variable["type"] == "double":
                    wdgt = self.addDoubleWidget(
                        pk,
                        obj,
                        v,
                        min=variable["min"],
                        max=variable["max"],
                        step=variable["step"],
                    )
                elif variable["type"] == "color":
                    wdgt = self.addColorWidget(v)
                    wdgt.colorChanged.connect(
                        lambda value, key=pk: self.updateVariable(
                            obj, key, value.name(QColor.HexArgb)
                        )
                    )
                else:
                    wdgt = self.addLineEditWidget(pk, obj, v)
            else:
                if "integer" in pk.lower():
                    wdgt = self.addIntWidget(pk, obj, v)
                elif "double" in pk.lower():
                    wdgt = self.addDoubleWidget(pk, obj, v)
                elif "real" in pk.lower():
                    wdgt = self.addDoubleWidget(pk, obj, v)
                elif "color" in pk.lower():
                    wdgt = self.addColorWidget(v)
                    wdgt.colorChanged.connect(
                        lambda value, key=pk: self.updateVariable(
                            obj, key, value.name(QColor.HexArgb)
                        )
                    )
                else:
                    wdgt = self.addLineEditWidget(pk, obj, v)

            if wdgt is not None:
                self.addWidget(wdgt, pk, x, self.y)
                x = x + 2
                if x > 5:
                    x = 1
                    self.y = self.y + 1

        self.y = self.y + 1

    def __init__(self, iface, conf, parent=None):
        """Initialize the VarWidget with the given interface and configuration."""
        super(VarWidget, self).__init__(parent)
        self.iface = iface
        self.conf = conf
        self._varBarLayout = QGridLayout()  # QHBoxLayout()

        """ Add widgets for the project variables. """
        self.y = 0

        self.addProjectWidgets()

        projectScope = QgsExpressionContextUtils.projectScope(QgsProject.instance())
        self.addVarWidgets(conf, QgsProject.instance(), projectScope)

        """ Add widgets for each checked layer variable in the project. """
        root = QgsProject.instance().layerTreeRoot()
        layers = root.checkedLayers()
        for _layer in layers:
            layerScope = QgsExpressionContextUtils.layerScope(_layer)
            self.addVarWidgets(conf, _layer, layerScope)

        self.setLayout(self._varBarLayout)


"""Adjust types and steps for some variables in the configuration dictionary.

types : integer, double, color

Take inspiration from this example
"""
conf = {
    "typo_size": {"type": "integer", "min": 100, "max": 10000, "step": 100},
    "typo_gap": {"type": "integer", "min": 100, "max": 10000, "step": 100},
    "roads": {"type": "color"},
}

w = VarWidget(iface, conf)
dock_widget = QDockWidget("Variables", iface.mainWindow())
dock_widget.setWidget(w)
dock_widget.setFloating(True)
dock_widget.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))
iface.addDockWidget(Qt.NoDockWidgetArea, dock_widget)
