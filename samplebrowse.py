#!/usr/bin/env python2.7
# *-* coding: utf-8 *-*

import sys
import os
from PyQt4 import QtCore, QtGui, QtMultimedia, uic
import soundfile

availableFormats = tuple(f.lower() for f in soundfile.available_formats().keys())
availableExtensions = tuple('*.' + f for f in availableFormats)

FilePathRole = QtCore.Qt.UserRole + 1

class AlignItemDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, alignment):
        QtGui.QStyledItemDelegate.__init__(self)
        self.alignment = alignment

    def paint(self, painter, option, index):
        option.displayAlignment = self.alignment
        return QtGui.QStyledItemDelegate.paint(self, painter, option, index)

class SampleControlDelegate(QtGui.QStyledItemDelegate):
    controlClicked = QtCore.pyqtSignal(object)
    doubleClicked = QtCore.pyqtSignal(object)
    def editorEvent(self, event, model, option, index):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.pos() in option.rect and event.pos().x() < option.rect.height():
                self.controlClicked.emit(index)
        elif event.type() == QtCore.QEvent.MouseButtonDblClick:
            if event.pos().x() > option.rect.height():
                self.controlClicked.emit(index)
        return QtGui.QStyledItemDelegate.editorEvent(self, event, model, option, index)

class Player(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        uic.loadUi('main.ui', self)
        self.setup()
        self.fsModel = QtGui.QFileSystemModel()
        self.fsModel.setFilter(QtCore.QDir.AllDirs|QtCore.QDir.NoDotAndDotDot)
        self.proxyModel = QtGui.QSortFilterProxyModel()
        self.proxyModel.setSourceModel(self.fsModel)
        self.fsView.setModel(self.proxyModel)
        for c in xrange(1, self.fsModel.columnCount()):
            self.fsView.hideColumn(c)
        self.fsModel.setRootPath(QtCore.QDir.currentPath())
        self.fsModel.directoryLoaded.connect(self.cleanFolders)
        self.fsView.sortByColumn(0, QtCore.Qt.AscendingOrder)
#        self.fsView.setRootIndex(self.fsModel.index(QtCore.QDir.currentPath()))
        self.fsView.setCurrentIndex(self.proxyModel.mapFromSource(self.fsModel.index(QtCore.QDir.currentPath())))
        self.fsView.doubleClicked.connect(self.dirChanged)
        self.sampleModel = QtGui.QStandardItemModel()
        self.sampleView.setModel(self.sampleModel)

        self.alignRightDelegate = AlignItemDelegate(QtCore.Qt.AlignVCenter|QtCore.Qt.AlignRight)
        self.alignCenterDelegate = AlignItemDelegate(QtCore.Qt.AlignCenter)
        self.sampleView.setItemDelegateForColumn(1, self.alignRightDelegate)
        for c in xrange(2, 5):
            self.sampleView.setItemDelegateForColumn(c, self.alignCenterDelegate)
        self.sampleControlDelegate = SampleControlDelegate()
        self.sampleControlDelegate.controlClicked.connect(self.playToggle)
        self.sampleControlDelegate.doubleClicked.connect(self.play)
        self.sampleView.setItemDelegateForColumn(0, self.sampleControlDelegate)

        self.browse()
        self.splitter.setStretchFactor(0, 10)
        self.splitter.setStretchFactor(1, 15)

        self.currentItem = None
        self.shown = False

    def showEvent(self, event):
        if not self.shown:
            QtCore.QTimer.singleShot(
                1000, 
                lambda: self.fsView.scrollTo(
                    self.proxyModel.mapFromSource(self.fsModel.index(QtCore.QDir.currentPath())), self.fsView.PositionAtTop
                    )
                )
            self.shown = True

    def setup(self):
        self.audioDevice = QtMultimedia.QAudioDeviceInfo.defaultOutputDevice()
        self.sampleSize = 32 if 32 in self.audioDevice.supportedSampleSizes() else 16
        self.sampleRate = 48000 if 48000 in self.audioDevice.supportedSampleRates() else 44100
        format = QtMultimedia.QAudioFormat()
        format.setFrequency(self.sampleRate)
        format.setChannels(2)
        format.setSampleSize(self.sampleSize)
        format.setCodec('audio/pcm')
        format.setByteOrder(QtMultimedia.QAudioFormat.LittleEndian)
        format.setSampleType(QtMultimedia.QAudioFormat.Float if self.sampleSize >= 32 else QtMultimedia.QAudioFormat.SignedInt)
        self.output = QtMultimedia.QAudioOutput(format)
        self.output.stateChanged.connect(self.stateChanged)
        self.dtype = 'float32' if self.sampleSize >= 32 else 'int16'

    def cleanFolders(self, path):
        index = self.fsModel.index(path)
        for row in xrange(self.fsModel.rowCount(index)):
            self.fsModel.fetchMore(index.sibling(row, 0))
        self.fsModel.fetchMore(self.fsModel.index(path))

    def highlightCurrent(self, path):
        if path == QtCore.QDir.currentPath():
            self.fsView.scrollTo(self.proxyModel.mapFromSource(self.fsModel.index(QtCore.QDir.currentPath())))
            self.fsModel.directoryLoaded.disconnect(self.highlightCurrent)

    def dirChanged(self, index):
        self.browse(self.fsModel.filePath(self.proxyModel.mapToSource(index)))

    def browse(self, path='.'):
        self.sampleModel.clear()
        self.sampleModel.setHorizontalHeaderLabels(['Name', 'Length', 'Format', 'Rate', 'Ch.'])
        for fileInfo in QtCore.QDir(path).entryInfoList(availableExtensions, QtCore.QDir.Files):
            filePath = unicode(fileInfo.absoluteFilePath())
            fileName = unicode(fileInfo.fileName())
#            if fileName.lower().endswith(availableFormats):
            fileItem = QtGui.QStandardItem(fileName)
            fileItem.setData(filePath, FilePathRole)
            fileItem.setIcon(QtGui.QIcon.fromTheme('media-playback-start'))
            try:
                info = soundfile.info(filePath)
            except Exception as e:
                print e
                continue
            lengthItem = QtGui.QStandardItem('{:.3f}'.format(float(info.frames) / info.samplerate))
            formatItem = QtGui.QStandardItem(info.format)
            rateItem = QtGui.QStandardItem(str(info.samplerate))
            channelsItem = QtGui.QStandardItem(str(info.channels))
            self.sampleModel.appendRow([fileItem, lengthItem, formatItem, rateItem, channelsItem])
        self.sampleView.resizeColumnsToContents()
        self.sampleView.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
#        self.sampleView.horizontalHeader().setMinimumSectionSize(100)
        for c in xrange(1, 5):
            self.sampleView.horizontalHeader().setResizeMode(c, QtGui.QHeaderView.Fixed)
        self.sampleView.resizeRowsToContents()

    def playToggle(self, index):
        if not index.isValid():
            return
        fileItem = self.sampleModel.itemFromIndex(index.sibling(index.row(), 0))
        if self.currentItem and self.currentItem == fileItem and self.output.state() == QtMultimedia.QAudio.ActiveState:
            self.output.stop()
        else:
            self.play(index)

    def play(self, index):
        if not index.isValid():
            return
        if self.output.state() == QtMultimedia.QAudio.ActiveState:
            self.output.stop()
        fileItem = self.sampleModel.itemFromIndex(index.sibling(index.row(), 0))
        buffer = QtCore.QBuffer(self)
        array = QtCore.QByteArray()
        with soundfile.SoundFile(unicode(fileItem.data(FilePathRole).toString())) as sf:
            data = sf.read(always_2d=True, dtype=self.dtype)
            if sf.channels == 1:
                data = data.repeat(2, axis=1)/2
            data *= self.volumeSpin.value()/100.
        array.append(data.tostring())
        buffer.setData(array)
        buffer.open(QtCore.QIODevice.ReadOnly)
        buffer.seek(0)
        self.currentItem = fileItem
        self.output.start(buffer)
        fileItem.setIcon(QtGui.QIcon.fromTheme('media-playback-stop'))

    def stateChanged(self, state):
        print 'son qui'
        if state in (QtMultimedia.QAudio.StoppedState, QtMultimedia.QAudio.IdleState) and self.currentItem:
            self.currentItem.setData(QtGui.QIcon.fromTheme('media-playback-start'), QtCore.Qt.DecorationRole)

def main():
    app = QtGui.QApplication(sys.argv)
#    app.setQuitOnLastWindowClosed(False)
#    DBusQtMainLoop(set_as_default=True)

    player = Player()
    player.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
