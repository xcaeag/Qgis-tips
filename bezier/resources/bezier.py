"""
A function dedicated to expressions, to construct Bezier curves.

Code very inspired by https://codereview.stackexchange.com/questions/240710/pure-python-b%C3%A9zier-curve-implementation
"""

from qgis.utils import qgsfunction
from qgis.core import QgsPointXY, QgsGeometry
import numpy as np


def bezierPoint(ctrlPoints, t):
    while len(ctrlPoints) > 1:
        controlLinestring = zip(ctrlPoints[:-1], ctrlPoints[1:])
        ctrlPoints = [(1 - t) * p1 + t * p2 for p1, p2 in controlLinestring]

    return ctrlPoints[0]

def bezierCurve(ctrlPoints, npoints):
    last_point = npoints - 1
    return [bezierPoint(ctrlPoints, i / last_point) for i in range(npoints)]

@qgsfunction(args="auto", group="Custom")
def bezierFromLine(lineGeom, npoints, feature, parent):
    """Returns a bezier curve linestring geometry from controls points (linestring nodes)
    <h2>Example usage:</h2>
    <ul>
      <li>bezierFromLine($geometry, 10)</li>
    </ul>
    
    Parameters:
    lineGeom (geometry): the original the linestring whose nodes are the control points.
    npoints (int) : number of intermediate curve points

    Returns:
    geometry : the bezier curve (linestring geometry)
    """
    ctrlpoints = [np.array([p.x(), p.y()]) for p in lineGeom.asPolyline()]
    newPoints = bezierCurve(ctrlpoints, npoints)
    polyLine = [QgsPointXY(p[0], p[1]) for p in newPoints]
    newG = QgsGeometry.fromPolylineXY(polyLine)

    return newG
