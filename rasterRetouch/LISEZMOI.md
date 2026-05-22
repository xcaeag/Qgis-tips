## Une barre d'outils pour retouche de modèle numérique de terrain (raster), au pinceau

[english version](README.md) - [sommaire](../LISEZMOI.md)

Ceci n'est pas un plugin !

![Démo](retouch.gif)

## Usage

Copier script.py + svg dans un dossier de votre choix. 

Ouvrir, lancer dans la console Python de QGis avec une couche Raster sélectionnée, une barre d'outil apparaît et vous permet de dessiner sur le raster (élever, creuser, flouter, copier etc...). 

Plutôt adapté au MNT, il travaille en modifiant la valeur des pixels d'un raster mono-bande.

Ne fonctionne que sur les couches locales, TIFF, ASC.

Attention : la source est altérée : pensez à travailler sur une copie de vos originaux.

Le pinceau : circulaire aux bords floutés. Sa taille, sa force, son floutage sont ajustables à l'aide des combinaisons Ctrl+molette, Shift+molette, Ctrl+Shift+Molette

![alt text](resources/rasterRetouchMode1.svg) : Élève le relief

![alt text](resources/rasterRetouchMode2.svg) : Creuse le relief

![alt text](resources/rasterRetouchMode3.svg) : Floute le relief

![alt text](resources/rasterRetouchMode4.svg) : Copie depuis un deuxième raster

![alt text](resources/rasterRetouchMode5.svg) : Copie au sein du même raster

![alt text](resources/rasterRetouchMode6.svg) : Aplatit le relief

![alt text](resources/rasterRetouchMode8.svg) : Accentue  le relief

![alt text](resources/rasterRetouchMode7.svg) : Traîne

![alt text](resources/close.svg) : Ferme la barre d'outils

## Les fichiers

- repo : [https://github.com/xcaeag/Qgis-tips](https://github.com/xcaeag/Qgis-tips)
- le script : [resources/rasterRetouchScript.py](resources/rasterRetouchScript.py)
