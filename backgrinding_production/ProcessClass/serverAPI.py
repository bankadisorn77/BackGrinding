import httpx
class API_CALL():
    def __init__(self,config=None):
        self.config = config
        self.server_url =  self.config.server_url
        self.port = 8080
        self.api_key =  self.config.api_key
        self.url=f'http://{self.server_url}:{self.port}'


    async def register(self):
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f'{self.url}/register_device'
            payload = {
                'name': self.config.device_id,
                'ip_address':self.config.ip,
                'mac_address':self.config.mac,
                'io_channel':{
                    'input_channel':self.config.inputChannel,
                    'output_alarm_channel':self.config.outputAlarm,
                    'output_relay_channel':self.config.outputContor,
                    'output_light_channel':self.config.outputStateMachine,
                },
                'model_path':self.config.model_path,
                'save_image_path':self.config.save_image_path,
                'mqtt_broker':self.config.MQTTServer
            }
            try:
                res = await client.post(url=url,json=payload)
                if res.status_code ==200:
                    data = res.json()
                    self.config.setnewConfig(data)
                    return True
                else:
                    return False
            except httpx.CloseError:
                print('Client Error Cannot connect to server')
                return False
            except httpx.TimeoutException:
                 print('Client Error Cannot Timeout')
                 return False
            except Exception as e:
                print(f'ERROR {e}')
                return False

    async def newAlarm(self,imagebase64 :str = None , detection_info :str = None):
        self.api_key =  self.config.api_key
        async with httpx.AsyncClient(timeout=10) as client:
            url = f'{self.url}/image_log'
            header ={"X-API-Key":self.api_key}
            payload = {
                'image':imagebase64,
                'detected_objects':str(detection_info)
            }
            try:
                res = await client.post(url=url,headers=header,json=payload)
                if res.status_code == 200:
                    print('send log successfully')
                else:
                    print(res.status_code, res.json())
            except httpx.CloseError:
                print('Client Error Cannot connect to server')
            # >>> FIXED: เหมือนจุดเดียวกับใน register() — httpx.Timeout ไม่ใช่
            # exception class ใช้ httpx.TimeoutException แทน (ดูคอมเมนต์เต็มด้านบน)
            except httpx.TimeoutException:
                print('Client Error Cannot Timeout')
            except Exception as e:
                print(f'ERROR {e}')
                
