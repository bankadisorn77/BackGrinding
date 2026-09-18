#!/usr/bin/python
# -*- coding:utf-8 -*-

from ctypes import c_int
from Automation.BDaq.DaqCtrlBase import DaqCtrlBase
from Automation.BDaq.BDaqApi import TAiCtrlBase, TArray, ErrorCode
from Automation.BDaq.AiFeatures import AiFeatures
from Automation.BDaq.AiChannel import AiChannel


class AiCtrlBase(DaqCtrlBase):
    def __init__(self, scenario, devInfo, hostName):
        super(AiCtrlBase, self).__init__(scenario, devInfo, hostName)
        self._ai_features = None
        self._ai_channels = []
        self._ai_channels.append(AiChannel(None))
        self._ai_channels = []

    @property
    def features(self):
        if self._ai_features is None:
            self._ai_features = AiFeatures(TAiCtrlBase.getFeatures(self._obj))
        return self._ai_features

    @property
    def channels(self):
        if not self._ai_channels:
            count = self.features.channelCountMax
            nativeArray = TAiCtrlBase.getChannels(self._obj)
            for i in range(count):
                aiChannObj = AiChannel(TArray.getItem(nativeArray, i))
                self._ai_channels.append(aiChannObj)
        return self._ai_channels

    @property
    def channelCount(self):
        return TAiCtrlBase.getChannelCount(self._obj)

    def getChannelState(self, count):
        stateArr = (c_int * count)()
        state = []
        ret = ErrorCode.lookup(TAiCtrlBase.getChannelState(self._obj, count, stateArr))
        for i in range(count):
            state.append(stateArr[i])
        return ret, state
