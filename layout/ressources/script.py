from osgeo import gdal
from affine import Affine
import processing

from qgis.PyQt.QtCore import QPointF

from qgis.utils import iface

from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsLayoutItemMap,
    QgsLayoutItemPage,
    QgsFeature,
    QgsPointXY,
    QgsGeometry,
)


def rotate_gt(affine_matrix, angle, pivot=None):
    """This function generate a rotated affine matrix"""

    # The gdal affine matrix format is not the same
    # of the Affine format, so we use a bullit-in function
    # to change it
    # see : https://github.com/sgillies/affine/blob/master/affine/__init__.py#L178
    affine_src = Affine.from_gdal(*affine_matrix)
    # We made the rotation. For this we calculate a rotation matrix,
    # with the rotation method and we combine it with the original affine matrix
    # Be carful, the star operator (*) is surcharged by Affine package. He make
    # a matrix multiplication, not a basic multiplication
    affine_dst = affine_src * affine_src.rotation(angle, pivot)
    # We retrun the rotated matrix in gdal format
    return affine_dst.to_gdal()


def tifRotation(rast, rot, pivotPointXY):
    filename = rast.dataProvider().dataSourceUri()
    nf = "{}.rot.tif".format(filename)

    dssrc = gdal.Open(filename)
    driver = gdal.GetDriverByName("GTiff")
    dsdst = driver.CreateCopy(nf, dssrc, strict=0)
    gt_affine = dssrc.GetGeoTransform()

    ulx, xres, _, uly, _, yres = gt_affine
    xpix = int((pivotPointXY.x() - ulx) / xres)
    ypix = int((pivotPointXY.y() - uly) / yres)
    pivot = (xpix, ypix)

    dsdst.SetGeoTransform(rotate_gt(gt_affine, rot, pivot))
    return nf


def getCompositionExtents(name="modele", map="principale"):
    projectInstance = QgsProject.instance()
    projectLayoutManager = projectInstance.layoutManager()
    layouts = projectLayoutManager.printLayouts()

    if len(layouts) == 0:
        raise Exception("No layout")

    mapItem = pagesize = None

    myLayout = False
    for layout in layouts:
        if layout.name() == name:
            myLayout = layout
            for item in layout.items():
                if (isinstance(item, QgsLayoutItemMap)) and item.id() == map:
                    mapItem = item
                if isinstance(item, QgsLayoutItemPage):
                    pagesize = item.pageSize()

    if myLayout is None:
        raise Exception("Layout '{}' not found".format(name))

    if item is None and myLayout is not None:
        raise Exception("Map '{}' not found".format(map))

    return (mapItem, pagesize)


def layerFromPolygon(geom, name="extent"):
    crs = iface.mapCanvas().mapSettings().destinationCrs()

    vl = QgsVectorLayer("Polygon?crs={}".format(crs.authid()), name, "memory")
    pr = vl.dataProvider()
    vl.startEditing()

    feat = QgsFeature()
    feat.setGeometry(geom)
    pr.addFeature(feat)

    vl.commitChanges()

    return vl


def layerFromExtent(extent, name="extent", rotation=0.0):
    geom = QgsGeometry.fromRect(extent)
    geom.rotate(-rotation, extent.center())
    return layerFromPolygon(geom, name)


def rasterClipToLayoutMapExtent(rast, composer="a", map="main"):
    mapItem, _ = getCompositionExtents(name=composer, map=map)
    # mapItem.itemRotation(), mapItem.extent(), mapItem.mapRotation()

    mapExtentGeom = QgsGeometry.fromRect(mapItem.extent())
    mapExtentGeom.rotate(-mapItem.mapRotation(), mapItem.extent().center())
    pivotPointXY = mapExtentGeom.centroid().asPoint()

    # rotation tif (rotation objet carte + rotation contenu carte), centré sur extent page
    alpha = mapItem.mapRotation() + mapItem.itemRotation()
    filename = tifRotation(rast, alpha, pivotPointXY)

    # rotation extent
    g = QgsGeometry(mapExtentGeom)
    g.rotate(alpha, g.centroid().asPoint())
    v3 = layerFromPolygon(g, name="carte dépivotée")

    # clip
    source = rast.dataProvider().dataSourceUri()
    out = "{}.clip.tif".format(source)
    clip = processing.run(
        "gdal:cliprasterbymasklayer",
        {
            "INPUT": filename,
            "MASK": v3,
            "SOURCE_CRS": None,
            "TARGET_CRS": None,
            "TARGET_EXTENT": None,
            "NODATA": None,
            "ALPHA_BAND": False,
            "CROP_TO_CUTLINE": True,
            "KEEP_RESOLUTION": False,
            "SET_RESOLUTION": False,
            "X_RESOLUTION": None,
            "Y_RESOLUTION": None,
            "MULTITHREADING": False,
            "OPTIONS": "",
            "DATA_TYPE": 0,
            "EXTRA": "",
            "OUTPUT": out,
        },
    )
    clipedRaster = QgsRasterLayer(clip["OUTPUT"], "clipped", "gdal")
    return clipedRaster


def rasterClipToLayoutPageExtent(rast, composer="a", map="main"):
    mapItem, pagesize = getCompositionExtents(name=composer, map=map)
    # mapItem.itemRotation(), mapItem.extent(), mapItem.mapRotation()

    alpha = mapItem.mapRotation() + mapItem.itemRotation()

    # rotation extent map
    g = QgsGeometry.fromRect(mapItem.extent())
    g.rotate(mapItem.itemRotation(), g.centroid().asPoint())

    p1 = QPointF(0, 0)
    p2 = QPointF(pagesize.width(), 0)
    p3 = QPointF(pagesize.width(), pagesize.height())
    p4 = QPointF(0, pagesize.height())

    toMapTransfo = mapItem.layoutToMapCoordsTransform()
    points_mapunit = [QgsPointXY(toMapTransfo.map(p)) for p in (p1, p2, p3, p4)]

    pageExtentGeom = QgsGeometry.fromPolygonXY([points_mapunit])
    pivotPointXY = pageExtentGeom.centroid().asPoint()

    # rotation tif (rotation objet carte + rotation contenu carte), centré sur extent page
    filename = tifRotation(rast, alpha, pivotPointXY)

    # rotation extent page
    g = QgsGeometry(pageExtentGeom)
    g.rotate(alpha, g.centroid().asPoint())
    v3 = layerFromPolygon(g, name="page dépivotée")
    QgsProject.instance().addMapLayer(v3, True)

    # clip
    source = rast.dataProvider().dataSourceUri()
    out = "{}.clip.tif".format(source)
    clip = processing.run(
        "gdal:cliprasterbymasklayer",
        {
            "INPUT": filename,
            "MASK": v3,
            "SOURCE_CRS": None,
            "TARGET_CRS": None,
            "TARGET_EXTENT": None,
            "NODATA": None,
            "ALPHA_BAND": False,
            "CROP_TO_CUTLINE": True,
            "KEEP_RESOLUTION": False,
            "SET_RESOLUTION": False,
            "X_RESOLUTION": None,
            "Y_RESOLUTION": None,
            "MULTITHREADING": False,
            "OPTIONS": "",
            "DATA_TYPE": 0,
            "EXTRA": "",
            "OUTPUT": out,
        },
    )

    fill = processing.run(
        "native:fillnodata",
        {
            "INPUT": clip["OUTPUT"],
            "BAND": 1,
            "FILL_VALUE": 0,
            "OUTPUT": "TEMPORARY_OUTPUT",
        },
    )
    clipedRaster = QgsRasterLayer(fill["OUTPUT"], "clipped", "gdal")

    return clipedRaster


"""
rast = iface.mapCanvas().currentLayer()

clipedRaster = rasterClipToLayoutPageExtent(
    rast, composer="modele +65 deg", map="map1"
)
QgsProject.instance().addMapLayer(clipedRaster, True)

"""
