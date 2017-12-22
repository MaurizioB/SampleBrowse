import os
import soundfile
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from samplebrowsesrc import utils
from samplebrowsesrc.constants import *
from samplebrowsesrc.dialogs.tagseditor import TagsEditorDialog
from samplebrowsesrc.classes import SampleSortFilterProxyModel, Crawler
from samplebrowsesrc.widgets import AlignItemDelegate, TagListDelegate, SubtypeDelegate

class ImportDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi('{}/importdialog.ui'.format(os.path.dirname(utils.__file__)), self)
        self.sampleModel = QtGui.QStandardItemModel()
        self.sampleProxyModel = SampleSortFilterProxyModel()
        self.sampleProxyModel.setSourceModel(self.sampleModel)
        self.sampleView.setModel(self.sampleProxyModel)
        self.sampleModel.setHorizontalHeaderLabels(['Name', 'Path', 'Length', 'Format', 'Rate', 'Ch.', 'Bits', 'Tags'])

        self.elidedItemDelegate = AlignItemDelegate(QtCore.Qt.AlignLeft, QtCore.Qt.ElideMiddle)
        self.sampleView.setItemDelegateForColumn(1, self.elidedItemDelegate)
        self.alignCenterDelegate = AlignItemDelegate(QtCore.Qt.AlignCenter)
        for c in range(2, channelsColumn + 1):
            self.sampleView.setItemDelegateForColumn(c, self.alignCenterDelegate)
        self.subtypeDelegate = SubtypeDelegate()
        self.sampleView.setItemDelegateForColumn(subtypeColumn, self.subtypeDelegate)
        self.tagListDelegate = TagListDelegate(self.parent().tagColorsDict)
        self.sampleView.setItemDelegateForColumn(tagsColumn, self.tagListDelegate)
        self.sampleView.setMouseTracking(True)

        fontMetrics = QtGui.QFontMetrics(self.font())

        self.sampleView.horizontalHeader().setSectionResizeMode(fileNameColumn, QtWidgets.QHeaderView.Stretch)
        self.sampleView.horizontalHeader().setSectionResizeMode(dirColumn, QtWidgets.QHeaderView.Stretch)
        self.sampleView.horizontalHeader().resizeSection(lengthColumn, fontMetrics.width('888.888') + 10)
        self.sampleView.horizontalHeader().setSectionResizeMode(lengthColumn, QtWidgets.QHeaderView.Fixed)
        self.sampleView.horizontalHeader().resizeSection(formatColumn, fontMetrics.width('Format') + 10)
        self.sampleView.horizontalHeader().setSectionResizeMode(formatColumn, QtWidgets.QHeaderView.Fixed)
        self.sampleView.horizontalHeader().resizeSection(rateColumn, fontMetrics.width('192000') + 10)
        self.sampleView.horizontalHeader().setSectionResizeMode(rateColumn, QtWidgets.QHeaderView.Fixed)
        self.sampleView.horizontalHeader().resizeSection(channelsColumn, fontMetrics.width('Ch.') + 10)
        self.sampleView.horizontalHeader().setSectionResizeMode(channelsColumn, QtWidgets.QHeaderView.Fixed)
        self.sampleView.horizontalHeader().resizeSection(subtypeColumn, fontMetrics.width('Bits') + 12)
        self.sampleView.horizontalHeader().setSectionResizeMode(subtypeColumn, QtWidgets.QHeaderView.Fixed)

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
        menu = QtWidgets.QMenu()
        setCheckedAction = QtWidgets.QAction('Set for import', menu)
        unsetCheckedAction = QtWidgets.QAction('Unset for import', menu)
        editTagsAction = QtWidgets.QAction('Edit tags...', menu)

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
        selectAllAction = QtWidgets.QAction('Select all', menu)

        menu.addActions([setCheckedAction, unsetCheckedAction, editTagsAction, utils.menuSeparator(menu), selectAllAction])
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

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
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


class ImportDialogScan(ImportDialog):
    def __init__(self, parent, dirList, scanMode, formats, sampleRates, channels, scanLimits):
        ImportDialog.__init__(self, parent)
        self.crawler = Crawler(dirList, scanMode, formats, sampleRates, channels, scanLimits)
        self.crawlerThread = QtCore.QThread()
        self.crawler.moveToThread(self.crawlerThread)
        self.crawlerThread.started.connect(self.crawler.run)
        self.popup = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, 'Scanning...', 'Scanning disk, please wait.', QtWidgets.QMessageBox.Cancel, self)
        self.popup.setModal(True)
#        self.popup.rejected.connect(lambda: self.crawler.stop.set())
        self.popup.button(self.popup.Cancel).clicked.connect(lambda: self.crawler.stop.set())
        self.crawler.found.connect(self.found)
        self.crawler.done.connect(self.popup.close)
        self.crawler.done.connect(self.scanDone)
        self.defaultTags = []

    def updatePopupDir(self, dirPath):
        self.popup.setInformativeText('Current path:\n{}'.format(dirPath[:-24]))

    def found(self, fileInfo, info):
        fileItem = QtGui.QStandardItem(fileInfo.fileName())
        fileItem.setData(fileInfo.absoluteFilePath(), FilePathRole)
        fileItem.setData(info, InfoRole)
        fileItem.setToolTip(fileInfo.fileName())
        fileItem.setCheckable(True)
        fileItem.setCheckState(QtCore.Qt.Checked)
        dirItem = QtGui.QStandardItem(fileInfo.absolutePath())
        dirItem.setToolTip(fileInfo.absoluteFilePath())
        lengthItem = QtGui.QStandardItem('{:.3f}'.format(float(info.frames) / info.samplerate))
        formatItem = QtGui.QStandardItem(info.format)
        rateItem = QtGui.QStandardItem(str(info.samplerate))
        channelsItem = QtGui.QStandardItem(str(info.channels))
        subtypeItem = QtGui.QStandardItem(info.subtype)
        tagsItem = QtGui.QStandardItem()
        tagsItem.setData(self.defaultTags, TagsRole)
        self.sampleModel.appendRow([fileItem, dirItem, lengthItem, formatItem, rateItem, channelsItem, subtypeItem, tagsItem])
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
#        self.sampleView.resizeColumnsToContents()
        found = str(self.sampleModel.rowCount())
        self.totalLbl.setText(found)
        self.selectedLbl.setText(found)
        self.checkChecked()

    def exec_(self):
        self.sampleProxyModel.dataChanged.disconnect(self.checkChecked)
        self.show()
        self.popup.show()
        self.crawlerThread.start()
        return ImportDialog.exec_(self)


class ImportDialogScanDnD(ImportDialogScan):
    def __init__(self, parent, dirList, fileList, scanMode, formats, sampleRates, channels, scanLimits, tag):
        if dirList:
            ImportDialogScan.__init__(self, parent, dirList, scanMode, formats, sampleRates, channels, scanLimits)
            self.defaultTags = [tag]
        else:
            ImportDialog.__init__(self, parent)
        unknownFiles = []
        self.dirList = dirList
        for filePath in fileList:
            try:
                info = soundfile.info(filePath)
            except:
                unknownFiles.append(filePath)
                continue
            fileInfo = QtCore.QFileInfo(filePath)
            fileItem = QtGui.QStandardItem(fileInfo.fileName())
            fileItem.setData(filePath, FilePathRole)
            fileItem.setData(info, InfoRole)
            fileItem.setToolTip(fileInfo.fileName())
            fileItem.setCheckable(True)
            fileItem.setCheckState(QtCore.Qt.Checked)
            dirItem = QtGui.QStandardItem(fileInfo.absolutePath())
            dirItem.setToolTip(fileInfo.absoluteFilePath())
            lengthItem = QtGui.QStandardItem('{:.3f}'.format(float(info.frames) / info.samplerate))
            formatItem = QtGui.QStandardItem(info.format)
            rateItem = QtGui.QStandardItem(str(info.samplerate))
            channelsItem = QtGui.QStandardItem(str(info.channels))
            subtypeItem = QtGui.QStandardItem(info.subtype)
            tagsItem = QtGui.QStandardItem()
            tagsItem.setData([tag], TagsRole)
            self.sampleModel.appendRow([fileItem, dirItem, lengthItem, formatItem, rateItem, channelsItem, subtypeItem, tagsItem])

    def exec_(self):
        if self.sampleModel.rowCount() == 0 and not self.dirList:
            return 0
        if self.dirList:
            return ImportDialogScan.exec_(self)
        else:
            return ImportDialog.exec_(self)


