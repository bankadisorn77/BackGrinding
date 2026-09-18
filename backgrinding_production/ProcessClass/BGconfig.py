import os
import json
from sqlalchemy import true
from ProcessClass.pathProcess import PathProcess
from ProcessClass.getip import GetIPAddress


class BackgrindConfig():
    def __init__(self):
        self.network = GetIPAddress()
        self.ip_addres,self.mac_addres = self.network.loopCheck()
        self.device_id = "BG-Dev-01"
        self.ip = "127.0.0.1"
        self.mac = "XX:XX:XX:XX:XX:XX"
        self.inputChannel = 0
        self.outputAlarm = 0
        self.outputContor = 1
        self.outputStateMachine = 0
        self.cameraAOI= {
            "width": 1920,
            "height": 1080
        }
        self.MQTTServer = "localhost"
        self.server_url = "localhost"
        self.model_path = "Yolov12best_bg_v2_openvino_model"
        self.save_image_path = "saved_images_output"
        self.project_id = "backgrinding"
        self.cameras = [
            {"id": "cam_1", "driver": "ueye", "hardware_index": 0, "enabled": True, "pipeline": "backgrinding"},
            {"id": "cam_2", "driver": "ueye", "hardware_index": 1, "enabled": True, "pipeline": "backgrinding"},
        ]
        self.pipelines = {
            "backgrinding": {
                "mode": "shared",
                "steps": [
                    {"id": "capture", "type": "capture"},
                    {"id": "detect", "type": "detect"},
                    {"id": "validate", "type": "validate"},
                    {"id": "decision", "type": "decision"},
                ],
            },
            "stream_only": {
                "mode": "shared",
                "steps": [{"id": "stream", "type": "stream_only"}]
            }
        }
        self.api_key = "api_key"
        self.loadConfig()
        self.setnewConfig({'ip':self.ip_addres,'mac':self.mac_addres})


    def setnewConfig(self,newParam):
        try:
            device_id = newParam.get('device_id',self.device_id)
            ip = newParam.get('ip',self.ip)
            mac = newParam.get('mac',self.mac)
            inputChannel = newParam.get('inputChannel',self.inputChannel)
            outputAlarm = newParam.get('outputAlarm',self.outputAlarm)
            outputContor = newParam.get('outputContor',self.outputContor)
            outputStateMachine = newParam.get('outputStateMachine',self.outputStateMachine)
            cameraAOI = newParam.get('cameraAOI',self.cameraAOI)
            MQTTServer = newParam.get('MQTTServer',self.MQTTServer)
            server_url = newParam.get('server_url',self.server_url)
            model_path = newParam.get('model_path',self.model_path)
            save_image_path = newParam.get('save_image_path',self.save_image_path)
            api_key = newParam.get('api_key',self.api_key)
            project_id = newParam.get('project_id', self.project_id)
            cameras = newParam.get('cameras', self.cameras)
            pipelines = newParam.get('pipelines', self.pipelines)

            self.device_id = device_id
            self.ip = ip 
            self.mac = mac 
            self.inputChannel = inputChannel 
            self.outputAlarm = outputAlarm
            self.outputContor = outputContor
            self.outputStateMachine = outputStateMachine
            self.cameraAOI = cameraAOI
            self.MQTTServer = MQTTServer
            self.server_url = server_url
            self.model_path = model_path
            self.save_image_path = save_image_path
            self.api_key = api_key
            self.project_id = project_id
            self.cameras = cameras
            self.pipelines = pipelines
            self.saveconfig()
        except Exception as e:
            print(f'Config format not correct !!! (ERROR : {e})')
            pass
    
    def getCurrentConfig(self):
        return  {
                    "device_id": self.device_id,
                    "ip": self.ip,
                    "mac": self.mac,
                    "inputChannel" : self.inputChannel,
                    "outputAlarm" : self.outputAlarm,
                    "outputContor" : self.outputContor,
                    "outputStateMachine" : self.outputStateMachine,
                    "cameraAOI" : self.cameraAOI,
                    "MQTTServer": self.MQTTServer,
                    "server_url": self.server_url,
                    "model_path":self.model_path,
                    "save_image_path":self.save_image_path,
                    "api_key":self.api_key,
                    "project_id":self.project_id,
                    "cameras":self.cameras,
                    "pipelines":self.pipelines
     
                }

    def createdir(self):
        config_dir = self.pathConfig()
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

    def pathConfig(self):
        return PathProcess.configPath
    
    def loadConfig(self):
        try:
            config_dir = os.path.join(self.pathConfig(),'config.json')
            self.createdir()
            param = {
                        "device_id": self.device_id,
                        "ip": self.ip,
                        "mac": self.mac,
                        "inputChannel" : self.inputChannel,
                        "outputAlarm" : self.outputAlarm,
                        "outputContor" : self.outputContor,
                        "outputStateMachine" : self.outputStateMachine,
                        "cameraAOI" : self.cameraAOI,
                        "MQTTServer": self.MQTTServer,
                        "server_url": self.server_url,
                        "model_path":self.model_path,
                        "save_image_path":self.save_image_path,
                        "api_key":self.api_key,
                        "project_id":self.project_id,
                        "cameras":self.cameras,
                        "pipelines":self.pipelines                    }
           
            if not os.path.exists(config_dir):
                json_data = json.dumps(param, indent=2)
                f = open(config_dir, 'x')
                f.write(json_data)
                f.close()
            with open(config_dir) as file:
                param = json.load(file)
                self.device_id = str(param['device_id'])
                self.ip = str(param['ip'])
                self.mac = str(param['mac'])
                self.inputChannel = int(param['inputChannel'])
                self.outputAlarm = int(param['outputAlarm'])
                self.outputContor = int(param['outputContor'])
                self.outputStateMachine = int(param['outputStateMachine'])
                self.cameraAOI = (param['cameraAOI'])
                self.MQTTServer = str(param['MQTTServer'])
                self.server_url = str(param['server_url'])
                self.model_path = str(param['model_path'])
                self.save_image_path = str(param['save_image_path'])
                self.api_key = str(param['api_key'])
                self.project_id = str(param.get('project_id', self.project_id))
                self.cameras = param.get('cameras', self.cameras)
                self.pipelines = param.get('pipelines', self.pipelines)
        except:
            self.saveconfig()
        return param

    def saveconfig(self):
        config_dir = os.path.join(self.pathConfig(),'config.json')
        self.createdir()
        param = {
            "device_id": self.device_id,
            "ip": self.ip,
            "mac": self.mac,
            "inputChannel" : self.inputChannel,
            "outputAlarm" : self.outputAlarm,
            "outputContor" : self.outputContor,
            "outputStateMachine" : self.outputStateMachine,
            "cameraAOI" : self.cameraAOI,
            "MQTTServer": self.MQTTServer,
            "server_url": self.server_url,
            "model_path":self.model_path,
            "save_image_path":self.save_image_path,
            "api_key":self.api_key,
            "project_id":self.project_id,
            "cameras":self.cameras,
            "pipelines":self.pipelines
        }
        
        json_data = json.dumps(param, indent=2)
        f = open(config_dir, 'w')
        f.write(json_data)
        f.close()
        self.loadConfig()
        

