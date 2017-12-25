import samplerate
from PyQt5 import QtCore, QtMultimedia


class WaveIODevice(QtCore.QIODevice):
    def __init__(self, parent):
        QtCore.QIODevice.__init__(self, parent)
        self.waveData = None
        self.byteArray = QtCore.QByteArray()
        self.bytePos = 0

    def stop(self):
        self.bytePos = 0
        self.close()

    def setWaveData(self, waveData, info):
        if info.samplerate != self.parent().sampleRate:
            #ratio is output/input
            waveData = samplerate.resample(waveData, self.parent().sampleRate / info.samplerate, self.parent().sampleRateConversion)

        if info.channels == 1:
            waveData = waveData.repeat(2, axis=1)/2
        elif info.channels == 2:
            pass
        elif info.channels == 3:
            front = waveData[:, [0, 1]]/1.5
            center = waveData[:, [2]].repeat(2, axis=1)/2
            waveData = front + center
        elif info.channels == 4:
            front = waveData[:, [0, 1]]/2
            rear = waveData[:, [2, 3]]/2
            waveData = front + rear
        elif info.channels == 5:
            front = waveData[:, [0, 1]]/2.5
            rear = waveData[:, [2, 3]]/2.5
            center = waveData[:, [4]].repeat(2, axis=1)/2
            waveData = front + rear + center
        elif info.channels == 6:
            front = waveData[:, [0, 1]]/3
            rear = waveData[:, [2, 3]]/3
            center = waveData[:, [4]].repeat(2, axis=1)/2
            sub = waveData[:, [5]].repeate(2, axis=1)/2
            waveData = front + rear + center + sub
        if self.parent().sampleSize == 16:
            waveData = (waveData * 32767).astype('int16')
        self.waveData = waveData
        self.byteArray.clear()
        self.byteArray.append(waveData.tostring())
        self.open(QtCore.QIODevice.ReadOnly)
#        self.byteArray.seek(0)

    def seekPos(self, pos):
        self.bytePos = int(self.byteArray.size() * pos) // self.parent().sampleSize * self.parent().sampleSize
#        print(pos, self.byteArray.size())

    def readData(self, maxlen):
        if self.bytePos > self.byteArray.size():
            return None

        data = QtCore.QByteArray()
        total = 0

#        print(self.bytePos)
        while maxlen > total and self.bytePos < self.byteArray.size():
            chunk = min(self.byteArray.size() - self.bytePos, maxlen - total)
            data.append(self.byteArray.mid(self.bytePos, chunk))
#            self.bytePos = (self.bytePos + chunk) % self.byteArray.size()
            self.bytePos += chunk
            total += chunk

        return data.data()


class Player(QtCore.QObject):
    stateChanged = QtCore.pyqtSignal(object)
    notify = QtCore.pyqtSignal(float)
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    paused = QtCore.pyqtSignal()

    def __init__(self, main, audioDeviceName=None, sampleRateConversion='sinc_fastest'):
        QtCore.QObject.__init__(self)
        self.main = main
#        self.audioBufferArray = QtCore.QBuffer(self)
        self.waveIODevice = WaveIODevice(self)
        self.output = None
        self.audioDevice = None
        self.setAudioDeviceByName(audioDeviceName)
        self.setAudioDevice()
        self.sampleRateConversion = sampleRateConversion

    def seekPos(self, pos):
        if pos < 0:
            pos = 0
        if pos > 1:
            pos = 1
        self.waveIODevice.seekPos(pos)

    def setSampleRateConversion(self, sampleRateConversion='sinc_fastest'):
        self.sampleRateConversion = sampleRateConversion

    def setAudioDeviceByName(self, audioDeviceName):
        defaultDevice = QtMultimedia.QAudioDeviceInfo.defaultOutputDevice()
        if not audioDeviceName:
            self.audioDevice = defaultDevice
        elif audioDeviceName == defaultDevice:
            self.audioDevice = defaultDevice
        else:
            for sysDevice in QtMultimedia.QAudioDeviceInfo.availableDevices(QtMultimedia.QAudio.AudioOutput):
                if sysDevice.deviceName() == audioDeviceName:
                    break
            else:
                sysDevice = defaultDevice
            self.audioDevice = sysDevice
#        self.audioDeviceName = audioDeviceName if audioDeviceName else QtMultimedia.QaudioDeviceInfo.defaultOutputDevice()

    def setAudioDevice(self, audioDevice=None):
        if audioDevice:
            self.audioDevice = audioDevice
        sampleSize = 32 if 32 in self.audioDevice.supportedSampleSizes() else 16
        sampleRate = 48000 if 48000 in self.audioDevice.supportedSampleRates() else 44100

        format = QtMultimedia.QAudioFormat()
        format.setSampleRate(sampleRate)
        format.setChannelCount(2)
        format.setSampleSize(sampleSize)
        format.setCodec('audio/pcm')
        format.setByteOrder(QtMultimedia.QAudioFormat.LittleEndian)
        format.setSampleType(QtMultimedia.QAudioFormat.Float if sampleSize >= 32 else QtMultimedia.QAudioFormat.SignedInt)

        if not self.audioDevice.isFormatSupported(format):
            format = self.audioDevice.nearestFormat(format)
            #do something else with self.audioDevice.nearestFormat(format)?
        self.sampleSize = format.sampleSize()
        self.sampleRate = format.sampleRate()
        try:
            self.output.notify.disconnect()
            del self.output
        except:
            pass
        self.output = QtMultimedia.QAudioOutput(self.audioDevice, format)
        self.output.setNotifyInterval(25)
        self.output.stateChanged.connect(self.stateChanged)

    def isPlaying(self):
        return self.output.state() == QtMultimedia.QAudio.ActiveState

    def isPaused(self):
        return self.output.state() == QtMultimedia.QAudio.SuspendedState

    def isActive(self):
        return self.output.state() in (QtMultimedia.QAudio.ActiveState, QtMultimedia.QAudio.SuspendedState)

    def stateChanged(self, state):
        if state in (QtMultimedia.QAudio.StoppedState, QtMultimedia.QAudio.IdleState):
            self.stopped.emit()
        elif state == QtMultimedia.QAudio.ActiveState:
            self.started.emit()
        else:
            self.paused.emit()

    def stop(self):
        self.output.stop()
        self.waveIODevice.stop()

    def play(self, waveData, info):
        self.waveIODevice.setWaveData(waveData, info)
#        self.output.start(self.audioBufferArray)
        self.output.start(self.waveIODevice)

    def setVolume(self, volume):
#        try:
#            volume = QtMultimedia.QAudio.convertVolume(volume / 100, QtMultimedia.QAudio.LogarithmicVolumeScale, QtMultimedia.QAudio.LinearVolumeScale)
#        except:
#            if volume >= 100:
#                volume = 1
#            else:
#                volume = -log(1 - volume/100) / 4.60517018599
        self.output.setVolume(volume/100)


