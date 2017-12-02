#!/usr/bin/env python3
# *-* coding: utf-8 *-*

import sys
import re
import sqlite3
from threading import Event
from queue import Queue
from PyQt4 import QtCore, QtGui, QtMultimedia, uic
import soundfile
import numpy as np

availableFormats = tuple(f.lower() for f in soundfile.available_formats().keys())
availableExtensions = tuple('*.' + f for f in availableFormats)

fileNameColumn, dirColumn, lengthColumn, formatColumn, rateColumn, channelsColumn, tagsColumn, previewColumn = range(8)
_allColumns = fileNameColumn, dirColumn, lengthColumn, formatColumn, rateColumn, channelsColumn, tagsColumn, previewColumn
_visibleColumns = fileNameColumn, lengthColumn, formatColumn, rateColumn, channelsColumn
_commonColumns = {c: True if c in _visibleColumns else False for c in _allColumns}
browseColumns = _commonColumns.copy()
dbColumns = _commonColumns.copy()
dbColumns.update({
    dirColumn: True, 
    tagsColumn: True, 
#    previewColumn: True;
    })
sampleViewColumns = browseColumns, dbColumns

FormatRole = QtCore.Qt.UserRole + 1
HoverRole = QtCore.Qt.UserRole + 1
FilePathRole = QtCore.Qt.UserRole + 1
InfoRole = FilePathRole + 1
WaveRole = InfoRole + 1
TagsRole = WaveRole + 1
PreviewRole = TagsRole + 1


class TagsEditorTextEdit(QtGui.QTextEdit):
    tagsApplied = QtCore.pyqtSignal(object)
    def __init__(self, *args, **kwargs):
        QtGui.QTextEdit.__init__(self, *args, **kwargs)
        self.document().setDefaultStyleSheet('''
            span {
                background-color: rgba(200,200,200,150);
            }
            span.sep {
                color: transparent;
                background-color: transparent;
                }
            ''')
        self.textChanged.connect(self.checkText)
        self.applyBtn = QtGui.QPushButton('Apply', self)
        self.applyBtn.setMaximumSize(self.applyBtn.fontMetrics().width('Apply') + 4, self.applyBtn.fontMetrics().height() + 2)
        self.applyBtn.setVisible(False)
        self.applyBtn.clicked.connect(self.applyTags)
        self.applyMode = False
        self._tagList = ''
        self.viewport().setCursor(QtCore.Qt.IBeamCursor)

    def keyPressEvent(self, event):
        if not self.applyMode:
            if event.key() == QtCore.Qt.Key_Tab:
                event.ignore()
                return
            return QtGui.QTextEdit.keyPressEvent(self, event)
        else:
            if event.key() == QtCore.Qt.Key_Escape:
                self.textChanged.disconnect(self.checkText)
                self._setTags(self._tagList)
                cursor = self.textCursor()
                cursor.movePosition(cursor.End)
                self.setTextCursor(cursor)
                self.textChanged.connect(self.checkText)
            elif event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
                self.clearFocus()
                self.applyTags()
            else:
                return QtGui.QTextEdit.keyPressEvent(self, event)

    def applyTags(self):
        self.checkText()
        self._tagList = self.toPlainText()
        self.tagsApplied.emit(self.tags())

    def checkText(self):
        pos = self.textCursor().position()
        self.textChanged.disconnect(self.checkText)
        if pos == 1 and self.toPlainText().startswith(','):
            pos = 0
        self._setTags(re.sub(r'\/,', ',', re.sub(r'[\n\t]+', ',', self.toPlainText())))
        self.textChanged.connect(self.checkText)
        cursor = self.textCursor()
        if len(self.toPlainText()) < pos:
            pos = len(self.toPlainText())
        cursor.setPosition(pos)
        self.setTextCursor(cursor)

    def _setTags(self, tagList):
        tagList = re.sub(r'\,\,+', ',', tagList.lstrip(','))
        tags = []
        for tag in tagList.split(','):
            tags.append(tag.lstrip().lstrip('/').strip('\n'))
        QtGui.QTextEdit.setHtml(self, '<span>{}</span>'.format('</span><span class="sep">,</span><span>'.join(tags)))

    def setTags(self, tagList):
        self._tagList = [tag for tag in tagList if tag is not None]
        self._setTags(','.join(self._tagList))
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        self.setTextCursor(cursor)

    def tags(self):
        tags = re.sub(r'\,\,+', ',', self.toPlainText()).replace('\n', ',').strip(',').split(',')
        tags = set(tag.strip('/') for tag in tags)
        return sorted(tags) if tags else []

    def enterEvent(self, event):
        if not self.applyMode:
            return
        self.applyBtn.setVisible(True)
        self.moveApplyBtn()

    def moveApplyBtn(self):
        self.applyBtn.move(self.width() - self.applyBtn.width() - 2, self.height() - self.applyBtn.height() - 2)

    def leaveEvent(self, event):
        self.applyBtn.setVisible(False)

    def resizeEvent(self, event):
        QtGui.QTextEdit.resizeEvent(self, event)
        self.moveApplyBtn()


class ImportDialog(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        uic.loadUi('importdialog.ui', self)
        self.sampleModel = QtGui.QStandardItemModel()
        self.sampleProxyModel = SampleSortFilterProxyModel()
        self.sampleProxyModel.setSourceModel(self.sampleModel)
        self.sampleView.setModel(self.sampleProxyModel)
        self.sampleModel.setHorizontalHeaderLabels(['Name', 'Path', 'Length', 'Format', 'Rate', 'Ch.', 'Tags'])


class Crawler(QtCore.QObject):
    currentBrowseDir = QtCore.pyqtSignal(str)
    found = QtCore.pyqtSignal(object, object)
    done = QtCore.pyqtSignal()
    def __init__(self, dirPath, scanMode, formats, sampleRates, channels):
        QtCore.QObject.__init__(self)
        self.stop = Event()
        self.dirPath = dirPath
        self.scanMode = scanMode
        self.formats = formats
        self.sampleRates = sampleRates
        self.channels = channels
        self.methodList = []

        if isinstance(sampleRates, (list, tuple)):
            self.methodList.append(self.checkSampleRate)
        if channels:
            self.methodList.append(self.checkChannels)

        if scanMode:
            if not isinstance(formats, (list, tuple)):
                formats = [f for f in soundfile.available_formats().keys()]
            self.iterator = QtCore.QDirIterator(
                dirPath, ['*.{}'.format(f) for f in formats], QtCore.QDir.Files, flags=QtCore.QDirIterator.Subdirectories|QtCore.QDirIterator.FollowSymlinks)
#            self.run = self.runByExtension
        else:
            if isinstance(formats, (list, tuple)):
                self.methodList.insert(0, self.checkFormat)
            self.iterator = QtCore.QDirIterator(
                dirPath, QtCore.QDir.Files, flags=QtCore.QDirIterator.Subdirectories|QtCore.QDirIterator.FollowSymlinks)
#            self.run = self.runByAll

    def checkFormat(self, info):
        return info.format in self.formats

    def checkSampleRate(self, info):
        return info.samplerate in self.sampleRates

    def checkChannels(self, info):
        return info.channels == self.channels

    def run(self):
        while self.iterator.hasNext() and not self.stop.is_set():
            filePath = self.iterator.next()
            self.currentBrowseDir.emit(self.iterator.filePath())
            try:
                info = soundfile.info(filePath)
                for method in self.methodList:
                    if not method(info):
                        break
                else:
                    self.found.emit(self.iterator.fileInfo(), info)
            except:
                pass
        self.done.emit()

#    def runByAll(self):
#        while self.iterator.hasNext() and not self.stop.is_set():
#            fileInfo = self.iterator.fileInfo()
#            if fileInfo.suffix().upper() in self.forma
#            filePath = self.iterator.next()


class ImportDialogScan(ImportDialog):
    def __init__(self, parent, dirPath, scanMode, formats, sampleRates, channels):
        ImportDialog.__init__(self, parent)
        self.elidedItemDelegate = AlignItemDelegate(QtCore.Qt.AlignLeft, QtCore.Qt.ElideMiddle)
        self.sampleView.setItemDelegateForColumn(1, self.elidedItemDelegate)
        self.alignCenterDelegate = AlignItemDelegate(QtCore.Qt.AlignCenter)
        for c in range(2, channelsColumn + 1):
            self.sampleView.setItemDelegateForColumn(c, self.alignCenterDelegate)
        self.tagListDelegate = TagListDelegate(self.parent().tagColorsDict)
        self.sampleView.setItemDelegateForColumn(tagsColumn, self.tagListDelegate)
        self.sampleView.setMouseTracking(True)

        fontMetrics = QtGui.QFontMetrics(self.font())

        self.sampleView.horizontalHeader().setResizeMode(fileNameColumn, QtGui.QHeaderView.Stretch)
        self.sampleView.horizontalHeader().setResizeMode(dirColumn, QtGui.QHeaderView.Stretch)
        self.sampleView.horizontalHeader().resizeSection(lengthColumn, fontMetrics.width('888.888') + 10)
        self.sampleView.horizontalHeader().setResizeMode(lengthColumn, QtGui.QHeaderView.Fixed)
        self.sampleView.horizontalHeader().resizeSection(formatColumn, fontMetrics.width('Format') + 10)
        self.sampleView.horizontalHeader().setResizeMode(formatColumn, QtGui.QHeaderView.Fixed)
        self.sampleView.horizontalHeader().resizeSection(rateColumn, fontMetrics.width('192000') + 10)
        self.sampleView.horizontalHeader().setResizeMode(rateColumn, QtGui.QHeaderView.Fixed)
        self.sampleView.horizontalHeader().resizeSection(channelsColumn, fontMetrics.width('Ch.') + 10)
        self.sampleView.horizontalHeader().setResizeMode(channelsColumn, QtGui.QHeaderView.Fixed)

        self.crawler = Crawler(dirPath, scanMode, formats, sampleRates, channels)
        self.crawlerThread = QtCore.QThread()
        self.crawler.moveToThread(self.crawlerThread)
        self.crawlerThread.started.connect(self.crawler.run)
        self.popup = QtGui.QMessageBox(QtGui.QMessageBox.Information, 'Scanning...', 'Scanning disk, please wait.', QtGui.QMessageBox.Cancel, self)
        self.popup.setModal(True)
        self.popup.rejected.connect(lambda: self.crawler.stop.set())
        self.crawler.found.connect(self.found)
        self.crawler.done.connect(self.popup.close)
        self.crawler.done.connect(self.scanDone)

        self.selectAllBtn.clicked.connect(self.sampleView.selectAll)
        self.checkSelectedBtn.clicked.connect(lambda: self.setSelectedCheckState(QtCore.Qt.Checked))
        self.uncheckSelectedBtn.clicked.connect(lambda: self.setSelectedCheckState(QtCore.Qt.Unchecked))
        self.sampleProxyModel.dataChanged.connect(self.checkChecked)
        self.sampleView.selectionModel().selectionChanged.connect(
            lambda *args: self.editTagsBtn.setEnabled(len(self.sampleView.selectionModel().selection().indexes())))
        self.editTagsBtn.clicked.connect(self.editTags)
        self.sampleView.customContextMenuRequested.connect(self.sampleContextMenu)

    def editTags(self):
        indexes = []
        tags = set()
        for index in self.sampleView.selectedIndexes():
            if index.column() == tagsColumn:
                indexes.append(index)
                tagList = index.data(TagsRole)
                if tagList:
                    tags.add(tuple(tagList))
        if not indexes:
            return
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
        for index in indexes:
            self.sampleProxyModel.setData(index, res, TagsRole)
        

    def sampleContextMenu(self, pos):
        menu = QtGui.QMenu()
        setCheckedAction = QtGui.QAction('Set for import', menu)
        unsetCheckedAction = QtGui.QAction('Unset for import', menu)
        editTagsAction = QtGui.QAction('Edit tags...', menu)

        selIndexes = self.sampleView.selectionModel().selection().indexes()
        if selIndexes:
            checked = 0
            for index in selIndexes:
                if index.column() == 0 and index.data(QtCore.Qt.CheckStateRole):
                    checked += 1
            setCheckedAction.setEnabled(checked != len(selIndexes) / self.sampleModel.columnCount())
            unsetCheckedAction.setEnabled(checked != 0)
        else:
            setCheckedAction.setEnabled(False)
            unsetCheckedAction.setEnabled(False)
            editTagsAction.setEnabled(False)
        sep = QtGui.QAction(menu)
        sep.setSeparator(True)
        selectAllAction = QtGui.QAction('Select all', menu)

        menu.addActions([setCheckedAction, unsetCheckedAction, editTagsAction, sep, selectAllAction])
        res = menu.exec_(self.sampleView.viewport().mapToGlobal(pos))
        if res == selectAllAction:
            self.sampleView.selectAll()
        elif res == setCheckedAction:
            self.setSelectedCheckState(QtCore.Qt.Checked)
        elif res == unsetCheckedAction:
            self.setSelectedCheckState(QtCore.Qt.Unchecked)
        elif res == editTagsAction:
            self.editTags()

    def setSelectedCheckState(self, state):
        self.sampleProxyModel.dataChanged.disconnect(self.checkChecked)
        for index in self.sampleView.selectedIndexes():
            if index.column() == 0:
                self.sampleProxyModel.setData(index, state, QtCore.Qt.CheckStateRole)
        self.sampleProxyModel.dataChanged.connect(self.checkChecked)
        self.checkChecked()

    def checkChecked(self, *args):
        checked = 0
        for row in range(self.sampleModel.rowCount()):
            if self.sampleModel.item(row, 0).checkState():
                checked += 1
        self.selectedLbl.setText(str(checked))

    def updatePopupDir(self, dirPath):
        self.popup.setInformativeText('Current path:\n{}'.format(dirPath[:-24]))

    def found(self, fileInfo, info):
        fileItem = QtGui.QStandardItem(fileInfo.fileName())
        fileItem.setData(fileInfo.absoluteFilePath(), FilePathRole)
        fileItem.setData(info, InfoRole)
        fileItem.setCheckable(True)
        fileItem.setCheckState(QtCore.Qt.Checked)
        dirItem = QtGui.QStandardItem(fileInfo.absolutePath())
        dirItem.setTextAlignment(QtCore.Qt.AlignCenter)
        lengthItem = QtGui.QStandardItem('{:.3f}'.format(float(info.frames) / info.samplerate))
        formatItem = QtGui.QStandardItem(info.format)
        rateItem = QtGui.QStandardItem(str(info.samplerate))
        channelsItem = QtGui.QStandardItem(str(info.channels))
        tagsItem = QtGui.QStandardItem()
        self.sampleModel.appendRow([fileItem, dirItem, lengthItem, formatItem, rateItem, channelsItem, tagsItem])
        if not self.sampleModel.rowCount() % 50:
            self.sampleView.scrollToBottom()
            found = str(self.sampleModel.rowCount())
            self.totalLbl.setText(found)
            self.selectedLbl.setText(found)
            self.popup.setInformativeText('Samples found: ' + found)
#        self.foundSamples.append(filePath)
#        self.popup.setDetailedText('Samples found: {}'.format(len(self.foundSamples)))

    def scanDone(self):
        try:
            self.sampleProxyModel.dataChanged.connect(self.checkChecked)
        except:
            pass
        found = str(self.sampleModel.rowCount())
        self.totalLbl.setText(found)
        self.selectedLbl.setText(found)
        self.checkChecked()

    def exec_(self):
        self.sampleProxyModel.dataChanged.disconnect(self.checkChecked)
        self.show()
        self.popup.show()
        self.crawlerThread.start()
        res = QtGui.QDialog.exec_(self)
        if res:
            sampleList = []
            for row in range(self.sampleModel.rowCount()):
                fileItem = self.sampleModel.item(row, 0)
                if not fileItem.checkState():
                    continue
                fileName = fileItem.text()
                filePath = fileItem.data(FilePathRole)
                info = fileItem.data(InfoRole)
                tags = self.sampleModel.item(row, tagsColumn).data(TagsRole)
                sampleList.append((filePath, fileName, info, tags))
            return sampleList
        else:
            return res


class SampleScanDialog(QtGui.QDialog):
    def __init__(self, parent, dirName):
        QtGui.QDialog.__init__(self, parent)
        uic.loadUi('directoryscan.ui', self)
        self.dirPathEdit.setText(dirName)
        self.browseBtn.clicked.connect(self.browse)
        self.allFormatsChk.setChecked(True)
        self.allFormatsChk.toggled.connect(self.toggleAllFormats)
        self.formatModel = QtGui.QStandardItemModel()
        self.formatModel.dataChanged.connect(self.checkAllFormatsFromModel)
        self.formatList.setModel(self.formatModel)
        for ext in sorted(soundfile.available_formats().keys()):
            format = soundfile.available_formats()[ext]
            item = QtGui.QStandardItem(format)
            item.setData(ext, FormatRole)
            item.setCheckable(True)
            item.setCheckState(QtCore.Qt.Checked)
            self.formatModel.appendRow(item)

        self.allSampleRatesChk.setChecked(True)
        self.allSampleRatesChk.toggled.connect(self.toggleAllSampleRates)
        self.sampleRatesModel = QtGui.QStandardItemModel()
        self.sampleRatesModel.dataChanged.connect(self.checkAllSampleRatesFromModel)
        self.sampleRatesList.setModel(self.sampleRatesModel)
        for sr in (192000, 176400, 96000, 88200, 48000, 44100, 32000, 22050, 16000, 8000):
            item = QtGui.QStandardItem('{:.1f} kHz'.format(sr/1000.))
            item.setData(sr, FormatRole)
            item.setCheckable(True)
            item.setCheckState(QtCore.Qt.Checked)
            self.sampleRatesModel.appendRow(item)

        self.okBtn = self.buttonBox.button(self.buttonBox.Ok)
        self.okBtn.setText('Scan')

    def checkAllFormatsFromModel(self, *args):
        self.allFormatsChk.blockSignals(True)
        self.allFormatsChk.setChecked(self.checkAllFormats())
        self.allFormatsChk.blockSignals(False)
        self.checkIntegrity()

    def toggleAllFormats(self, state):
        if state == False and self.checkAllFormats():
            self.allFormatsChk.blockSignals(True)
            self.allFormatsChk.setChecked(True)
            self.allFormatsChk.blockSignals(False)
        else:
            for row in range(self.formatModel.rowCount()):
                self.formatModel.item(row).setCheckState(QtCore.Qt.Checked)

    def checkAllFormats(self):
        for row in range(self.formatModel.rowCount()):
            if not self.formatModel.item(row).checkState():
                return False
        else:
            return True

    def checkAllSampleRatesFromModel(self, *args):
        self.allSampleRatesChk.blockSignals(True)
        self.allSampleRatesChk.setChecked(self.checkAllSampleRates())
        self.allSampleRatesChk.blockSignals(False)
        self.checkIntegrity()

    def toggleAllSampleRates(self, state):
        if state == False and self.checkAllSampleRates():
            self.allSampleRatesChk.blockSignals(True)
            self.allSampleRatesChk.setChecked(True)
            self.allSampleRatesChk.blockSignals(False)
        else:
            for row in range(self.sampleRatesModel.rowCount()):
                self.sampleRatesModel.item(row).setCheckState(QtCore.Qt.Checked)

    def checkAllSampleRates(self):
        for row in range(self.sampleRatesModel.rowCount()):
            if not self.sampleRatesModel.item(row).checkState():
                return False
        else:
            return True

    def checkIntegrity(self):
        for row in range(self.formatModel.rowCount()):
            if self.formatModel.item(row).checkState():
                break
        else:
            self.okBtn.setEnabled(False)
            return
        for row in range(self.sampleRatesModel.rowCount()):
            if self.sampleRatesModel.item(row).checkState():
                self.okBtn.setEnabled(True)
                break
        else:
            self.okBtn.setEnabled(False)

    def browse(self):
        filePath = QtGui.QFileDialog.getExistingDirectory(self, 'Select directory', self.dirPathEdit.text())
        if filePath:
            self.dirPathEdit.setText(filePath)

    def getFormats(self):
        if self.allFormatsChk.isChecked():
            return True
        formats = []
        for row in range(self.formatModel.rowCount()):
            item = self.formatModel.item(row)
            if item.checkState():
                formats.append(item.data(FormatRole))
        return formats

    def getSampleRates(self):
        if self.allSampleRatesChk.isChecked():
            return True
        sampleRates = []
        for row in range(self.sampleRatesModel.rowCount()):
            item = self.sampleRatesModel.item(row)
            if item.checkState():
                sampleRates.append(item.data(FormatRole))
        return sampleRates


class TagsEditorDialog(QtGui.QDialog):
    def __init__(self, parent, tags, fileName=None, uncommon=False):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle('Edit tags')
        layout = QtGui.QGridLayout()
        self.setLayout(layout)
        if fileName:
            headerLbl = QtGui.QLabel('Edit tags for sample "{}".\nSeparate tags with commas.'.format(fileName))
        else:
            text = 'Edit tags for selected samples.'
            if uncommon:
                text += '\nTags for selected samples do not match, be careful!'
            text += '\nSeparate tags with commas.'
            headerLbl = QtGui.QLabel(text)
        layout.addWidget(headerLbl)
        self.tagsEditor = TagsEditorTextEdit()
        self.tagsEditor.setTags(tags)
#        self.tagsEditor.setReadOnly(False)
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


class AddSamplesWithTagDialog(QtGui.QDialog):
    def __init__(self, parent, fileList):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle('Add samples to database')
        layout = QtGui.QGridLayout()
        self.setLayout(layout)
        layout.addWidget(QtGui.QLabel('The following samples are about to be added to the database'))
        sampleModel = QtGui.QStandardItemModel()
        sampleView = QtGui.QTableView()
        sampleView.setHorizontalScrollMode(sampleView.ScrollPerPixel)
        sampleView.setVerticalScrollMode(sampleView.ScrollPerPixel)
        sampleView.setMaximumHeight(100)
        layout.addWidget(sampleView)
        sampleView.setModel(sampleModel)
        sampleView.setEditTriggers(sampleView.NoEditTriggers)
        sampleView.horizontalHeader().setVisible(False)
        sampleView.verticalHeader().setVisible(False)
        if isinstance(fileList[0], str):
            for filePath in fileList:
                fileItem = QtGui.QStandardItem(QtCore.QFile(filePath).fileName())
                filePathItem = QtGui.QStandardItem(filePath)
                sampleModel.appendRow([fileItem, filePathItem])
        else:
            for index in fileList:
                fileItem = QtGui.QStandardItem(index.data())
                filePathItem = QtGui.QStandardItem(index.data(FilePathRole))
                sampleModel.appendRow([fileItem, filePathItem])
        sampleView.resizeColumnsToContents()
        sampleView.resizeRowsToContents()
#        sampleView.setStretchLastSection(True)
        layout.addWidget(QtGui.QLabel('Tags that will be applied to all of them (separate tags with commas):'))
        self.tagsEditor = TagsEditorTextEdit()
        self.tagsEditor.setMaximumHeight(100)
#        self.tagsEditor.setReadOnly(False)
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

class RemoveSamplesDialog(QtGui.QDialog):
    def __init__(self, parent, fileList):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle('Remove samples from database')
        layout = QtGui.QGridLayout()
        self.setLayout(layout)
        layout.addWidget(QtGui.QLabel('Remove the following samples from the database?'))
        sampleModel = QtGui.QStandardItemModel()
        sampleView = QtGui.QTableView()
        sampleView.setHorizontalScrollMode(sampleView.ScrollPerPixel)
        sampleView.setVerticalScrollMode(sampleView.ScrollPerPixel)
        sampleView.setMaximumHeight(100)
        layout.addWidget(sampleView)
        sampleView.setModel(sampleModel)
        sampleView.setEditTriggers(sampleView.NoEditTriggers)
        sampleView.horizontalHeader().setVisible(False)
        sampleView.verticalHeader().setVisible(False)
        if isinstance(fileList[0], str):
            for filePath in fileList:
                fileItem = QtGui.QStandardItem(QtCore.QFile(filePath).fileName())
                filePathItem = QtGui.QStandardItem(filePath)
                sampleModel.appendRow([fileItem, filePathItem])
        else:
            for index in fileList:
                fileItem = QtGui.QStandardItem(index.data())
                filePathItem = QtGui.QStandardItem(index.data(FilePathRole))
                sampleModel.appendRow([fileItem, filePathItem])
        sampleView.resizeColumnsToContents()
        sampleView.resizeRowsToContents()
        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok|QtGui.QDialogButtonBox.Cancel)
        self.buttonBox.button(self.buttonBox.Ok).clicked.connect(self.accept)
        self.buttonBox.button(self.buttonBox.Cancel).clicked.connect(self.reject)
        layout.addWidget(self.buttonBox)

class TagsModel(QtGui.QStandardItemModel):
    def __init__(self, db, *args, **kwargs):
        QtGui.QStandardItemModel.__init__(self, *args, **kwargs)
        self.db = db
        self.totalCountItem = QtGui.QStandardItem('0')
        self.appendRow([QtGui.QStandardItem('All samples'), self.totalCountItem])
        self.tags = set()

    def indexFromPath(self, path):
        tagTree = path.split('/')
        depth = 0
        current = self.index(0, 0)
        while depth < len(tagTree):
            childItemMatch = self.match(self.index(0, 0, current), QtCore.Qt.DisplayRole, tagTree[depth], flags=QtCore.Qt.MatchExactly)
            if not childItemMatch:
                return None
            current = childItemMatch[0]
            depth += 1
        return current

    def setTags(self, tags):
        tags = set(tags)
        try:
            tags.remove('')
        except:
            pass
        self.db.execute('SELECT COUNT(*) FROM samples')
        self.totalCountItem.setText(str(self.db.fetchall()[0][0]))
        for tag in tags:
            self.checkAndCreateTags(tag.split('/'), 0)
        currentTags = self.tags & tags
        #check for removed tags
        for tag in self.tags ^ currentTags:
            self.clearTag(tag.split('/'), 0)
        self.tags = tags

    def clearTag(self, tagTree, depth, parentItem=None):
#        return
        if parentItem is None:
            parentItem = self.item(0, 0)
            parentIndex = self.index(0, 0, self.index(0, 0))
        else:
            parentIndex = self.index(0, 0, parentItem.index())
        childTag = tagTree[depth]
        childItemMatch = self.match(parentIndex, QtCore.Qt.DisplayRole, childTag, flags=QtCore.Qt.MatchExactly)
        if not childItemMatch:
            print('maccheccazz')
            return
        childIndex = childItemMatch[0]
        if depth + 1 == len(tagTree):
            childCountItem = self.itemFromIndex(childIndex.sibling(childIndex.row(), 1))
            subtract = int(childCountItem.text())
            childCountItem.setText('0')
            return subtract
        else:
            subtract = self.clearTag(tagTree, depth + 1, self.itemFromIndex(childIndex))
            try:
                countItem = self.itemFromIndex(childIndex.sibling(childIndex.row(), 1))
#                row = parentIndex.parent().row() if parentItem != self else childIndex.row()
#                countItem = self.itemFromIndex(parentIndex.parent().sibling(parentIndex.row(), 1))
                print(countItem.text(), subtract)
#                countItem.setText('{}'.format(int(countItem.text()) - subtract))
            except Exception as e:
                print(e)

    def checkAndCreateTags(self, tagTree, depth, parentItem=None):
        if parentItem is None:
            parentItem = self.item(0, 0)
            parentIndex = self.index(0, 0, self.index(0, 0))
        else:
            parentIndex = self.index(0, 0, parentItem.index())
        childTag = tagTree[depth]
        currentTree = '/'.join(tagTree[:depth+1])
        hasChildren = True if len(tagTree) > depth + 1 else False
        self.db.execute('SELECT * FROM samples WHERE tags LIKE ?', ('%{}%'.format(currentTree), ))
        count = 0
        for item in self.db.fetchall():
            for tag in item[6].split(','):
                if hasChildren:
                    if tag.startswith(currentTree + '/'):
                        count += 1
                        break
                else:
                    if tag == currentTree:
                        count += 1
                        break
        count = str(count)
        childItemMatch = self.match(parentIndex, QtCore.Qt.DisplayRole, childTag, flags=QtCore.Qt.MatchExactly)
        if childItemMatch:
            childIndex = childItemMatch[0]
            childItem = self.itemFromIndex(childIndex)
            self.itemFromIndex(childIndex.sibling(childIndex.row(), 1)).setText(count)
        else:
            childItem = QtGui.QStandardItem(childTag)
            self.db.execute('SELECT foreground,background FROM tagColors WHERE tag=?', ('/'.join(tagTree[:depth+1]), ))
            colors = self.db.fetchone()
            if colors:
                childItem.setData(QtGui.QColor(colors[0]), QtCore.Qt.ForegroundRole)
                childItem.setData(QtGui.QColor(colors[1]), QtCore.Qt.BackgroundRole)

            countItem = QtGui.QStandardItem(count)
            parentItem.appendRow([childItem, countItem])
#        if len(tagTree[depth:]) > 1:
        if hasChildren:
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
    def __init__(self, alignment, elideMode=QtCore.Qt.ElideRight):
        QtGui.QStyledItemDelegate.__init__(self)
        self.alignment = alignment
        if not alignment & (QtCore.Qt.AlignTop|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignBottom):
            self.alignment |= QtCore.Qt.AlignVCenter
        self.elideMode = elideMode

    def paint(self, painter, option, index):
        option.displayAlignment = self.alignment
        option.textElideMode = self.elideMode
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


class ColorLineEdit(QtGui.QLineEdit):
    editBtnClicked = QtCore.pyqtSignal()
    def __init__(self, *args, **kwargs):
        QtGui.QLineEdit.__init__(self, *args, **kwargs)
        self.editBtn = QtGui.QPushButton('...', self)
        self.editBtn.setCursor(QtCore.Qt.ArrowCursor)
        self.editBtn.clicked.connect(self.editBtnClicked.emit)

    def resizeEvent(self, event):
        size = self.height() - 8
        self.editBtn.resize(size, size)
        self.editBtn.move(self.width() - size - 4, (self.height() - size) / 2)


class TagColorDialog(QtGui.QDialog):
    def __init__(self, parent, index):
        QtGui.QDialog.__init__(self, parent)
        layout = QtGui.QGridLayout()
        self.setLayout(layout)
        layout.addWidget(QtGui.QLabel('Text color:'))
        self.foregroundColor = index.data(QtCore.Qt.ForegroundRole)
        self.backgroundColor = index.data(QtCore.Qt.BackgroundRole)
        self.foregroundEdit = ColorLineEdit()
        basePalette = self.foregroundEdit.palette()
        self.defaultForeground = basePalette.color(basePalette.Active, basePalette.Text)
        self.defaultBackground = basePalette.color(basePalette.Active, basePalette.Base)
        if self.foregroundColor is None:
            self.foregroundColor = self.defaultForeground
        else:
            basePalette.setColor(basePalette.Active, basePalette.Text, self.foregroundColor)
            basePalette.setColor(basePalette.Inactive, basePalette.Text, self.foregroundColor)
        if self.backgroundColor is None:
            self.backgroundColor = self.defaultBackground
        else:
            basePalette.setColor(basePalette.Active, basePalette.Base, self.backgroundColor)
            basePalette.setColor(basePalette.Inactive, basePalette.Base, self.backgroundColor)
        self.foregroundEdit.setText(self.foregroundColor.name())
        self.foregroundEdit.textChanged.connect(self.setForegroundColor)
        self.foregroundEdit.editBtnClicked.connect(self.foregroundSelect)
        self.foregroundEdit.setPalette(basePalette)
        layout.addWidget(self.foregroundEdit, 0, 1)
        autoBgBtn = QtGui.QPushButton('Autoset background')
        layout.addWidget(autoBgBtn, 0, 2)
        autoBgBtn.clicked.connect(lambda: self.setBackgroundColor(self.reverseColor(self.foregroundColor)))

        layout.addWidget(QtGui.QLabel('Background:'))
        self.backgroundEdit = ColorLineEdit()
        self.backgroundEdit.setText(self.backgroundColor.name())
        self.backgroundEdit.textChanged.connect(self.setBackgroundColor)
        self.backgroundEdit.editBtnClicked.connect(self.backgroundSelect)
        self.backgroundEdit.setPalette(basePalette)
        layout.addWidget(self.backgroundEdit, 1, 1)
        autoFgBtn = QtGui.QPushButton('Autoset text')
        layout.addWidget(autoFgBtn, 1, 2)
        autoFgBtn.clicked.connect(lambda: self.setForegroundColor(self.reverseColor(self.backgroundColor)))

        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok|QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.RestoreDefaults)
        layout.addWidget(self.buttonBox, layout.rowCount(), 0, 1, layout.columnCount())
        self.okBtn = self.buttonBox.button(self.buttonBox.Ok)
        self.okBtn.clicked.connect(self.accept)
        self.buttonBox.button(self.buttonBox.Cancel).clicked.connect(self.reject)
        self.restoreBtn = self.buttonBox.button(self.buttonBox.RestoreDefaults)
        self.restoreBtn.setIcon(QtGui.QIcon.fromTheme('edit-undo'))
        self.restoreBtn.clicked.connect(lambda: [self.setBackgroundColor(), self.setForegroundColor()])

    def reverseColor(self, color):
        r, g, b, a = color.getRgb()
        return QtGui.QColor(r^255, g^255, b^255)

    def foregroundSelect(self):
        color = QtGui.QColorDialog.getColor(self.foregroundColor, self, 'Select text color')
        if color.isValid():
            self.foregroundEdit.setText(color.name())
            self.setForegroundColor(color)

    def setForegroundColor(self, color=None):
        if not color:
            color = self.defaultForeground
        elif isinstance(color, str):
            color = QtGui.QColor(color)
        self.foregroundColor = color
        palette = self.foregroundEdit.palette()
        palette.setColor(palette.Active, palette.Text, self.foregroundColor)
        palette.setColor(palette.Inactive, palette.Text, self.foregroundColor)
        self.foregroundEdit.setPalette(palette)
        self.backgroundEdit.setPalette(palette)

    def backgroundSelect(self):
        color = QtGui.QColorDialog.getColor(self.backgroundColor, self, 'Select background color')
        if color.isValid():
            self.backgroundEdit.setText(color.name())
            self.setBackgroundColor(color)

    def setBackgroundColor(self, color=None):
        if not color:
            color = self.defaultBackground
        elif isinstance(color, str):
            color = QtGui.QColor(color)
        self.backgroundColor = color
        palette = self.backgroundEdit.palette()
        palette.setColor(palette.Active, palette.Base, self.backgroundColor)
        palette.setColor(palette.Inactive, palette.Base, self.backgroundColor)
        self.foregroundEdit.setPalette(palette)
        self.backgroundEdit.setPalette(palette)

    def exec_(self):
        res = QtGui.QDialog.exec_(self)
        if self.foregroundColor == self.defaultForeground and self.backgroundColor == self.defaultBackground:
            self.foregroundColor = None
            self.backgroundColor = None
        return res


class TagTreeDelegate(QtGui.QStyledItemDelegate):
    tagColorsChanged = QtCore.pyqtSignal(object, object, object)
    def editorEvent(self, event, model, _option, index):
        if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.RightButton:
            if index != model.index(0, 0):
                menu = QtGui.QMenu()
                editColorAction = QtGui.QAction('Edit tag color...', menu)
                menu.addAction(editColorAction)
                res = menu.exec_(_option.widget.viewport().mapToGlobal(event.pos()))
                if res == editColorAction:
                    colorDialog = TagColorDialog(_option.widget.window(), index)
                    if colorDialog.exec_():
                        model.setData(index, colorDialog.foregroundColor, QtCore.Qt.ForegroundRole)
                        model.setData(index, colorDialog.backgroundColor, QtCore.Qt.BackgroundRole)
                        self.tagColorsChanged.emit(index, colorDialog.foregroundColor, colorDialog.backgroundColor)
                return True
            return True
        return QtGui.QStyledItemDelegate.editorEvent(self, event, model, _option, index)




class TagListDelegate(QtGui.QStyledItemDelegate):
    tagSelected = QtCore.pyqtSignal(str)
    def __init__(self, tagColorsDict, *args, **kwargs):
        QtGui.QStyledItemDelegate.__init__(self, *args, **kwargs)
        self.tagColorsDict = tagColorsDict

    def sizeHint(self, option, index):
        sizeHint = QtGui.QStyledItemDelegate.sizeHint(self, option, index)
        tagList = index.data(TagsRole)
        if tagList:
            sizeHint.setWidth(sum(option.fontMetrics.width(tag) + 5 for tag in tagList) + 10)
        return sizeHint

    def editorEvent(self, event, model, option, index):
        if event.type() == QtCore.QEvent.MouseMove:
            model.setData(index, event.pos(), HoverRole)
#            _option.widget.dataChanged(index, index)
            return True
        elif event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton and index.data(TagsRole):
            delta = 1
            height = option.fontMetrics.height()
            left = option.rect.x() + .5
            top = option.rect.y() + .5 + (option.rect.height() - height) / 2
            for tag in index.data(TagsRole):
                width = option.fontMetrics.width(tag) + 5
                rect = QtCore.QRectF(left + delta + 1, top, width, height)
                if event.pos() in rect:
                    self.tagSelected.emit(tag)
                    break
                delta += width + 2
            return True
        return QtGui.QStyledItemDelegate.editorEvent(self, event, model, option, index)

    def paint(self, painter, _option, index):
        if not index.isValid():
            QtGui.QStyledItemDelegate.paint(self, painter, _option, index)
            return
        option = QtGui.QStyleOptionViewItemV4()
        option.__init__(_option)
        self.initStyleOption(option, QtCore.QModelIndex())
        option.text = ''
        QtGui.QApplication.style().drawControl(QtGui.QStyle.CE_ItemViewItem, option, painter)

        tagList = index.data(TagsRole)
        if not tagList:
            return
        pos = index.data(HoverRole) if option.state & QtGui.QStyle.State_MouseOver else False
        height = option.fontMetrics.height()
        delta = 1
        painter.setRenderHints(painter.Antialiasing)
#        painter.setBrush(QtCore.Qt.lightGray)
        left = option.rect.x() + .5
        top = option.rect.y() + .5 + (option.rect.height() - height) / 2
        for tag in tagList:
            width = option.fontMetrics.width(tag) + 5
            rect = QtCore.QRectF(left + delta + 1, top, width, height)
            if tag in self.tagColorsDict:
                foreground, background = self.tagColorsDict[tag]
                border = foreground if pos and pos in rect else QtCore.Qt.NoPen
            else:
                if pos and pos in rect:
                    border = foreground = QtCore.Qt.black
                else:
                    foreground = QtCore.Qt.darkGray
                    border = QtCore.Qt.NoPen
                background = QtCore.Qt.lightGray
            painter.setPen(border)
            painter.setBrush(background)
            painter.drawRoundedRect(rect, 2, 2)
            painter.setPen(foreground)
            painter.drawText(rect, QtCore.Qt.AlignCenter, tag)
            delta += width + 2


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
        self.tagTreeDelegate = TagTreeDelegate()
        self.tagTreeDelegate.tagColorsChanged.connect(self.saveTagColors)
        self.dbTreeView.setItemDelegateForColumn(0, self.tagTreeDelegate)
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
        self.alignCenterDelegate = AlignItemDelegate(QtCore.Qt.AlignCenter)
        self.alignLeftElideMidDelegate = AlignItemDelegate(QtCore.Qt.AlignLeft, QtCore.Qt.ElideMiddle)
        self.sampleView.setItemDelegateForColumn(1, self.alignLeftElideMidDelegate)
        for c in range(2, channelsColumn + 1):
            self.sampleView.setItemDelegateForColumn(c, self.alignCenterDelegate)
        self.tagListDelegate = TagListDelegate(self.tagColorsDict)
        self.sampleView.setItemDelegateForColumn(tagsColumn, self.tagListDelegate)
        self.tagListDelegate.tagSelected.connect(self.selectTagOnTree)
        self.sampleView.setMouseTracking(True)
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

        self.tagsEdit.applyMode = True
        self.tagsEdit.tagsApplied.connect(self.tagsApplied)

        self.currentSampleIndex = None
        self.currentShownSampleIndex = None
        self.currentBrowseDir = None
        self.currentDbQuery = None
        self.sampleDbUpdated = False

        self.browse()
        for column, visible in browseColumns.items():
            self.sampleView.horizontalHeader().setSectionHidden(column, not visible)
        self.mainSplitter.setStretchFactor(0, 8)
        self.mainSplitter.setStretchFactor(1, 16)
        self.fsSplitter.setStretchFactor(0, 50)
        self.fsSplitter.setStretchFactor(1, 1)

        self.infoTabWidget.setTabEnabled(1, False)
        self.shown = False
        self.playerThread.start()

        self.reloadTags()
        self.dbTreeView.expandToDepth(0)

    def loadDb(self):
        dataDir = QtCore.QDir(QtGui.QDesktopServices.storageLocation(QtGui.QDesktopServices.DataLocation))
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
        dirName = dirIndex.data()
        dirPath = self.fsModel.filePath(self.fsProxyModel.mapToSource(dirIndex))

        menu = QtGui.QMenu()
        addDirAction = QtGui.QAction('Add "{}" to favourites'.format(dirName), menu)
        for row in range(self.favouritesModel.rowCount()):
            dirPathItem = self.favouritesModel.item(row, 1)
            if dirPathItem.text() == dirPath:
                addDirAction.setEnabled(False)
                break
        sep = QtGui.QAction(menu)
        sep.setSeparator(True)
        scanAction = QtGui.QAction('Scan "{}" for samples'.format(dirName), menu)

        menu.addActions([addDirAction, sep, scanAction])
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
        elif res == scanAction:
            self.sampleScan(dirPath)

    def sampleScan(self, dirPath=QtCore.QDir('.').absolutePath()):
        scanDialog = SampleScanDialog(self, dirPath)
        if not scanDialog.exec_():
            return
        dirPath = scanDialog.dirPathEdit.text()
        scanMode = scanDialog.scanModeCombo.currentIndex()
        formats = scanDialog.getFormats()
        sampleRates = scanDialog.getSampleRates()
        channels = scanDialog.channelsCombo.currentIndex()
        res = ImportDialogScan(self, dirPath, scanMode, formats, sampleRates, channels).exec_()
        if not res:
            return
        for filePath, fileName, info, tags in res:
            self._addSampleToDb(filePath, fileName, info, ','.join(tags))
        self.dbConn.commit()
        self.reloadTags()
        #TODO reload database table?

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
        self.browseModel.setHorizontalHeaderLabels(['Name', None, 'Length', 'Format', 'Rate', 'Ch.', None, None])
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
            lengthItem = QtGui.QStandardItem('{:.3f}'.format(float(info.frames) / info.samplerate))
            formatItem = QtGui.QStandardItem(info.format)
            rateItem = QtGui.QStandardItem(str(info.samplerate))
            channelsItem = QtGui.QStandardItem(str(info.channels))
            self.browseModel.appendRow([fileItem, None, lengthItem, formatItem, rateItem, channelsItem])
        self.sampleView.resizeColumnsToContents()
        self.sampleView.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        for c in range(1, channelsColumn):
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
        if len(self.sampleView.selectionModel().selectedRows()) == 1:
            self.singleSampleContextMenu(selIndex.sibling(selIndex.row(), 0), pos)
        else:
            self.multiSampleContextMenu(pos)

    def singleSampleContextMenu(self, fileIndex, pos):
        fileName = fileIndex.data()
        filePath = fileIndex.data(FilePathRole)
        menu = QtGui.QMenu()
        addToDatabaseAction = QtGui.QAction('Add "{}" to database'.format(fileName), menu)
        editTagsAction = QtGui.QAction('Edit "{}" tags...'.format(fileName), menu)
        delFromDatabaseAction = QtGui.QAction('Remove "{}" from database'.format(fileName), menu)
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
        elif res == editTagsAction:
            self.editTags(fileIndex.sibling(fileIndex.row(), tagsColumn))

    def multiSampleContextMenu(self, pos):
        new = []
        exist = []
        for fileIndex in self.sampleView.selectionModel().selectedRows():
            filePath = fileIndex.data(FilePathRole)
            self.sampleDb.execute('SELECT * FROM samples WHERE filePath=?', (filePath, ))
            if not self.sampleDb.fetchone():
                new.append(fileIndex)
            else:
                exist.append(fileIndex)
        menu = QtGui.QMenu()
        if self.sampleView.model() == self.browseModel:
            removeAllAction = QtGui.QAction('Remove {} existing samples from database'.format(len(exist)), menu)
        else:
            removeAllAction = QtGui.QAction('Remove selected samples from database', menu)
        addAllAction = QtGui.QAction('Add selected samples to database', menu)
        addAllActionWithTags = QtGui.QAction('Add selected samples to database with tags...', menu)
        if new:
            menu.addActions([addAllAction, addAllActionWithTags])
        if exist:
            if new:
                sep = QtGui.QAction(menu)
                sep.setSeparator(True)
                menu.addAction(sep)
            menu.addAction(removeAllAction)
        res = menu.exec_(self.sampleView.viewport().mapToGlobal(pos))
        if res == addAllAction:
            self.addSampleGroupToDb(new)
        elif res == addAllActionWithTags:
            tags = AddSamplesWithTagDialog(self, new).exec_()
            if isinstance(tags, str):
                self.addSampleGroupToDb(new, tags)
        elif res == removeAllAction:
            if RemoveSamplesDialog(self, exist).exec_():
                fileNames = [i.data(FilePathRole) for i in exist]
                self.sampleDb.execute(
                    'DELETE FROM samples WHERE filePath IN ({})'.format(','.join(['?' for i in fileNames])), 
                    fileNames
                    )
                self.dbConn.commit()
                if self.sampleView.model() == self.dbProxyModel:
                    for index in sorted(exist, key=lambda index: index.row(), reverse=True):
                        self.dbModel.takeRow(index.row())
                else:
                    self.sampleDbUpdated = True
                self.reloadTags()

    def addSampleGroupToDb(self, fileIndexes, tags=''):
        for fileIndex in fileIndexes:
            filePath = fileIndex.data(FilePathRole)
            fileName = fileIndex.data()
            info = fileIndex.data(InfoRole)
            self._addSampleToDb(filePath, fileName, info, tags)
        self.dbConn.commit()
        self.reloadTags()
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
#        else:
#            reload query

    def _addSampleToDb(self, filePath, fileName=None, info=None, tags='', preview=None):
        if not fileName:
            fileName = QtCore.QFile(filePath).fileName()
        if not info:
            soundfile.info(filePath)
        self.sampleDb.execute(
            'INSERT INTO samples values (?,?,?,?,?,?,?,?)', 
            (filePath, fileName, float(info.frames) / info.samplerate, info.format, info.samplerate, info.channels, tags, preview), 
            )

    def browseDb(self, query=None, force=True):
        if query is None:
            if not force and (self.currentDbQuery and not self.sampleDbUpdated):
                if self.currentShownSampleIndex and self.currentShownSampleIndex.model() == self.dbModel:
                    self.sampleView.setCurrentIndex(self.currentShownSampleIndex)
                return
            else:
                query = 'SELECT * FROM samples'
        self.currentDbQuery = query
        self.sampleDbUpdated = False
        self.dbModel.clear()
        self.dbModel.setHorizontalHeaderLabels(['Name', 'Path', 'Length', 'Format', 'Rate', 'Ch.', 'Tags', 'Preview'])
        for column, visible in dbColumns.items():
            self.sampleView.horizontalHeader().setSectionHidden(column, not visible)
        for row in self.sampleDb.execute(query):
            filePath, fileName, length, format, sampleRate, channels, tags, data = row
            fileItem = QtGui.QStandardItem(fileName)
            fileItem.setData(filePath, FilePathRole)
            dirItem = QtGui.QStandardItem(QtCore.QFileInfo(filePath).absolutePath())
            fileItem.setIcon(QtGui.QIcon.fromTheme('media-playback-start'))
            lengthItem = QtGui.QStandardItem('{:.3f}'.format(length))
            formatItem = QtGui.QStandardItem(format)
            rateItem = QtGui.QStandardItem(str(sampleRate))
            channelsItem = QtGui.QStandardItem(str(channels))
            tagsItem = QtGui.QStandardItem()
            tagsItem.setData(list(filter(None, tags.split(','))), TagsRole)
#            self.dbModel.appendRow([fileItem, lengthItem, formatItem, rateItem, channelsItem, tagsItem])
            self.dbModel.appendRow([fileItem, dirItem, lengthItem, formatItem, rateItem, channelsItem, tagsItem])
        self.sampleView.resizeColumnsToContents()
        self.sampleView.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.sampleView.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        for c in range(2, channelsColumn + 1):
            self.sampleView.horizontalHeader().setResizeMode(c, QtGui.QHeaderView.Fixed)
        self.sampleView.resizeRowsToContents()

    def searchDb(self, text):
        self.dbProxyModel.setFilterRegExp(text)

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

    def reloadTags(self):
        self.sampleDb.execute('SELECT tags FROM samples')
        tags = set()
        for tagList in self.sampleDb.fetchall():
            tagList = tagList[0].strip(',').split(',')
            [tags.add(tag.strip().strip('\n')) for tag in tagList]
        self.dbTreeModel.setTags(tags)
        self.dbTreeView.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.dbTreeView.resizeColumnToContents(1)
        self.dbTreeView.header().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.dbTreeView.header().setResizeMode(1, QtGui.QHeaderView.Fixed)

    def dbTreeViewDoubleClicked(self, index):
        if self.dbTreeProxyModel.mapToSource(index) == self.dbTreeModel.index(0, 0):
            self.browseDb()
            return
        #TODO this has to be implemented along with browseDb
        self.dbModel.clear()
        self.dbModel.setHorizontalHeaderLabels(['Name', 'Path', 'Length', 'Format', 'Rate', 'Ch.', 'Tags', 'Preview'])
        for column, visible in dbColumns.items():
            self.sampleView.horizontalHeader().setSectionHidden(column, not visible)

        currentTag = index.data()
        current = index
        while True:
            parent = current.parent()
            if not parent.isValid() or parent == self.dbTreeProxyModel.index(0, 0):
                break
            currentTag = '{parent}/{current}'.format(parent=parent.data(), current=currentTag)
            current = parent
        hasChildren = self.dbTreeProxyModel.hasChildren(index)
        self.sampleDb.execute('SELECT * FROM samples WHERE tags LIKE ?', ('%{}%'.format(currentTag), ))
        for row in self.sampleDb.fetchall():
            filePath, fileName, length, format, sampleRate, channels, tags, data = row
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
            dirItem = QtGui.QStandardItem(QtCore.QFileInfo(filePath).absolutePath())
            lengthItem = QtGui.QStandardItem('{:.3f}'.format(length))
            formatItem = QtGui.QStandardItem(format)
            rateItem = QtGui.QStandardItem(str(sampleRate))
            channelsItem = QtGui.QStandardItem(str(channels))
            tagsItem = QtGui.QStandardItem()
            tagsItem.setData(list(filter(None, tags.split(','))), TagsRole)
            self.dbModel.appendRow([fileItem, dirItem, lengthItem, formatItem, rateItem, channelsItem, tagsItem])
        self.sampleView.resizeColumnsToContents()
        self.sampleView.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.sampleView.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        for c in range(2, channelsColumn + 1):
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
        self.setCurrentWave(fileIndex)
        fileItem = self.sampleView.model().itemFromIndex(fileIndex)
        info = fileIndex.data(InfoRole)
        waveData = fileItem.data(WaveRole)
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
        self.sampleDb.execute('UPDATE samples SET tags=? WHERE filePath=?', (tagList, filePath))
        self.reloadTags()
        sampleMatch = self.dbModel.match(self.dbModel.index(0, 0), FilePathRole, filePath, flags=QtCore.Qt.MatchExactly)
        if sampleMatch:
            fileIndex = sampleMatch[0]
            tagsIndex = fileIndex.sibling(fileIndex.row(), tagsColumn)
            self.dbModel.itemFromIndex(tagsIndex).setText(tagList)

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

        if self.sampleView.model() == self.dbProxyModel:
            tagsIndex = index.sibling(index.row(), tagsColumn)
            if tagsIndex.isValid():
                self.tagsEdit.setTags(tagsIndex.data(TagsRole))

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
