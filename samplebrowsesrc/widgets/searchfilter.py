import re
from collections import namedtuple, OrderedDict
import soundfile
from PyQt5 import QtCore, QtGui, QtWidgets

from samplebrowsesrc.constants import *
from samplebrowsesrc.utils import HoverDecorator, timeStr

rangeData = namedtuple('rangeData', 'greater less')
contextData = namedtuple('contextData', 'full short')

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
    def __init__(self, parent, header, field, context, editorClass, filter=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.closeBtn = FilterCloseButton(self)
        self.closeBtn.clicked.connect(lambda: self.deleted.emit(self))
        self.valid = False
        self.hMargin = 4
        self.header = header
        self.field = field
        self.contentWidth = 0
        self.context = context
        self.editorClass = editorClass
        self.editorVisible = False
        self.setFilter(filter)
        self.name = ''

    def data(self):
        return self.values if self.valid else None

    def setFilter(self, valueList=None):
        self.values = valueList
        if not valueList:
            self.displayValues = ['None']
            self.contentWidth = self.fontMetrics().width('None') + self.hMargin * 2
            self.valid = False
        else:
            self.contentWidth = 0
            self.displayValues = []
            for value in valueList:
                displayValue = self.context[value].short
                self.displayValues.append(displayValue)
                self.contentWidth += self.fontMetrics().width(displayValue) + self.hMargin * 2
            self.valid = True
        self.resizeToContents()
        self.changed.emit()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and not self.editorVisible:
            self.editFilter()

    def editFilter(self):
        editor = self.editorClass(self)
        editor.changed.connect(self.setFilter)
        editor.closed.connect(self.closeEditor)
#        editor.move(self.mapToGlobal(QtCore.QPoint(0, self.height())))
        editor.show()
        self.editorVisible = True

    def closeEditor(self, editor):
        editor.changed.disconnect()
        editor.deleteLater()
        self.editorVisible = False

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
        for value in self.displayValues:
            rect = QtCore.QRect(0, self.hMargin, self.fontMetrics().width(value) + self.hMargin * 2, self.height() - self.hMargin * 2)
            qp.drawRoundedRect(rect, 2, 2)
            rect = QtCore.QRect(2, self.hMargin, rect.width() -4, rect.height())
            qp.drawText(rect, QtCore.Qt.AlignCenter, value)
            qp.translate(rect.width() + self.hMargin, 0)


class BaseSelectionWidget(QtWidgets.QWidget):
    changed = QtCore.pyqtSignal(object)
    closed = QtCore.pyqtSignal(object)

    def mousePressEvent(self, event):
        if event.pos() not in self.rect():
            self.closed.emit(self)
            event.accept()
            return
        QtWidgets.QWidget.mousePressEvent(self, event)

    def showEvent(self, event):
        desktopGeo = QtWidgets.QDesktopWidget().screenGeometry(self.parent())
        topLeft = self.parent().mapToGlobal(QtCore.QPoint(0, 0))
        parentHeight = self.parent().height()
        y = topLeft.y() + parentHeight
        if y + self.height() > desktopGeo.height():
            y = topLeft.y() - self.height()
        if topLeft.x() + self.width() <= desktopGeo.width():
            x = topLeft.x()
        else:
            x = desktopGeo.width() - self.width()
        self.move(x, y)


class ListSelectionWidget(BaseSelectionWidget):
    def __init__(self, parent):
        BaseSelectionWidget.__init__(self, parent, QtCore.Qt.Popup)
        self.setWindowModality(QtCore.Qt.WindowModal)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.listView = QtWidgets.QListView()
        layout.addWidget(self.listView)
        self.model = QtGui.QStandardItemModel()
        self.listView.setModel(self.model)
        self.model.dataChanged.connect(self.checkData)
        self.listView.setEditTriggers(self.listView.NoEditTriggers)
        self.listView.doubleClicked.connect(self.toggleItem)
        checked = []
        unchecked = []
        for value, display in parent.context.items():
            item = QtGui.QStandardItem(display.full)
            item.setData(value)
            item.setCheckable(True)
            if parent.values and value in parent.values:
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


class FormatFilterWidget(FilterWidget):
    def __init__(self, parent, filter=None):
        FilterWidget.__init__(
            self, 
            parent, 
            'Formats: ', 
            formatColumn, 
            OrderedDict([(ext, contextData(soundfile.available_formats()[ext], ext)) for ext in sorted(soundfile.available_formats().keys())]), 
            ListSelectionWidget, 
            filter
            )
        self.name = 'File format'

class SampleRateFilterWidget(FilterWidget):
    def __init__(self, parent, filter=None):
        FilterWidget.__init__(
            self, 
            parent, 
            'Sample rates: ', 
            rateColumn, 
            OrderedDict([(sr, contextData('{:.1f} kHz'.format(sr/1000.), str(sr))) for sr in sampleRatesList]), 
            ListSelectionWidget, 
            filter
            )
        self.name = 'Sample rate'


class ChannelsFilterWidget(FilterWidget):
    def __init__(self, parent, filter=None):
        FilterWidget.__init__(
            self, 
            parent, 
            'Channels: ', 
            channelsColumn, 
            OrderedDict([(ch, contextData(channelsLabels[ch], channelsLabels[ch])) for ch in sorted(channelsLabels.keys())]), 
            ListSelectionWidget, 
            filter
            )
        self.name = 'Channels'


class GrayedCheckBox(QtWidgets.QCheckBox):
    def __init__(self, *args, **kwargs):
        QtWidgets.QCheckBox.__init__(self, *args, **kwargs)
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


class ComboRangeSelectionWidget(BaseSelectionWidget):
    changed = QtCore.pyqtSignal(object, object)
    def __init__(self, parent):
        BaseSelectionWidget.__init__(self, parent, QtCore.Qt.Popup)
        self.setWindowModality(QtCore.Qt.WindowModal)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        self.lessChk = QtWidgets.QCheckBox('Less than')
        layout.addWidget(self.lessChk, 0, 0)
        self.lessOrEqualChk = GrayedCheckBox('or equal to')
        layout.addWidget(self.lessOrEqualChk, 0, 1)
        self.lessCombo = QtWidgets.QComboBox()
        layout.addWidget(self.lessCombo, 0, 2)

        self.greaterChk = QtWidgets.QCheckBox('Greater than')
        layout.addWidget(self.greaterChk, 1, 0)
        self.greaterOrEqualChk = GrayedCheckBox('or equal to')
        layout.addWidget(self.greaterOrEqualChk, 1, 1)
        self.greaterCombo = QtWidgets.QComboBox()
        layout.addWidget(self.greaterCombo,1, 2)

        for value, display in parent.context.items():
            self.lessCombo.addItem(display.full, value)
            self.greaterCombo.addItem(display.full, value)
        self.lessCombo.model().takeRow(self.lessCombo.model().rowCount() - 1)
        self.greaterCombo.model().takeRow(0)

        if parent.less:
            lessValue, lessEqual = parent.less
            self.lessChk.setChecked(True)
            self.lessOrEqualChk.setChecked(lessEqual)
            self.lessCombo.setCurrentIndex(self.lessCombo.findData(lessValue))
        else:
            self.lessCombo.setCurrentIndex(0)
        if parent.greater:
            greaterValue, greaterEqual = parent.greater
            self.greaterChk.setChecked(True)
            self.greaterOrEqualChk.setChecked(greaterEqual)
            self.greaterCombo.setCurrentIndex(self.greaterCombo.findData(greaterValue))
        else:
            self.greaterCombo.setCurrentIndex(self.greaterCombo.count() - 1)

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


class SampleRateRangeFilterWidget(FilterWidget):
    def __init__(self, parent, filter=None):
        FilterWidget.__init__(
            self, 
            parent, 
            'Sample rate range: ', 
            rateColumn, 
            OrderedDict([(sr, contextData('{:.1f} kHz'.format(sr/1000.), str(sr))) for sr in sampleRatesList]), 
            ComboRangeSelectionWidget, 
            filter
            )
        self.name = 'Sample rate range'

    def data(self):
        return rangeData(self.greater, self.less) if self.valid else None

    def setFilter(self, greater=None, less=None):
        self.values = None
        self.less = less
        self.greater = greater
        self.valid = True
        if less is None and greater is None:
            self.displayValues = ['None']
            self.valid = False
        elif less is None:
            greaterValue, greaterEqual = greater
            symbol = '≥' if greaterEqual else '>'
            self.displayValues = ['{} {:.1f} kHz'.format(symbol, int(greaterValue)/1000.)]
        elif greater is None:
            lessValue, lessEqual = less
            symbol = '≤' if lessEqual else '<'
            self.displayValues = ['{} {:.1f} kHz'.format(symbol, int(lessValue)/1000.)]
        else:
            lessValue, lessEqual = less
            lessSymbol = '≤' if lessEqual else '<'
            greaterValue, greaterEqual = greater
            greaterSymbol = '≤' if greaterEqual else '<'
            self.displayValues = ['{greater:.1f} kHz {greaterSymbol} R {lessSymbol} {less:.1f} kHz'.format(greater=int(greaterValue)/1000., greaterSymbol=greaterSymbol, lessSymbol=lessSymbol, less=int(lessValue)/1000.)]
            if greater >= less:
                self.valid = False
        self.contentWidth = self.fontMetrics().width(self.displayValues[0]) + self.hMargin * 2
        self.resizeToContents()
        self.changed.emit()


class TimeValidator(QtGui.QValidator):
    def __init__(self, *args, **kwargs):
        QtGui.QValidator.__init__(self, *args, **kwargs)
        self.fullRegex = re.compile(r'^(?:(?:(?P<hh>\d)[:])?(?P<mm>[0-5]?\d)[:])?(?P<ss>\d{1,3})[\.](?:(?P<ff>\d{1,3}))$')
        self.midRegex = re.compile(r'^(?:(\d)?[:])?(?:([0-5]?\d)?[:])?(\d{0,3})(?:[.]\d{0,3})?$')

    def validate(self, input, pos):
        if not self.fullRegex.match(input):
            if self.midRegex.match(input):
                return self.Intermediate, input, pos
            else:
                return self.Invalid, input, pos
        return self.Acceptable, input, pos


class TimeSpinBox(QtWidgets.QAbstractSpinBox):
    valueChanged = QtCore.pyqtSignal(float)
    def __init__(self, *args, **kwargs):
        QtWidgets.QAbstractSpinBox.__init__(self, *args, **kwargs)
        self.setRange(0.001, 5040)
        self._decimals = 3
        self._step = 10
        self._suffix = 's'
        self._value = 10
        self.timeRegex = re.compile(r'(?:(?:(?P<hh>\d)[:])?(?P<mm>[0-5]?\d)[:])?(?P<ss>\d{1,3})(?:(?P<ff>[\.]\d{1,3}))')
        self.lineEdit().setMaxLength(11)
        self.lineEdit().setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.lineEdit().sizeHint = self.lineEditSizeHint
        self.validator = TimeValidator(self)
        self.lineEdit().setValidator(self.validator)
        self.lineEdit().textChanged.connect(self.textChanged)

    def textChanged(self, text):
        value = self.validate(text)
        if value:
            self._value = value
            self.valueChanged.emit(value)

    def validate(self, text):
        match = self.timeRegex.match(text.strip(':').strip('.'))
        if match:
            value = 0
            h = match.group('hh')
            if h:
                value += 3600 * int(h)
            m = match.group('mm')
            if m:
                value += 60 * int(m)
            s = match.group('ss')
            if s:
                value += int(s)
            f = match.group('ff')
            if f:
                value += float(f)
            return value
        return

    def focusOutEvent(self, event):
        value = self.validate(self.lineEdit().text())
        if value:
            self._value = value
            self.lineEdit().setText(timeStr(self._value, leading=2, trailingAlways=True, full=True))
            self.valueChanged.emit(value)
        else:
            self.lineEdit().setText(timeStr(self._value, leading=2, trailingAlways=True, full=True))
        QtWidgets.QAbstractSpinBox.focusOutEvent(self, event)

    def lineEditSizeHint(self):
        return QtCore.QSize(self.fontMetrics().width('0:00:00.000'), self.lineEdit().sizeHint().height())

    def minimumSizeHint(self):
        return self.lineEdit().sizeHint()

    def value(self):
        return self._value

    def setValue(self, value):
        self._setValue(value)
        self.valueChanged.emit(value)

    def _setValue(self, value):
        self._value = value
        self.lineEdit().setText(timeStr(value, leading=2, trailingAlways=True, full=True))

    def minimum(self):
        return self._minimum

    def setMinimum(self, minimum):
        self._minimum = minimum

    def maximum(self):
        return self._maximum

    def setMaximum(self, maximum):
        self._maximum = maximum

    def setRange(self, minimum, maximum):
        self._minimum = minimum
        self._maximum = maximum

    def stepBy(self, step):
        if abs(step) == 1:
            step *= 10
        elif abs(step) == 10:
            step *= 6
        value = self._value + step
        if value > self._maximum:
            value = self._maximum
        elif value < self._minimum:
            value = self._minimum
        self._setValue(value)
        self.valueChanged.emit(value)

    def stepEnabled(self):
        flags = 0
        if self._value > self._minimum:
            flags |= self.StepDownEnabled
        if self._value < self._maximum:
            flags |= self.StepUpEnabled
        return flags


class SpinRangeSelectionWidget(BaseSelectionWidget):
    changed = QtCore.pyqtSignal(object, object)
    def __init__(self, parent):
        BaseSelectionWidget.__init__(self, parent, QtCore.Qt.Popup)
        self.setWindowModality(QtCore.Qt.WindowModal)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        self.lessChk = QtWidgets.QCheckBox('Less than')
        layout.addWidget(self.lessChk, 0, 0)
        self.lessOrEqualChk = GrayedCheckBox('or equal to')
        layout.addWidget(self.lessOrEqualChk, 0, 1)
        self.lessSpin = TimeSpinBox()
        self.lessSpin.setValue(60)
        layout.addWidget(self.lessSpin, 0, 2)

        self.greaterChk = QtWidgets.QCheckBox('Greater than')
        layout.addWidget(self.greaterChk, 1, 0)
        self.greaterOrEqualChk = GrayedCheckBox('or equal to')
        layout.addWidget(self.greaterOrEqualChk, 1, 1)
        self.greaterSpin = TimeSpinBox()
        self.greaterSpin.setValue(1)
        layout.addWidget(self.greaterSpin, 1, 2)

        if parent.less:
            lessValue, lessEqual = parent.less
            self.lessChk.setChecked(True)
            self.lessOrEqualChk.setChecked(lessEqual)
            self.lessSpin.setValue(lessValue)
        if parent.greater:
            greaterValue, greaterEqual = parent.greater
            self.greaterChk.setChecked(True)
            self.greaterOrEqualChk.setChecked(greaterEqual)
            self.greaterSpin.setValue(greaterValue)

        self.lessChk.toggled.connect(self.checkData)
        self.greaterChk.toggled.connect(self.checkData)
        self.lessOrEqualChk.toggled.connect(self.checkData)
        self.greaterOrEqualChk.toggled.connect(self.checkData)
        self.lessSpin.valueChanged.connect(self.checkData)
        self.greaterSpin.valueChanged.connect(self.checkData)

        self.checkData()

    def checkData(self, *args):
        less = self.lessChk.isChecked()
        lessValue = self.lessSpin.value()
        lessEqual = self.lessOrEqualChk.isChecked()
        self.lessOrEqualChk.setEnabled(less)
        self.lessSpin.setEnabled(less)
        greater = self.greaterChk.isChecked()
        greaterValue = self.greaterSpin.value()
        greaterEqual = self.greaterOrEqualChk.isChecked()
        self.greaterOrEqualChk.setEnabled(greater)
        self.greaterSpin.setEnabled(greater)
        self.changed.emit((greaterValue, greaterEqual) if greater else None, (lessValue, lessEqual) if less else None)


class LengthRangeFilterWidget(FilterWidget):
    def __init__(self, parent, filter=None):
        FilterWidget.__init__(
            self, 
            parent, 
            'Length: ', 
            lengthColumn, 
            None, 
            SpinRangeSelectionWidget, 
            )
        self.name = 'Length'

    def data(self):
        return rangeData(self.greater, self.less) if self.valid else None

    def setFilter(self, greater=None, less=None):
        self.values = None
        self.less = less
        self.greater = greater
        self.valid = True
        if less is None and greater is None:
            self.displayValues = ['None']
            self.valid = False
        elif less is None:
            greaterValue, greaterEqual = greater
            symbol = '≥' if greaterEqual else '>'
            self.displayValues = ['{} {}s'.format(symbol, timeStr(greaterValue, leading=2))]
        elif greater is None:
            lessValue, lessEqual = less
            symbol = '≤' if lessEqual else '<'
            self.displayValues = ['{} {}s'.format(symbol, timeStr(lessValue, leading=2))]
        else:
            lessValue, lessEqual = less
            lessSymbol = '≤' if lessEqual else '<'
            greaterValue, greaterEqual = greater
            greaterSymbol = '≤' if greaterEqual else '<'
            self.displayValues = ['{greater:}s {greaterSymbol} T {lessSymbol} {less}s'.format(greater=timeStr(greaterValue, leading=2), greaterSymbol=greaterSymbol, lessSymbol=lessSymbol, less=timeStr(lessValue, leading=2))]
            if greater >= less:
                self.valid = False
        self.contentWidth = self.fontMetrics().width(self.displayValues[0]) + self.hMargin * 2
        self.resizeToContents()
        self.changed.emit()


@HoverDecorator
class FilterContainer(QtWidgets.QFrame):
    filterTypes = {
        'format': FormatFilterWidget, 
        'sampleRate': SampleRateFilterWidget, 
        'sampleRateRange': SampleRateRangeFilterWidget, 
        'lengthRange': LengthRangeFilterWidget, 
        'channels': ChannelsFilterWidget, 
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
        self.hoverText = 'No filter selected, use the "+" button.'

    def addFilter(self, filterType, applyFilter=None):
        filterClass = self.filterTypes[filterType]
        for filter in self.filters:
            if isinstance(filter, filterClass):
                return
        filterClasses = set([filter.__class__ for filter in self.filters] + [filterClass])
        for incompatible in self.incompatible:
            if len(incompatible & filterClasses) > 1:
                return
        filter = filterClass(self.innerWidget, applyFilter)
        filter.deleted.connect(self.filterRemoved)
        filter.resized.connect(self.redrawFilters)
        filter.changed.connect(self.updateFilters)
        self.filters.append(filter)
        filter.show()
        self.redrawFilters()
        if filter:
            self.updateFilters()

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
        self.aniList = []
        for filter in self.filters:
            filter.setMaximumHeight(self.height() - 5)
            filter.setMinimumHeight(self.height() - 5)
            if filter.pos():
                ani = QtCore.QPropertyAnimation(filter, b'pos')
                ani.setDuration(64)
                ani.setStartValue(filter.pos())
                ani.setEndValue(QtCore.QPoint(delta, 0))
                self.aniList.append(ani)
            else:
                filter.move(delta, 0)
            delta += filter.width()
        for ani in self.aniList:
            ani.start()

    def resizeEvent(self, event):
        self.redrawFilters()

    def updateFilters(self):
        filterNames = []
        filterData = []
        for filter in self.filters:
            if not filter.valid:
                continue
            filterNames.append(filter.name)
            filterData.append((filter.field, filter.data()))
        self.filtersChanged.emit(filterData)
        if filterData:
            self.hoverText = 'Active filters: ' + ', '.join(filterNames)
        elif self.filters:
            self.hoverText = 'No valid filters selected, set them or add another filter.'
        else:
            self.hoverText = 'No filter selected, use the "+" button.'

    def minimumSizeHint(self):
        return QtCore.QSize(240, self.fontMetrics().height() + 18)


@HoverDecorator
class FilterLineEdit(QtWidgets.QLineEdit):
    def __init__(self, *args, **kwargs):
        QtWidgets.QLineEdit.__init__(self, *args, **kwargs)
        self.setClearButtonEnabled(True)
        self.hoverText = 'Filter samples by name'

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

        self.addFilterBtn = HoverDecorator(QtWidgets.QToolButton)()
        self.addFilterBtn.setHoverText('Add search filters')
        self.addFilterBtn.setText('+')
        self.addFilterBtn.setAutoRaise(True)
        self.addFilterBtn.setArrowType(QtCore.Qt.NoArrow)
        self.addFilterBtn.setStyleSheet('QToolButton::menu-indicator {image:none;}')
        self.addFilterBtn.setPopupMode(self.addFilterBtn.InstantPopup)
        layout.addWidget(self.addFilterBtn, 1, 2)
        self.filterMenu = QtWidgets.QMenu(self)
        self.filterMenu.aboutToShow.connect(self.checkMenuFilters)
        self.addFilterBtn.setMenu(self.filterMenu)

        self.hoverWidgets = [self.nameSearchEdit, self.filterWidget, self.addFilterBtn]

        formatMenu = self.filterMenu.addMenu('Formats')
        formatMenu.menuAction().setData(FormatFilterWidget)
        formatMenu.addAction('Custom filter', lambda: self.filterWidget.addFilter('format'))
        formatSeparator = formatMenu.addAction('Format templates')
        formatSeparator.setSeparator(True)
        for ext in sorted(soundfile.available_formats().keys()):
            formatMenu.addAction(soundfile.available_formats()[ext], lambda ext=ext: self.filterWidget.addFilter('format', [ext]))

        addLengthAction = self.filterMenu.addAction('Length', lambda: self.filterWidget.addFilter('lengthRange'))
        addLengthAction.setData(LengthRangeFilterWidget)

        sampleRateMenu = self.filterMenu.addMenu('Sample rate')
        sampleRateMenu.menuAction().setData(SampleRateFilterWidget)
        sampleRateMenu.addAction('Sample rate range', lambda: self.filterWidget.addFilter('sampleRateRange'))
        sampleRateMenu.addAction('Custom filter', lambda: self.filterWidget.addFilter('sampleRate'))
        sampleRateSeparator = sampleRateMenu.addAction('Sample rate templates')
        sampleRateSeparator.setSeparator(True)
        for sr in sampleRatesList:
            sampleRateMenu.addAction('{:.1f} kHz'.format(sr/1000.), lambda sr=sr: self.filterWidget.addFilter('sampleRate', [sr]))
        
        channelsMenu = self.filterMenu.addMenu('Channels')
        channelsMenu.menuAction().setData(ChannelsFilterWidget)
        channelsMenu.addAction('Custom filter', lambda: self.filterWidget.addFilter('channels'))
        channelsSeparator = channelsMenu.addAction('Channels templates')
        channelsSeparator.setSeparator(True)
        for ch in sorted(channelsLabels.keys()):
            channelsMenu.addAction('{}: {}'.format(ch, channelsLabels[ch]), lambda ch=ch: self.filterWidget.addFilter('channels', [ch]))

        layout.setColumnStretch(1, 100)

    def checkMenuFilters(self):
        existingClasses = [filter.__class__ for filter in self.filterWidget.filters]
        for action in self.filterMenu.actions():
            filterData = action.data()
            if not filterData:
                continue
            if filterData in existingClasses:
                action.setEnabled(False)
                continue
            filterClasses = set(existingClasses + [filterData])
            for incompatible in self.filterWidget.incompatible:
                if len(incompatible & filterClasses) > 1:
                    action.setEnabled(False)
                    break
            else:
                action.setEnabled(True)

    def updateFilters(self, filterData):
        self.filterData = filterData
        self.filtersChanged.emit([(fileNameColumn, self.nameSearchEdit.text())] + filterData)

    def textSearchChanged(self, text):
        self.filtersChanged.emit([(fileNameColumn, text)] + self.filterData)

