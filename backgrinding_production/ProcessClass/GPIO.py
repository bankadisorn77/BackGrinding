import logging
from Automation.BDaq import ErrorCode
from Automation.BDaq.InstantDiCtrl import InstantDiCtrl
from Automation.BDaq.InstantDoCtrl import InstantDoCtrl

class GPIO:
    def __init__(self, device='USB-4761,BID#0'):
        self.device = device
        self.di_ctrl = None
        self.do_ctrl = None
        self.is_connected = False
        self.connect()

    def connect(self) -> bool:
        try:
            self.closeIO()
            
            self.di_ctrl = InstantDiCtrl(self.device)
            self.do_ctrl = InstantDoCtrl(self.device)
            
            err, _ = self.di_ctrl.readBit(0, 0)
            if err == ErrorCode.Success:
                self.is_connected = True
                print(f"[GPIO] Connected successfully to {self.device}")
                return True
            else:
                self.is_connected = False
                return False
        except Exception as e:
            self.is_connected = False
            return False

    def ping(self) -> bool:
        if not self.is_connected or not self.di_ctrl:
            return self.connect()
        
        try:
            err, _ = self.di_ctrl.readBit(0, 0)
            if err != ErrorCode.Success:
                self.is_connected = False
                return False
            self.is_connected = True
            return True
        except Exception:
            self.is_connected = False
            return False

    def outputWrite(self, ch: int, on: bool = False) -> bool:
        if not self.is_connected or not self.do_ctrl:
            return False
        
        try:
            bit_val = 1 if on else 0
            err = self.do_ctrl.writeBit(0, ch, bit_val)
            if err != ErrorCode.Success:
                print(f"[GPIO] WriteBit Failed (Code: {err}). Hardware disconnected.")
                self.is_connected = False
                return False
            return True
        except Exception as e:
            print(f"[GPIO] Exception on writeBit: {e}")
            self.is_connected = False
            return False

    def readInput(self, ch: int):
        """อ่านสัญญาณ Input (DI) พร้อมเช็คสายหลุด"""
        if not self.is_connected or not self.di_ctrl:
            return None
        
        try:
            err, input_state = self.di_ctrl.readBit(0, ch)
            if err != ErrorCode.Success:
                print(f"[GPIO] ReadBit Failed (Code: {err}). Hardware disconnected.")
                self.is_connected = False
                return None
            return input_state
        except Exception as e:
            print(f"[GPIO] Exception on readBit: {e}")
            self.is_connected = False
            return None

    def closeIO(self):
        """ปิดและคืนทรัพยากรพอร์ต IO"""
        self.is_connected = False
        try:
            if self.do_ctrl:
                self.do_ctrl.dispose()
        except Exception:
            pass
        try:
            if self.di_ctrl:
                self.di_ctrl.dispose()
        except Exception:
            pass
        self.do_ctrl = None
        self.di_ctrl = None