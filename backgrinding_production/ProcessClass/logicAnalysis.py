import cv2 as cv
from ProcessClass.getChecklistData import ChecklistData
from ProcessClass.pathProcess import PathProcess

class Analysis:
    def __init__(self):
        self.checklist = ChecklistData(use_server=False, csv_path=PathProcess.configPath)
        self.pos = []

    def calculateIntersection(self,a0, a1, b0, b1):
        if a0 >= b0 and a1 <= b1:  # Contained
            intersection = a1 - a0
        elif a0 < b0 and a1 > b1:  # Contains
            intersection = b1 - b0
        elif a0 < b0 and a1 > b0:  # Intersects right
            intersection = a1 - b0
        elif a1 > b1 and a0 < b1:  # Intersects left
            intersection = b1 - a0
        else:
            intersection = 0
        return intersection
    
    def findIntersectArea(self,res):
        try:
            p0,p1= res
            x0,y0 = p0
            x1,y1 = p1
            top = [485, 7, 2095,865]
            left = [1,280,1240,1944]
            right = [1375,280,2590,1944]

            aoi = [top,left,right]
            
            position = ""
            for i in range(len(aoi)):
                X0, Y0, X1, Y1 = aoi[i]
                AREA = float((x1 - x0) * (y1 - y0))
                if AREA <= 0:
                    continue

                width = self.calculateIntersection(x0, x1, X0, X1)
                height = self.calculateIntersection(y0, y1, Y0, Y1)

                if width is None or height is None:
                    continue

                area = width * height
                percent = area / AREA
                if (percent >= 0.65):
                    if i == 0 :
                        position = "top"
                    elif i == 1:
                        position = "left"
                    elif i == 2:
                        position = "right"
                    else:
                        print('not in area')
                    self.pos.append(position)
            return self.pos
        except Exception:
            return []


    def findOverlap(self,x0, y0, x1, y1):
        X0, Y0, X1, Y1, = [485, 7, 2095,865]
        # AREA = float((X1 - X0) * (Y1 - Y0))
        AREA = float((X1 - X0) * (Y1 - Y0))
        print(AREA)
        width = self.calculateIntersection(x0, x1, X0, X1)
        height = self.calculateIntersection(y0, y1, Y0, Y1)
        area = width * height
        print(area)
        print(width,height)
        percent = area / AREA
        print(f' {percent} % ')
        if (percent >= 0.65):
            print('IsOverlap')
            return True
        else:
            return False

    def rearrangeList(self,position,label):
        try:
            order = [(position.index('top')),(position.index('left')),(position.index('right'))]
            position = [position[i] for i in order]
            label = [label[i] for i in order]
            label = [((label[0]).split(' ',1)[0]),((label[1]).split(' ',1)[0]),((label[2]).split(' ',1)[0])]
            # print(position,label)
            return label
        except Exception:
            return []
    
    def logicCheck(self,labelcheck):
        print(labelcheck)
        detectclass = ['black_4', 'black_5', 'black_6', 'black_8', 'handle_big', 'handle_small', 'whitebox']
        for i in labelcheck:
            idx = detectclass.index(i)
            print(idx)
    
    def checklistData(self,handle):
        try:
            data = []
            for check in range(3):
                res = self.checklist.getChecklistData(handle)
            # if res is not None:
            try: 
                checklist = (res[f"{handle}"])
            except:
                checklist = None
            # print(checklist)
            if checklist is not None:
                for i,j in enumerate(checklist):
                    data.append([handle,j["LEFT_CASSETE"],j["RIGHT_CASSETE"]])
                return data
            else:
                return None
        except:
            return None


    def logicAnalysis(self,res):
        try:
            self.pos = []
            # res = res
            lenres = len(res)
            if(lenres < 3) and (lenres > 0):
                return False,res
            elif (lenres == 3):
                for i , j in enumerate(res):
                    res_1 = []
                    label = []    
                    # print(i," : ",j)
                    for k in range(lenres-1):
                        res_1.append(j[k])
                    for l in res:
                        label.append(l[lenres-1])

                    position = self.findIntersectArea(res_1)
                relabelpos = self.rearrangeList(position,label)
                print(relabelpos)
                handle = relabelpos[0]
                data = self.checklistData(handle)
                if data is not None:
                # print(data)
                    for checklist in data:
                        # print(checklist)
                        if relabelpos == checklist:
                            print(f'Setup is Correct {checklist}')
                            return True,checklist
                        elif 'nobox' in relabelpos:
                            print('nobox in list')
                            return True,checklist
                else:
                    return False,[]
            else:
                return False,[]
            return False,[]
        except Exception:
            return False, []


def DrawRectangle(frame3, R1, C1, R2, C2):
    start_point = (C1, R1)
    end_point = (C2, R2)
    color = (0, 255, 0)
    thickness = 3
    return cv.rectangle(cv.cvtColor(frame3, cv.COLOR_GRAY2BGR), start_point, end_point, color, thickness)

def drawrect(path,start1,end1,start2,end2):
    img = cv.imread(path)
    color1 = (225,0,0)
    color2 = (0,225,0)
    thickness = 2
    img = cv.rectangle(img, start1, end1, color1, thickness)
    img = cv.rectangle(img,start2,end2,color2,thickness)

    img = cv.resize(img,(0,0),fx=0.5, fy=0.5) 

