# Qgis-tips

[french version](LISEZMOI.md) - [this page on github.io](https://xcaeag.github.io/Qgis-tips/)

[Project macros](#project-macros-for-specific-toolbar)\
[Bezier curves style](#function-expressions-styles-to-construct-bezier-curves)\
[Altitude profile style](#expressions--style-for-altitude-profile)\
[Tracking shot script](#script-for-a-tracking-shot)\
[Prepare DEM for blender](#prepare-a-dem-for-blender-well-aligned-with-a-print-layout)\
[Virtual layers](#virtual-layers-for-planting-trees)\
[A dock for adjusting variables](#a-dock-for-adjusting-variables)\
[Typograph - labelling](#typograph)

## Project Macros for specific toolbar

To avoid having to write a plugin (a bit complex), and to offer a toolbar specific to a project, we use "macros".  
Some details here : [Macros](macros/README.md)

![macros demo](macros/macros.gif)

## Function, expressions, styles to construct Bezier curves

The idea: propose an expression to draw a Bezier curve dynamically from control points carried by a 'linestring'.

Details here: [Bezier](bezier/README.md)

![bezier demo](bezier/bezier2.gif)

## Expressions + style for altitude profile

The idea: propose an expression to dynamically draw an altitudinal profile.

Details here : [Profil](profil/README.md)

![Démo](profil/profil.gif)

## Script for a tracking shot

Using the temporal controller, the idea is to follow a 'camera' path defined by a linestring geometry.

Details here: [Travelling](travelling/README.md)

![alt text](travelling/plantorel.gif)

## Prepare a DEM for Blender, well aligned with a print layout

Or how to cut, rotate a raster according to the extent of a print layout, by extrapolating the extent of the map to the entire page, taking into account rotations.

![alt text](layout/resources/transformation.png)

here : [layout](layout/README.md)

## Virtual layers... for planting trees

Virtual layer - recursion - or how to replace the geometry generator with a piece of SQL code.

![alt text](forest/resources/forest.gif)

a little more here : [forest](forest/README.md)

## A dock for adjusting variables

![alt text](varWidget/resources/demo-480.gif)

Explanations : [Var Widget](varWidget/README.md)

## Typograph

Enforce labelling, animate it !

![alt text](typograph/resources/demo2.gif)

Explanations : [Typograph](typograph/README.md)
