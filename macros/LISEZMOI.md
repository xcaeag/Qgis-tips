## Les macros de projet pour une barre d'outil dédiée au projet

[english version](README.md) - [sommaire](../LISEZMOI.md)

L'idée : pour ne pas se lancer dans l'écriture (un peu lourde) d'un plugin, et proposer une barre d'outils propre à un projet, on utilise les "macros".

Comme exemple, une mini barre d'outils qui propose un mode "copie d'attributs", d'un simple glissé de la souris entre deux polygones dans la couche selectionnée + possibilité de retour en arrière. Seuls les attributs cochés comme modifiables (voir l'onglet 'formulaire' des propriétés de la couche) sont copiés.

En plaçant le code "MyTool.py" à coté du projet (l'icône svg aussi), en activant les macros du projet avec le code qui suit, la barre d'outils apparaîtra comme par magie à l'ouverture du projet.

Je vous laisse explorer "MyTool.py" et le modifier selon vos besoins.

## Macros

cf. Propriétés du projet. 

```python
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
```

![Démo](./macros.gif)