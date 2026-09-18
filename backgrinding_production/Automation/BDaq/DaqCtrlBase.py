#!/usr/bin/python
# -*- coding:utf-8 -*-

from Automation.BDaq import *
from Automation.BDaq.BDaqApi import TDaqCtrlBase, TArray, BioFailed
from Automation.BDaq.DeviceCtrl import DeviceCtrl

account_s = u"Adm"
pwd_s = u"123"
time_out = 3000

class DaqCtrlBase(object):
    def __init__(self, scenario, devInfo, hostName):
        self._deviceCtrl = None
        self._obj = self.create(scenario)

        if hostName != None:
            self.login(hostName, account_s, pwd_s, time_out)              
        
        if devInfo is not None:
            self.selectedDevice = devInfo

    def addEventHandler(self, eventId, proc, userParam):
        userParam.Sender = id(self)
        TDaqCtrlBase.addEventHandler(self._obj, eventId, proc, cast(byref(userParam), c_void_p))

    def removeEventHandler(self, eventId, proc, userParam):
        TDaqCtrlBase.removeEventHandler(self._obj, eventId, proc, userParam)

    @property
    def initialized(self):
        return self.state != ControlState.Uninited

    def cleanup(self):
        TDaqCtrlBase.cleanup(self._obj)

    def dispose(self):
        TDaqCtrlBase.dispose(self._obj)

    @property
    def selectedDevice(self):
        devInfo = DeviceInformation()
        TDaqCtrlBase.getSelectedDevice(self._obj, devInfo)
        return devInfo

    @selectedDevice.setter
    def selectedDevice(self, devInfo):
        if not isinstance(devInfo, (DeviceInformation, int, str)):
            raise TypeError('The parameter value is not supported.')
        
        if isinstance(devInfo, str):
            ret = ErrorCode.lookup(TDaqCtrlBase.setSelectedDevice(self._obj, DeviceInformation(Description=devInfo)))
        elif isinstance(devInfo, int):
            ret = ErrorCode.lookup(TDaqCtrlBase.setSelectedDevice(self._obj, DeviceInformation(Description=u'', DeviceNumber=devInfo)))
        else:
            ret = ErrorCode.lookup(TDaqCtrlBase.setSelectedDevice(self._obj, devInfo))
        
        if BioFailed(ret):
            raise ValueError('The device is not opened, and the error code is 0x%X' % (ret.value))

    @property
    def state(self):
        ret = TDaqCtrlBase.getState(self._obj)
        return Utils.toControlState(ret)

    @property
    def device(self):
        if self._deviceCtrl is None:
            self._deviceCtrl = DeviceCtrl(TDaqCtrlBase.getDevice(self._obj))
        return self._deviceCtrl

    @property
    def supportedDevices(self):
        nativeArray = TDaqCtrlBase.getSupportedDevices(self._obj)
        deviceTreeNodeArr = TArray.toDeviceTreeNode(nativeArray)
        return deviceTreeNodeArr

    @property
    def supportedModes(self):
        nativeArray = TDaqCtrlBase.getSupportedModes(self._obj)
        accessModeList = TArray.toAccessMode(nativeArray)
        return accessModeList

    @property
    def module(self):
        return TDaqCtrlBase.getModule(self._obj)    

    def create(self, scenario):
        return TDaqCtrlBase.Create(scenario.value)

    def login(self, edgeName, account, pwd, timeout):
        ret = ErrorCode.lookup(TDaqCtrlBase.Login(self._obj, edgeName, account, pwd, timeout))
        if BioFailed(ret):
            raise ValueError('Login server failed, and the error code is 0x%X' % ret.value)
    
    def logout(self):
        ret = ErrorCode.lookup(TDaqCtrlBase.Logout(self._obj))
        if BioFailed(ret):
            raise ValueError('Logout server failed, and the error code is 0x%X' % (ret.value))

    def __set_loadProfile(self, profile):
        ret = ErrorCode.lookup(TDaqCtrlBase.LoadProfile(self._obj, profile))
        if BioFailed(ret):
            raise ValueError('set loadProfile is failed, the error code is 0x%X' % (ret.value))
    
    loadProfile = property(None, __set_loadProfile)
