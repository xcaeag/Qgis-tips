"""
Clips a raster to a layout's extent,
by extrapolating the map extent to the entire page (beyond the extent of the "map" object)
Takes rotations into account !
Allows you to obtain, for example, a DEM of the same proportion as an export of the same layout, well aligned, for Blender.

Découper, pivoter un raster selon l'emprise d'une mise en page,
en extrapollant l'étendue de la carte à la page entière (au delà de l'emprise de l'objet 'map')
Tient compte des rotations !
Permet d'obtenir par exemple un MNT de même proportion qu'un export de la même mise en page, bien callé, pour Blender.
"""

from osgeo import gdal
import processing
import numpy as np
from skimage import transform

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
    QgsProcessingUtils,
)


def writeGeotiff(filename, arr, proj, transfo, nodatavalue=None):
    """Save a Geotiff file from numpy array

    Args:
        filename (String): file to write
        arr (array): numpy array
        proj : GDal projection
        transfo : GDal GeoTransform
        nodatavalue (optional): the 'nodata' value. Defaults to None.
    """
    if arr.dtype == np.float32:
        arr_type = gdal.GDT_Float32
    elif arr.dtype == np.int8:
        arr_type = gdal.GDT_Int8
    elif arr.dtype == np.int16:
        arr_type = gdal.GDT_Int16
    else:
        arr_type = gdal.GDT_Int32

    if len(arr.shape) == 3:
        Z, H, W = arr.shape
    if len(arr.shape) == 2:
        Z = 1
        H, W = arr.shape

    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(filename, W, H, Z, arr_type)
    out_ds.SetProjection(proj)
    out_ds.SetGeoTransform(transfo)
    for b in range(Z):
        data = arr if (len(arr.shape) == 2) else arr[b]
        band = out_ds.GetRasterBand(b + 1)
        if nodatavalue is not None:
            band.SetNoDataValue(nodatavalue)
        band.WriteArray(data)
        band.FlushCache()
        band.ComputeStatistics(False)


def tifTransform(rast, geom1, geom2):
    """Image warping with scikit-image transform

    The target image is "projected", but no longer corresponds to the ground reality...
    it is possibly rotated according to the orientation of the source and target locations.
    This "fictitious" projection will be used for subsequent processing: clip, embossing.

    see https://scikit-image.org/docs/stable/auto_examples/transform/plot_geometric.html#image-warping

    Args:
        rast (QgsRaster): the raster to transform
        geom1 (QgsGeometry): Rectangle (Four points polygon), zone to warp
        geom2 (QgsGeometry): Rectangle (Four points polygon), the destination

    Returns:
        String: temporary file name of the transformed raster
    """
    filename = rast.dataProvider().dataSourceUri()
    base = gdal.Open(filename)
    proj, transfo = base.GetProjection(), base.GetGeoTransform()
    aBase = base.ReadAsArray()

    # src :
    xmin, _, _, ymax = rast.extent().toRectF().getCoords()
    newPoints = [
        [
            int((pt.x() - xmin) / rast.rasterUnitsPerPixelX()),
            int((ymax - pt.y()) / rast.rasterUnitsPerPixelY()),
        ]
        for pt in geom2.asPolygon()[0]
    ]
    fromPoints = [
        [
            int((pt.x() - xmin) / rast.rasterUnitsPerPixelX()),
            int((ymax - pt.y()) / rast.rasterUnitsPerPixelY()),
        ]
        for pt in geom1.asPolygon()[0]
    ]

    tform3 = transform.ProjectiveTransform()
    tform3.estimate(newPoints, fromPoints)
    warped = transform.warp(aBase, tform3)

    nf = QgsProcessingUtils.generateTempFilename("rotated.tif")
    writeGeotiff(nf, warped, proj, transfo)

    return nf


def getCompositionExtents(layoutName="myLayout", mapItemId="map1"):
    """Find map item and page size

    Args:
        layoutName (str, optional): The layout name. Defaults to "myLayout".
        mapItemId (str, optional): The map item id. Defaults to "map1".

    Returns:
        tuple: map item, page size
    """
    projectInstance = QgsProject.instance()
    projectLayoutManager = projectInstance.layoutManager()

    myLayout = projectLayoutManager.layoutByName(layoutName)
    if myLayout is None:
        raise Exception("Layout '{}' not found".format(layoutName))

    myMapItem = myLayout.itemById(mapItemId)
    if myMapItem is None or not isinstance(myMapItem, QgsLayoutItemMap):
        raise Exception("Map '{}' not found".format(mapItemId))

    for item in myLayout.items():
        if isinstance(item, QgsLayoutItemPage):
            pagesize = item.pageSize()

    return (myMapItem, pagesize)


def buildPolygonLayerFromGeom(geom, name="extent"):
    """Create a layer from polygon Geometry

    Args:
        geom (QgsGeometry): the geometry
        name (str, optional): layer name. Defaults to "extent".

    Returns:
        QgsVectorLayer: the polygon layer
    """
    crs = iface.mapCanvas().mapSettings().destinationCrs()
    vl = QgsVectorLayer("Polygon?crs={}".format(crs.authid()), name, "memory")

    vl.startEditing()
    feat = QgsFeature()
    feat.setGeometry(geom)
    vl.dataProvider().addFeature(feat)
    vl.commitChanges()

    return vl


def rasterClipToLayoutPageExtent(rasterLayer, layoutName="myLayout", mapItemId="Map 1"):
    """Clips a raster to a layout's extent,

    by extrapolating the map extent to the entire page (beyond the extent of the "map" object)
    Takes rotations into account !

        Args:
            rasterLayer (QgsRasterLayer): the raster to clip
            layoutName (str, optional): the name of layout to consider. Defaults to "myLayout".
            mapItemId (str, optional): the map id (the map on the page, the extent of which we wish to extrapolate). Defaults to "Map 1".

        Returns:
            tuple(QgsVectorLayer, QgsVectorLayer, QgsRasterLayer): the unpivoted Map Layer, unpivoted Page Layer for any subsequent treatments, the cliped Raster
    """
    mapItem, pagesize = getCompositionExtents(layoutName=layoutName, mapItemId=mapItemId)
    alpha = mapItem.mapRotation() + mapItem.itemRotation()

    mapGeom = QgsGeometry.fromQPolygonF(mapItem.visibleExtentPolygon())

    p1 = QPointF(0, 0)
    p2 = QPointF(pagesize.width(), 0)
    p3 = QPointF(pagesize.width(), pagesize.height())
    p4 = QPointF(0, pagesize.height())

    toMapTransfo = mapItem.layoutToMapCoordsTransform()
    points_mapunit = [QgsPointXY(toMapTransfo.map(p)) for p in (p1, p2, p3, p4)]

    pageGeom = QgsGeometry.fromPolygonXY([points_mapunit])
    pageLayer = buildPolygonLayerFromGeom(pageGeom, name="page")

    # rotation
    pivotPointXY = pageGeom.centroid().asPoint()

    unpivotedPageGeom = QgsGeometry(pageGeom)
    unpivotedPageGeom.rotate(alpha, pivotPointXY)
    unpivotedPageLayer = buildPolygonLayerFromGeom(
        unpivotedPageGeom, name="unpivoted page"
    )

    # map
    mapGeom.rotate(alpha, pivotPointXY)
    unpivotedMapLayer = buildPolygonLayerFromGeom(mapGeom, name="unpivoted map")

    # first clip for perf
    clipFile = QgsProcessingUtils.generateTempFilename("clip1.tif")
    processing.run(
        "gdal:cliprasterbymasklayer",
        {
            "INPUT": rasterLayer,
            "MASK": pageLayer,
            "NODATA": None,
            "ALPHA_BAND": False,
            "CROP_TO_CUTLINE": True,
            "KEEP_RESOLUTION": False,
            "SET_RESOLUTION": False,
            "OPTIONS": "",
            "DATA_TYPE": 6,
            "EXTRA": "",
            "OUTPUT": clipFile,
        },
    )
    clipedRaster1 = QgsRasterLayer(clipFile, "clipped 1")

    # raster transformation
    filename = tifTransform(clipedRaster1, pageGeom, unpivotedPageGeom)

    # clip
    clipFile = QgsProcessingUtils.generateTempFilename("rotated.tif")
    processing.run(
        "gdal:cliprasterbymasklayer",
        {
            "INPUT": filename,
            "MASK": unpivotedPageLayer,
            "NODATA": None,
            "ALPHA_BAND": False,
            "CROP_TO_CUTLINE": True,
            "KEEP_RESOLUTION": False,
            "SET_RESOLUTION": False,
            "OPTIONS": "",
            "DATA_TYPE": 0,
            "EXTRA": "",
            "OUTPUT": clipFile,
        },
    )

    clipedRaster = QgsRasterLayer(clipFile, "clipped")
    return (unpivotedMapLayer, unpivotedPageLayer, clipedRaster)


def rasterEmboss(
    rasterLayer,
    unpivotedMapLayer,
    pageLayer,
    embossPage=-100,
    embossZero=-50,
    zero=0,
):
    """Emboss DEM raster

    embossed the DEM by lowering the values ​​below zero (the sea appears lower, the coasts will be better drawn),
    possibly also embossed the DEM outside the map area, for a relief effect at the edge.

    Args:
        rasterLayer (QgsRasterLayer): the raster DEM to emboss
        unpivotedMapLayer (QgsVectorLayer): the map extent
        pageLayer (_type_): the page extent
        embossPage (int, optional): depth of page stamping. Defaults to -100.
        embossZero (int, optional): depth of sea stamping. Defaults to -50.
        zero (int, optional): altitude of the "sea". Defaults to 0. None for no emboss.

    Returns:
        QgsRasterLayer: the embossed raster layer
    """
    if zero is None or embossZero is None:
        emboss_sea = rasterLayer
    else:
        r = processing.run(
            "gdal:rastercalculator",
            {
                "INPUT_A": rasterLayer,
                "BAND_A": 1,
                "FORMULA": f"(A<={zero})*({embossZero}) + (A>{zero})*A",
                "OUTPUT": "TEMPORARY_OUTPUT",
                "NO_DATA": None,
                "RTYPE": 5,
            },
        )
        emboss_sea = r["OUTPUT"]

    if embossPage is None:
        return emboss_sea
    else:
        diff = processing.run(
            "native:difference",
            {
                "INPUT": pageLayer,
                "OVERLAY": unpivotedMapLayer,
                "OUTPUT": "TEMPORARY_OUTPUT",
                "GRID_SIZE": None,
            },
        )

        box = rasterLayer.dataProvider().extent()
        extent = "{},{},{},{} [{}]".format(
            box.xMinimum(),
            box.xMaximum(),
            box.yMinimum(),
            box.yMaximum(),
            rasterLayer.crs().authid(),
        )

        mask = processing.run(
            "gdal:rasterize",
            {
                "INPUT": diff["OUTPUT"],
                "FIELD": "",
                "BURN": embossPage,
                "USE_Z": False,
                "UNITS": 1,
                "WIDTH": rasterLayer.rasterUnitsPerPixelX(),
                "HEIGHT": rasterLayer.rasterUnitsPerPixelY(),
                "EXTENT": extent,
                "OPTIONS": "",
                "DATA_TYPE": 5,
                "NODATA": None,
                "INIT": 0,
                "INVERT": False,
                "EXTRA": "",
                "OUTPUT": "TEMPORARY_OUTPUT",
            },
        )

        emboss2 = processing.run(
            "gdal:rastercalculator",
            {
                "INPUT_A": emboss_sea,
                "BAND_A": 1,
                "INPUT_B": mask["OUTPUT"],
                "BAND_B": 1,
                "FORMULA": "A*(B==0)+B",
                "OUTPUT": "TEMPORARY_OUTPUT",
                "NO_DATA": None,
                "RTYPE": 5,
            },
        )

        return QgsRasterLayer(emboss2["OUTPUT"], "embossed")


def rastToUNIT16(rast):
    """
    convert to uint16 for blender
    """
    stats = processing.run(
        "native:rasterlayerstatistics",
        {"INPUT": rast, "OUTPUT": "TEMPORARY_OUTPUT", "BAND": 1},
    )

    r = processing.run(
        "gdal:rastercalculator",
        {
            "INPUT_A": rast,
            "BAND_A": 1,
            "FORMULA": "(A-({min})) / ({max}-({min})) * 65535".format(
                min=stats["MIN"], max=stats["MAX"]
            ),
            "OUTPUT": "TEMPORARY_OUTPUT",
            "NO_DATA": None,
            "RTYPE": 2,  # uint16
        },
    )
    return QgsRasterLayer(r["OUTPUT"], "embossed uint16")


"""
# Exemple usage :

# get current selected raster layer 
rast = iface.mapCanvas().currentLayer()

# clip, rotate according to the elements of the composer
unpivotedMapLayer, unpivotedPageLayer, clipedRaster = rasterClipToLayoutPageExtent(
    rast, layoutName="myLayout", mapItemId="Map 1"
)
# show result
QgsProject.instance().addMapLayer(clipedRaster)

# emboss raster 
embossed = rasterEmboss(
    clipedRaster, unpivotedMapLayer, unpivotedPageLayer, embossPage=-1000, embossZero=-300, zero=0
)
# show result
QgsProject.instance().addMapLayer(embossed, True)

# convert to uint16 for Blender
uint = rastToUNIT16(embossed)
QgsProject.instance().addMapLayer(uint, True)
"""
