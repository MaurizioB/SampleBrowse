import soundfile
from PyQt5 import QtCore, QtGui, QtWidgets

from samplebrowsesrc.constants import *


class FilterCloseButton(QtWidgets.QAbstractButton):
    backgroundOut = QtCore.Qt.darkGray
    backgroundIn = QtGui.QColor('#ba0003')
    backgroundBrushes = backgroundOut, backgroundIn
    def __init__(self, parent=None):
        QtWidgets.QAbstractButton.__init__(self, parent)
        self.setMaximumSize(16, 16)
        self.backgroundBrush = self.backgroundBrushes[0]

    def enterEvent(self, event):
        self.backgroundBrush = self.backgroundBrushes[1]
        self.update()

    def leaveEvent(self, event):
        self.backgroundBrush = self.backgroundBrushes[0]
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(self.backgroundBrush)
        qp.drawEllipse(2, 2, 12, 12)
        qp.setPen(QtCore.Qt.white)
        qp.drawLine(6, 6, 11, 11)
        qp.drawLine(6, 10, 11, 5)
        qp.end()


class FilterWidget(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal()
    deleted = QtCore.pyqtSignal(object)
    resized = QtCore.pyqtSignal()
    validColor = QtCore.Qt.black
    invalidColor = QtCore.Qt.red
    headerColors = invalidColor, validColor
    def __init__(self, header, field, parent, fmtString=None, fmtFunc=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.closeBtn = FilterCloseButton(self)
        self.closeBtn.clicked.connect(lambda: self.deleted.emit(self))
        self.valid = False
        self.hMargin = 4
        self.header = header
        self.field = field
        self.contentWidth = 0
        self.fmtString = fmtString
        self.fmtFunc = fmtFunc
        self.setContent()

    def data(self):
        return self.contents if self.valid else None

    def setContent(self, contentList=None):
        if not contentList:
            self.contents = ['None']
            self.contentWidth = self.fontMetrics().width('None') + self.hMargin * 2
            self.valid = False
        else:
            self.contents = contentList[:]
            self.contentWidth = sum([self.fontMetrics().width(content) for content in contentList]) + self.hMargin * (len(contentList) * 2 + 1)
            self.valid = True
        self.resizeToContents()
        self.changed.emit()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.editFilter()

    def editFilter(self, editor):
        editor.changed.connect(self.setContent)
        editor.closed.connect(lambda: [editor.changed.disconnect(), editor.deleteLater()])
        editor.move(self.mapToGlobal(QtCore.QPoint(0, self.height())))
        editor.show()

    def paintPrimitive(self):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.setRenderHints(qp.Antialiasing)
        qp.translate(.5, .5)
        QtWidgets.qDrawShadePanel(qp, 2, 2, self.width() - 2, self.height() - 2, self.palette(), sunken=False)
        qp.setPen(self.headerColors[self.valid])
        baseWidth = self.fontMetrics().width(self.header) + self.hMargin
        qp.drawText(self.hMargin, 0, baseWidth, self.height(), QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter, self.header)
        qp.translate(baseWidth, 0)
        return qp

    def resizeToContents(self):
        size = self.fontMetrics().width(self.header) + self.hMargin * 2 + self.closeBtn.width() + self.contentWidth
        self.setMinimumWidth(size)
        self.setMaximumWidth(size)
        self.closeBtn.move(self.width() - self.closeBtn.width() - self.hMargin, (self.height() - self.closeBtn.height()) / 2)
        self.update()
        self.resized.emit()

    def showEvent(self, event):
        self.resizeToContents()

    def resizeEvent(self, event):
        self.resizeToContents()

    def paintEvent(self, event):
        qp = self.paintPrimitive()
        qp.setBrush(QtCore.Qt.darkGray)
        qp.setPen(QtCore.Qt.white)
        for content in self.contents:
            if self.fmtString:
                try:
                    if self.fmtFunc:
                        content = self.fmtString.format(self.fmtFunc(content))
                    else:
                        content = self.fmtString.format(content)
                except:
                    pass
            rect = QtCore.QRect(0, self.hMargin, self.fontMetrics().width(content) + self.hMargin * 2, self.height() - self.hMargin * 2)
            qp.drawRoundedRect(rect, 2, 2)
            rect = QtCore.QRect(2, self.hMargin, rect.width() -4, rect.height())
            qp.drawText(rect, QtCore.Qt.AlignCenter, content)
            qp.translate(rect.width() + self.hMargin, 0)


class BaseSelectionWidget(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal(object)
    closed = QtCore.pyqtSignal()
    def __init__(self, parent, context, selected):
        QtWidgets.QWidget.__init__(self, parent, QtCore.Qt.Popup)
        self.setWindowModality(QtCore.Qt.WindowModal)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.listView = QtWidgets.QListView()
        layout.addWidget(self.listView)
        self.model = QtGui.QStandardItemModel()
        self.listView.setModel(self.model)
        self.model.dataChanged.connect(self.checkData)
        self.listView.setEditTriggers(self.listView.NoEditTriggers)
#        self.listView.clicked.connect(self.toggleItem)
        self.listView.doubleClicked.connect(self.toggleItem)
        checked = []
        unchecked = []
        for label, data in context:
            item = QtGui.QStandardItem(label)
            item.setData(data)
            item.setCheckable(True)
            if data in selected:
                item.setCheckState(QtCore.Qt.Checked)
                checked.append(item)
            else:
                item.setCheckState(QtCore.Qt.Unchecked)
                unchecked.append(item)
        for item in checked + unchecked:
            self.model.appendRow(item)

    def toggleItem(self, index):
        self.model.setData(index, QtCore.Qt.Unchecked if index.data(QtCore.Qt.CheckStateRole) else QtCore.Qt.Checked, QtCore.Qt.CheckStateRole)

    def checkData(self):
        data = []
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item.checkState():
                data.append(item.data())
        self.changed.emit(data)

    def hideEvent(self, event):
        self.closed.emit()


class FormatFilterWidget(FilterWidget):
    def __init__(self, parent):
        FilterWidget.__init__(self, 'Formats: ', formatColumn, parent)
        
    def editFilter(self):
        context = [(soundfile.available_formats()[ext], ext) for ext in sorted(soundfile.available_formats().keys())]
        editor = BaseSelectionWidget(self, context, self.contents)
        FilterWidget.editFilter(self, editor)


class SampleRateFilterWidget(FilterWidget):
    def __init__(self, parent):
        func = lambda v: int(v)/1000.
        FilterWidget.__init__(self, 'Sample rates: ', rateColumn, parent, fmtString='{:.1f} kHz', fmtFunc=func)
        
    def editFilter(self):
        context = [('{:.1f} kHz'.format(sampleRate/1000.), str(sampleRate)) for sampleRate in sampleRatesList]
        editor = BaseSelectionWidget(self, context, self.contents)
        FilterWidget.editFilter(self, editor)


class RangeSelectionWidget(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal(object, object)
    closed = QtCore.pyqtSignal()
    def __init__(self, parent, context, greater, less):
        QtWidgets.QWidget.__init__(self, parent, QtCore.Qt.Popup)
        self.setWindowModality(QtCore.Qt.WindowModal)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        palette = self.palette()
        enabled = palette.color(palette.Active, palette.ButtonText)
        disabled = palette.color(palette.Disabled, palette.ButtonText)
        self.setStyleSheet('''
            QCheckBox:checked {{
                color: {enabled};
            }}
            QCheckBox:disabled {{
                color: {disabled}
            }}
            QCheckBox:unchecked {{
                color: {disabled};
            }}
            '''.format(enabled=enabled.name(), disabled=disabled.name()))

        self.lessChk = QtWidgets.QCheckBox('Less than')
        layout.addWidget(self.lessChk, 0, 0)
        self.lessOrEqualChk = QtWidgets.QCheckBox('or equal to')
        layout.addWidget(self.lessOrEqualChk, 0, 1)
        self.lessCombo = QtWidgets.QComboBox()
        layout.addWidget(self.lessCombo, 0, 2)

        self.greaterChk = QtWidgets.QCheckBox('Greater than')
        layout.addWidget(self.greaterChk, 1, 0)
        self.greaterOrEqualChk = QtWidgets.QCheckBox('or equal to')
        layout.addWidget(self.greaterOrEqualChk, 1, 1)
        self.greaterCombo = QtWidgets.QComboBox()
        layout.addWidget(self.greaterCombo,1, 2)

        for label, data in context:
            self.lessCombo.addItem(label, data)
            self.greaterCombo.addItem(label, data)

        if less:
            lessValue, lessEqual = less
            self.lessChk.setChecked(True)
            self.lessOrEqualChk.setChecked(lessEqual)
            self.lessCombo.setCurrentIndex(self.lessCombo.findData(lessValue))
        if greater:
            greaterValue, greaterEqual = greater
            self.greaterChk.setChecked(True)
            self.greaterOrEqualChk.setChecked(greaterEqual)
            self.greaterCombo.setCurrentIndex(self.greaterCombo.findData(greaterValue))

        self.lessChk.toggled.connect(self.checkData)
        self.greaterChk.toggled.connect(self.checkData)
        self.lessOrEqualChk.toggled.connect(self.checkData)
        self.greaterOrEqualChk.toggled.connect(self.checkData)
        self.lessCombo.currentIndexChanged.connect(self.checkData)
        self.greaterCombo.currentIndexChanged.connect(self.checkData)

        self.checkData()

    def checkData(self, *args):
        less = self.lessChk.isChecked()
        lessValue = self.lessCombo.currentData()
        lessEqual = self.lessOrEqualChk.isChecked()
        self.lessOrEqualChk.setEnabled(less)
        self.lessCombo.setEnabled(less)
        greater = self.greaterChk.isChecked()
        greaterValue = self.greaterCombo.currentData()
        greaterEqual = self.greaterOrEqualChk.isChecked()
        self.greaterOrEqualChk.setEnabled(greater)
        self.greaterCombo.setEnabled(greater)
        self.changed.emit((greaterValue, greaterEqual) if greater else None, (lessValue, lessEqual) if less else None)

    def hideEvent(self, event):
        self.closed.emit()


#TODO: needs a good fix for value conversion
class SampleRateRangeFilterWidget(FilterWidget):
    def __init__(self, parent):
        FilterWidget.__init__(self, 'Sample rate range: ', rateColumn, parent)

    def data(self):
        return rangeData(self.greater, self.less) if self.valid else None

    def editFilter(self):
        context = [('{:.1f} kHz'.format(sampleRate/1000.), str(sampleRate)) for sampleRate in sampleRatesList]
        editor = RangeSelectionWidget(self, context, self.greater, self.less)
        FilterWidget.editFilter(self, editor)

    def setContent(self, greater=None, less=None):
        self.less = less
        self.greater = greater
        self.valid = True
        if less is None and greater is None:
            self.contents = ['None']
            self.valid = False
        elif less is None:
            greaterValue, greaterEqual = greater
            symbol = '≥' if greaterEqual else '>'
            self.contents = ['{} {:.1f} kHz'.format(symbol, int(greaterValue)/1000.)]
        elif greater is None:
            lessValue, lessEqual = less
            symbol = '≤' if lessEqual else '<'
            self.contents = ['{} {:.1f} kHz'.format(symbol, int(lessValue)/1000.)]
        else:
            lessValue, lessEqual = less
            lessSymbol = '≤' if lessEqual else '<'
            greaterValue, greaterEqual = greater
            greaterSymbol = '≤' if greaterEqual else '<'
            self.contents = ['{greater:.1f} kHz {greaterSymbol} x {lessSymbol} {less:.1f} kHz'.format(greater=int(greaterValue)/1000., greaterSymbol=greaterSymbol, lessSymbol=lessSymbol, less=int(lessValue)/1000.)]
            if greater >= less:
                self.valid = False
        self.contentWidth = self.fontMetrics().width(self.contents[0]) + self.hMargin * 2
        self.resizeToContents()
        self.changed.emit()


class FilterContainer(QtWidgets.QFrame):
    filterTypes = {
        'format': FormatFilterWidget, 
        'sampleRate': SampleRateFilterWidget, 
        'sampleRateRange': SampleRateRangeFilterWidget, 
        }
    incompatible = [
        set([SampleRateFilterWidget, SampleRateRangeFilterWidget])
        ]
    filtersChanged = QtCore.pyqtSignal(object)
    def __init__(self, parent=None):
        QtWidgets.QFrame.__init__(self, parent)
        self.setFrameShadow(self.Sunken)
        self.setFrameShape(self.StyledPanel)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        self.innerWidget = QtWidgets.QWidget()
        layout.addWidget(self.innerWidget)
        self.filters = []

    def addFilter(self, filterType):
        filterClass = self.filterTypes[filterType]
        for filter in self.filters:
            if isinstance(filter, filterClass):
                return
        filterClasses = set([filter.__class__ for filter in self.filters] + [filterClass])
        for incompatible in self.incompatible:
            if len(incompatible & filterClasses) > 1:
                return
        filter = filterClass(self.innerWidget)
        filter.deleted.connect(self.filterRemoved)
        filter.resized.connect(self.redrawFilters)
        filter.changed.connect(self.updateFilters)
        self.filters.append(filter)
        filter.show()
        self.redrawFilters()

    def filterRemoved(self, filter):
        try:
            self.filters.pop(self.filters.index(filter))
            filter.deleted.disconnect()
            filter.resized.disconnect()
            self.redrawFilters()
            filter.deleteLater()
            self.updateFilters()
        except:
            pass

    def redrawFilters(self):
        delta = 0
        for btn in self.filters:
            btn.move(delta, 0)
            btn.setMaximumHeight(self.height() - 5)
            btn.setMinimumHeight(self.height() - 5)
            delta += btn.width()

    def resizeEvent(self, event):
        self.redrawFilters()

    def updateFilters(self):
        filterData = []
        for filter in self.filters:
            if not filter.valid:
                continue
            filterData.append((filter.field, filter.data()))
        self.filtersChanged.emit(filterData)


class FilterLineEdit(QtWidgets.QLineEdit):
    def __init__(self, *args, **kwargs):
        QtWidgets.QLineEdit.__init__(self, *args, **kwargs)
        self.setClearButtonEnabled(True)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.setText('')
        else:
            QtWidgets.QLineEdit.keyPressEvent(self, event)


class MainFilterWidget(QtWidgets.QWidget):
    filtersChanged = QtCore.pyqtSignal(object)
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QtWidgets.QLabel('Name:'), 0, 0)
        self.nameSearchEdit = FilterLineEdit()
        self.nameSearchEdit.textChanged.connect(self.textSearchChanged)
        layout.addWidget(self.nameSearchEdit, 0, 1, 1, 2)

        layout.addWidget(QtWidgets.QLabel('Filters:'), 1, 0)
        self.filterWidget = FilterContainer()
        self.filterWidget.filtersChanged.connect(self.updateFilters)
        self.filterData = []
        layout.addWidget(self.filterWidget, 1, 1)

        self.addFilterBtn = QtWidgets.QToolButton()
        self.addFilterBtn.setText('+')
        self.addFilterBtn.setAutoRaise(True)
        self.addFilterBtn.setArrowType(QtCore.Qt.NoArrow)
        self.addFilterBtn.setStyleSheet('QToolButton::menu-indicator {image:none;}')
        self.addFilterBtn.setPopupMode(self.addFilterBtn.InstantPopup)
        layout.addWidget(self.addFilterBtn, 1, 2)
        filterMenu = QtWidgets.QMenu(self)
        self.addFilterBtn.setMenu(filterMenu)
        addFormatAction = QtWidgets.QAction('Formats', self)
        addFormatAction.triggered.connect(lambda: self.filterWidget.addFilter('format'))
        addSampleRateAction = QtWidgets.QAction('Sample rates', self)
        addSampleRateAction.triggered.connect(lambda: self.filterWidget.addFilter('sampleRate'))
        addSampleRateRangeAction = QtWidgets.QAction('Sample rate range', self)
        addSampleRateRangeAction.triggered.connect(lambda: self.filterWidget.addFilter('sampleRateRange'))
        filterMenu.addActions([addFormatAction, addSampleRateAction, addSampleRateRangeAction])

        layout.setColumnStretch(1, 100)

    def updateFilters(self, filterData):
        self.filterData = filterData
        self.filtersChanged.emit([(fileNameColumn, self.nameSearchEdit.text())] + filterData)

    def textSearchChanged(self, text):
        self.filtersChanged.emit([(fileNameColumn, text)] + self.filterData)


