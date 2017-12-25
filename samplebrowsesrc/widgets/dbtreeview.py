from PyQt5 import QtCore, QtWidgets
from samplebrowsesrc.constants import *
from samplebrowsesrc.dialogs import ImportDialogScanDnD, ScanOptionsDialog
from samplebrowsesrc.widgets import *

class DropTimer(QtCore.QTimer):
    expandIndex = QtCore.pyqtSignal(object)
    def __init__(self):
        QtCore.QTimer.__init__(self)
        self.setInterval(500)
        self.setSingleShot(True)
        self.currentIndex = None
        self.timeout.connect(self.expandEmit)

    def expandEmit(self):
        if self.currentIndex:
            self.expandIndex.emit(self.currentIndex)
            self.currentIndex = None
#        self.expandIndex.emit(self.currentIndex) if self.currentIndex else None

    def start(self, index):
        if not index:
            self.stop()
            return
        if index == self.currentIndex:
            return
        self.currentIndex = index
        QtCore.QTimer.start(self)


class DbTreeView(TreeViewWithLines):
    samplesAddedToTag = QtCore.pyqtSignal(object, str)
    samplesImported = QtCore.pyqtSignal(object, object)
    def __init__(self, parent, *args, **kwargs):
        QtWidgets.QTreeView.__init__(self, *args, **kwargs)
        self.main = parent
        self.setAcceptDrops(True)
        #something is wrong with setAutoExpandDelay, we use a custom QTimer
        self.dropTimer = QtCore.QTimer()
        self.dropTimer.setInterval(500)
        self.dropTimer.setSingleShot(True)
        self.dropTimer.timeout.connect(self.expandDrag)
        self.currentTagIndex = None

    def expandDrag(self):
        if not (self.currentTagIndex and self.currentTagIndex.isValid()):
            return
        if not self.isExpanded(self.currentTagIndex):
            self.expand(self.currentTagIndex)
        else:
            self.collapse(self.currentTagIndex)

    def dragEnterEvent(self, event):
        formats = event.mimeData().formats()
        if 'application/x-qabstractitemmodeldatalist' in formats:
            event.accept()
            currentTagIndex = self.indexAt(event.pos())
            if currentTagIndex.isValid() and currentTagIndex not in (self.model().index(0, 0), self.model().index(0, 1)):
                self.currentTagIndex = currentTagIndex
                self.dropTimer.start()
        elif 'text/uri-list' in formats:
            event.accept()

    def dragMoveEvent(self, event):
        currentTagIndex = self.indexAt(event.pos())
        formats = event.mimeData().formats()
        if self.currentTagIndex:
            self.update(self.currentTagIndex)
        if not currentTagIndex.isValid() or currentTagIndex in (self.model().index(0, 0), self.model().index(0, 1)):
            self.currentTagIndex = None
            self.dropTimer.stop()
            if 'text/uri-list' in formats and (event.source() and not isinstance(event.source(), SampleView)):
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
            if currentTagIndex != self.currentTagIndex:
                self.currentTagIndex = currentTagIndex
                self.dropTimer.start()
            #to enable item highlight at least for dbmodel drag we need this,
            #otherwise it will not show the right cursor icon when dragging from external sources
            if 'application/x-qabstractitemmodeldatalist' in formats:
                QtWidgets.QTreeView.dragMoveEvent(self, event)

    def dragLeaveEvent(self, event):
        self.currentTagIndex = None
        self.dropTimer.stop()
        event.accept()

    def dropEvent(self, event):
        self.dropTimer.stop()
        currentTagIndex = self.indexAt(event.pos())
        formats = event.mimeData().formats()
        if not 'text/uri-list' in formats and (
            'application/x-qabstractitemmodeldatalist' in formats and (
                not currentTagIndex.isValid() or currentTagIndex in (self.model().index(0, 0), self.model().index(0, 1)))):
            event.ignore()
            return
        event.accept()

        if 'application/x-qabstractitemmodeldatalist' in formats:
            itemsDict = {}
            data = event.mimeData().data('application/x-qabstractitemmodeldatalist')
            stream = QtCore.QDataStream(data)
            while not stream.atEnd():
                row = stream.readInt32()
                if not row in itemsDict:
                    itemsDict[row] = {}
                #column is ignored
                stream.readInt32()
                items = stream.readInt32()
                for i in range(items):
                    key = stream.readInt32()
                    value = stream.readQVariant()
                    itemsDict[row][key] = value
            sampleList = [row[FilePathRole] for row in itemsDict.values()]
            #TODO: use indexFromPath?
            currentTag = currentTagIndex.data()
            parentIndex = currentTagIndex.parent()
            while parentIndex != self.model().index(0, 0):
                currentTag = '{}/{}'.format(parentIndex.data(), currentTag)
                parentIndex = parentIndex.parent()
            self.samplesAddedToTag.emit(sampleList, currentTag)
        elif 'text/uri-list' in formats:
            tag = self.model().sourceModel().pathFromIndex(self.model().mapToSource(currentTagIndex))
            urlList = str(event.mimeData().data('text/uri-list'), encoding='ascii').split()
            fileList = []
            dirList = []
            for encodedUrl in urlList:
                fileInfo = QtCore.QFileInfo(QtCore.QUrl(encodedUrl).toLocalFile())
                if fileInfo.isDir():
                    dirList.append(fileInfo.absoluteFilePath())
                else:
                    fileList.append(fileInfo.absoluteFilePath())
            if dirList:
                scanOptionsDialog = ScanOptionsDialog(self)
                if not scanOptionsDialog.exec_():
                    return
                scanMode = scanOptionsDialog.scanModeCombo.currentIndex()
                formats = scanOptionsDialog.getFormats()
                sampleRates = scanOptionsDialog.getSampleRates()
                channels = scanOptionsDialog.channelsCombo.currentIndex()
                scanLimits = scanOptionsDialog.getScanLimits()
            else:
                scanMode = 0
                formats = True
                sampleRates = True
                channels = 0
                scanLimits = None, None, None, None
            res = ImportDialogScanDnD(self.main, dirList, fileList, scanMode, formats, sampleRates, channels, scanLimits, tag).exec_()
            if not res:
                return
            self.samplesImported.emit([(filePath, fileName, info, tags) for (filePath, fileName, info, tags) in res], currentTagIndex)

