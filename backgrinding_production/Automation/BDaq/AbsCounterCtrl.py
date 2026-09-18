#!/usr/bin/python
# -*- coding:utf-8 -*-

from ctypes import c_int32

from Automation.BDaq.CntrCtrlBase import CntrCtrlBase
from Automation.BDaq import Scenario, ErrorCode
from Automation.BDaq.AbsChannel import AbsChannel
from Automation.BDaq.BDaqApi import TArray, TAbsCounterCtrl


class AbsCounterCtrl(CntrCtrlBase):
    def __init__(self, devInfo = None, hostName = None):
        super(AbsCounterCtrl, self).__init__(Scenario.SceAbsCounter, devInfo, hostName)
        self._abs_channls = []
        self._abs_channls.append(AbsChannel(None))
        self._abs_channls = []

    @property
    def channels(self):
        if not self._abs_channls:
            count = self.features.channelCountMax
            nativeArr = TAbsCounterCtrl.getChannels(self._obj)
            for i in range(count):
                absChannObj = AbsChannel(TArray.getItem(nativeArr, i))
                self._abs_channls.append(absChannObj)
        return self._abs_channls

    def read(self, count = 1):
        dataArr = (c_int32 * count)()
        data = []
        ret = ErrorCode.lookup(TAbsCounterCtrl.Read(self._obj, count, dataArr))

        for i in range(count):
            data.append(dataArr[i])
        return ret, data
