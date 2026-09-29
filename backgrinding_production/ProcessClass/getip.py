import socket
import netifaces as ni
import fcntl
import struct
import time
import uuid

class GetIPAddress:
    def __init__(self):
        pass

    def get_local_ip(self):
        ip = self.get_ip_address('enp0s31f6')
        if ip:
            return ip
        ip = self.get_ip_address('enp1s0')
        if ip:
            return ip
        return '127.0.0.1'

    def get_ip_address(self, interface):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ip = fcntl.ioctl(
                sock.fileno(),
                0x8915, 
                struct.pack('256s', interface[:15].encode('utf-8'))
            )[20:24]
            return socket.inet_ntoa(ip)
        except Exception:
            return None

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