#!/usr/bin/env python3

from PyQt5 import QtCore, QtWidgets
try:
    from tagseditor import TagsEditorTextEdit
except:
    from .tagseditor import TagsEditorTextEdit

class AudioInfoTabWidget(QtWidgets.QWidget):
    tagsApplied = QtCore.pyqtSignal(object)
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Expanding))
        mainLayout = QtWidgets.QHBoxLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(mainLayout)
        self.tabWidget = QtWidgets.QTabWidget()
        mainLayout.addWidget(self.tabWidget)

        self.infoTab = QtWidgets.QWidget()
        self.infoTab.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Expanding))
        self.tabWidget.addTab(self.infoTab, 'Info')
        infoLayout = QtWidgets.QGridLayout()
        self.infoTab.setLayout(infoLayout)

        self.infoFileNameLbl = QtWidgets.QLabel()
        infoLayout.addWidget(self.infoFileNameLbl, 0, 0, 1, 5)
        infoLayout.addWidget(QtWidgets.QLabel('Length:'), 1, 0)
        self.infoLengthLbl = QtWidgets.QLabel('0')
        infoLayout.addWidget(self.infoLengthLbl, 1, 1)
        infoLayout.addItem(QtWidgets.QSpacerItem(16, 8, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed), 1, 2)
        infoLayout.addWidget(QtWidgets.QLabel('Format:'), 1, 3)
        self.infoFormatLbl = QtWidgets.QLabel('NO')
        infoLayout.addWidget(self.infoFormatLbl, 1, 4)

        infoLayout.addWidget(QtWidgets.QLabel('Rate:'), 2, 0)
        self.infoSampleRateLbl = QtWidgets.QLabel('0')
        infoLayout.addWidget(self.infoSampleRateLbl, 2, 1)
        infoLayout.addWidget(QtWidgets.QLabel('Chans:'), 2, 3)
        self.infoChannelsLbl = QtWidgets.QLabel('0')
        infoLayout.addWidget(self.infoChannelsLbl, 2, 4)

        self.tagsWidget = QtWidgets.QWidget()
        self.tagsWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Expanding))
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

    def setInfo(self, fileName=None, info=None, tags=None):
        if not fileName or info==None:
            self.clear()
            return
        self.infoTab.setEnabled(True)
        self.infoFileNameLbl.setText(fileName)
        self.infoLengthLbl.setText('{:.3f}'.format(float(info.frames) / info.samplerate))
        self.infoFormatLbl.setText(info.format)
        self.infoSampleRateLbl.setText(str(info.samplerate))
        self.infoChannelsLbl.setText(str(info.channels))
        if tags is not None:
            self.tagsEdit.setTags(tags)
            self.tabWidget.setTabEnabled(1, True)
        else:
            self.tagsEdit.setTags([])
            self.tabWidget.setTabEnabled(1, False)

    def clear(self):
        self.infoTab.setEnabled(False)
        self.infoFileNameLbl.setText('')
        self.infoLengthLbl.setText('0')
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

