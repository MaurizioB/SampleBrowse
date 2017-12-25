from PyQt5 import QtCore, QtWidgets

from samplebrowsesrc.utils import HoverDecorator

@HoverDecorator
class FsTreeView(QtWidgets.QTreeView):
    def __init__(self, *args, **kwargs):
        QtWidgets.QTreeView.__init__(self, *args, **kwargs)
        self.currentRequest = None
        self.currentTimer = QtCore.QTimer()
        self.currentTimer.setSingleShot(True)
        self.currentTimer.setInterval(1000)
        self.currentTimer.timeout.connect(self.resetCurrent)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space and self.currentIndex().isValid():
            self.activated.emit(self.currentIndex())
        else:
            QtWidgets.QTreeView.keyPressEvent(self, event)

    def setModel(self, model):
        QtWidgets.QTreeView.setModel(self, model)
        model.sourceModel().directoryLoaded.connect(self.scrollToCheck)

    def resetCurrent(self):
        self.currentRequest = None

    def scrollToCheck(self, loadedDirPath):
        if not self.currentRequest:
            return
        dirPath = self.currentRequest
        if loadedDirPath != dirPath:
            return
        #we need to track again the index, because its dynamically created
        dirIndex = self.model().mapFromSource(self.model().sourceModel().index(dirPath))
        self.currentTimer.stop()
        self.currentRequest = None
        self.scrollTo(dirIndex, self.PositionAtTop)
        self.setCurrentIndex(dirIndex)

    def scrollToPath(self, dirPath):
        dirIndex = self.model().mapFromSource(self.model().sourceModel().index(dirPath))
        if not dirIndex.isValid():
            return
        if not self.isExpanded(dirIndex.parent()):
            self.currentRequest = dirPath
            self.currentTimer.start()
        self.expand(dirIndex)
        self.scrollTo(dirIndex, self.PositionAtTop)
        self.setCurrentIndex(dirIndex)
        self.clicked.emit(dirIndex)

