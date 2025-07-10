from qgis.core import QgsProject, QgsExpressionContextUtils, QgsMapLayer
from qgis.gui import QgsDoubleSpinBox, QgsSpinBox, QgsColorButton

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QLabel, QWidget, QGridLayout, QLineEdit, QDockWidget


class VarWidget(QWidget):
    """Widget for displaying and editing project and layers variables.
    """

    def updateVariable(self, obj, key, stringValue):
        """Update the variable in the project or layer scope."""
        if isinstance(obj, QgsProject):
            QgsExpressionContextUtils.setProjectVariable(
                obj, key, stringValue
            )

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

    def addColorWidget(self, pk, obj, v):
        """Create a color button widget for color variables."""
        wdgt = QgsColorButton()
        wdgt.setColor(QColor(v))
        wdgt.colorChanged.connect(
            lambda value, key=pk: self.updateVariable(obj, key, value.name())
        )
        return wdgt

    def addLineEditWidget(self, pk, obj, v):
        """Create a line edit widget for string variables."""
        wdgt = QLineEdit()
        try:
            wdgt.setText(str(v))
        except ValueError:
            wdgt.setText('')
        wdgt.textChanged.connect(
            lambda value, key=pk: self.updateVariable(obj, key, value)
        )
        return wdgt

    def addWidgets(self, conf, obj, scope, y):
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
            return y
        
        if isinstance(obj, QgsProject):
            title = "Project variables"
        elif isinstance(obj, QgsMapLayer):
            title = f"'{obj.name()}' layer variables"

        label = QLabel(title)
        label.setAlignment(Qt.AlignLeft)
        self._varBarLayout.addWidget(label, y, x)
        x = x + 1

        for pk in variables:
            if scope.isReadOnly(pk):
                continue
            wdgt = None
            v = scope.variable(pk)

            if pk in conf.keys():
                variable = conf[pk]

                if variable["type"] == "int":
                    wdgt = self.addIntWidget(pk, obj, v, min=variable["min"], max=variable["max"], step=variable["step"])
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
                    wdgt = self.addColorWidget(pk, obj, v)
                else:
                    wdgt = self.addLineEditWidget(pk, obj, v)
            else:
                if "integer" in pk.lower():
                    wdgt = self.addIntWidget(pk, obj, v)
                elif "double" in pk.lower():
                    wdgt = self.addDoubleWidget(pk, obj, v)
                elif "float" in pk.lower():
                    wdgt = self.addDoubleWidget(pk, obj, v)
                elif "color" in pk.lower():
                    wdgt = self.addColorWidget(pk, obj, v)
                else:
                    wdgt = self.addLineEditWidget(pk, obj, v)

            if wdgt is not None:
                """Label for widget"""
                label = QLabel(pk)
                label.setAlignment(Qt.AlignRight)
                label.setBuddy(wdgt)

                self._varBarLayout.addWidget(label, y, x)
                x = x + 1
                self._varBarLayout.addWidget(wdgt, y, x)
                x = x + 1

                if x > 5:
                    x = 1
                    y = y + 1

        return y

    def __init__(self, iface, conf, parent=None):
        """Initialize the VarWidget with the given interface and configuration."""
        super(VarWidget, self).__init__(parent)
        self.iface = iface
        self.conf = conf
        self._varBarLayout = QGridLayout()  # QHBoxLayout()

        """ Add widgets for the project variables. """
        y = 0
        projectScope = QgsExpressionContextUtils.projectScope(QgsProject.instance())
        y = self.addWidgets(conf, QgsProject.instance(), projectScope, y)
        y = y + 1

        """ Add widgets for each checked layer variable in the project. """
        root = QgsProject.instance().layerTreeRoot()
        layers = root.checkedLayers()
        for _layer in layers:
            layerScope = QgsExpressionContextUtils.layerScope(_layer)
            y = self.addWidgets(conf, _layer, layerScope, y)
            y = y + 1

        self.setLayout(self._varBarLayout)


conf = {
    "typo_size": {"type": "int", "min": 100, "max": 10000, "step": 100},
    "typo_gap": {"type": "int", "min": 100, "max": 10000, "step": 100},
}

w = VarWidget(iface, conf)
dock_widget = QDockWidget("Variables", iface.mainWindow())
dock_widget.setWidget(w)
iface.addDockWidget(Qt.RightDockWidgetArea, dock_widget)
dock_widget.setFloating(True)

"""w = VarWidget(iface, conf)
msgbar = iface.messageBar()
msgbar.pushWidget(w)
"""
