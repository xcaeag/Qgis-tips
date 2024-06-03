## Expressions + style for altitude profile

[english version](README.md)

The idea: propose an expression to dynamically draw an altitudinal profile.

![Démo](profil.gif)

## Expressions

One only generates a simple line, the other a polygon, they look similar.

They exploit the interesting `with_variable` function which allows you to factorize and make the code more readable,\
but also :
- `generate_series`: create a series of numbers
- `array_foreach`: transform the values ​​of an array
- `raster_value`: return the value of a pixel in a raster (for altitude)

The expressions are to be placed in a geometry generator style of line type for the first, polygon for the second.

The name of the raster layer (dem) carrying the altitudes must be adapted (theDemLayer here).

```pgsql
with_variable('transect', smooth($geometry, 3), -- the smoothed geom
with_variable('dem', 'theDemLayer', -- dem layer name 
with_variable('fz', 3, -- z exageration 
with_variable('x0', x_min(@transect), -- left
with_variable('y0', y_min(@transect), -- bottom 
with_variable('xs',  -- x array : distance from path origin, at nodes
	array_foreach(
		generate_series(1, num_points(@transect)),
		distance_to_vertex(@transect, @element-1)
	),
with_variable('zs', -- z array : nodes altitudes (exageration)
	array_foreach(
		generate_series(1, num_points(@transect)),
		@fz * raster_value(@dem, 1, point_n(nodes_to_points(@transect), @element))
	),
with_variable('xz', -- x/z array, zip of preceding x and z arrays
	array_foreach(
		generate_series(1, num_points(@transect)),
		array(array_get(@xs, @element-1), array_get(@zs, @element-1))
	),
with_variable('points', -- points array
	array_foreach(@xz, make_point(@element[0], @element[1])), 
	-- > and then, the line geometry
	translate(make_line(@points), @x0, @y0-array_max(@zs)
	)
)))))))))
```

```pgsql
with_variable('transect',  densify_by_distance( smooth($geometry, 3), $length/50), -- the smoothed geom
with_variable('dem', 'theDemLayer', -- dem layer name 
with_variable('base_height', 1000, -- base height 
with_variable('fz', 3, -- z exageration 
with_variable('x0', x_min(@transect), -- left
with_variable('y0', y_min(@transect), -- bottom 
with_variable('xs',  -- x array : distance from path origin, at nodes
	array_foreach(
		generate_series(1, num_points(@transect)),
		distance_to_vertex(@transect, @element-1)
	),
with_variable('zs', -- z array : nodes altitudes (exageration)
	array_foreach(
		generate_series(1, num_points(@transect)),
		@fz * coalesce(raster_value(@dem, 1, point_n(nodes_to_points(@transect), @element)), 0)
	),
with_variable('xz', -- x/z array, zip of preceding x and z arrays
	array_foreach(
		generate_series(1, num_points(@transect)),
		array(array_get(@xs, @element-1), array_get(@zs, @element-1))
	),
with_variable('points', -- points array
	array_foreach(@xz, make_point(@element[0], @element[1])), 
	-- > and then, the polgygon with two additionnals bottom points
	translate(
		make_polygon(make_line(
			array_append(
				array_append(@points, 
					make_point(array_max(@xs), 0) --array_min(@zs)-@base_height)
				), 
				make_point(array_min(@xs), 0) --array_min(@zs)-@base_height)
			)
		)), 
		@x0, @y0-array_max(@zs)
	)
))))))))))
```

## The files

- repo : [https://github.com/xcaeag/Qgis-tips](https://github.com/xcaeag/Qgis-tips)
- style for simple ligne : [resources/style-line.qml](resources/style-line.qml)
- style for polygon : [resources/style-poly.qml](resources/style-poly.qml)
