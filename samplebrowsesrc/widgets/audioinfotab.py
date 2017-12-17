#!/usr/bin/env python3

from PyQt5 import QtCore, QtWidgets
import soundfile
try:
    from tagseditor import TagsEditorTextEdit
except:
    from .tagseditor import TagsEditorTextEdit

from samplebrowsesrc.widgets.ellipsislabel import EllipsisLabel

class AudioInfoTabWidget(QtWidgets.QWidget):

    class LengthFormat:
        Secs, Full = 0, 1

    QtCore.Q_ENUMS(LengthFormat)
    Secs = LengthFormat.Secs
    Full = LengthFormat.Full

    tagsApplied = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self._length = 0
        self._lengthFormat = self.LengthFormat.Secs
        self._showMSecs = True
        self._showMSecsTrailingZeros = True
        self._maxNumWidth = max(self.fontMetrics().width(str(n)) for n in range(10))

        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Expanding))
        headerSizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        valueSizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        mainLayout = QtWidgets.QHBoxLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(mainLayout)
        self.tabWidget = QtWidgets.QTabWidget()
        mainLayout.addWidget(self.tabWidget)

        self.infoTab = QtWidgets.QWidget()
        self.infoTab.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum))
        self.tabWidget.addTab(self.infoTab, 'Info')
        infoLayout = QtWidgets.QGridLayout()
        self.infoTab.setLayout(infoLayout)

        self.infoFileNameLbl = EllipsisLabel()
        infoLayout.addWidget(self.infoFileNameLbl, 0, 0, 1, 5)
        lengthLbl = QtWidgets.QLabel('Length:')
        lengthLbl.setSizePolicy(headerSizePolicy)
        infoLayout.addWidget(lengthLbl, 1, 0)
        self.infoLengthLbl = QtWidgets.QLabel()
        self.infoLengthLbl.setSizePolicy(valueSizePolicy)
        infoLayout.addWidget(self.infoLengthLbl, 1, 1)
        infoLayout.addItem(QtWidgets.QSpacerItem(16, 8, QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed), 1, 2)
        formatLbl = QtWidgets.QLabel('Format:')
        formatLbl.setSizePolicy(headerSizePolicy)
        infoLayout.addWidget(formatLbl, 1, 3)
        self.infoFormatLbl = QtWidgets.QLabel()
        self.infoFormatLbl.setFixedWidth(max([self.fontMetrics().width(fmt) for fmt in soundfile.available_formats().keys()]))
        infoLayout.addWidget(self.infoFormatLbl, 1, 4)

        sampleRateLbl = QtWidgets.QLabel('Rate:')
        sampleRateLbl.setSizePolicy(headerSizePolicy)
        infoLayout.addWidget(sampleRateLbl, 2, 0)
        self.infoSampleRateLbl = QtWidgets.QLabel()
        infoLayout.addWidget(self.infoSampleRateLbl, 2, 1)
        channelsLbl = QtWidgets.QLabel('Chans:')
        channelsLbl.setSizePolicy(headerSizePolicy)
        infoLayout.addWidget(channelsLbl, 2, 3)
        self.infoChannelsLbl = QtWidgets.QLabel()
        self.infoChannelsLbl.setFixedWidth(self._maxNumWidth * 2)
        infoLayout.addWidget(self.infoChannelsLbl, 2, 4)

        self.tagsWidget = QtWidgets.QWidget()
        self.tagsWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum))
        self.tabWidget.addTab(self.tagsWidget, 'Tags')
        tagsLayout = QtWidgets.QHBoxLayout()
        self.tagsWidget.setLayout(tagsLayout)

        self.tagsEdit = TagsEditorTextEdit()
        self.tagsEdit.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored))
        tagsLayout.addWidget(self.tagsEdit)
        self.tagsEdit.setApplyMode(True)
        self.tagsEdit.tagsApplied.connect(self.tagsApplied.emit)

        self.tabWidget.setTabEnabled(1, False)
        self.infoTab.setEnabled(False)
        self.resetLengthWidth()
        self.clear()

    @QtCore.pyqtProperty(LengthFormat)
    def lengthFormat(self):
        return self._lengthFormat

    @lengthFormat.setter
    def lengthFormat(self, lengthFormat):
        self._lengthFormat = lengthFormat
        self.showLength()
        self.resetLengthWidth()

    @QtCore.pyqtSlot(LengthFormat)
    def setLengthFormat(self, lengthFormat):
        self.lengthFormat = lengthFormat

    @QtCore.pyqtProperty(bool)
    def showMSecs(self):
        return self._showMSecs

    @showMSecs.setter
    def showMSecs(self, show):
        self._showMSecs = show
        self.showLength()
        self.resetLengthWidth()

    @QtCore.pyqtSlot(bool)
    def setShowMSecs(self, show):
        self.showMSecs = show

    @QtCore.pyqtProperty(bool)
    def showMSecsTrailingZeros(self):
        return self._showMSecsTrailingZeros

    @showMSecsTrailingZeros.setter
    def showMSecsTrailingZeros(self, show):
        self._showMSecsTrailingZeros = show
        self.showLength()
        self.resetLengthWidth()

    @QtCore.pyqtSlot(bool)
    def setShowMSecsTrailingZeros(self, show):
        self.showMSecsTrailingZeros = show

    @QtCore.pyqtProperty(float)
    def length(self):
        return self._length

    @length.setter
    def length(self, secs):
        self._length = secs
        self.showLength()

    def resetLengthWidth(self):
        if self._lengthFormat == self.Secs:
            size = 4 * self._maxNumWidth
        else:
            size = 6 * self._maxNumWidth
        if self._showMSecs:
            size += 3 * self._maxNumWidth
        self.infoLengthLbl.setMinimumWidth(size)
        col1 = max(self.fontMetrics().width(s) for s in ('Length:', 'Rate:'))
        col2 = max(self.infoLengthLbl.minimumWidth(), self.infoSampleRateLbl.minimumWidth())
        col3 = max(self.fontMetrics().width(s) for s in ('Format:', 'Chans:'))
        col4 = max(self.infoFormatLbl.minimumWidth(), self.infoChannelsLbl.minimumWidth())
        maxWidth = col1 + col2 + col3 + col4 + 16 + self.infoTab.layout().horizontalSpacing() * 4
        self.infoTab.setMinimumWidth(maxWidth)
        self.infoFileNameLbl.setMaximumWidth(maxWidth)

    def showLength(self):
        if self._lengthFormat == self.Secs:
            if self._showMSecs:
                text = '{:.3f}'.format(self._length)
                if not self._showMSecsTrailingZeros:
                    text.rstrip('0').rstrip('.')
            else:
                text = str(int(self._length))
            self.infoLengthLbl.setText(text)
        else:
            length = QtCore.QTime(0, 0, 0).addSecs(int(self._length)).addMSecs((self._length - int(self._length)) * 1000)
            if self._showMSecs:
                msecsFmt = '.zzz'
            else:
                msecsFmt = ''
            fmt = 'mm:s' + msecsFmt
            if length.hour():
                fmt = 'h:' + fmt
            text = length.toString(fmt)
            self.infoLengthLbl.setText(text.rstrip('0').rstrip('.') if self._showMSecs and not self._showMSecsTrailingZeros else text)

    def setInfo(self, fileName=None, info=None, tags=None):
        if not fileName or info==None:
            self.clear()
            return
        self.length = info.frames / info.samplerate
        self.infoTab.setEnabled(True)
        self.infoFileNameLbl.setText(fileName)
        self.infoFormatLbl.setText(info.format)
        self.infoSampleRateLbl.setText(str(info.samplerate))
        self.infoChannelsLbl.setText(str(info.channels))
        if tags is not None:
            self.tagsEdit.setTags(tags)
            self.tabWidget.setTabEnabled(1, True)
        else:
            self.tagsEdit.setTags([])
            self.tabWidget.setTabEnabled(1, False)

    @QtCore.pyqtSlot()
    def clear(self):
        self.infoTab.setEnabled(False)
        self.infoFileNameLbl.setText('')
        self.length = 0
        self.showLength()
        self.infoFormatLbl.setText('NO')
        self.infoSampleRateLbl.setText('0')
        self.infoChannelsLbl.setText('0')
        self.tagsEdit.setTags([])
        self.infoTab.setEnabled(False)
        self.tabWidget.setTabEnabled(1, False)

if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    widget = AudioInfoTabWidget()
    widget.show()
    sys.exit(app.exec_())

