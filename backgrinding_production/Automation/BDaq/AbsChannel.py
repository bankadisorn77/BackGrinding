#!/usr/bin/python
# -*- coding:utf-8 -*-

from Automation.BDaq.BDaqApi import TAbsChannel, BioFailed
from Automation.BDaq import ErrorCode, CodingType, Baudrate, ErrorRetType, ActiveSignal, OutSignalType
from Automation.BDaq import Utils


class AbsChannel(object):
    def __init__(self, nativeAbsChanObj):
        self._nativeAbsChanObj = nativeAbsChanObj

    @property
    def channel(self):
        return TAbsChannel.getChannel(self._nativeAbsChanObj)

    @property
    def noiseFiltered(self):
        value = TAbsChannel.getNoiseFiltered(self._nativeAbsChanObj)
        return True if value else False

    @noiseFiltered.setter
    def noiseFiltered(self, value):
        if not isinstance(value, bool):
            raise TypeError('a bool is required')
        ret = ErrorCode.lookup(TAbsChannel.setNoiseFiltered(self._nativeAbsChanObj, value))
        if BioFailed(ret):
            raise ValueError('set noiseFiltered is failed, the error code is 0x%X' % (ret.value))

    @property
    def codingType(self):
        value = TAbsChannel.getCodingType(self._nativeAbsChanObj)
        return Utils.toCodingType(value)

    @codingType.setter
    def codingType(self, value):
        if not isinstance(value, CodingType):
            raise TypeError("a CodingType is required")
        ret = ErrorCode.lookup(TAbsChannel.setCodingType(self._nativeAbsChanObj, value))
        if BioFailed(ret):
            raise ValueError('set codingType is failed, the error code is 0x%X' % (ret.value))

    @property
    def baudrate(self):
        value = TAbsChannel.getBaudrate(self._nativeAbsChanObj)
        return Utils.toBaudrate(value)

    @baudrate.setter
    def baudrate(self, value):
        if not isinstance(value, Baudrate):
            raise TypeError("a Baudrate is required")
        ret = ErrorCode.lookup(TAbsChannel.setBaudrate(self._nativeAbsChanObj, value))
        if BioFailed(ret):
            raise ValueError('set Baudrate is failed, the error code is 0x%X' % (ret.value))

    @property
    def errorRetType(self):
        value = TAbsChannel.getErrorRetType(self._nativeAbsChanObj)
        return Utils.toErrorRetType(value)

    @errorRetType.setter
    def errorRetType(self, value):
        if not isinstance(value, ErrorRetType):
            raise TypeError("a ErrorRetType is required")
        ret = ErrorCode.lookup(TAbsChannel.setErrorRetType(self._nativeAbsChanObj, value))
        if BioFailed(ret):
            raise ValueError('set ErrorRetType is failed, the error code is 0x%X' % (ret.value))

    @property
    def errorRetValue(self):
        return TAbsChannel.getErrorRetValue(self._nativeAbsChanObj)

    @errorRetValue.setter
    def errorRetValue(self, value):
        if not isinstance(value, int):
            raise TypeError("a int is required")
        ret = ErrorCode.lookup(TAbsChannel.setErrorRetValue(self._nativeAbsChanObj, value))
        if BioFailed(ret):
            raise ValueError('set ErrorRetValue is failed, the error code is 0x%X' % (ret.value))

    @property
    def latchSigEdge(self):
        value = TAbsChannel.getLatchSigEdge(self._nativeAbsChanObj)
        return Utils.toActiveSignal(value)

    @latchSigEdge.setter
    def latchSigEdge(self, value):
        if not isinstance(value, ActiveSignal):
            raise TypeError("a ActiveSignal is required")
        ret = ErrorCode.lookup(TAbsChannel.setLatchSigEdge(self._nativeAbsChanObj, value))
        if BioFailed(ret):
            raise ValueError('set LatchSigEdge is failed, the error code is 0x%X' % (ret.value))

    @property
    def outSignal(self):
        value = TAbsChannel.getOutSignal(self._nativeAbsChanObj)
        return Utils.toOutSignalType(value)

    @outSignal.setter
    def outSignal(self, value):
        if not isinstance(value, OutSignalType):
            raise TypeError("a OutSignalType is required")
        ret = ErrorCode.lookup(TAbsChannel.setOutSignal(self._nativeAbsChanObj, value))
        if BioFailed(ret):
            raise ValueError('set OutSignal is failed, the error code is 0x%X' % (ret.value))

    @property
    def compareValue0(self):
        return TAbsChannel.getCompareValue0(self._nativeAbsChanObj)

    @compareValue0.setter
    def compareValue0(self, value):
        if not isinstance(value, int):
            raise TypeError("a int is required")
        ret = ErrorCode.lookup(TAbsChannel.setCompareValue0(self._nativeAbsChanObj, value))
        if BioFailed(ret):
            raise ValueError('set CompareValue0 is failed, the error code is 0x%X' % (ret.value))

    @property
    def compareValue1(self):
        return TAbsChannel.getCompareValue1(self._nativeAbsChanObj)

    @compareValue1.setter
    def compareValue1(self, value):
        if not isinstance(value, int):
            raise TypeError("a int is required")
        ret = ErrorCode.lookup(TAbsChannel.setCompareValue1(self._nativeAbsChanObj, value))
        if BioFailed(ret):
            raise ValueError('set CompareValue1 is failed, the error code is 0x%X' % (ret.value))

    @property
    def compare0Enabled(self):
        value = TAbsChannel.getCompare0Enabled(self._nativeAbsChanObj)
        return True if value else False

    @compare0Enabled.setter
    def compare0Enabled(self, value):
        if not isinstance(value, bool):
            raise TypeError("a bool is required")
        ret = ErrorCode.lookup(TAbsChannel.setCompare0Enabled(self._nativeAbsChanObj, value))
        if BioFailed(ret):
            raise ValueError('set Compare0Enabled is failed, the error code is 0x%X' % (ret.value))

    @property
    def compare1Enabled(self):
        value = TAbsChannel.getCompare1Enabled(self._nativeAbsChanObj)
        return True if value else False

    @compare1Enabled.setter
    def compare1Enabled(self, value):
        if not isinstance(value, bool):
            raise TypeError("a bool is required")
        ret = ErrorCode.lookup(TAbsChannel.setCompare1Enabled(self._nativeAbsChanObj, value))
        if BioFailed(ret):
            raise ValueError('set Compare1Enabled is failed, the error code is 0x%X' % (ret.value))
