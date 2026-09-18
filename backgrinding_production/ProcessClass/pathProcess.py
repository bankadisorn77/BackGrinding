import os
from datetime import date,datetime
import enum

def getdatetime1():
    today = date.today()
    return today.strftime("%b-%d-%Y")

def getdatetime():
    now = datetime.today()
    return now.strftime("%Y-%m-%d-%H-%M-%S-%f")

class StatusLevel(enum.Enum):
    INFO = 1
    WARNING = 2
    ERROR = 3

class PathProcess:
    mainPath = r'D:\BG\backgrinding_production'
    configPath = r'{}\config'.format(mainPath)
    savePath = r'{}\ImageSave'.format(mainPath)
    resultPath = r'{}\resultPath'.format(mainPath)
    logPath = r'{}\log'.format(mainPath)
    logfile = r'{}\backgrind_{}.log'.format(logPath,getdatetime1())
    
    def createdir(self):
        if not os.path.exists(PathProcess.mainPath):
            os.makedirs(PathProcess.mainPath)
        if not os.path.exists(PathProcess.savePath):
            os.makedirs(PathProcess.savePath)
        if not os.path.exists(PathProcess.resultPath):
            os.makedirs(PathProcess.resultPath)
        if not os.path.exists(PathProcess.logPath):
            os.makedirs(PathProcess.logPath)
        if not os.path.exists(PathProcess.configPath):
            os.makedirs(PathProcess.configPath)

if __name__=='__main__':
    print(PathProcess.logfile)

    