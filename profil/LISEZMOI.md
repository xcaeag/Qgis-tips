## Expressions + style pour profil d'altitude

[english version](README.md)

L'idée : proposer une expression pour dessiner un profil altitudinal dynamiquement.

![Démo](profil.gif)

## Les expressions

L'une ne génère qu'une simple ligne, l'autre un polygone, elles se ressemblent.

Elles exploitent l'interessante fonction `with_variable` qui permet de factoriser et rendre le code plus lisible,\
mais aussi : 
- `generate_series` : créer une suite de nombre 
- `array_foreach` : transformer les valeurs d'un tableau
- `raster_value` : retourner la valeur d'un pixel dans un raster (pou l'altitude)

Les expressions sont à placer dans un style générateur de géométrie de type ligne pour la première, polygone pour la seconde.

Le nom de la couche raster (dem) portant les altitudes doit être adapté (theDemLayer ici).

```pgsql
-- Expression à placer dans un style générateur de géométrie de type LINESTRING
with_variable('transect', smooth($geometry, 3), -- la géométrie liséee
with_variable('dem', 'theDemLayer', -- nom de la couche raster (mnt) à adapter
with_variable('fz', 3, -- exagération du relief
with_variable('x0', x_min(@transect), -- gauche
with_variable('y0', y_min(@transect), -- bas 
with_variable('xs',  -- tableau d'abscisses : distance depuis l'origine, en chaque point
	array_foreach(
		generate_series(1, num_points(@transect)),
		distance_to_vertex(@transect, @element-1)
	),
with_variable('zs', -- tableau d'altitudes (exagérées) ou non
	array_foreach(
		generate_series(1, num_points(@transect)),
		@fz * raster_value(@dem, 1, point_n(nodes_to_points(@transect), @element))
	),
with_variable('xz', -- tableau de couples x/z
	array_foreach(
		generate_series(1, num_points(@transect)),
		array(array_get(@xs, @element-1), array_get(@zs, @element-1))
	),
with_variable('points', -- tableau de points
	array_foreach(@xz, make_point(@element[0], @element[1])), 
	-- > et la ligne 
	translate(make_line(@points), @x0, @y0-array_max(@zs)
	)
)))))))))
```

```pgsql
-- Expression à placer dans un style générateur de géométrie de type POLYGON
with_variable('transect',  densify_by_distance( smooth($geometry, 3), $length/50), 
with_variable('dem', 'theDemLayer', 
with_variable('base_height', 1000,
with_variable('fz', 3, 
with_variable('x0', x_min(@transect), 
with_variable('y0', y_min(@transect), 
with_variable('xs', 
	array_foreach(
		generate_series(1, num_points(@transect)),
		distance_to_vertex(@transect, @element-1)
	),
with_variable('zs', 
	array_foreach(
		generate_series(1, num_points(@transect)),
		@fz * coalesce(raster_value(@dem, 1, point_n(nodes_to_points(@transect), @element)), 0)
	),
with_variable('xz',
	array_foreach(
		generate_series(1, num_points(@transect)),
		array(array_get(@xs, @element-1), array_get(@zs, @element-1))
	),
with_variable('points', 
	array_foreach(@xz, make_point(@element[0], @element[1])), 
	-- > et le polgygone avec les deux point de la base en plus
	translate(
		make_polygon(make_line(
			array_append(
				array_append(@points, 
					make_point(array_max(@xs), 0) 
				), 
				make_point(array_min(@xs), 0) 
			)
		)), 
		@x0, @y0-array_max(@zs)
	)
))))))))))
```

## Les fichiers

- repo : [https://github.com/xcaeag/Qgis-tips](https://github.com/xcaeag/Qgis-tips)
- style pour une ligne simple : [resources/style-line.qml](resources/style-line.qml)
- style pour un polygone : [resources/style-poly.qml](resources/style-poly.qml)
