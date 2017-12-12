from PyQt5 import QtCore, QtGui, QtWidgets
from samplebrowsesrc import utils
from samplebrowsesrc.constants import *

class TagTreeDelegate(QtWidgets.QStyledItemDelegate):
    tagColorsChanged = QtCore.pyqtSignal(object, object, object)
    startEditTag = QtCore.pyqtSignal(object)
    removeTag = QtCore.pyqtSignal(object)
    def editorEvent(self, event, model, _option, index):
        if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.RightButton:
            if index != model.index(0, 0):
                menu = QtWidgets.QMenu()
                editTagAction = QtWidgets.QAction('Rename tag...', menu)
                editColorAction = QtWidgets.QAction('Edit tag color...', menu)
                removeTagAction = QtWidgets.QAction('Remove tag', menu)
                menu.addActions([editTagAction, editColorAction, utils.menuSeparator(menu), removeTagAction])
                res = menu.exec_(_option.widget.viewport().mapToGlobal(event.pos()))
                if res == editColorAction:
                    #TODO: Temporary fix for circular import?
                    from samplebrowsesrc.dialogs import TagColorDialog
                    colorDialog = TagColorDialog(_option.widget.window(), index)
                    if colorDialog.exec_():
                        model.setData(index, colorDialog.foregroundColor, QtCore.Qt.ForegroundRole)
                        model.setData(index, colorDialog.backgroundColor, QtCore.Qt.BackgroundRole)
                        self.tagColorsChanged.emit(index, colorDialog.foregroundColor, colorDialog.backgroundColor)
                elif res == editTagAction:
                    self.startEditTag.emit(index)
                elif res == removeTagAction:
                    self.removeTag.emit(index)
                return True
            return True
        return QtWidgets.QStyledItemDelegate.editorEvent(self, event, model, _option, index)

    def createEditor(self, parent, option, index):
        widget = QtWidgets.QStyledItemDelegate.createEditor(self, parent, option, index)
        widget.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp(r'[^\/,]+')))
        return widget

    def setModelData(self, widget, model, index):
        if not widget.text():
            return
        QtWidgets.QStyledItemDelegate.setModelData(self, widget, model, index)


class SampleControlDelegate(QtWidgets.QStyledItemDelegate):
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
        return QtWidgets.QStyledItemDelegate.editorEvent(self, event, model, option, index)


class SubtypeDelegate(QtWidgets.QStyledItemDelegate):
    def sizeHint(self, option, index):
        sizeHint = QtWidgets.QStyledItemDelegate.sizeHint(self, option, index)
        sizeHint.setWidth(option.fontMetrics.width('64f') + 10)
        return sizeHint

    def paint(self, painter, option, index):
        option.text = subtypesDict.get(index.data())
        option.displayAlignment = QtCore.Qt.AlignCenter
        QtWidgets.QStyledItemDelegate.paint(self, painter, option, QtCore.QModelIndex())


class AlignItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, alignment, elideMode=QtCore.Qt.ElideRight):
        QtWidgets.QStyledItemDelegate.__init__(self)
        self.alignment = alignment
        if not alignment & (QtCore.Qt.AlignTop|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignBottom):
            self.alignment |= QtCore.Qt.AlignVCenter
        self.elideMode = elideMode

    def paint(self, painter, option, index):
        option.displayAlignment = self.alignment
        option.textElideMode = self.elideMode
        return QtWidgets.QStyledItemDelegate.paint(self, painter, option, index)


class TagListDelegate(QtWidgets.QStyledItemDelegate):
    tagSelected = QtCore.pyqtSignal(str)
    def __init__(self, tagColorsDict, *args, **kwargs):
        QtWidgets.QStyledItemDelegate.__init__(self, *args, **kwargs)
        self.tagColorsDict = tagColorsDict

    def sizeHint(self, option, index):
        sizeHint = QtWidgets.QStyledItemDelegate.sizeHint(self, option, index)
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
        return QtWidgets.QStyledItemDelegate.editorEvent(self, event, model, option, index)

    def paint(self, painter, _option, index):
        if not index.isValid():
            QtWidgets.QStyledItemDelegate.paint(self, painter, _option, index)
            return
        option = QtWidgets.QStyleOptionViewItem()
        option.__init__(_option)
        self.initStyleOption(option, QtCore.QModelIndex())
        option.text = ''
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter)

        tagList = index.data(TagsRole)
        if not tagList:
            return
        pos = index.data(HoverRole) if option.state & QtWidgets.QStyle.State_MouseOver else False
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


