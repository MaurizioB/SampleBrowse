import sys
from threading import Event
import soundfile
from PyQt5 import QtCore, QtGui
from samplebrowsesrc.constants import *


class DbDirModel(QtGui.QStandardItemModel):
    loaded = QtCore.pyqtSignal()
    def __init__(self, db, *args, **kwargs):
        QtGui.QStandardItemModel.__init__(self, *args, **kwargs)
        self.db = db
#        self.updateTree()
#        self.rootItem = QtGui.QStandardItem('/')
#        self.appendRow(self.rootItem)

    def updateTree(self):
        self.db.execute('SELECT filePath FROM samples')
        root = '/' if sys.platform != 'win32' else ''
        for data in self.db.fetchall():
            filePath = data[0]
            fileInfo = QtCore.QFileInfo(filePath)
            qdir = fileInfo.absoluteDir()
            dirTree = tuple(filter(None, qdir.absolutePath().split('/')))
            depth = 0
            parentIndex = QtCore.QModelIndex()
            sep = QtCore.QDir.separator()
            while depth < len(dirTree):
                subdir = '{}'.format(dirTree[depth])
                if depth == 0:
                    subdir = '{root}{subdir}'.format(root=root, subdir=subdir)
                dirMatch = self.match(self.index(0, 0, parentIndex), DirNameRole, subdir, flags=QtCore.Qt.MatchExactly)
                if not dirMatch:
                    childItem = QtGui.QStandardItem('{subdir}{sep}'.format(subdir=subdir, sep=sep))
                    childItem.setData(subdir, DirNameRole)
                    childItem.setData('{root}{dirTree}'.format(root=root, dirTree='/'.join(dirTree[:depth + 1])), FilePathRole)
                    countItem = QtGui.QStandardItem('1')
                    try:
                        self.itemFromIndex(parentIndex).appendRow([childItem, countItem])
                    except:
                        self.appendRow([childItem, countItem])
                    parentIndex = childItem.index()
                    depth += 1
                    continue
                parentIndex = dirMatch[0]
                countIndex = parentIndex.sibling(parentIndex.row(), 1)
                self.setData(countIndex, '{}'.format(int(countIndex.data()) + 1))
                depth += 1
        self.optimizeTree()
        self.loaded.emit()


    def optimizeTree(self):
        for row in range(self.rowCount()):
            self.optimizeItemTree(self.item(row))

    def optimizeItemTree(self, parent):
        if not parent.rowCount():
            return True
        if parent.rowCount() > 1:
            for row in range(parent.rowCount()):
                self.optimizeItemTree(parent.child(row))
            return False
        child = parent.child(0)
        if self.optimizeItemTree(child):
            parent.takeRow(0)
            parent.setText('{parent}{sep}{child}'.format(parent=parent.data(DirNameRole), sep=QtCore.QDir.separator(), child=child.text()))
            parent.setData(child.data(FilePathRole), FilePathRole)
            return True

class TagsModel(QtGui.QStandardItemModel):
    tagRenamed = QtCore.pyqtSignal(str, str)
    def __init__(self, db, *args, **kwargs):
        QtGui.QStandardItemModel.__init__(self, *args, **kwargs)
        self.db = db
        self.totalCountItem = QtGui.QStandardItem('0')
        self.appendRow([QtGui.QStandardItem('All samples'), self.totalCountItem])
        self.tags = set()
        self.dataChanged.connect(self.updateTags)

    def pathFromIndex(self, index):
        if not index.isValid():
            return ''
        currentTag = index.data()
        parentIndex = index.parent()
        while parentIndex != self.index(0, 0):
            currentTag = '{}/{}'.format(parentIndex.data(), currentTag)
            parentIndex = parentIndex.parent()
        return currentTag

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
        self.dataChanged.disconnect(self.updateTags)
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
        self.dataChanged.connect(self.updateTags)

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
            for tag in item[tagsColumn].split(','):
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

    def updateTags(self, index, _):
        self.dataChanged.disconnect(self.updateTags)
        if not index.data(TagsRole) or index.data() == index.data(TagsRole):
            #check model editing status
            self.setData(index, None, TagsRole)
            self.dataChanged.connect(self.updateTags)
            return
        currentNewTag = index.data()
        currentOldTag = index.data(TagsRole)
        self.setData(index, None, TagsRole)
        parent = index.parent()
        while parent != self.index(0, 0):
            currentNewTag = '{}/{}'.format(parent.data(), currentNewTag)
            currentOldTag = '{}/{}'.format(parent.data(), currentOldTag)
            parent = parent.parent()
        self.tagRenamed.emit(currentNewTag, currentOldTag)
        self.setData(index, None, TagsRole)
        self.dataChanged.connect(self.updateTags)


class SampleSortFilterProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        QtCore.QSortFilterProxyModel.__init__(self, *args, **kwargs)
        self.currentFilterData = {}
        self.currentTextFilter = ''

    def itemFromIndex(self, index):
        return self.sourceModel().itemFromIndex(self.mapToSource(index))
#        self.dbProxyModel.setFilterRegExp(text)

    def setFilterData(self, filterDataList):
        self.currentFilterData = {}
        for filterColumn, filterData in filterDataList:
            if filterColumn == fileNameColumn:
                self.currentTextFilter = filterData
                continue
            self.currentFilterData[filterColumn] = filterData
        self.invalidateFilter()
#        print(self.currentFilterData)

    def filterAcceptsRow(self, row, parent):
        if not self.currentFilterData:
            if not self.currentTextFilter:
                return True
            if self.currentTextFilter.lower() in self.sourceModel().item(row, fileNameColumn).text().lower():
                return True
        else:
            for filterColumn, filterData in self.currentFilterData.items():
                if isinstance(filterData, list):
                    for item in filterData:
                        if self.sourceModel().item(row, filterColumn).data(DataRole) == item:
                            break
                    else:
                        return False
                else:
                    value = self.sourceModel().item(row, filterColumn).data(DataRole)
                    if filterData.greater:
                        greater, greaterEqual = filterData.greater
                        greater = float(greater)
                        if (greater > value) or (not greaterEqual and greater >= value):
                            return False
                    if filterData.less:
                        less, lessEqual = filterData.less
                        less = float(less)
                        if (less < value) or (not lessEqual and less <= value):
                            return False
            if not self.currentTextFilter or self.currentTextFilter.lower() in self.sourceModel().item(row, fileNameColumn).text().lower():
                return True
        return False


class MultiDirIterator(object):
    def __init__(self, dirList, *args, **kwargs):
        self.dirList = dirList
        iteratorList = []
        for dir in dirList:
            iteratorList.append(QtCore.QDirIterator(dir, *args, **kwargs))
        self.iterators = iter(iteratorList)
        self.currentIterator = self.iterators.next()

    def hasNext(self):
        if self.currentIterator.hasNext():
            return True
        try:
            self.currentIterator = self.iterators.next()
            return self.hasNext()
        except:
            return False

    def next(self):
        next = self.currentIterator.next()
        if next:
            return next
        if self.hasNext():
            return self.next()
        else:
            return False


class DirIterator(object):
    def __new__(self, dirList, *args, **kwargs):
        if isinstance(dirList, str):
            return QtCore.QDirIterator(dirList, *args, **kwargs)
        if len(dirList) == 1:
            return QtCore.QDirIterator(dirList[0], *args, **kwargs)
        return MultiDirIterator(self, dirList, *args, **kwargs)


class Crawler(QtCore.QObject):
    currentBrowseDir = QtCore.pyqtSignal(str)
    found = QtCore.pyqtSignal(object, object)
    done = QtCore.pyqtSignal()
    def __init__(self, dirPath, scanMode, formats, sampleRates, channels, scanLimits):
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
        self.bigger, self.smaller, self.longer, self.shorter = scanLimits

        if self.bigger and self.smaller:
            self.methodList.append(self.checkSize)
        elif self.bigger:
            self.methodList.append(self.checkSizeBigger)
        elif self.smaller:
            self.methodList.append(self.checkSizeSmaller)

        if self.longer and self.shorter:
            self.methodList.append(self.checkLength)
        elif self.longer:
            self.methodList.append(self.checkLengthLonger)
        elif self.shorter:
            self.methodList.append(self.checkLengthShorter)


        if scanMode:
            if not isinstance(formats, (list, tuple)):
                formats = [f for f in soundfile.available_formats().keys()]
            self.iterator = DirIterator(
                dirPath, ['*.{}'.format(f) for f in formats], QtCore.QDir.Files, flags=QtCore.QDirIterator.Subdirectories|QtCore.QDirIterator.FollowSymlinks)
        else:
            if isinstance(formats, (list, tuple)):
                self.methodList.insert(0, self.checkFormat)
            self.iterator = DirIterator(
                dirPath, QtCore.QDir.Files, flags=QtCore.QDirIterator.Subdirectories|QtCore.QDirIterator.FollowSymlinks)

    def checkFormat(self, fileInfo, info):
        return info.format in self.formats

    def checkSampleRate(self, fileInfo, info):
        return info.samplerate in self.sampleRates

    def checkChannels(self, fileInfo, info):
        return info.channels == self.channels

    def checkSize(self, fileInfo, info):
        return self.bigger <= fileInfo.size() <= self.smaller

    def checkSizeBigger(self, fileInfo, info):
        return self.bigger <= fileInfo.size()

    def checkSizeSmaller(self, fileInfo, info):
        return fileInfo.size() <= self.smaller

    def checkLength(self, fileInfo, info):
        return self.longer <= info.frames / info.samplerate <= self.shorter

    def checkLengthLonger(self, fileInfo, info):
        return self.longer <= info.frames / info.samplerate

    def checkLengthShorter(self, fileInfo, info):
        return info.frames / info.samplerate <= self.shorter


    def run(self):
        while self.iterator.hasNext() and not self.stop.is_set():
            filePath = self.iterator.next()
            fileInfo = self.iterator.fileInfo()
#            use an internal function to update directory?
#            self.currentBrowseDir.emit(self.iterator.filePath())
            try:
                info = soundfile.info(filePath)
                for method in self.methodList:
                    if not method(fileInfo, info):
                        break
                else:
                    self.found.emit(fileInfo, info)
            except:
                pass
        self.done.emit()


