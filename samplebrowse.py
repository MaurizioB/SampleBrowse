#!/usr/bin/env python3
# *-* coding: utf-8 *-*

import sys
import re
import sqlite3
from queue import Queue
from PyQt4 import QtCore, QtGui, QtMultimedia, uic
import soundfile
import numpy as np

availableFormats = tuple(f.lower() for f in soundfile.available_formats().keys())
availableExtensions = tuple('*.' + f for f in availableFormats)

FilePathRole = QtCore.Qt.UserRole + 1
InfoRole = FilePathRole + 1
WaveRole = InfoRole + 1
PreviewRole = WaveRole + 1


class TagsEditorTextBrowser(QtGui.QTextBrowser):
    def setText(self, text):
        tags = []
        for tag in text.split(','):
            tags.append(tag.strip().strip('\n'))
        QtGui.QTextBrowser.setText(self, ','.join(tags))
#        self.setReadOnly(False)

    def tags(self):
        return re.sub(r'\,\,+', ',', self.toPlainText().replace('\n', '').strip(','))


class TagsEditorDialog(QtGui.QDialog):
    def __init__(self, parent, filePath, tags):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle('Edit tags')
        layout = QtGui.QGridLayout()
        self.setLayout(layout)
        layout.addWidget(QtGui.QLabel('Edit tags for sample "{}"'.format(filePath)))
        self.tagsEditor = TagsEditorTextBrowser()
        self.tagsEditor.setText(tags)
        self.tagsEditor.setReadOnly(False)
        layout.addWidget(self.tagsEditor)
        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok|QtGui.QDialogButtonBox.Cancel)
        self.buttonBox.button(self.buttonBox.Ok).clicked.connect(self.accept)
        self.buttonBox.button(self.buttonBox.Cancel).clicked.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def exec_(self):
        res = QtGui.QDialog.exec_(self)
        if res:
            return self.tagsEditor.tags()
        else:
            return res


class TagsModel(QtGui.QStandardItemModel):
    def __init__(self, db, *args, **kwargs):
        QtGui.QStandardItemModel.__init__(self, *args, **kwargs)
        self.db = db

    def setTags(self, tags):
        for tag in tags:
            self.checkAndCreateTags(tag.split('/'), 0)

    def checkAndCreateTags(self, tagTree, depth, parentItem=None):
        if parentItem is None:
            parentItem = self
            parentIndex = self.index(0, 0)
        else:
            parentIndex = self.index(0, 0, parentItem.index())
        childTag = tagTree[depth]
        currentTree = '/'.join(tagTree[:depth+1])
        self.db.execute('SELECT * FROM samples WHERE tags LIKE ?', ('%{}%'.format(currentTree), ))
        count = str(len(self.db.fetchall()))
#        print('/'.join(tagTree[:depth+1]))
        childItemMatch = self.match(parentIndex, QtCore.Qt.DisplayRole, childTag, QtCore.Qt.MatchFixedString)
        if childItemMatch:
            childItem = self.itemFromIndex(childItemMatch[0])
            self.item(childItem.row(), 1).setText(count)
        else:
            childItem = QtGui.QStandardItem(childTag)
            countItem = QtGui.QStandardItem(count)
            parentItem.appendRow([childItem, countItem])
        if len(tagTree[depth:]) > 1:
            self.checkAndCreateTags(tagTree, depth + 1, childItem)


class EllipsisLabel(QtGui.QLabel):
    def __init__(self, *args, **kwargs):
        QtGui.QLabel.__init__(self, *args, **kwargs)
        self._text = self.text()

    def minimumSizeHint(self):
        default = QtGui.QLabel.minimumSizeHint(self)
        return QtCore.QSize(10, default.height())

    def setText(self, text):
        self._text = text
        QtGui.QLabel.setText(self, text)

    def resizeEvent(self, event):
        QtGui.QLabel.setText(self, self.fontMetrics().elidedText(self._text, QtCore.Qt.ElideMiddle, self.width()))


class AlignItemDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, alignment):
        QtGui.QStyledItemDelegate.__init__(self)
        self.alignment = alignment

    def paint(self, painter, option, index):
        option.displayAlignment = self.alignment
        return QtGui.QStyledItemDelegate.paint(self, painter, option, index)


class SampleSortFilterProxyModel(QtGui.QSortFilterProxyModel):
    def itemFromIndex(self, index):
        return self.sourceModel().itemFromIndex(self.mapToSource(index))


class SampleControlDelegate(QtGui.QStyledItemDelegate):
    controlClicked = QtCore.pyqtSignal(object)
    doubleClicked = QtCore.pyqtSignal(object)
    def editorEvent(self, event, model, option, index):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.RightButton:
                pass
            elif event.pos() in option.rect and event.pos().x() < option.rect.height():
                self.controlClicked.emit(index)
        elif event.type() == QtCore.QEvent.MouseButtonDblClick:
            if event.pos().x() > option.rect.height():
                self.controlClicked.emit(index)
        return QtGui.QStyledItemDelegate.editorEvent(self, event, model, option, index)


class WaveScene(QtGui.QGraphicsScene):
    _orange = QtGui.QColor()
    _orange.setNamedColor('orangered')
    waveGrad = QtGui.QLinearGradient(0, -1, 0, 1)
    waveGrad.setSpread(waveGrad.RepeatSpread)
#    waveGrad.setCoordinateMode(waveGrad.ObjectBoundingMode)
    waveGrad.setColorAt(0.0, QtCore.Qt.red)
    waveGrad.setColorAt(.1, _orange)
    waveGrad.setColorAt(.5, QtCore.Qt.darkGreen)
    waveGrad.setColorAt(.9, _orange)
    waveGrad.setColorAt(1, QtCore.Qt.red)
    waveBrush = QtGui.QBrush(waveGrad)

    def __init__(self, *args, **kwargs):
        QtGui.QGraphicsScene.__init__(self, *args, **kwargs)
        self.waveRect = QtCore.QRectF()
        self.wavePen = QtGui.QPen(QtCore.Qt.NoPen)
        self.zeroPen = QtGui.QPen(QtCore.Qt.lightGray)

    def showPlayhead(self):
        self.playhead.show()

    def hidePlayhead(self):
        self.playhead.hide()

    def movePlayhead(self, pos):
        self.playhead.setX(pos)

    def drawWave(self, data, dtype):
        left, right = data
        self.clear()
        self.playhead = self.addLine(-50, -2, -50, 4)
        path = QtGui.QPainterPath()
        pos = 0
        path.moveTo(0, 0)
        for value in left[0]:
            path.lineTo(pos, value)
            pos += 10
        path.lineTo(pos, 0)
        path.moveTo(0, 0)
        pos = 0
        for value in left[1]:
            path.lineTo(pos, value)
            pos += 10
        path.lineTo(pos, 0)
        path.closeSubpath()
        leftPath = self.addPath(path, self.wavePen, self.waveBrush)
        leftLine = self.addLine(0, 0, leftPath.boundingRect().width(), 0, self.zeroPen)
        if not right:
            self.waveRect = QtCore.QRectF(0, -1, leftPath.boundingRect().width(), 2)
            return

        path = QtGui.QPainterPath()
        pos = 0
        path.moveTo(0, 0)
        for value in right[0]:
            path.lineTo(pos, value)
            pos += 10
        path.lineTo(pos, 0)
        path.moveTo(0, 0)
        pos = 0
        for value in right[1]:
            path.lineTo(pos, value)
            pos += 10
        path.lineTo(pos, 0)
        path.closeSubpath()
        path.translate(0, 2)
        rightPath = self.addPath(path, self.wavePen, self.waveBrush)
        rightLine = self.addLine(0, 2, rightPath.boundingRect().width(), 2, self.zeroPen)
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
        path.moveTo(2, 2)
        path.lineTo(6, 8)
        path.lineTo(10, 2)
        qp.drawPath(path)
        del qp
        QtGui.QIcon.__init__(self, pm)


class VerticalDownToggleBtn(QtGui.QToolButton):
    def __init__(self, *args, **kwargs):
        QtGui.QToolButton.__init__(self, *args, **kwargs)
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

    def __init__(self, main, audioDevice=None):
        QtCore.QObject.__init__(self)
        self.main = main

        self.audioDevice = audioDevice if audioDevice else QtMultimedia.QAudioDeviceInfo.defaultOutputDevice()
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
        self.output.setNotifyInterval(50)
        self.output.stateChanged.connect(self.stateChanged)
        self.output.notify.connect(self.notify)
        self.dtype = 'float32' if self.sampleSize >= 32 else 'int16'

        self.audioQueue = Queue()
        self.audioBufferArray = QtCore.QBuffer(self)

    def isPlaying(self):
        return True if self.output.state() == QtMultimedia.QAudio.ActiveState else False

    def stateChanged(self, state):
        if state in (QtMultimedia.QAudio.StoppedState, QtMultimedia.QAudio.IdleState):
            self.stopped.emit()
        elif state == QtMultimedia.QAudio.ActiveState:
            self.started.emit()
        else:
            self.paused.emit()

    def run(self):
        while True:
            res = self.audioQueue.get()
            if res == -1:
                break
            self.output.stop()
            self.audioBufferArray.close()
            self.audioBufferArray.setData(res)
            self.audioBufferArray.open(QtCore.QIODevice.ReadOnly)
            self.audioBufferArray.seek(0)
            self.output.start(self.audioBufferArray)
        self.output.stop()

    def quit(self):
        self.audioQueue.put(-1)

    def stop(self):
        self.output.stop()

    def play(self, array):
        self.audioQueue.put(array)


class SampleBrowse(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        uic.loadUi('main.ui', self)
        self.settings = QtCore.QSettings()
        self.player = Player(self)
        self.player.stopped.connect(self.stopped)
        self.player.output.notify.connect(self.movePlayhead)
        self.playerThread = QtCore.QThread()
        self.player.moveToThread(self.playerThread)
        self.playerThread.started.connect(self.player.run)
        self.sampleSize = self.player.sampleSize
        self.sampleRate = self.player.sampleRate
        self.dtype = self.player.dtype

        self.browseSelectGroup.setId(self.browseSystemBtn, 0)
        self.browseSelectGroup.setId(self.browseDbBtn, 1)
        self.volumeSpin.valueChanged.connect(self.setVolumeSpinColor)
        self.volumeSlider.mousePressEvent = self.volumeSliderMousePressEvent

        self.browserStackedWidget = QtGui.QWidget()
        self.browserStackedLayout = QtGui.QStackedLayout()
        self.browserStackedWidget.setLayout(self.browserStackedLayout)
        self.mainSplitter.insertWidget(0, self.browserStackedWidget)

        self.fsSplitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.browserStackedLayout.addWidget(self.fsSplitter)
        self.fsView = QtGui.QTreeView()
        self.fsView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.fsView.setHeaderHidden(True)
        self.fsSplitter.addWidget(self.fsView)
        self.favouriteWidget = QtGui.QWidget()
        self.fsSplitter.addWidget(self.favouriteWidget)
        favouriteLayout = QtGui.QGridLayout()
        self.favouriteWidget.setLayout(favouriteLayout)
        favouriteHeaderLayout = QtGui.QHBoxLayout()
        favouriteLayout.addLayout(favouriteHeaderLayout, 0, 0)
        favouriteHeaderLayout.addWidget(QtGui.QLabel('Favourites'))
        favouriteHeaderLayout.addStretch()
        self.favouritesToggleBtn = VerticalDownToggleBtn()
        favouriteHeaderLayout.addWidget(self.favouritesToggleBtn)
        favouriteHeaderLayout.addSpacing(5)
        self.favouritesTable = QtGui.QTableView()
        self.favouritesTable.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.favouritesTable.setSelectionBehavior(self.favouritesTable.SelectRows)
        self.favouritesTable.setSortingEnabled(True)
        self.favouritesTable.horizontalHeader().setHighlightSections(False)
        self.favouritesTable.verticalHeader().setVisible(False)
        favouriteLayout.addWidget(self.favouritesTable)
        
        self.fsModel = QtGui.QFileSystemModel()
        self.fsModel.setFilter(QtCore.QDir.AllDirs|QtCore.QDir.NoDotAndDotDot)
        self.fsProxyModel = QtGui.QSortFilterProxyModel()
        self.fsProxyModel.setSourceModel(self.fsModel)
        self.fsView.setModel(self.fsProxyModel)
        for c in range(1, self.fsModel.columnCount()):
            self.fsView.hideColumn(c)
        self.fsModel.setRootPath(QtCore.QDir.currentPath())
        self.fsModel.directoryLoaded.connect(self.cleanFolders)
        self.fsView.sortByColumn(0, QtCore.Qt.AscendingOrder)
#        self.fsView.setRootIndex(self.fsModel.index(QtCore.QDir.currentPath()))
        self.fsView.setCurrentIndex(self.fsProxyModel.mapFromSource(self.fsModel.index(QtCore.QDir.currentPath())))
        self.fsView.doubleClicked.connect(self.dirChanged)
        self.fsView.customContextMenuRequested.connect(self.fsViewContextMenu)

        self.favouritesModel = QtGui.QStandardItemModel()
        self.favouritesModel.setHorizontalHeaderLabels(['Name', 'Path'])
        self.favouritesTable.setModel(self.favouritesModel)
        self.favouritesTable.mousePressEvent = self.favouritesTableMousePressEvent
        self.favouritesTable.horizontalHeader().setStretchLastSection(True)
        self.loadFavourites()
        self.favouritesModel.dataChanged.connect(self.favouritesDataChanged)
        self.favouritesToggleBtn.clicked.connect(self.favouritesToggle)

        self.loadDb()

        self.dbWidget = QtGui.QWidget()
        dbLayout = QtGui.QGridLayout()
        self.dbWidget.setLayout(dbLayout)
        self.dbTreeView = QtGui.QTreeView()
        self.dbTreeView.setEditTriggers(self.dbTreeView.NoEditTriggers)
        self.dbTreeView.header().setStretchLastSection(False)
        self.dbTreeView.setHeaderHidden(True)
        self.dbTreeModel = TagsModel(self.sampleDb)
        self.dbTreeProxyModel = QtGui.QSortFilterProxyModel()
        self.dbTreeProxyModel.setSourceModel(self.dbTreeModel)
        self.dbTreeView.setModel(self.dbTreeProxyModel)
        self.dbTreeView.doubleClicked.connect(self.dbTreeViewDoubleClicked)
        dbLayout.addWidget(self.dbTreeView)
        self.browserStackedLayout.addWidget(self.dbWidget)

        self.browseSelectGroup.buttonClicked[int].connect(self.toggleBrowser)
        self.browseModel = QtGui.QStandardItemModel()
        self.dbModel = QtGui.QStandardItemModel()
        self.dbProxyModel = SampleSortFilterProxyModel()
        self.dbProxyModel.setSourceModel(self.dbModel)
        self.sampleView.setModel(self.browseModel)
        self.alignRightDelegate = AlignItemDelegate(QtCore.Qt.AlignVCenter|QtCore.Qt.AlignRight)
        self.alignCenterDelegate = AlignItemDelegate(QtCore.Qt.AlignCenter)
        self.sampleView.setItemDelegateForColumn(1, self.alignRightDelegate)
        for c in range(2, 5):
            self.sampleView.setItemDelegateForColumn(c, self.alignCenterDelegate)
        self.sampleControlDelegate = SampleControlDelegate()
        self.sampleControlDelegate.controlClicked.connect(self.playToggle)
        self.sampleControlDelegate.doubleClicked.connect(self.play)
#        self.sampleControlDelegate.contextMenuRequested.connect(self.sampleContextMenu)
        self.sampleView.clicked.connect(self.setCurrentWave)
        self.sampleView.doubleClicked.connect(self.editTags)
        self.sampleView.setItemDelegateForColumn(0, self.sampleControlDelegate)
        self.sampleView.keyPressEvent = self.sampleViewKeyPressEvent
        self.sampleView.customContextMenuRequested.connect(self.sampleContextMenu)

        self.waveScene = WaveScene()
        self.waveView.setScene(self.waveScene)
        self.player.stopped.connect(self.waveScene.hidePlayhead)
        self.player.started.connect(self.waveScene.showPlayhead)

        self.filterStackedLayout = QtGui.QStackedLayout()
        self.filterStackedWidget.setLayout(self.filterStackedLayout)
        self.browsePathLbl = EllipsisLabel()
        self.filterStackedLayout.addWidget(self.browsePathLbl)
        self.filterWidget = QtGui.QWidget()
        self.filterWidget.setContentsMargins(0, 0, 0, 0)
        self.filterStackedLayout.addWidget(self.filterWidget)
        filterLayout = QtGui.QHBoxLayout()
        filterLayout.setContentsMargins(0, 0, 0, 0)
        self.filterWidget.setLayout(filterLayout)
        filterLayout.addWidget(QtGui.QLabel('Search'))
        self.searchEdit = QtGui.QLineEdit()
        self.searchEdit.textChanged.connect(self.searchDb)
        filterLayout.addWidget(self.searchEdit)

        self.currentSampleIndex = None
        self.currentShownSampleIndex = None
        self.currentBrowseDir = None
        self.currentDbQuery = None
        self.sampleDbUpdated = False

        self.browse()
        self.mainSplitter.setStretchFactor(0, 10)
        self.mainSplitter.setStretchFactor(1, 15)
        self.fsSplitter.setStretchFactor(0, 50)
        self.fsSplitter.setStretchFactor(1, 1)

        self.infoTabWidget.setTabEnabled(1, False)
        self.shown = False
        self.playerThread.start()
        self.reloadTags()

    def loadDb(self):
        dataDir = QtCore.QDir(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation))
        dbFile = QtCore.QFile(dataDir.filePath('sample.sqlite'))
        if not dbFile.exists():
            if not dataDir.exists():
                dataDir.mkpath(dataDir.absolutePath())
        self.dbConn = sqlite3.connect(dbFile.fileName())
        self.sampleDb = self.dbConn.cursor()
        try:
            self.sampleDb.execute('create table samples(filePath varchar primary key, fileName varchar, length float, format varchar, sampleRate int, channels int, tags varchar, preview blob)')
        except:
            pass
#        for x in range(8):
#            self.sampleDb.execute('insert into samples values("asdf{}", 5232, "gnang gneoir")'.format(x))
#        print([row for row in self.sampleDb.execute('SELECT * FROM samples')])
        self.dbConn.commit()

    def showEvent(self, event):
        if not self.shown:
            QtCore.QTimer.singleShot(
                1000, 
                lambda: self.fsView.scrollTo(
                    self.fsProxyModel.mapFromSource(self.fsModel.index(QtCore.QDir.currentPath())), self.fsView.PositionAtTop
                    )
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
            QtGui.QTableView.keyPressEvent(self.sampleView, event)

    def cleanFolders(self, path):
        index = self.fsModel.index(path)
        for row in range(self.fsModel.rowCount(index)):
            self.fsModel.fetchMore(index.sibling(row, 0))
        self.fsModel.fetchMore(self.fsModel.index(path))

    def fsViewContextMenu(self, pos):
        dirIndex = self.fsView.indexAt(pos)
        dirPath = self.fsModel.filePath(self.fsProxyModel.mapToSource(dirIndex))

        menu = QtGui.QMenu()
        addDirAction = QtGui.QAction('Add "{}" to favourites'.format(dirIndex.data()), menu)
        for row in range(self.favouritesModel.rowCount()):
            dirPathItem = self.favouritesModel.item(row, 1)
            if dirPathItem.text() == dirPath:
                addDirAction.setEnabled(False)
                break

        menu.addAction(addDirAction)
        res = menu.exec_(self.fsView.mapToGlobal(pos))
        if res == addDirAction:
            dirLabelItem = QtGui.QStandardItem(dirIndex.data())
            dirPathItem = QtGui.QStandardItem(dirPath)
            dirPathItem.setFlags(dirPathItem.flags() ^ QtCore.Qt.ItemIsEditable)
            self.favouritesModel.dataChanged.disconnect(self.favouritesDataChanged)
            self.favouritesModel.appendRow([dirLabelItem, dirPathItem])
            self.favouritesModel.dataChanged.connect(self.favouritesDataChanged)
            self.settings.beginGroup('Favourites')
            self.settings.setValue(dirIndex.data(), dirPath)
            self.settings.endGroup()

    def favouritesDataChanged(self, index, _):
        dirPathIndex = index.sibling(index.row(), 1)
        dirLabel = index.sibling(index.row(), 0).data()
        dirPath = dirPathIndex.data()
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
            dirPathItem = QtGui.QStandardItem(self.settings.value(fav))
            dirPathItem.setFlags(dirPathItem.flags() ^ QtCore.Qt.ItemIsEditable)
            self.favouritesModel.appendRow([dirLabelItem, dirPathItem])
        self.settings.endGroup()

    def browseFromFavourites(self, index):
        if not index.isValid():
            return
        dirPathIndex = index.sibling(index.row(), 1)
        self.browse(dirPathIndex.data())

    def favouritesTableMousePressEvent(self, event):
        index = self.favouritesTable.indexAt(event.pos())
        if event.button() != QtCore.Qt.RightButton:
            self.browseFromFavourites(index)
            return QtGui.QTableView.mousePressEvent(self.favouritesTable, event)
        if not index.isValid():
            return
        QtGui.QTableView.mousePressEvent(self.favouritesTable, event)
        dirPathIndex = index.sibling(index.row(), 1)
        dirPath = dirPathIndex.data()
        menu = QtGui.QMenu()
        scrollToAction = QtGui.QAction('Show directory in tree', menu)
        removeAction = QtGui.QAction('Remove from favourites', menu)
        menu.addActions([scrollToAction, removeAction])
        res = menu.exec_(self.favouritesTable.viewport().mapToGlobal(event.pos()))
        if res == scrollToAction:
            self.fsView.setCurrentIndex(self.fsProxyModel.mapFromSource(self.fsModel.index(dirPath)))
            self.fsView.scrollTo(
                self.fsProxyModel.mapFromSource(self.fsModel.index(dirPath)), self.fsView.PositionAtTop
                )
        elif res == removeAction:
            self.settings.beginGroup('Favourites')
            for fav in self.settings.childKeys():
                if self.settings.value(fav) == dirPath:
                    self.settings.remove(fav)
                    break
            self.favouritesModel.takeRow(index.row())
            self.settings.endGroup()

    def favouritesToggle(self):
        visible = self.favouritesTable.isVisible()
        self.favouritesTable.setVisible(not visible)
        self.favouritesToggleBtn.toggle(not visible)

    def dirChanged(self, index):
        self.browse(self.fsModel.filePath(self.fsProxyModel.mapToSource(index)))

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
        self.browseModel.setHorizontalHeaderLabels(['Name', 'Length', 'Format', 'Rate', 'Ch.'])
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
            lengthItem = QtGui.QStandardItem('{:.3f}'.format(float(info.frames) / info.samplerate))
            formatItem = QtGui.QStandardItem(info.format)
            rateItem = QtGui.QStandardItem(str(info.samplerate))
            channelsItem = QtGui.QStandardItem(str(info.channels))
            self.browseModel.appendRow([fileItem, lengthItem, formatItem, rateItem, channelsItem])
        self.sampleView.resizeColumnsToContents()
        self.sampleView.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        for c in range(1, 5):
            self.sampleView.horizontalHeader().setResizeMode(c, QtGui.QHeaderView.Fixed)
        self.sampleView.resizeRowsToContents()
        self.browsePathLbl.setText(path.absolutePath())

    def volumeSliderMousePressEvent(self, event):
        if event.button() == QtCore.Qt.MidButton:
            self.volumeSpin.setValue(100)
        else:
            QtGui.QSlider.mousePressEvent(self.volumeSlider, event)

    def setVolumeSpinColor(self, value):
        palette = self.volumeSpin.palette()
        if value > 100:
            palette.setColor(palette.Text, QtCore.Qt.red)
        else:
            palette.setColor(palette.Text, QtGui.QPalette().color(palette.Active, palette.Text))
        self.volumeSpin.setPalette(palette)

    def sampleContextMenu(self, pos):
        selIndex = self.sampleView.indexAt(pos)
        if not selIndex.isValid():
            return
        fileIndex = selIndex.sibling(selIndex.row(), 0)
        fileName = fileIndex.data()
        menu = QtGui.QMenu()
        addToDatabaseAction = QtGui.QAction('Add "{}" to database'.format(fileName), menu)
        delFromDatabaseAction = QtGui.QAction('Remove "{}" from database'.format(fileName), menu)
        if self.sampleView.model() == self.browseModel:
            menu.addAction(addToDatabaseAction)
        else:
            menu.addAction(delFromDatabaseAction)
        res = menu.exec_(self.sampleView.viewport().mapToGlobal(pos))
        if res == addToDatabaseAction:
            filePath = fileIndex.data(FilePathRole)
            info = fileIndex.data(InfoRole)
            #fileName varchar primary key, path varchar, length float, format varchar, sampleRate int, channels int, tags varchar, preview blob
            self.sampleDb.execute(
                'insert into samples values (?,?,?,?,?,?,?,?)', 
                (filePath, fileName, float(info.frames) / info.samplerate, info.format, info.samplerate, info.channels, '', None), 
                )
            self.sampleDbUpdated = True
            self.dbConn.commit()
        elif res == delFromDatabaseAction:
            filePath = fileIndex.data(FilePathRole)
            self.sampleDb.execute(
                'DELETE FROM samples WHERE filePath=?', 
                (filePath, )
                )
            self.sampleDbUpdated = True
            self.dbConn.commit()
            self.reloadTags()
            self.dbModel.takeRow(selIndex.row())

    def browseDb(self, query=None):
        if query is None:
            if self.currentDbQuery and not self.sampleDbUpdated:
                if self.currentShownSampleIndex and self.currentShownSampleIndex.model() == self.dbModel:
                    self.sampleView.setCurrentIndex(self.currentShownSampleIndex)
                return
            else:
                query = 'SELECT * FROM samples'
        self.currentDbQuery = query
        self.sampleDbUpdated = False
        self.dbModel.clear()
        self.dbModel.setHorizontalHeaderLabels(['Name', 'Length', 'Format', 'Rate', 'Ch.', 'Tags'])
        for row in self.sampleDb.execute(query):
            filePath, fileName, length, format, sampleRate, channels, tags, data = row
            fileItem = QtGui.QStandardItem(fileName)
            fileItem.setData(filePath, FilePathRole)
            fileItem.setIcon(QtGui.QIcon.fromTheme('media-playback-start'))
            lengthItem = QtGui.QStandardItem('{:.3f}'.format(length))
            formatItem = QtGui.QStandardItem(format)
            rateItem = QtGui.QStandardItem(str(sampleRate))
            channelsItem = QtGui.QStandardItem(str(channels))
            tagsItem = QtGui.QStandardItem(tags)
            self.dbModel.appendRow([fileItem, lengthItem, formatItem, rateItem, channelsItem, tagsItem])
        self.sampleView.resizeColumnsToContents()
        self.sampleView.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        for c in range(1, 5):
            self.sampleView.horizontalHeader().setResizeMode(c, QtGui.QHeaderView.Fixed)
        self.sampleView.resizeRowsToContents()

    def searchDb(self, text):
        self.dbProxyModel.setFilterRegExp(text)

    def editTags(self, index):
        if self.sampleView.model() != self.dbProxyModel or index.column() != 5:
            return
        filePath = index.sibling(index.row(), 0).data(FilePathRole)
        self.sampleDb.execute('SELECT tags FROM samples WHERE filePath=?', (filePath, ))
        tags = self.sampleDb.fetchone()[0]
        res = TagsEditorDialog(self, filePath, tags).exec_()
        if not res:
            return
        tagsItem = self.sampleView.model().itemFromIndex(index)
        tagsItem.setText(res)
        self.sampleDb.execute('UPDATE samples SET tags=? WHERE filePath=?', (res, filePath))
        self.dbConn.commit()
        self.reloadTags()

    def reloadTags(self):
        self.sampleDb.execute('SELECT tags FROM samples')
        tags = set()
        for taglist in self.sampleDb.fetchall():
            taglist = taglist[0].strip(',').split(',')
            [tags.add(tag.strip().strip('\n')) for tag in taglist]
        self.dbTreeModel.setTags(tags)
        self.dbTreeView.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.dbTreeView.resizeColumnToContents(1)
        self.dbTreeView.header().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.dbTreeView.header().setResizeMode(1, QtGui.QHeaderView.Fixed)

    def dbTreeViewDoubleClicked(self, index):
        #TODO this has to be implemented along with browseDb
        self.dbModel.clear()
        self.dbModel.setHorizontalHeaderLabels(['Name', 'Length', 'Format', 'Rate', 'Ch.', 'Tags'])
        tag = index.data()
        current = index
        while True:
            parent = current.parent()
            if not parent.isValid():
                break
            tag = '{parent}/{current}'.format(parent=parent.data(), current=tag)
            current = parent
        self.sampleDb.execute('SELECT * FROM samples WHERE tags LIKE ?', ('%{}%'.format(tag), ))
        for row in self.sampleDb.fetchall():
            filePath, fileName, length, format, sampleRate, channels, tags, data = row
            if not tag in tags.split(','):
                continue
            fileItem = QtGui.QStandardItem(fileName)
            fileItem.setData(filePath, FilePathRole)
            fileItem.setIcon(QtGui.QIcon.fromTheme('media-playback-start'))
            lengthItem = QtGui.QStandardItem('{:.3f}'.format(length))
            formatItem = QtGui.QStandardItem(format)
            rateItem = QtGui.QStandardItem(str(sampleRate))
            channelsItem = QtGui.QStandardItem(str(channels))
            tagsItem = QtGui.QStandardItem(tags)
            self.dbModel.appendRow([fileItem, lengthItem, formatItem, rateItem, channelsItem, tagsItem])
        self.sampleView.resizeColumnsToContents()
        self.sampleView.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        for c in range(1, 5):
            self.sampleView.horizontalHeader().setResizeMode(c, QtGui.QHeaderView.Fixed)
        self.sampleView.resizeRowsToContents()

    def toggleBrowser(self, index):
        self.browserStackedLayout.setCurrentIndex(index)
        self.filterStackedLayout.setCurrentIndex(index)
        if index == 0:
            self.sampleView.setModel(self.browseModel)
            self.browse()
        else:
            self.sampleView.setModel(self.dbProxyModel)
            self.browseDb()

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
        self.setCurrentWave(fileIndex)
        fileItem = self.sampleView.model().itemFromIndex(fileIndex)
        info = fileIndex.data(InfoRole)
        waveData = fileItem.data(WaveRole)
        if info.channels == 1:
            waveData = waveData.repeat(2, axis=1)/2
        waveData = waveData * self.volumeSpin.value()/100.
        self.waveScene.movePlayhead(0)
        self.player.play(waveData.tostring())
        fileItem.setIcon(QtGui.QIcon.fromTheme('media-playback-stop'))

    def movePlayhead(self):
#        bytesInBuffer = self.output.bufferSize() - self.output.bytesFree()
#        usInBuffer = 1000000. * bytesInBuffer / (2 * self.sampleSize / 8) / self.sampleRate
#        self.waveScene.movePlayhead((self.output.processedUSecs() - usInBuffer) / 200)
        self.waveScene.movePlayhead(self.waveScene.playhead.x() + self.sampleRate / 200.)

    def stopped(self):
        if self.currentSampleIndex:
            model = self.currentSampleIndex.model()
            model.itemFromIndex(self.currentSampleIndex).setData(QtGui.QIcon.fromTheme('media-playback-start'), QtCore.Qt.DecorationRole)
            self.currentSampleIndex = None
#            self.waveScene.movePlayhead(-50)

    def getWaveData(self, filePath):
        with soundfile.SoundFile(filePath) as sf:
            waveData = sf.read(always_2d=True, dtype=self.dtype)
        return waveData

    def setCurrentWave(self, index=None):
        self.infoTab.setEnabled(True)
        self.infoTabWidget.setTabEnabled(1, True if self.sampleView.model() == self.dbProxyModel else False)
        if index is None:
            self.waveScene.clear()
        if self.currentShownSampleIndex and self.currentShownSampleIndex == index:
            return
        fileIndex = index.sibling(index.row(), 0)
        if self.player.isPlaying():
            self.play(fileIndex)
        info = fileIndex.data(InfoRole)
        if not info:
            fileItem = self.sampleView.model().itemFromIndex(fileIndex)
            info = soundfile.info(fileItem.data(FilePathRole))
            fileItem.setData(info, InfoRole)
        self.infoFileNameLbl.setText(fileIndex.data())
        self.infoLengthLbl.setText('{:.3f}'.format(float(info.frames) / info.samplerate))
        self.infoFormatLbl.setText(info.format)
        self.infoSampleRateLbl.setText(str(info.samplerate))
        self.infoChannelsLbl.setText(str(info.channels))

        tagsIndex = index.sibling(index.row(), 5)
        if tagsIndex.isValid():
            self.tagsEdit.setText(tagsIndex.data())

        previewData = fileIndex.data(PreviewRole)
        if not previewData:
            waveData = fileIndex.data(WaveRole)
            if waveData is None:
                fileItem = self.sampleView.model().itemFromIndex(fileIndex)
                waveData = self.getWaveData(fileItem.data(FilePathRole))
                fileItem.setData(waveData, WaveRole)
            ratio = 100
            if info.channels > 1:
                left = waveData[:, 0]
                leftMin = np.amin(np.pad(left, (0, ratio - left.size % ratio), mode='constant', constant_values=0).reshape(-1, ratio), axis=1)
                leftMax = np.amax(np.pad(left, (0, ratio - left.size % ratio), mode='constant', constant_values=0).reshape(-1, ratio), axis=1)
                right = waveData[:, 1]
                rightMin = np.amin(np.pad(right, (0, ratio - right.size % ratio), mode='constant', constant_values=0).reshape(-1, ratio), axis=1)
                rightMax = np.amax(np.pad(right, (0, ratio - right.size % ratio), mode='constant', constant_values=0).reshape(-1, ratio), axis=1)
                rightData = rightMax, rightMin
            else:
                leftMin = np.amin(np.pad(waveData, (0, ratio - waveData.size % ratio), mode='constant', constant_values=0).reshape(-1, ratio), axis=1)
                leftMax = np.amax(np.pad(waveData, (0, ratio - waveData.size % ratio), mode='constant', constant_values=0).reshape(-1, ratio), axis=1)
                rightData = None
            leftData = leftMax, leftMin
            previewData = leftData, rightData
            fileItem.setData(previewData, PreviewRole)
        self.waveScene.drawWave(previewData, self.dtype)
        self.waveView.fitInView(self.waveScene.waveRect)
        self.currentShownSampleIndex = fileIndex

    def resizeEvent(self, event):
        self.waveView.fitInView(self.waveScene.waveRect)


def main():
    app = QtGui.QApplication(sys.argv)
    app.setOrganizationName('jidesk')
    app.setApplicationName('SampleBrowse')

    player = SampleBrowse()
    player.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
