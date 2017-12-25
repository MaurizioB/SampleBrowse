import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from samplebrowsesrc.utils import HoverDecorator

class WaveScene(QtWidgets.QGraphicsScene):
    _orange = QtGui.QColor()
    _orange.setNamedColor('orangered')
    waveGrad = QtGui.QLinearGradient(0, -1, 0, 1)
    waveGrad.setSpread(waveGrad.RepeatSpread)
#    waveGrad.setCoordinateMode(waveGrad.ObjectBoundingMode)
    waveGrad.setColorAt(0.0, QtCore.Qt.red)
    waveGrad.setColorAt(.15, _orange)
    waveGrad.setColorAt(.5, QtCore.Qt.darkGreen)
    waveGrad.setColorAt(.85, _orange)
    waveGrad.setColorAt(1, QtCore.Qt.red)
    waveBrush = QtGui.QBrush(waveGrad)
    wavePen = QtGui.QPen(QtCore.Qt.NoPen)
    zeroPen = QtGui.QPen(QtCore.Qt.darkGray, .5)
    zeroPen.setCosmetic(True)
    playheadPen = QtGui.QPen(QtCore.Qt.red, .5)
    playheadPen.setCosmetic(True)
    cursorPlayheadPen = QtGui.QPen(QtCore.Qt.black, .5)
    cursorPlayheadPen.setCosmetic(True)

    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsScene.__init__(self, *args, **kwargs)
        self.waveRect = QtCore.QRectF()
        self.realStep = 0
        self.sampleRate = 0
        self.deltaPos = 0

    def setPlayheadDeltaPos(self, pos):
        self.deltaPos += pos - self.playhead.x()

    def setCursorPlayheadPos(self, pos):
        if pos < 0:
            pos = 0
        elif pos > self.sceneRect().width():
            pos = self.sceneRect().width()
        self.cursorPlayhead.setX(pos)

    def showPlayhead(self):
        self.playhead.show()

    def hidePlayhead(self):
        self.playhead.hide()

    def resetPlayhead(self, sampleRate):
        self.playhead.setX(0)
        self.deltaPos = 0
        self.sampleRate = sampleRate
#        self.playhead.setX(.05 * sampleRate / self.realStep)

    def movePlayhead(self, secs):
        self.playhead.setX((secs) * self.sampleRate / self.realStep + self.deltaPos)
#        self.playhead.setX(self.playhead.x() + sampleRate * .05 / self.realStep)

    def drawWave(self, waveData, width):
        self.deltaPos = 0
        self.clear()
        self.cursorPlayhead = self.addLine(0, -100, 0, 100, self.cursorPlayheadPen)
        self.cursorPlayhead.hide()
        self.playhead = self.addLine(0, -100, 0, 100, self.playheadPen)
        self.playhead.setZValue(100)

        samples, channels = waveData.shape
        #resolution is 5 samples per scene pixel
        step = samples//(width*5)
        self.realStep = step

        path = QtGui.QPainterPath()
        path.moveTo(0, 0)
        pos = 0
        leftData = waveData[:, 0]
        leftMin = np.amin(np.pad(leftData, (0, step - leftData.size % step), mode='constant', constant_values=0).reshape(-1, step), axis=1)
        leftMax = np.amax(np.pad(leftData, (0, step - leftData.size % step), mode='constant', constant_values=0).reshape(-1, step), axis=1)
        for value in leftMax:
            path.lineTo(pos, value)
            pos += 1
        path.lineTo(pos, 0)
        path.moveTo(0, 0)
        pos = 0
        for value in leftMin:
            path.lineTo(pos, value)
            pos += 1
        path.lineTo(pos, 0)
        path.closeSubpath()
        leftPath = self.addPath(path, self.wavePen, self.waveBrush)
        self.addLine(0, 0, leftPath.boundingRect().width(), 0, self.zeroPen)
        if channels == 1:
            self.waveRect = QtCore.QRectF(0, -1, leftPath.boundingRect().width(), 2)
            return

        path = QtGui.QPainterPath()
        path.moveTo(0, 0)
        pos = 0
        rightData = waveData[:, 1]
        rightMin = np.amin(np.pad(rightData, (0, step - rightData.size % step), mode='constant', constant_values=0).reshape(-1, step), axis=1)
        rightMax = np.amax(np.pad(rightData, (0, step - rightData.size % step), mode='constant', constant_values=0).reshape(-1, step), axis=1)
        for value in rightMax:
            path.lineTo(pos, value)
            pos += 1
        path.lineTo(pos, 0)
        path.moveTo(0, 0)
        pos = 0
        for value in rightMin:
            path.lineTo(pos, value)
            pos += 1
        path.lineTo(pos, 0)
        path.closeSubpath()
        path.translate(0, 2)
        rightPath = self.addPath(path, self.wavePen, self.waveBrush)
        self.addLine(0, 2, rightPath.boundingRect().width(), 2, self.zeroPen)

        leftText = self.addText('L')
        leftText.setY(-1)
        leftText.setFlag(leftText.ItemIgnoresTransformations, True)
        rightText = self.addText('R')
        rightText.setY(1)
        rightText.setFlag(leftText.ItemIgnoresTransformations, True)
        self.waveRect = QtCore.QRectF(0, -1, leftPath.boundingRect().width(), 4)


class WaveViewPlayer(QtWidgets.QFrame):
    def __init__(self, *args, **kwargs):
        QtWidgets.QFrame.__init__(self, *args, **kwargs)
        self.setContentsMargins(0, 0, 2, 2)
        self.opacity = QtWidgets.QGraphicsOpacityEffect()
        self.opacity.setOpacity(.5)
        self.setGraphicsEffect(self.opacity)
        self.opacityAnimation = QtCore.QPropertyAnimation(self.opacity, b'opacity')
        self.opacityAnimation.setDuration(100)
        self.opacityAnimation.setStartValue(.5)
        self.opacityAnimation.setEndValue(.8)
        layout = QtWidgets.QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.playBtn = QtWidgets.QPushButton()
        self.playBtn.setIcon(QtGui.QIcon.fromTheme('media-playback-start'))
        layout.addWidget(self.playBtn)
        self.stopBtn = QtWidgets.QPushButton()
        self.stopBtn.setIcon(QtGui.QIcon.fromTheme('media-playback-stop'))
        self.stopBtn.setEnabled(False)
        layout.addWidget(self.stopBtn)

    def enterEvent(self, event):
        self.opacityAnimation.setDirection(self.opacityAnimation.Forward)
        self.opacityAnimation.start()

    def leaveEvent(self, event):
        self.opacityAnimation.setDirection(self.opacityAnimation.Backward)
        self.opacityAnimation.start()

    def started(self):
        self.playBtn.setIcon(QtGui.QIcon.fromTheme('media-playback-pause'))
        self.stopBtn.setEnabled(True)

    def paused(self):
        self.playBtn.setIcon(QtGui.QIcon.fromTheme('media-playback-start'))
        self.stopBtn.setEnabled(True)

    def stopped(self):
        self.playBtn.setIcon(QtGui.QIcon.fromTheme('media-playback-start'))
        self.stopBtn.setEnabled(False)


@HoverDecorator
class WaveView(QtWidgets.QGraphicsView):
    toggle = QtCore.pyqtSignal()
    stop = QtCore.pyqtSignal()
    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsView.__init__(self, *args, **kwargs)
        self.waveScene = WaveScene()
        self.setScene(self.waveScene)
        self.playerFrame = WaveViewPlayer(self)
        self.playerFrame.hide()
        self.playerFrame.stopBtn.clicked.connect(self.stop.emit)
        self.playerFrame.playBtn.clicked.connect(self.toggle.emit)

    def clear(self):
        self.waveScene.clear()
        self.playerFrame.hide()
        self.setEnabled(False)

    def drawWave(self, waveData):
        self.setEnabled(True)
        self.waveScene.drawWave(waveData, self.viewport().rect().width())
        self.fitInView(self.waveScene.waveRect)
        self.playerFrame.show()
        self.playerFrame.move(self.width() - self.playerFrame.width(), self.height() - self.playerFrame.height())

    def resetPlayhead(self, sampleRate):
        self.waveScene.resetPlayhead(sampleRate)

    def stopped(self):
        self.waveScene.hidePlayhead()
        self.playerFrame.stopped()

    def started(self):
        self.waveScene.showPlayhead()
        self.playerFrame.started()

    def paused(self):
        self.playerFrame.paused()

    def wheelEvent(self, event):
        pass

    def resizeEvent(self, event):
        self.playerFrame.move(self.width() - self.playerFrame.width(), self.height() - self.playerFrame.height())
