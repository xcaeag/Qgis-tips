import time

def theLongProcess(task):
    delay = 5 # s
    steps = 20
    for i in range(steps+1):
        time.sleep(delay/steps)
        task.setProgress(100*i/steps)
        QApplication.processEvents()

class MyTask(QgsTask):
    def __init__(self, desc):
        QgsTask.__init__(self, desc)

    def canCancel(self):
        return True
        
    def run(self):
        try:
            theLongProcess(self)
            return True
        except Exception as e:
            return False

def runThelongProcess():
    def onBegun():
        iface.messageBar().pushMessage("onBegun", level=Qgis.Info)

    def onStatusChanged(s):
        STATUS = {0:"Queued", 1:"OnHold", 2:"Running", 3:"Complete", 4:"Terminated"}
        iface.messageBar().pushMessage("StatusChanged : {} {}".format(s, STATUS[s]), level=Qgis.Info)

    task = MyTask('A long process')
    task.begun.connect(onBegun)
    task.statusChanged.connect(onStatusChanged)
    tm = QgsApplication.taskManager()
    tm.addTask(task)

    return task

task = runThelongProcess()
