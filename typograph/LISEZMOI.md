## Des expressions pour étiquetage forcé... et animé

[english version](README.md) - [sommaire](../LISEZMOI.md)

N'arrivant pas à étiqueter (en mode incurvé) un linéaire sur toute sa longueur, et avant que cela soit possible nativement, 
voilà une expression qui va permettre d'étiqueter
quelque-soit le rayon de courbure et répéter le texte à l'infini.

![alt text](resources/orange-blue.png)

Le principe : 
- utiliser le style "ligne de symbole", avec intervalle.
- comme symbole : un symbole de police
- comme caractère : l'expression 'charloop()' qui va égrainer les caractères de votre texte

En paramètres de la fonction : le texte à étiqueter, l'identifiant de la couche (pour des raisons techniques).

Reste à régler la taille, l'espacement...

![alt text](expression.png)

```python
# Exemples :

# un texte statique
charloop( 'ABCDE...', @layer_id)

# ou un champ de votre couche
charloop( "toponyme"||' ', @layer_id)
```

**Comment ça marche ?**

Le moteur d'étiquetage de QGis parcoure la ligne pour placer chaque élément graphique à intervalle régulier et par chance, 
sollicite l'expression à chaque emplacement, 
l'expression se contente alors de distribuer un à un les caractères.

Elle gère les éventuels soucis d'ordre (le moteur de rendu passe d'une entité à l'autre, d'une couche à l'autre et complique les choses).

Un dictionnaire (python) stocke l'indice du caractère couramment affiché, pour chaque entité.

![alt text](resources/zoom.png)

## Les expressions

Dans le dossier de votre profil, sous python/expressions, placez ce script (ou passez par l'interface "éditeur de fonctions" et copiez le contenu dans votre nouveau script) :

- ['resources/expressions/typograph.py'](resources/expressions/typograph.py)

## Version animée

![alt text](resources/demo2.gif)

Les fonctions *animated_charloop()*, *charloop_shift* (pour un décalage fin des caractères), 
combinées avec l'utilisation du 'contrôleur temporel', et c'est le texte qui s'écoule !

- la vitesse de progression dépendra de la longueur du texte : 
  en fin de cycle, le texte retrouve sa position initiale (l'animation est infinie !).
- le sens de progression suit le sens de vos lignes

![alt text](resources/abcd.gif)

**Marche à suivre**

- activer le contrôle temporel pour la couche
- configuration : "redessiner uniquement"
- dans le contrôleur temporel, choisir une période (en jours par exemple) 
  qui correspondra au nombre d'images attendues
- utilisez l'expression (pour le caractère du symbole de police) de la façon suivante : 

```python
animated_charloop('ABCDE', @layerid, @frame_number, @total_frame_count)
```

ou @frame_number est une variable native (l'indice de l'étape courante du contrôleur temporel) et @total_frame_count le nombre d'étapes total (variable native ou à définir dans les propriétés du projet en version < 3.40)

Mais cela produit une animation trop saccadée (la fonction décale simplement le texte d'un caractère).

On affine alors le positionnement par une expression sur le paramètre "décalage le long de la ligne" :

```python
charloop_shift('ABCDE', @typo_gap, @frame_number, @total_frame_count)
```

ou *@typo_gap* correspond à la valeur de l'intervalle choisi pour votre 
ligne de symbole (variable à définir ou à remplacer par une valeur numérique)

## fonctions annexes

- **charloop_random** : comme *charloop*, mais décalage aléatoire (pour éviter les alignements malheureux)
- **animated_charloop_random** : version animée
- **line_direction_we** : détermine si une ligne est plutôt orientée ouest-est ou est-ouest

## pb / difficultés

- Texte à l'envers, linéaire ouest-est, est-ouest ? Le sens de saisie de la ligne est important. Le texte avance dans son sens. Si vous ne la maîtrisez pas à la source, vous pouvez la changer à l'aide d'un style 'Générateur de géométrie' qui pourra contenir :

```python
case when line_direction_we()
	then ($geometry)
	else reverse($geometry)
end
```

- bug détecté : l'animation ne fonctionnera pas bien si une seule entité est visible !

## Les fichiers

Le script à placer dans le dossier de votre profil, sous python/expressions

- [resources/expressions/typograph.py](resources/expressions/typograph.py)

Un projet exemple et ses couches :

- [resources/demo.qgs](resources/demo.qgs)
- [resources/layers.gpkg](resources/layers.gpkg)

