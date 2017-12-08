#!/usr/bin/env python3
# *-* coding: utf-8 *-*

import sys
from PyQt5 import QtCore, QtGui, QtWidgets


class SplitterHandle(QtWidgets.QSplitterHandle):
    moved = QtCore.pyqtSignal(QtCore.QPoint)
    acquired = QtCore.pyqtSignal(QtCore.QPoint)
    released = QtCore.pyqtSignal(QtCore.QPoint)
    grad = QtGui.QConicalGradient(.5, .5, -45)
    grad.setCoordinateMode(grad.ObjectBoundingMode)
    grad.setColorAt(0, QtCore.Qt.white)
    grad.setColorAt(.5, QtCore.Qt.lightGray)
    grad.setColorAt(1, QtCore.Qt.white)
    def mousePressEvent(self, event):
        QtWidgets.QSplitterHandle.mousePressEvent(self, event)
        self.acquired.emit(event.pos())

    def mouseMoveEvent(self, event):
        QtWidgets.QSplitterHandle.mouseMoveEvent(self, event)
        self.moved.emit(event.pos())

    def mouseReleaseEvent(self, event):
        QtWidgets.QSplitterHandle.mouseReleaseEvent(self, event)
        self.released.emit(event.pos())

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, 1.5)
#        QtGui.qDrawShadeLine(qp, 0, self.height() / 2, self.width() - 1, self.height() / 2, self.palette(), sunken=True)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.grad)
        repeat = self.width() // 120
        ratio = self.width() / (repeat if repeat else 1)
        mid = ratio / 2 - 4
        for delta in range(repeat):
            qp.drawEllipse(mid, 0, 3, 3)
            qp.drawEllipse(mid + 3, 0, 3, 3)
            qp.drawEllipse(mid + 6, 0, 3, 3)
            qp.translate(ratio, 0)
        qp.end()


class SplitterHeader(QtWidgets.QWidget):
    upPath = QtGui.QPainterPath()
    upPath.moveTo(0, 6)
    upPath.lineTo(4, 0)
    upPath.lineTo(8, 6)
    downPath = QtGui.QPainterPath()
    downPath.moveTo(0, 0)
    downPath.lineTo(4, 6)
    downPath.lineTo(8, 0)
    arrowPaths = upPath, downPath
    toggled = QtCore.pyqtSignal(bool)
    def __init__(self, text='', orientation=QtCore.Qt.Vertical, hideable=True):
        QtWidgets.QWidget.__init__(self)
        self.text = text
        self.hideable = hideable
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum))
        self.state = False

        self._borderColor = QtGui.QColor(20, 20, 20, 20)
        self.hoverBorderAnimation = QtCore.QPropertyAnimation(self, b'borderColor')
        self.hoverBorderAnimation.setDuration(100)
        self.hoverBorderAnimation.setStartValue(self._borderColor)
        self.hoverBorderAnimation.setEndValue(QtGui.QColor(150, 150, 150, 150))

    def minimumSizeHint(self):
        return QtCore.QSize(32, self.fontMetrics().height() + 4)

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        rect = QtCore.QRect(0, 0, self.width() - 1, self.height() - 1)
        textRect = QtCore.QRect(rect)
        textRect.setLeft(4)
        textRect.setRight(textRect.width() - (16 if self.hideable else 0))
        qp.begin(self)
        qp.setPen(self._borderColor)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        qp.drawRoundedRect(rect, 2, 2)
        qp.setPen(QtCore.Qt.black)
        qp.drawText(textRect, QtCore.Qt.AlignVCenter|QtCore.Qt.AlignLeft, self.fontMetrics().elidedText(self.text, QtCore.Qt.ElideRight, textRect.width()))
        if self.hideable:
            qp.translate(self.width() - 8 - 8, (self.height() - 6) / 2)
            qp.drawPath(self.arrowPaths[not self.state])
        qp.end()

    def mousePressEvent(self, event):
        if self.hideable and event.button() == QtCore.Qt.LeftButton:
            self.state = not self.state
            self.toggled.emit(self.state)

    def toggle(self, state):
        self.state = state
        self.update()

    @QtCore.pyqtProperty(QtGui.QColor)
    def borderColor(self):
        return self._borderColor

    @borderColor.setter
    def borderColor(self, color):
        self._borderColor = color
        self.update()

    def enterEvent(self, event):
        self.hoverBorderAnimation.setDirection(self.hoverBorderAnimation.Forward)
        self.hoverBorderAnimation.start()

    def leaveEvent(self, event):
        self.hoverBorderAnimation.setDirection(self.hoverBorderAnimation.Backward)
        self.hoverBorderAnimation.start()

class SplitterContainer(QtWidgets.QWidget):
    def __init__(self, widget, label, orientation=QtCore.Qt.Vertical, collapsible=True, hideable=True):
        QtWidgets.QWidget.__init__(self)
        self.widget = widget
        self.collapsible = collapsible
        layout = QtWidgets.QHBoxLayout() if orientation == QtCore.Qt.Horizontal else QtWidgets.QVBoxLayout()
        layout.setSizeConstraint(layout.SetMinimumSize)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.header = SplitterHeader(label, orientation=orientation, hideable=True if collapsible else hideable)
        self.header.toggled.connect(self.setCollapsed)
        layout.addWidget(self.header)
        layout.addWidget(widget)
        widget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.handlePos = QtCore.QPoint()
        self.referencePos = QtCore.QPoint()

    def setHandle(self, handle):
        self.handle = handle
        handle.acquired.connect(self.handleAcquired)
        handle.moved.connect(self.handleMoved)
        handle.released.connect(self.handleReleased)

    @QtCore.pyqtSlot(QtCore.QPoint)
    def handleAcquired(self, pos):
        self.handlePos = pos

    @QtCore.pyqtSlot(QtCore.QPoint)
    def handleReleased(self, pos):
        self.handlePos = QtCore.QPoint()
        self.referencePos = QtCore.QPoint()

    @QtCore.pyqtSlot(QtCore.QPoint)
    def handleMoved(self, pos):
        if not self.collapsible:
            return
        if pos.y() > self.header.height() + self.layout().spacing():
            if not self.collapsed:
                if self.referencePos:
                    if pos.y() < self.referencePos.y() + 8:
                        return
                self.handlePos = QtCore.QPoint(pos.x() - self.widget.minimumSizeHint().width(), pos.y() - self.widget.minimumSizeHint().height() - self.layout().spacing())
                self.referencePos = QtCore.QPoint(self.handlePos)
                self.setCollapsed(True)
            else:
                #emit signal to parent?
                pass
        elif pos.y() < 0:
#            if pos.y() > self.handlePos.y():
#                if pos.y() > self.referencePos.y() + 4:
#                    #increase
#                    self.referencePos = QtCore.QPoint(pos)
            if pos.y() < self.handlePos.y():
                if pos.y() < self.referencePos.y() - 8:
                    self.setCollapsed(False)
                    self.referencePos = QtCore.QPoint(pos.x() + self.widget.minimumSizeHint().width(), pos.y() + self.widget.minimumSizeHint().height() + self.layout().spacing())
            self.handlePos = pos

    @QtCore.pyqtProperty(bool)
    def collapsed(self):
        return not self.widget.isVisible()

    @collapsed.setter
    def collapsed(self, collapsed):
        self.widget.setVisible(not collapsed)
        self.header.toggle(collapsed)
        if collapsed:
            self.setMaximumHeight(self.header.height())
        else:
            self.setMaximumHeight(16777215)

    def isCollapsed(self):
        return self.collapsed

    @QtCore.pyqtSlot(bool)
    def setCollapsed(self, state):
        self.collapsed = state

    @QtCore.pyqtProperty(QtCore.QSize)
    def widgetSizeHint(self):
        return self.widget.sizeHint()


class AdvancedSplitter(QtWidgets.QSplitter):
    def __init__(self, *args, **kwargs):
        QtWidgets.QSplitter.__init__(self, *args, **kwargs)
        self.setHandleWidth(7)

    def createHandle(self):
        return SplitterHandle(self.orientation(), self)

    def addWidget(self, widget, label=None, collapsible=True, hideable=True):
        if label is None:
            QtWidgets.QSplitter.addWidget(self, widget)
            QtWidgets.QSplitter.setCollapsible(self, self.indexOf(widget), collapsible)
            return
        parentWidget = SplitterContainer(widget, label, orientation=self.orientation(), collapsible=collapsible, hideable=hideable)
        QtWidgets.QSplitter.addWidget(self, parentWidget)
        index = self.indexOf(parentWidget)
        QtWidgets.QSplitter.setCollapsible(self, index, False)
        parentWidget.setHandle(self.handle(index))


class _ExampleWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        QtWidgets.QWidget.__init__(self, *args, **kwargs)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        self.splitter = AdvancedSplitter(QtCore.Qt.Vertical)
        layout.addWidget(self.splitter)
        edit = QtWidgets.QLineEdit()
        self.splitter.addWidget(edit)
        tree = QtWidgets.QTreeView()
        self.splitter.addWidget(tree, label='Tree with very long text header', collapsible=False)
        self.splitter.addWidget(QtWidgets.QPushButton('Some button'), label='Another header')


def _main():
    app = QtWidgets.QApplication(sys.argv)
    player = _ExampleWidget()
    player.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    _main()
