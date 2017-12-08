from PyQt4 import QtCore, QtGui
from src.constants import *


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


class SubtypeDelegate(QtGui.QStyledItemDelegate):
    def sizeHint(self, option, index):
        sizeHint = QtGui.QStyledItemDelegate.sizeHint(self, option, index)
        sizeHint.setWidth(option.fontMetrics.width('64f') + 10)
        return sizeHint

    def paint(self, painter, option, index):
        option.text = subtypesDict.get(index.data())
        option.displayAlignment = QtCore.Qt.AlignCenter
        QtGui.QStyledItemDelegate.paint(self, painter, option, QtCore.QModelIndex())


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


