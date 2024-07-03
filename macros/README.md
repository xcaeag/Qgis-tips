## Project Macros for specific toolbar

[french version](LISEZMOI.md) - [top](../README.md)

The idea: to avoid having to write a plugin (a bit complex), and to offer a toolbar specific to a project, we use "macros".

As an example, a mini toolbar which offers a "copy attributes" mode, with a simple drag of the mouse between two polygons in seleted layer + possibility of undo. Only attributes checked as modifiable (see the 'form' tab of the layer properties) are copied.

By placing the "MyTool.py" code next to the project (the svg icon too), by activating the project's macros with the following code (see below), the toolbar will appear as if by magic when opening the project.

I'll let you explore "MyTool.py" and modify it according to your needs.

## Macros

cf. Project properties

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