#!/usr/bin/env python3
# *-* coding: utf-8 *-*

import sys
import os
import sqlite3
#from math import log
from PyQt5 import QtCore, QtGui, QtMultimedia, QtWidgets, uic
import soundfile
import samplerate
import numpy as np

import samplebrowsesrc.icons
from samplebrowsesrc.widgets import *
from samplebrowsesrc.constants import *
from samplebrowsesrc.dialogs import *
from samplebrowsesrc.classes import *
from samplebrowsesrc.utils import *

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
    playheadPen = QtGui.QPen(QtCore.Qt.black, .5)
    playheadPen.setCosmetic(True)

    def __init__(self, *args, **kwargs):
        QtWidgets.QGraphicsScene.__init__(self, *args, **kwargs)
        self.waveRect = QtCore.QRectF()
        self.realStep = 0
        self.sampleRate = 0

    def showPlayhead(self):
        self.playhead.show()

    def hidePlayhead(self):
        self.playhead.hide()

    def resetPlayhead(self, sampleRate):
        self.playhead.setX(0)
        self.sampleRate = sampleRate
#        self.playhead.setX(.05 * sampleRate / self.realStep)
#        print(sampleRate * .05 / self.realStep)

    def movePlayhead(self, secs):
        self.playhead.setX((secs) * self.sampleRate / self.realStep)
#        self.playhead.setX(self.playhead.x() + sampleRate * .05 / self.realStep)

    def drawWave(self, waveData, width):
        self.clear()
        self.playhead = self.addLine(0, -100, 0, 100, self.playheadPen)
#        self.playhead.setFlags(self.playhead.flags() ^ self.playhead.ItemIgnoresTransformations)

        samples, channels = waveData.shape
        #resolution is 5 samples per scene pixel
        step = samples//(width*5)
#        self.realStep = samples/(width*5)
        print(step, samples/(width*5))
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


class UpArrowIcon(QtGui.QIcon):
    def __init__(self):
        pm = QtGui.QPixmap(12, 12)
        pm.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pm)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        path = QtGui.QPainterPath()
        path.moveTo(2, 8)
        path.lineTo(6, 2)
        path.lineTo(10, 8)
        qp.drawPath(path)
        del qp
        QtGui.QIcon.__init__(self, pm)


class DownArrowIcon(QtGui.QIcon):
    def __init__(self):
        pm = QtGui.QPixmap(12, 12)
        pm.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pm)
        qp.setRenderHints(QtGui.QPainter.Antialiasing)
        path = QtGui.QPainterPath()
        path.moveTo(2, 4)
        path.lineTo(6, 10)
        path.lineTo(10, 4)
        qp.drawPath(path)
        del qp
        QtGui.QIcon.__init__(self, pm)


class VerticalDownToggleBtn(QtWidgets.QToolButton):
    def __init__(self, *args, **kwargs):
        QtWidgets.QToolButton.__init__(self, *args, **kwargs)
        self.upIcon = UpArrowIcon()
        self.downIcon = DownArrowIcon()
        self.setMaximumSize(16, 16)
        self.setIcon(self.downIcon)

    def toggle(self, value):
        if value:
            self.setDown()
        else:
            self.setUp()

    def setDown(self):
        self.setIcon(self.downIcon)

    def setUp(self):
        self.setIcon(self.upIcon)


class Player(QtCore.QObject):
    stateChanged = QtCore.pyqtSignal(object)
    notify = QtCore.pyqtSignal()
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    paused = QtCore.pyqtSignal()

    def __init__(self, main, audioDeviceName=None, sampleRateConversion='sinc_fastest'):
        QtCore.QObject.__init__(self)
        self.main = main
        self.audioBufferArray = QtCore.QBuffer(self)
        self.output = None
        self.audioDevice = None
        self.setAudioDeviceByName(audioDeviceName)
        self.setAudioDevice()
        self.sampleRateConversion = sampleRateConversion

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
        self.output = QtMultimedia.QAudioOutput(self.audioDevice, format)
        self.output.setNotifyInterval(50)
        self.output.stateChanged.connect(self.stateChanged)
        self.output.notify.connect(self.notify)

    def isPlaying(self):
        return True if self.output.state() == QtMultimedia.QAudio.ActiveState else False

    def stateChanged(self, state):
        if state in (QtMultimedia.QAudio.StoppedState, QtMultimedia.QAudio.IdleState):
            self.stopped.emit()
        elif state == QtMultimedia.QAudio.ActiveState:
            self.started.emit()
        else:
            self.paused.emit()

#    def run(self):
#        while True:
#            res = self.audioQueue.get()
#            if res == -1:
#                break
#            self.output.stop()
#            self.audioBufferArray.close()
#            self.audioBufferArray.setData(res)
#            self.audioBufferArray.open(QtCore.QIODevice.ReadOnly)
#            self.audioBufferArray.seek(0)
#            self.output.start(self.audioBufferArray)
#        self.output.stop()

    def stop(self):
        self.output.stop()

    def play(self, waveData, info):
        if info.samplerate != self.sampleRate:
            #ratio is output/input
            waveData = samplerate.resample(waveData, self.sampleRate / info.samplerate, self.sampleRateConversion)
            
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
        if self.sampleSize == 16:
            waveData = (waveData * 32767).astype('int16')
        self.audioBufferArray.close()
        self.audioBufferArray.setData(waveData.tostring())
        self.audioBufferArray.open(QtCore.QIODevice.ReadOnly)
        self.audioBufferArray.seek(0)
        self.output.start(self.audioBufferArray)

    def setVolume(self, volume):
#        try:
#            volume = QtMultimedia.QAudio.convertVolume(volume / 100, QtMultimedia.QAudio.LogarithmicVolumeScale, QtMultimedia.QAudio.LinearVolumeScale)
#        except:
#            if volume >= 100:
#                volume = 1
#            else:
#                volume = -log(1 - volume/100) / 4.60517018599
        self.output.setVolume(volume/100)


class SampleBrowse(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        uic.loadUi('{}/main.ui'.format(os.path.dirname(constants.__file__)), self, package='samplebrowsesrc.widgets', resource_suffix='')
        self.setWindowIcon(QtGui.QIcon(':/icons/TangoCustom/32x32/samplebrowse.png'))
        if not QtGui.QIcon.themeName():
            QtGui.QIcon.setThemeName('TangoCustom')
        self.settings = QtCore.QSettings()
        self.player = Player(self, self.settings.value('AudioDevice'), self.settings.value('SampleRateConversion', 'sinc_fastest'))
        self.player.stopped.connect(self.stopped)
        self.player.output.notify.connect(self.movePlayhead)
        self.sampleSize = self.player.sampleSize
        self.sampleRate = self.player.sampleRate

        self.browseSelectGroup.setId(self.browseSystemBtn, 0)
        self.browseSelectGroup.setId(self.browseDbBtn, 1)
        self.volumeSlider.mousePressEvent = self.volumeSliderMousePressEvent
        self.volumeSlider.valueChanged.connect(self.player.setVolume)

        self.browserStackedWidget = QtWidgets.QWidget()
        self.browserStackedLayout = QtWidgets.QStackedLayout()
        self.browserStackedWidget.setLayout(self.browserStackedLayout)
        self.mainSplitter.insertWidget(0, self.browserStackedWidget)

        self.fsSplitter = AdvancedSplitter(QtCore.Qt.Vertical)
        self.browserStackedLayout.addWidget(self.fsSplitter)
        self.fsView = FsTreeView()
        self.fsSplitter.addWidget(self.fsView, collapsible=False)
        self.fsView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.fsView.setHeaderHidden(True)
        self.favouritesTable = QtWidgets.QTableView()
        self.fsSplitter.addWidget(self.favouritesTable, label='Favourites')
        self.favouritesTable.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.favouritesTable.setSelectionBehavior(self.favouritesTable.SelectRows)
        self.favouritesTable.setSortingEnabled(True)
        self.favouritesTable.horizontalHeader().setMaximumHeight(self.favouritesTable.fontMetrics().height() + 4)
        self.favouritesTable.horizontalHeader().setHighlightSections(False)
        self.favouritesTable.verticalHeader().setVisible(False)
        
        self.fsModel = QtWidgets.QFileSystemModel()
        self.fsModel.setFilter(QtCore.QDir.AllDirs|QtCore.QDir.NoDot | QtCore.QDir.NoDotDot)
        self.fsProxyModel = QtCore.QSortFilterProxyModel()
        self.fsProxyModel.setSourceModel(self.fsModel)
        self.fsView.setModel(self.fsProxyModel)
        for c in range(1, self.fsModel.columnCount()):
            self.fsView.hideColumn(c)
        self.fsModel.setRootPath(QtCore.QDir.currentPath())
        self.fsModel.directoryLoaded.connect(self.cleanFolders)
        self.fsView.sortByColumn(0, QtCore.Qt.AscendingOrder)
#        self.fsView.setRootIndex(self.fsModel.index(QtCore.QDir.currentPath()))
        self.fsView.setCurrentIndex(self.fsProxyModel.mapFromSource(self.fsModel.index(QtCore.QDir.currentPath())))
        self.fsView.clicked.connect(self.dirChanged)
        self.fsView.customContextMenuRequested.connect(self.fsViewContextMenu)

        self.favouritesModel = QtGui.QStandardItemModel()
        self.favouritesModel.setHorizontalHeaderLabels(['Name', 'Path'])
        self.favouritesTable.setModel(self.favouritesModel)
        self.favouritesTable.mousePressEvent = self.favouritesTableMousePressEvent
        self.favouritesTable.horizontalHeader().setStretchLastSection(True)
        self.loadFavourites()
        self.favouritesModel.dataChanged.connect(self.favouritesDataChanged)

        self.fsSplitter.setStretchFactor(0, 50)
        self.fsSplitter.setStretchFactor(1, 1)

        self.loadDb()

        self.dbSplitter = AdvancedSplitter(QtCore.Qt.Vertical)
        self.browserStackedLayout.addWidget(self.dbSplitter)
        self.dbTreeView = DbTreeView(self)
        self.dbTreeView.samplesAddedToTag.connect(self.addSamplesToTag)
        self.dbTreeView.samplesImported.connect(self.importSamplesWithTags)
        self.tagTreeDelegate = TagTreeDelegate()
        self.tagTreeDelegate.tagColorsChanged.connect(self.saveTagColors)
        self.tagTreeDelegate.startEditTag.connect(self.renameTag)
        self.tagTreeDelegate.removeTag.connect(self.removeTag)
        self.dbTreeView.setItemDelegateForColumn(0, self.tagTreeDelegate)
        self.dbTreeView.setEditTriggers(self.dbTreeView.NoEditTriggers)
        self.dbTreeView.header().setStretchLastSection(False)
        self.dbTreeView.setHeaderHidden(True)
        self.dbTreeModel = TagsModel(self.sampleDb)
        self.dbTreeModel.tagRenamed.connect(self.tagRenamed)
        self.dbTreeProxyModel = QtCore.QSortFilterProxyModel()
        self.dbTreeProxyModel.setSourceModel(self.dbTreeModel)
        self.dbTreeView.setModel(self.dbTreeProxyModel)
        self.dbTreeView.clicked.connect(self.dbTreeViewDoubleClicked)
        self.dbSplitter.addWidget(self.dbTreeView, collapsible=False)

        self.dbDirView = TreeViewWithLines()
        self.dbDirView.setEditTriggers(self.dbDirView.NoEditTriggers)
        self.dbDirView.clicked.connect(self.dbDirViewSelect)
        self.dbSplitter.addWidget(self.dbDirView, label='Directories')
        self.dbDirModel = DbDirModel(self.sampleDb)
        self.dbDirView.setModel(self.dbDirModel)
        self.dbDirView.setHeaderHidden(True)
        self.dbDirView.header().setStretchLastSection(False)
        self.dbDirModel.loaded.connect(lambda: [
            self.dbDirView.resizeColumnToContents(1), 
            self.dbDirView.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch), 
            self.dbDirView.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents), 
            ] if self.dbDirModel.rowCount() else None)
        self.dbDirModel.updateTree()
#        self.dbDirView.resizeColumnToContents(1)
        #TODO: wtf?!
#        self.dbDirView.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
#        self.dbDirView.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)

        self.dbSplitter.setStretchFactor(0, 50)
        self.dbSplitter.setStretchFactor(1, 1)


        self.browseSelectGroup.buttonClicked[int].connect(self.toggleBrowser)
        self.browseModel = QtGui.QStandardItemModel()
        self.dbModel = QtGui.QStandardItemModel()
        self.dbProxyModel = SampleSortFilterProxyModel()
        self.dbProxyModel.setSourceModel(self.dbModel)
        self.sampleView.setModel(self.browseModel)
        self.alignCenterDelegate = AlignItemDelegate(QtCore.Qt.AlignCenter)
        self.alignLeftElideMidDelegate = AlignItemDelegate(QtCore.Qt.AlignLeft, QtCore.Qt.ElideMiddle)
        self.sampleView.setItemDelegateForColumn(1, self.alignLeftElideMidDelegate)
        for c in range(2, subtypeColumn + 1):
            self.sampleView.setItemDelegateForColumn(c, self.alignCenterDelegate)
        self.subtypeDelegate = SubtypeDelegate()
        self.sampleView.setItemDelegateForColumn(subtypeColumn, self.subtypeDelegate)
        self.tagListDelegate = TagListDelegate(self.tagColorsDict)
        self.sampleView.setItemDelegateForColumn(tagsColumn, self.tagListDelegate)
        self.tagListDelegate.tagSelected.connect(self.selectTagOnTree)
        self.sampleView.setMouseTracking(True)
        self.sampleControlDelegate = SampleControlDelegate()
        self.sampleControlDelegate.controlClicked.connect(self.playToggle)
        #TODO: fix this inconsistency!
        self.sampleControlDelegate.doubleClicked.connect(self.play)
        self.sampleView.clicked.connect(self.setCurrentWave)
        self.sampleView.doubleClicked.connect(self.editTags)
        self.sampleView.setItemDelegateForColumn(0, self.sampleControlDelegate)
        self.sampleView.keyPressEvent = self.sampleViewKeyPressEvent
        self.sampleView.customContextMenuRequested.connect(self.sampleContextMenu)
        self.sampleView.fileReadable.connect(self.setIndexReadable)

        self.waveScene = WaveScene()
        self.waveView.setScene(self.waveScene)
        self.player.stopped.connect(self.waveScene.hidePlayhead)
        self.player.started.connect(self.waveScene.showPlayhead)

        self.filterStackedLayout = QtWidgets.QStackedLayout()
        self.filterStackedLayout.sizeHint = lambda: QtCore.QSize(10, 10)
        self.filterStackedLayout.minimumSize = lambda: QtCore.QSize(10, 10)
        self.filterStackedWidget.setLayout(self.filterStackedLayout)
        self.browsePathLbl = EllipsisLabel()
        self.filterStackedLayout.addWidget(self.browsePathLbl)
        self.filterWidget = MainFilterWidget()
        self.filterWidget.filtersChanged.connect(self.dbProxyModel.setFilterData)
        self.filterStackedLayout.addWidget(self.filterWidget)

        self.audioInfoTabWidget.tagsApplied.connect(self.tagsApplied)

        self.currentSampleIndex = None
        self.currentShownSampleIndex = None
        self.currentBrowseDir = None
        self.currentDbQuery = None
        self.sampleDbUpdated = False

#        self.browse()
#        for column, visible in browseColumns.items():
#            self.sampleView.horizontalHeader().setSectionHidden(column, not visible)

        self.mainSplitter.setStretchFactor(0, 8)
        self.mainSplitter.setStretchFactor(1, 16)

        defaultVolumeMode = self.settings.value('defaultVolumeMode', 0, type=int)
        if defaultVolumeMode == 1:
            self.volumeSlider.setValue(self.settings.value('previousVolume', 100, type=int))
        elif defaultVolumeMode == 2:
            self.volumeSlider.setValue(self.settings.value('customVolume', 100, type=int))

        self.shown = False

        self.reloadTags()
        self.dbTreeView.expandToDepth(0)

        self.doMenu()

    def doMenu(self):
        self.fileMenu.addAction('Show database statistics...', self.showStats)
        self.fileMenu.addSeparator()
        quitAction = self.fileMenu.addAction(QtGui.QIcon.fromTheme('application-exit'), 'Quit', self.quit)
        quitAction.setMenuRole(QtWidgets.QAction.QuitRole)

        rightMenuBar = QtWidgets.QMenuBar(self.menubar)
        helpMenu = QtWidgets.QMenu('&?', self.menubar)
        rightMenuBar.addMenu(helpMenu)
        self.menubar.setCornerWidget(rightMenuBar)

        settingsAction = helpMenu.addAction(QtGui.QIcon.fromTheme('preferences-system'), 'Preferences...', lambda: SettingsDialog(self).exec_())
        settingsAction.setMenuRole(QtWidgets.QAction.PreferencesRole)
        audioSettingsAction = helpMenu.addAction(QtGui.QIcon.fromTheme('preferences-desktop-multimedia'), 'Audio settings...', self.showAudioSettings)
        audioSettingsAction.setMenuRole(QtWidgets.QAction.PreferencesRole)
        helpMenu.addSeparator()
        aboutAction = helpMenu.addAction(QtGui.QIcon.fromTheme('help-about'), 'About...', AboutDialog(self).exec_)
        aboutAction.setMenuRole(QtWidgets.QAction.AboutRole)

    def showStats(self):
        StatsDialog(self).exec_()

    def showAudioSettings(self):
        res = AudioSettingsDialog(self).exec_()
        if not res:
            return
        device, conversion = res
        self.player.setAudioDevice(device)
        self.player.setSampleRateConversion(conversion)

    def closeEvent(self, event):
        self.quit()

    def quit(self):
        self.settings.setValue('previousVolume', self.volumeSlider.value())
        self.settings.sync()
        self.dbConn.commit()
        self.dbConn.close()
        QtWidgets.QApplication.quit()

    def loadDb(self):
        dataDir = QtCore.QDir(QtCore.QStandardPaths.standardLocations(QtCore.QStandardPaths.AppDataLocation)[0])
        dbFile = QtCore.QFile(dataDir.filePath('sample.sqlite'))
        if not dbFile.exists():
            if not dataDir.exists():
                dataDir.mkpath(dataDir.absolutePath())
        self.dbConn = sqlite3.connect(dbFile.fileName())
        self.sampleDb = self.dbConn.cursor()
        try:
            self.sampleDb.execute('CREATE table samples(filePath varchar primary key, fileName varchar, length float, format varchar, sampleRate int, channels int, tags varchar, preview blob)')
        except Exception as e:
            print(e)
            #migrate
            self.sampleDb.execute('PRAGMA table_info(samples)')
            if len(self.sampleDb.fetchall()) != len(allColumns):
                self.sampleDb.execute('ALTER TABLE samples RENAME TO oldsamples')
                self.sampleDb.execute('CREATE table samples(filePath varchar primary key, fileName varchar, length float, format varchar, sampleRate int, channels int, subtype varchar, tags varchar, preview blob)')
                self.sampleDb.execute('INSERT INTO samples (filePath, fileName, length, format, sampleRate, channels, tags, preview) SELECT filePath, fileName, length, format, sampleRate, channels, tags, preview FROM oldsamples')
                self.sampleDb.execute('DROP TABLE oldsamples')
        try:
            self.sampleDb.execute('CREATE table tagColors(tag varchar primary key, foreground varchar, background varchar)')
        except Exception as e:
            print(e)
        self.dbConn.commit()
        self.tagColorsDict = {}
        self.sampleDb.execute('SELECT tag,foreground,background FROM tagColors')
        for res in self.sampleDb.fetchall():
            tag, foreground, background = res
            self.tagColorsDict[tag] = QtGui.QColor(foreground), QtGui.QColor(background)

    def showEvent(self, event):
        if not self.shown:
            startupView = self.settings.value('startupView', 0, type=int)
            self.browseSelectGroup.button(startupView).setChecked(True)
            QtCore.QTimer.singleShot(
                0, 
                lambda: [self.fsView.scrollToPath(QtCore.QDir.currentPath()), self.toggleBrowser(startupView)]
                )
            self.resize(640, 480)
            self.shown = True

    def sampleViewKeyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            if not self.player.isPlaying():
                if self.sampleView.currentIndex().isValid():
                    self.play(self.sampleView.currentIndex())
                    self.sampleView.setCurrentIndex(self.sampleView.currentIndex())
            else:
                if self.sampleView.model().rowCount() <= 1:
                    self.player.stop()
                else:
                    if event.modifiers() == QtCore.Qt.ShiftModifier:
                        if self.currentSampleIndex.row() == 0:
                            next = self.currentSampleIndex.sibling(self.sampleView.model().rowCount() -1, 0)
                        else:
                            next = self.currentSampleIndex.sibling(self.currentSampleIndex.row() - 1, 0)
                    else:
                        if self.currentSampleIndex.row() == self.sampleView.model().rowCount() - 1:
                            next = self.currentSampleIndex.sibling(0, 0)
                        else:
                            next = self.currentSampleIndex.sibling(self.currentSampleIndex.row() + 1, 0)
                    self.sampleView.setCurrentIndex(next)
                    self.play(next)
        elif event.key() in (QtCore.Qt.Key_Period, QtCore.Qt.Key_Escape):
            self.player.stop()
        else:
            QtWidgets.QTableView.keyPressEvent(self.sampleView, event)

    def cleanFolders(self, path):
        index = self.fsModel.index(path)
        for row in range(self.fsModel.rowCount(index)):
            self.fsModel.fetchMore(index.sibling(row, 0))
        self.fsModel.fetchMore(self.fsModel.index(path))

    def fsViewContextMenu(self, pos):
        dirIndex = self.fsView.indexAt(pos)
        dirName = dirIndex.data()
        dirPath = self.fsModel.filePath(self.fsProxyModel.mapToSource(dirIndex))

        menu = QtWidgets.QMenu()
        addDirAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('emblem-favorite'), 'Add "{}" to favourites'.format(dirName), menu)
        for row in range(self.favouritesModel.rowCount()):
            dirPathItem = self.favouritesModel.item(row, 1)
            if dirPathItem.text() == dirPath:
                addDirAction.setEnabled(False)
                break
        scanAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('edit-find'), 'Scan "{}" for samples'.format(dirName), menu)

        menu.addActions([addDirAction, utils.menuSeparator(menu), scanAction])
        res = menu.exec_(self.fsView.mapToGlobal(pos))
        if res == addDirAction:
            dirLabelItem = QtGui.QStandardItem(dirIndex.data())
            dirPathItem = QtGui.QStandardItem(QtCore.QDir.toNativeSeparators(dirPath))
            dirPathItem.setData(dirPath, FilePathRole)
            dirPathItem.setFlags(dirPathItem.flags() ^ QtCore.Qt.ItemIsEditable)
            self.favouritesModel.dataChanged.disconnect(self.favouritesDataChanged)
            self.favouritesModel.appendRow([dirLabelItem, dirPathItem])
            self.favouritesModel.dataChanged.connect(self.favouritesDataChanged)
            self.settings.beginGroup('Favourites')
            self.settings.setValue(dirIndex.data(), dirPath)
            self.settings.endGroup()
        elif res == scanAction:
            self.sampleScan(dirPath)

    def sampleScan(self, dirPath=QtCore.QDir('.').absolutePath()):
        scanOptionsDialog = ScanOptionsDialog(self, dirPath)
        if not scanOptionsDialog.exec_():
            return
        dirPath = scanOptionsDialog.dirPathEdit.text()
        scanMode = scanOptionsDialog.scanModeCombo.currentIndex()
        formats = scanOptionsDialog.getFormats()
        sampleRates = scanOptionsDialog.getSampleRates()
        channels = scanOptionsDialog.channelsCombo.currentIndex()
        scanLimits = scanOptionsDialog.getScanLimits()
        res = ImportDialogScan(self, dirPath, scanMode, formats, sampleRates, channels, scanLimits).exec_()
        if not res:
            return
        for filePath, fileName, info, tags in res:
            self._addSampleToDb(filePath, fileName, info, ','.join(tags))
        self.dbConn.commit()
        self.reloadTags()
        self.dbDirModel.updateTree()
        #TODO: reload database table?

    def favouritesDataChanged(self, index, _):
        dirPathIndex = index.sibling(index.row(), 1)
        dirLabel = index.sibling(index.row(), 0).data()
        dirPath = dirPathIndex.data(FilePathRole)
        self.settings.beginGroup('Favourites')
        for fav in self.settings.childKeys():
            if self.settings.value(fav) == dirPath:
                self.settings.remove(fav)
                self.settings.setValue(dirLabel, dirPath)
                break
        else:
            self.settings.setValue(dirLabel, dirPath)
        self.settings.endGroup()

    def loadFavourites(self):
        self.settings.beginGroup('Favourites')
        for fav in self.settings.childKeys():
            dirLabelItem = QtGui.QStandardItem(fav)
            dirPath = self.settings.value(fav)
            dirPathItem = QtGui.QStandardItem(QtCore.QDir.toNativeSeparators(dirPath))
            dirPathItem.setData(dirPath, FilePathRole)
            dirPathItem.setFlags(dirPathItem.flags() ^ QtCore.Qt.ItemIsEditable)
            self.favouritesModel.appendRow([dirLabelItem, dirPathItem])
        self.settings.endGroup()

    def browseFromFavourites(self, index):
        if not index.isValid():
            return
        dirPathIndex = index.sibling(index.row(), 1)
        self.browse(dirPathIndex.data(FilePathRole))

    def favouritesTableMousePressEvent(self, event):
        index = self.favouritesTable.indexAt(event.pos())
        if event.button() != QtCore.Qt.RightButton:
            self.browseFromFavourites(index)
            return QtWidgets.QTableView.mousePressEvent(self.favouritesTable, event)
        if not index.isValid():
            return
        QtWidgets.QTableView.mousePressEvent(self.favouritesTable, event)
        dirPathIndex = index.sibling(index.row(), 1)
        dirPath = dirPathIndex.data(FilePathRole)
        menu = QtWidgets.QMenu()
        scrollToAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('folder'), 'Show directory in tree', menu)
        removeAction = QtWidgets.QAction(QtGui.QIcon.fromTheme('edit-delete'), 'Remove from favourites', menu)
        menu.addActions([scrollToAction, utils.menuSeparator(menu), removeAction])
        res = menu.exec_(self.favouritesTable.viewport().mapToGlobal(event.pos()))
        if res == scrollToAction:
            self.fsView.scrollToPath(dirPath)
        elif res == removeAction:
            self.settings.beginGroup('Favourites')
            for fav in self.settings.childKeys():
                if self.settings.value(fav) == dirPath:
                    self.settings.remove(fav)
                    break
            self.favouritesModel.takeRow(index.row())
            self.settings.endGroup()

#    def favouritesToggle(self, *args):
#        visible = not self.favouritesTable.isVisible()
#        self.favouritesTable.setVisible(visible)
#        self.favouritesToggleBtn.toggle(visible)
#        self.favouriteWidget.setMaximumHeight(self.favouriteWidget.layout().sizeHint().height())
#
#    def dbDirToggle(self, *args):
#        visible = not self.dbDirView.isVisible()
#        self.dbDirView.setVisible(visible)
#        self.dbDirToggleBtn.toggle(visible)
#        self.dbDirWidget.setMaximumHeight(self.dbDirWidget.layout().sizeHint().height())

    def dirChanged(self, index):
        self.browse(self.fsModel.filePath(self.fsProxyModel.mapToSource(index)))

    def setIndexReadable(self, fileIndex, readable):
        if not fileIndex.column() == 0:
            fileIndex = fileIndex.sibling(fileIndex.row(), 0)
        model = fileIndex.model()
        item = model.itemFromIndex(fileIndex)
        utils.setItalic(item, not readable)
        if not readable:
            self.audioInfoTabWidget.clear()
    
    def browse(self, path=None):
        if path is None:
            if self.currentBrowseDir:
                if self.currentShownSampleIndex and self.currentShownSampleIndex.model() == self.browseModel:
                    self.sampleView.setCurrentIndex(self.currentShownSampleIndex)
                return
            else:
                path = QtCore.QDir('.')
        else:
            path = QtCore.QDir(path)
        self.currentBrowseDir = path
        self.browseModel.clear()
        self.browseModel.setHorizontalHeaderLabels(['Name', None, 'Length', 'Format', 'Rate', 'Ch.', 'Bits', None, None])
        for column, visible in browseColumns.items():
            self.sampleView.horizontalHeader().setSectionHidden(column, not visible)
        for fileInfo in path.entryInfoList(availableExtensions, QtCore.QDir.Files):
            filePath = fileInfo.absoluteFilePath()
            fileName = fileInfo.fileName()
#            if fileName.lower().endswith(availableFormats):
            fileItem = QtGui.QStandardItem(fileName)
            fileItem.setData(filePath, FilePathRole)
            fileItem.setIcon(QtGui.QIcon.fromTheme('media-playback-start'))
            try:
                info = soundfile.info(filePath)
                fileItem.setData(info, InfoRole)
            except Exception as e:
#                print e
                continue
            dirItem = QtGui.QStandardItem(fileInfo.absolutePath())
            lengthItem = QtGui.QStandardItem(timeStr(info.frames / info.samplerate, trailingAlways=True))
            formatItem = QtGui.QStandardItem(info.format)
            rateItem = QtGui.QStandardItem(str(info.samplerate))
            channelsItem = QtGui.QStandardItem(str(info.channels))
            subtypeItem = QtGui.QStandardItem(info.subtype)
            self.browseModel.appendRow([fileItem, dirItem, lengthItem, formatItem, rateItem, channelsItem, subtypeItem])
        self.sampleView.resizeColumnsToContents()
        self.sampleView.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        for c in range(1, subtypeColumn + 1):
            self.sampleView.horizontalHeader().setSectionResizeMode(c, QtWidgets.QHeaderView.Fixed)
        self.sampleView.resizeRowsToContents()
        self.browsePathLbl.setText(path.absolutePath())

    def volumeSliderMousePressEvent(self, event):
        if event.button() == QtCore.Qt.MidButton:
            self.volumeSpin.setValue(100)
        else:
            QtWidgets.QSlider.mousePressEvent(self.volumeSlider, event)

    def sampleContextMenu(self, pos):
        selIndex = self.sampleView.indexAt(pos)
        if not selIndex.isValid():
            return
        if len(self.sampleView.selectionModel().selectedRows()) == 1:
            self.singleSampleContextMenu(selIndex.sibling(selIndex.row(), 0), pos)
        else:
            self.multiSampleContextMenu(pos)

    def singleSampleContextMenu(self, fileIndex, pos):
        fileName = fileIndex.data()
        filePath = fileIndex.data(FilePathRole)
        menu = QtWidgets.QMenu()
        addToDatabaseAction = QtWidgets.QAction('Add "{}" to database'.format(fileName), menu)
        editTagsAction = QtWidgets.QAction('Edit "{}" tags...'.format(fileName), menu)
        delFromDatabaseAction = QtWidgets.QAction('Remove "{}" from database'.format(fileName), menu)
        self.sampleDb.execute('SELECT * FROM samples WHERE filePath=?', (filePath, ))
        if self.sampleView.model() == self.browseModel and not self.sampleDb.fetchone():
            menu.addAction(addToDatabaseAction)
        else:
            if self.sampleView.model() == self.dbProxyModel:
                menu.addAction(editTagsAction)
            menu.addAction(delFromDatabaseAction)
        res = menu.exec_(self.sampleView.viewport().mapToGlobal(pos))
        if res == addToDatabaseAction:
            info = fileIndex.data(InfoRole)
            self.addSampleToDb(filePath, fileName, info, '', None)
        elif res == delFromDatabaseAction:
            filePath = fileIndex.data(FilePathRole)
            self.sampleDb.execute(
                'DELETE FROM samples WHERE filePath=?', 
                (filePath, )
                )
            self.dbConn.commit()
            self.reloadTags()
            if self.sampleView.model() == self.dbProxyModel:
                self.dbModel.takeRow(fileIndex.row())
            else:
                self.sampleDbUpdated = True
            self.dbDirModel.updateTree()
        elif res == editTagsAction:
            self.editTags(fileIndex.sibling(fileIndex.row(), tagsColumn))

    def multiSampleContextMenu(self, pos):
        new = []
        exist = []
        fileIndexList = self.sampleView.selectionModel().selectedRows()
        for fileIndex in fileIndexList:
            filePath = fileIndex.data(FilePathRole)
            self.sampleDb.execute('SELECT * FROM samples WHERE filePath=?', (filePath, ))
            if not self.sampleDb.fetchone():
                new.append(fileIndex)
            else:
                exist.append(fileIndex)
        menu = QtWidgets.QMenu()
        if self.sampleView.model() == self.browseModel:
            editTagsAction = None
            removeAllAction = QtWidgets.QAction('Remove {} existing samples from database'.format(len(exist)), menu)
        else:
            editTagsAction = QtWidgets.QAction('Edit tags for selected samples...', menu)
            removeAllAction = QtWidgets.QAction('Remove selected samples from database', menu)
        addAllAction = QtWidgets.QAction('Add selected samples to database', menu)
        addAllWithTagsAction = QtWidgets.QAction('Add selected samples to database with tags...', menu)
        if new:
            menu.addActions([addAllAction, addAllWithTagsAction])
        if exist:
            if new:
                menu.addAction(utils.menuSeparator(menu))
            if editTagsAction:
                menu.addAction(editTagsAction)
            menu.addAction(removeAllAction)
        res = menu.exec_(self.sampleView.viewport().mapToGlobal(pos))
        if res == addAllAction:
            self.addSampleGroupToDb(new)
            self.dbDirModel.updateTree()
        elif res == addAllWithTagsAction:
            tags = AddSamplesWithTagDialog(self, new).exec_()
            if isinstance(tags, str):
                self.addSampleGroupToDb(new, tags)
            self.dbDirModel.updateTree()
        elif res == editTagsAction:
            indexes = []
            fileList = []
            tags = set()
            for fileIndex in fileIndexList:
                filePath = fileIndex.data(FilePathRole)
                fileList.append(filePath)
                tagsIndex = fileIndex.sibling(fileIndex.row(), tagsColumn)
                indexes.append(tagsIndex)
                self.sampleDb.execute('SELECT tags FROM samples WHERE filePath=?', (filePath, ))
                tagList = list(filter(None, self.sampleDb.fetchone()[0].split(',')))
                if tagList:
                    tags.add(tuple(tagList))
            uncommon = False
            if not tags:
                tags = []
            elif len(tags) == 1:
                tags = list(tags)[0]
            else:
                tags = sorted(set(tag for tagList in tags for tag in tagList))
                uncommon = True
            res = TagsEditorDialog(self, tags, uncommon=uncommon).exec_()
            if not isinstance(res, list):
                return
            for filePath, index in zip(fileList, indexes):
                self.sampleView.model().setData(index, res, TagsRole)
                self.sampleDb.execute('UPDATE samples SET tags=? WHERE filePath=?', (','.join(res), filePath))
            self.reloadTags()
            self.dbConn.commit()
        elif res == removeAllAction:
            if RemoveSamplesDialog(self, exist).exec_():
                fileNames = [i.data(FilePathRole) for i in exist]
                if len(fileNames) < 999:
                    self.sampleDb.execute(
                        'DELETE FROM samples WHERE filePath IN ({})'.format(','.join(['?' for i in fileNames])), 
                        fileNames
                        )
                else:
                    for items in [fileNames[i:i+999] for i in range(0, len(fileNames), 999)]:
                        self.sampleDb.execute(
                            'DELETE FROM samples WHERE filePath IN ({})'.format(','.join(['?' for i in items])), 
                            items
                            )
                self.dbConn.commit()
                if self.sampleView.model() == self.dbProxyModel:
                    for index in sorted(exist, key=lambda index: index.row(), reverse=True):
                        self.dbModel.takeRow(index.row())
                else:
                    self.sampleDbUpdated = True
                self.reloadTags()
                self.dbDirModel.updateTree()

    def addSampleGroupToDb(self, fileIndexes, tags=''):
        for fileIndex in fileIndexes:
            filePath = fileIndex.data(FilePathRole)
            fileName = fileIndex.data()
            info = fileIndex.data(InfoRole)
            self._addSampleToDb(filePath, fileName, info, tags)
        self.dbConn.commit()
        self.reloadTags()
        self.dbDirModel.updateTree()
#        if self.sampleView.model() == self.browseModel:
#            self.sampleDbUpdated = True
#        else:
#            reload query

    def addSampleToDb(self, filePath, fileName=None, info=None, tags='', preview=None):
        self._addSampleToDb(filePath, fileName, info, tags, preview)
        self.dbConn.commit()
        self.reloadTags()
        if self.sampleView.model() == self.browseModel:
            self.sampleDbUpdated = True
        self.dbDirModel.updateTree()
#        else:
#            reload query

    def _addSampleToDb(self, filePath, fileName=None, info=None, tags='', preview=None):
        if not fileName:
            fileName = QtCore.QFile(filePath).fileName()
        if not info:
            soundfile.info(filePath)
        self.sampleDb.execute(
            'INSERT OR REPLACE INTO samples values (?,?,?,?,?,?,?,?,?)', 
            (filePath, fileName, float(info.frames) / info.samplerate, info.format, info.samplerate, info.channels, info.subtype, tags, preview), 
            )

    def browseDb(self, query=None, force=True):
        if query is None:
            if not force and (self.currentDbQuery and not self.sampleDbUpdated):
                if self.currentShownSampleIndex and self.currentShownSampleIndex.model() == self.dbModel:
                    self.sampleView.setCurrentIndex(self.currentShownSampleIndex)
                return
            elif not self.currentDbQuery:
                query = 'SELECT * FROM samples', tuple()
            else:
                query = self.currentDbQuery
        self.currentDbQuery = query
        self.sampleDbUpdated = False
        self.dbModel.clear()
        self.dbModel.setHorizontalHeaderLabels(['Name', 'Path', 'Length', 'Format', 'Rate', 'Ch.', 'Bits', 'Tags', 'Preview'])
        for column, visible in dbColumns.items():
            self.sampleView.horizontalHeader().setSectionHidden(column, not visible)
        for row in self.sampleDb.execute(*query):
            filePath, fileName, length, format, sampleRate, channels, subtype, tags, data = row
            fileItem = QtGui.QStandardItem(fileName)
            fileItem.setData(filePath, FilePathRole)
            dirItem = QtGui.QStandardItem(QtCore.QDir.toNativeSeparators(QtCore.QFileInfo(filePath).absolutePath()))
            fileItem.setIcon(QtGui.QIcon.fromTheme('media-playback-start'))
            lengthItem = QtGui.QStandardItem(timeStr(length, trailingAlways=True))
            lengthItem.setData(length, DataRole)
            formatItem = QtGui.QStandardItem(format)
            formatItem.setData(format, DataRole)
            rateItem = QtGui.QStandardItem(str(sampleRate))
            rateItem.setData(sampleRate, DataRole)
            channelsItem = QtGui.QStandardItem(str(channels))
            channelsItem.setData(channels, DataRole)
            subtypeItem = QtGui.QStandardItem(subtype)
            subtypeItem.setData(subtype, DataRole)
            tagsItem = QtGui.QStandardItem()
            tagsItem.setData(list(filter(None, tags.split(','))), TagsRole)
#            self.dbModel.appendRow([fileItem, lengthItem, formatItem, rateItem, channelsItem, tagsItem])
            self.dbModel.appendRow([fileItem, dirItem, lengthItem, formatItem, rateItem, channelsItem, subtypeItem, tagsItem])
        self.sampleView.resizeColumnsToContents()
        self.sampleView.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.sampleView.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        for c in range(2, subtypeColumn + 1):
            self.sampleView.horizontalHeader().setSectionResizeMode(c, QtWidgets.QHeaderView.Fixed)
        self.sampleView.resizeRowsToContents()

    def editTags(self, index):
        if self.sampleView.model() != self.dbProxyModel or index.column() != tagsColumn:
            return
        fileIndex = index.sibling(index.row(), 0)
        filePath = fileIndex.data(FilePathRole)
        self.sampleDb.execute('SELECT tags FROM samples WHERE filePath=?', (filePath, ))
        tags = list(filter(None, self.sampleDb.fetchone()[0].split(',')))
        res = TagsEditorDialog(self, tags, fileIndex.data()).exec_()
        if not isinstance(res, list):
            return
        self.sampleView.model().setData(index, res, TagsRole)
        self.sampleDb.execute('UPDATE samples SET tags=? WHERE filePath=?', (','.join(res), filePath))
        self.dbConn.commit()
        self.reloadTags()
        self.sampleView.resizeColumnToContents(tagsColumn)

    def saveTagColors(self, index, foregroundColor, backgroundColor):
        root = self.dbTreeProxyModel.index(0, 0)
        tag = index.data()
        parent = index.parent()
        while parent != root:
            tag = '{parent}/{current}'.format(parent=parent.data(), current=tag)
            parent = parent.parent()
        if not foregroundColor and not backgroundColor:
            self.sampleDb.execute(
                'DELETE FROM tagColors WHERE tag=?', 
                (tag, )
                )
            try:
                self.tagColorsDict.pop(tag)
            except:
                pass
        else:
            self.sampleDb.execute(
                'INSERT OR REPLACE INTO tagColors(tag,foreground,background) VALUES (?,?,?)', 
                (tag, foregroundColor.name(), backgroundColor.name())
                )
            self.tagColorsDict[tag] = foregroundColor, backgroundColor
        self.dbConn.commit()
        self.sampleView.viewport().update()

    def tagRenamed(self, newTag, oldTag):
        newTagTree = newTag.split('/')
        oldTagTree = oldTag.split('/')
        for depth, (new, old) in enumerate(zip(newTagTree, oldTagTree), 1):
            if new != old:
                break
        else:
            return
        newTag = '/'.join(newTagTree[:depth])
        oldTag = '/'.join(oldTagTree[:depth])
        self.sampleDb.execute('SELECT filePath,tags FROM samples WHERE tags LIKE ?', ('%{}%'.format(oldTag), ))
        for filePath, tags in self.sampleDb.fetchall():
            tags = tags.split(',')
            newTags = set()
            for tag in tags:
                if tag == oldTag:
                    newTags.add(newTag)
                elif tag.startswith('{}/'.format(oldTag)):
                    newTags.add('{}/{}'.format(newTag, tag[len(oldTag):]))
                else:
                    newTags.add(tag)
            self.sampleDb.execute('UPDATE samples SET tags=? WHERE filePath=?', (','.join(sorted(newTags)), filePath))
            self.dbConn.commit()
            sampleMatch = self.dbModel.match(self.dbModel.index(0, 0), FilePathRole, filePath, flags=QtCore.Qt.MatchExactly)
            if not sampleMatch:
                continue
            fileIndex = sampleMatch[0]
            tagsIndex = fileIndex.sibling(fileIndex.row(), tagsColumn)
            self.dbModel.setData(tagsIndex, sorted(newTags), TagsRole)

    def renameTag(self, index):
        changing = self.dbTreeView.edit(index, self.dbTreeView.AllEditTriggers, QtCore.QEvent(QtCore.QEvent.None_))
        self.dbTreeModel.blockSignals(True)
        if not changing:
            self.dbTreeProxyModel.setData(index, None, TagsRole)
        else:
            self.dbTreeProxyModel.setData(index, index.data(), TagsRole)
        self.dbTreeModel.blockSignals(False)

    def removeTag(self, index):
        index = self.dbTreeProxyModel.mapToSource(index)
        currentTag = self.dbTreeModel.pathFromIndex(index)
        self.sampleDb.execute('SELECT filePath, tags FROM samples WHERE tags LIKE ?', ('%{}%'.format(currentTag), ))
        files = []
        for filePath, tags in self.sampleDb.fetchall():
            tags = set(filter(None, tags.split(',')))
            if currentTag in tags:
                files.append((filePath, tags ^ set((currentTag, ))))
            else:
                for tag in tags:
                    if tag.startswith(currentTag):
                        files.append((filePath, tags ^ set((currentTag, ))))
                        break
        if QtWidgets.QMessageBox.question(
            self, 
            'Remove tag?', 
            'Remove tag "{tag}" {children}from database?{hasFiles}'.format(
                tag=currentTag, 
                children='and its children ' if self.dbTreeModel.hasChildren(index) else '', 
                hasFiles='\nThis action applies to {} files in database (they will not be removed).'.format(len(files)) if files else '', 
                )
            ) == QtWidgets.QMessageBox.Yes:
                for filePath, tags in files:
                    tags = sorted(tags)
                    self.sampleDb.execute('UPDATE samples SET tags=? WHERE filePath=?', (','.join(tags), filePath))
                    match = self.dbModel.match(self.dbModel.index(0, 0), FilePathRole, filePath, flags=QtCore.Qt.MatchExactly)
                    if match:
                        fileIndex = match[0]
                        tagsIndex = fileIndex.sibling(fileIndex.row(), tagsColumn)
                        self.dbModel.setData(tagsIndex, tags, TagsRole)
                self.sampleDb.execute(
                    'DELETE FROM tagColors WHERE tag=?', 
                    (currentTag, )
                    )
                try:
                    self.tagColorsDict.pop(currentTag)
                except:
                    pass
                self.dbConn.commit()
                self.dbTreeModel.itemFromIndex(index.parent()).takeRow(index.row())

    def reloadTags(self):
        self.sampleDb.execute('SELECT tags FROM samples')
        tags = set()
        for tagList in self.sampleDb.fetchall():
            tagList = tagList[0].strip(',').split(',')
            [tags.add(tag.strip().strip('\n')) for tag in tagList]
        self.dbTreeModel.setTags(tags)
        self.dbTreeView.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.dbTreeView.resizeColumnToContents(1)
        self.dbTreeView.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.dbTreeView.header().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)

    
    def dbTreeViewDoubleClicked(self, index):
        if self.dbTreeProxyModel.mapToSource(index) == self.dbTreeModel.index(0, 0):
            self.currentDbQuery = None
            self.browseDb(force=True)
            return
        #TODO this has to be implemented along with browseDb
        self.dbModel.clear()
        self.dbModel.setHorizontalHeaderLabels(['Name', 'Path', 'Length', 'Format', 'Rate', 'Ch.', 'Bits', 'Tags', 'Preview'])
        for column, visible in dbColumns.items():
            self.sampleView.horizontalHeader().setSectionHidden(column, not visible)

        currentTag = index.data()
        current = index
        #TODO: use indexFromPath?
        while True:
            parent = current.parent()
            if not parent.isValid() or parent == self.dbTreeProxyModel.index(0, 0):
                break
            currentTag = '{parent}/{current}'.format(parent=parent.data(), current=currentTag)
            current = parent
        hasChildren = self.dbTreeProxyModel.hasChildren(index)
        self.sampleDb.execute('SELECT * FROM samples WHERE tags LIKE ?', ('%{}%'.format(currentTag), ))
        for row in self.sampleDb.fetchall():
            filePath, fileName, length, format, sampleRate, channels, subtype, tags, data = row
            if hasChildren:
                for tag in tags.split(','):
                    if tag.startswith(currentTag):
                        break
                else:
                    continue
            elif not currentTag in tags:
                continue
            fileItem = QtGui.QStandardItem(fileName)
            fileItem.setData(filePath, FilePathRole)
            fileItem.setIcon(QtGui.QIcon.fromTheme('media-playback-start'))
            dirItem = QtGui.QStandardItem(QtCore.QDir.toNativeSeparators(QtCore.QFileInfo(filePath).absolutePath()))
            lengthItem = QtGui.QStandardItem(timeStr(length, trailingAlways=True))
            lengthItem.setData(length, DataRole)
            formatItem = QtGui.QStandardItem(format)
            formatItem.setData(format, DataRole)
            rateItem = QtGui.QStandardItem(str(sampleRate))
            rateItem.setData(sampleRate, DataRole)
            channelsItem = QtGui.QStandardItem(str(channels))
            channelsItem.setData(channels, DataRole)
            subtypeItem = QtGui.QStandardItem(subtype)
            subtypeItem.setData(subtype, DataRole)
            tagsItem = QtGui.QStandardItem()
            tagsItem.setData(list(filter(None, tags.split(','))), TagsRole)
            self.dbModel.appendRow([fileItem, dirItem, lengthItem, formatItem, rateItem, channelsItem, subtypeItem, tagsItem])
        self.sampleView.resizeColumnsToContents()
        self.sampleView.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.sampleView.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        for c in range(2, subtypeColumn + 1):
            self.sampleView.horizontalHeader().setSectionResizeMode(c, QtWidgets.QHeaderView.Fixed)
        self.sampleView.resizeRowsToContents()

    def dbDirViewSelect(self, index):
        if index.column() != 0:
            index = index.sibling(index.row(), 0)
        self.browseDb(('SELECT * from samples WHERE filePath LIKE ?', ('{}%'.format(index.data(FilePathRole)), )))

    def addSamplesToTag(self, sampleList, newTag):
        for filePath in sampleList:
            self.sampleDb.execute('SELECT tags FROM samples WHERE filePath=?', (filePath, ))
            tags = set(filter(None, self.sampleDb.fetchone()[0].split(',')))
            tags.add(newTag)
            self.sampleDb.execute('UPDATE samples SET tags=? WHERE filePath=?', (','.join(tags), filePath))
            sampleMatch = self.dbModel.match(self.dbModel.index(0, 0), FilePathRole, filePath, flags=QtCore.Qt.MatchExactly)
            if sampleMatch:
                fileIndex = sampleMatch[0]
                tagsIndex = fileIndex.sibling(fileIndex.row(), tagsColumn)
                self.dbModel.setData(tagsIndex, tags, TagsRole)
        self.sampleView.viewport().update()
        self.dbConn.commit()
        self.reloadTags()

    def importSamplesWithTags(self, sampleList, tagIndex):
        for filePath, fileName, info, tags in sampleList:
            self._addSampleToDb(filePath, fileName, info, ','.join(tags))
        self.dbConn.commit()
        self.reloadTags()
        if tagIndex.isValid():
            self.dbTreeViewDoubleClicked(tagIndex)
        self.dbDirModel.updateTree()


    def toggleBrowser(self, index):
        if self.browserStackedLayout.currentIndex() == index:
            return
        self.browserStackedLayout.setCurrentIndex(index)
        self.filterStackedLayout.minimumSize = self.filterStackedLayout.itemAt(index).widget().minimumSizeHint
        self.filterStackedLayout.setCurrentIndex(index)


        if index == 0:
            self.sampleView.setModel(self.browseModel)
            self.browse()
        else:
            self.sampleView.setModel(self.dbProxyModel)
            self.browseDb()
        for column, visible in sampleViewColumns[index].items():
            self.sampleView.horizontalHeader().setSectionHidden(column, not visible)

    def playToggle(self, index):
        if not index.isValid():
            self.player.stop()
            return
        fileIndex = index.sibling(index.row(), 0)
        if self.currentSampleIndex and self.currentSampleIndex == fileIndex and self.player.isPlaying():
            self.player.stop()
        else:
            self.play(index)

    def play(self, index):
        if not index.isValid():
            self.player.stop()
            return
        self.player.stop()
        fileIndex = index.sibling(index.row(), 0)
        self.currentSampleIndex = fileIndex
        #setCurrentWave also loads waveData
        #might want to launch it in a separated thread or something else whenever a database will be added?
        if not self.setCurrentWave(fileIndex):
            #file not available or not readable... do something!
            self.setIndexReadable(fileIndex, False)
            self.audioInfoTabWidget.clear()
            return
        self.setIndexReadable(fileIndex, True)
        fileItem = self.sampleView.model().itemFromIndex(fileIndex)
        info = fileIndex.data(InfoRole)
        waveData = fileItem.data(WaveRole)
        self.waveScene.resetPlayhead(info.samplerate)
        self.player.play(waveData, info)
        fileItem.setIcon(QtGui.QIcon.fromTheme('media-playback-stop'))

    def movePlayhead(self):
#        bytesInBuffer = self.player.output.bufferSize() - self.player.output.bytesFree()
#        usInBuffer = 1000000. * bytesInBuffer / (2 * self.player.sampleSize / 8) / self.player.sampleRate
#        self.waveScene.movePlayhead((self.player.output.processedUSecs() - usInBuffer) / 1000000)
        self.waveScene.movePlayhead(self.player.output.processedUSecs() / 1000000)

    def stopped(self):
        if self.currentSampleIndex:
            model = self.currentSampleIndex.model()
            model.itemFromIndex(self.currentSampleIndex).setData(QtGui.QIcon.fromTheme('media-playback-start'), QtCore.Qt.DecorationRole)
            self.currentSampleIndex = None

    def getWaveData(self, filePath):
        try:
            with soundfile.SoundFile(filePath) as sf:
                waveData = sf.read(always_2d=True, dtype='float32')
            return waveData
        except:
            return False

    def selectTagOnTree(self, tag):
        index = self.dbTreeModel.indexFromPath(tag)
        if index:
            mapIndex = self.dbTreeProxyModel.mapFromSource(index)
            self.dbTreeView.setCurrentIndex(mapIndex)
            self.dbTreeView.scrollTo(index, self.dbTreeView.EnsureVisible)
            self.dbTreeViewDoubleClicked(mapIndex)

    def tagsApplied(self, tagList):
        filePath = self.currentShownSampleIndex.data(FilePathRole)
        self.sampleDb.execute('SELECT * FROM samples WHERE filePath=?', (filePath, ))
        if not self.sampleDb.fetchone():
            return
        self.sampleDb.execute('UPDATE samples SET tags=? WHERE filePath=?', (','.join(tagList), filePath))
        self.dbConn.commit()
        self.reloadTags()
        sampleMatch = self.dbModel.match(self.dbModel.index(0, 0), FilePathRole, filePath, flags=QtCore.Qt.MatchExactly)
        if sampleMatch:
            fileIndex = sampleMatch[0]
            tagsIndex = fileIndex.sibling(fileIndex.row(), tagsColumn)
            self.dbModel.itemFromIndex(tagsIndex).setData(tagList, TagsRole)

    def setCurrentWave(self, index=None):
        if index is None:
            self.waveScene.clear()
            self.audioInfoTabWidget.clear()
        if self.currentShownSampleIndex and self.currentShownSampleIndex == index:
            return True
        fileIndex = index.sibling(index.row(), 0)
        if self.player.isPlaying():
            self.play(fileIndex)
        info = fileIndex.data(InfoRole)
        if not info:
            fileItem = self.sampleView.model().itemFromIndex(fileIndex)
            try:
                info = soundfile.info(fileItem.data(FilePathRole))
                fileItem.setData(info, InfoRole)
            except:
                self.waveScene.clear()
                self.audioInfoTabWidget.clear()
                utils.setItalic(fileItem)
                return False
        if self.sampleView.model() == self.dbProxyModel:
            tags = []
            tagsIndex = index.sibling(index.row(), tagsColumn)
            if tagsIndex.isValid():
                tags = tagsIndex.data(TagsRole)
        else:
            tags = None
        self.audioInfoTabWidget.setInfo(fileIndex.data(), info, tags)

        self.currentShownSampleIndex = fileIndex

        self.drawWave(fileIndex)

        return True

    def drawWave(self, fileIndex):
        waveData = fileIndex.data(WaveRole)
        if waveData is None:
            fileItem = self.sampleView.model().itemFromIndex(fileIndex)
            waveData = self.getWaveData(fileItem.data(FilePathRole))
            if not len(waveData):
                return False
            fileItem.setData(waveData, WaveRole)
        self.waveScene.drawWave(waveData, self.waveView.viewport().rect().width())
        self.waveView.fitInView(self.waveScene.waveRect)

    def resizeEvent(self, event):
        self.waveView.fitInView(self.waveScene.waveRect)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName('jidesk')
    app.setApplicationName('SampleBrowse')

    player = SampleBrowse()
    player.show()
    sys.exit(app.exec_())

#if __name__ == '__main__':
#    main()
