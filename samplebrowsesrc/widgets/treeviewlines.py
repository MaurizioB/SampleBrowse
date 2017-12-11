from PyQt5 import QtCore, QtWidgets

class TreeViewWithLines(QtWidgets.QTreeView):
    def drawRow(self, painter, option, index):
        QtWidgets.QTreeView.drawRow(self, painter, option, index)
        painter.setPen(QtCore.Qt.lightGray)
        y = option.rect.y()
        painter.save()
        for sectionId in range(self.header().count()):
            painter.drawLine(0, y, 0, y + option.rect.height())
            painter.translate(self.header().sectionSize(sectionId), 0)
        painter.restore()
