import socket
import time
import uuid
class GetIPAddress:
    def __init__(self):
        pass

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            e = int('dsfk')
            return ip        
        except Exception:
            try:
                hostname = socket.gethostname()
                return socket.gethostbyname(hostname)
            except Exception:
                return "127.0.0.1"

    def get_local_mac(self):
         mac_num = uuid.getnode()
         mac_hex = f'{mac_num:012X}'
         mac_formatted = ':'.join(
              mac_hex[i : i + 2] for i in range(0,12,2)
         )
         return mac_formatted

    def loopCheck(self):
        ip = self.get_local_ip()
        mac = mac = self.get_local_mac()
        while ip == "127.0.0.1" :
            print('Network is not connect! Try to connect ....')
            time.sleep(5.0)
            ip = self.get_local_ip()
            mac = self.get_local_mac()
        return ip,mac

    

if __name__ == '__main__':
    a = GetIPAddress()
    ip = a.get_local_ip()
    mac = mac = a.get_local_mac()
    while ip == "127.0.0.1" :
        print('Network is not connect! Try to connect ....')
        time.sleep(5.0)
        ip = a.get_local_ip()
        mac = a.get_local_mac()
    print(f"Network connected IP :{ip} amd MAC :{mac}")