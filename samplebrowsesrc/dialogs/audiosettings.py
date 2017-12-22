import os
from samplebrowsesrc import utils
from samplebrowsesrc.constants import *
from PyQt5 import QtCore, QtGui, QtWidgets, QtMultimedia, uic
from collections import namedtuple

audioDevice = namedtuple('audioDevice', 'device name sampleRates sampleSizes channels')

class AudioDeviceProber(QtCore.QObject):
    deviceList = QtCore.pyqtSignal(object)
    def probe(self):
        deviceList = []
        for device in QtMultimedia.QAudioDeviceInfo.availableDevices(QtMultimedia.QAudio.AudioOutput):
            deviceInfo = audioDevice(device, device.deviceName(), device.supportedSampleRates(), device.supportedSampleSizes(), device.supportedChannelCounts())
            deviceList.append(deviceInfo)
        self.deviceList.emit(deviceList)


class AudioDevicesListView(QtWidgets.QListView):
    deviceSelected = QtCore.pyqtSignal(object)
    def currentChanged(self, current, previous):
        self.deviceSelected.emit(current)


class AudioSettingsDialog(QtWidgets.QDialog):
    def __init__(self, main, parent=None):
        if parent is None:
            parent = main
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi('{}/audiosettings.ui'.format(os.path.dirname(utils.__file__)), self)
        self.main = main
        self.settings = QtCore.QSettings()

        self.popup = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Information, 
            'Probing audio devices', 
            'Probing audio devices, please wait...', 
            parent=self)
        self.popup.setStandardButtons(self.popup.NoButton)
        self.deviceModel = QtGui.QStandardItemModel()
        self.deviceList.setModel(self.deviceModel)
        self.sampleRatesModel = QtGui.QStandardItemModel()
        self.sampleRatesList.setModel(self.sampleRatesModel)
        self.deviceList.deviceSelected.connect(self.deviceSelected)
        self.channelsModel = QtGui.QStandardItemModel()
        self.channelsList.setModel(self.channelsModel)

        for chk in (self.depth8Chk, self.depth16Chk, self.depth32Chk):
            chk.mousePressEvent = lambda *args: None
            chk.keyPressEvent = lambda *args: None

    def deviceSelected(self, index):
        self.sampleRatesModel.clear()
        device = index.data(DeviceRole)
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(True if index.data(ValidRole) != False else False)
        self.deviceInfoBox.setTitle(device.deviceName())
        preferredFormat = index.data(FormatRole)
        if not preferredFormat:
            preferredFormat = device.preferredFormat()
        for sampleRate in sorted(index.data(SampleRateRole), reverse=True):
            item = QtGui.QStandardItem('{:.1f} kHz'.format(sampleRate/1000.))
            if sampleRate == preferredFormat.sampleRate():
                utils.setBold(item)
            self.sampleRatesModel.appendRow(item)
        sampleSizes = index.data(SampleSizeRole)
        for sampleSize in (8, 16, 32):
            checkBox = getattr(self, 'depth{}Chk'.format(sampleSize))
            checkBox.setChecked(True if sampleSize in sampleSizes else False)
            utils.setBold(checkBox, True if sampleSize == preferredFormat.sampleSize() else False)
        self.channelsModel.clear()
        for channelCount in sorted(index.data(ChannelsRole)):
            item = QtGui.QStandardItem('{}: {}'.format(channelCount, channelsLabels.get(channelCount, '(unknown configuration)')))
            if channelCount == preferredFormat.channelCount():
                utils.setBold(item)
            self.channelsModel.appendRow(item)

    def probed(self, deviceList):
        self.popup.hide()
        default = QtMultimedia.QAudioDeviceInfo.defaultOutputDevice()
        current = None
        for device, name, sampleRates, sampleSizes, channels in deviceList:
            if device == default:
                name = '{} (default)'.format(name)
            deviceItem = QtGui.QStandardItem(name)
            if device == self.main.player.audioDevice:
                current = deviceItem
                utils.setBold(deviceItem)
            deviceItem.setData(device, DeviceRole)
            deviceItem.setData(sampleRates, SampleRateRole)
            deviceItem.setData(sampleSizes, SampleSizeRole)
            deviceItem.setData(channels, ChannelsRole)
            if not (sampleRates and sampleSizes and channels):
                deviceItem.setData(False, ValidRole)
            self.deviceModel.appendRow(deviceItem)
        currentDeviceName = self.settings.value('AudioDevice')
        if current:
            if currentDeviceName:
                match = self.deviceModel.match(self.deviceModel.index(0, 0), QtCore.Qt.DisplayRole, currentDeviceName, flags=QtCore.Qt.MatchExactly)
                if not match:
                    self.deviceList.setCurrentIndex(current.index())
                else:
                    self.deviceList.setCurrentIndex(match[0])
            else:
                self.deviceList.setCurrentIndex(current.index())

    def exec_(self):
        try:
            getattr(self, '{}Radio'.format(self.settings.value('SampleRateConversion', 'sinc_fastest'))).setChecked(True)
        except:
            self.sinc_fastestRadio.setChecked(True)

        prober = AudioDeviceProber()
        proberThread = QtCore.QThread()
        prober.moveToThread(proberThread)
        proberThread.started.connect(prober.probe)
        prober.deviceList.connect(self.probed)
        prober.deviceList.connect(lambda _: [proberThread.quit(), prober.deleteLater(), proberThread.deleteLater()])
        self.deviceModel.clear()
        self.show()
        self.popup.show()
        self.popup.setModal(True)
        proberThread.start()
        res = QtWidgets.QDialog.exec_(self)
        if not res:
            return res
        device = self.deviceList.currentIndex().data(DeviceRole)
        self.settings.setValue('AudioDevice', device.deviceName())
        conversion = self.sampleRateGroup.checkedButton().objectName()[:-len('Radio')]
        if conversion == 'sinc_fastest':
            self.settings.remove('SampleRateConversion')
        else:
            self.settings.setValue('SampleRateConversion', conversion)
        return device, conversion


