import os
import soundfile
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from samplebrowsesrc import utils
from samplebrowsesrc.constants import *

class ScanOptionsDialog(QtWidgets.QDialog):
    def __init__(self, parent, dirName=None):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi('{}/scanoptions.ui'.format(os.path.dirname(utils.__file__)), self)
        if dirName:
            self.dirPathEdit.setText(dirName)
        else:
            self.dirNameFrame.setVisible(False)
        self.browseBtn.clicked.connect(self.browse)
        self.allFormatsChk.setChecked(True)
        self.allFormatsChk.toggled.connect(self.toggleAllFormats)
        self.formatModel = QtGui.QStandardItemModel()
        self.formatModel.dataChanged.connect(self.checkAllFormatsFromModel)
        self.formatList.setModel(self.formatModel)
        for ext in sorted(soundfile.available_formats().keys()):
            format = soundfile.available_formats()[ext]
            item = QtGui.QStandardItem(format)
            item.setData(ext, FormatRole)
            item.setCheckable(True)
            item.setCheckState(QtCore.Qt.Checked)
            self.formatModel.appendRow(item)

        self.allSampleRatesChk.setChecked(True)
        self.allSampleRatesChk.toggled.connect(self.toggleAllSampleRates)
        self.sampleRatesModel = QtGui.QStandardItemModel()
        self.sampleRatesModel.dataChanged.connect(self.checkAllSampleRatesFromModel)
        self.sampleRatesList.setModel(self.sampleRatesModel)
        for sr in (192000, 176400, 96000, 88200, 48000, 44100, 32000, 22050, 16000, 8000):
            item = QtGui.QStandardItem('{:.1f} kHz'.format(sr/1000.))
            item.setData(sr, FormatRole)
            item.setCheckable(True)
            item.setCheckState(QtCore.Qt.Checked)
            self.sampleRatesModel.appendRow(item)

        self.okBtn = self.buttonBox.button(self.buttonBox.Ok)
        self.okBtn.setText('Scan')

        self.currentSizeBiggerUnit = self.sizeBiggerCombo.currentIndex()
        self.currentSizeSmallerUnit = self.sizeSmallerCombo.currentIndex()
        self.sizeBiggerChk.toggled.connect(lambda state: self.checkSizeIntegrity('Smaller') if state else None)
        self.sizeBiggerSpin.valueChanged.connect(lambda *args: self.checkSizeIntegrity('Bigger'))
        self.sizeBiggerCombo.currentIndexChanged.connect(lambda *args: self.checkSizeIntegrity('Bigger'))
        self.sizeSmallerChk.toggled.connect(lambda state: self.checkSizeIntegrity('Bigger') if state else None)
        self.sizeSmallerSpin.valueChanged.connect(lambda *args: self.checkSizeIntegrity('Smaller'))
        self.sizeSmallerCombo.currentIndexChanged.connect(lambda *args: self.checkSizeIntegrity('Smaller'))

        self.currentLengthLongerUnit = self.lengthLongerCombo.currentIndex()
        self.currentLengthShorterUnit = self.lengthShorterCombo.currentIndex()
        self.lengthLongerChk.toggled.connect(lambda state: self.checkLengthIntegrity('Shorter') if state else None)
        self.lengthLongerSpin.valueChanged.connect(lambda * args: self.checkLengthIntegrity('Longer'))
        self.lengthLongerCombo.currentIndexChanged.connect(lambda * args: self.checkLengthIntegrity('Longer'))
        self.lengthShorterChk.toggled.connect(lambda state: self.checkLengthIntegrity('Longer') if state else None)
        self.lengthShorterSpin.valueChanged.connect(lambda * args: self.checkLengthIntegrity('Shorter'))
        self.lengthShorterCombo.currentIndexChanged.connect(lambda * args: self.checkLengthIntegrity('Shorter'))

    def checkAllFormatsFromModel(self, *args):
        self.allFormatsChk.blockSignals(True)
        self.allFormatsChk.setChecked(self.checkAllFormats())
        self.allFormatsChk.blockSignals(False)
        self.checkIntegrity()

    def toggleAllFormats(self, state):
        if state == False and self.checkAllFormats():
            self.allFormatsChk.blockSignals(True)
            self.allFormatsChk.setChecked(True)
            self.allFormatsChk.blockSignals(False)
        else:
            for row in range(self.formatModel.rowCount()):
                self.formatModel.item(row).setCheckState(QtCore.Qt.Checked)

    def checkAllFormats(self):
        for row in range(self.formatModel.rowCount()):
            if not self.formatModel.item(row).checkState():
                return False
        else:
            return True

    def checkAllSampleRatesFromModel(self, *args):
        self.allSampleRatesChk.blockSignals(True)
        self.allSampleRatesChk.setChecked(self.checkAllSampleRates())
        self.allSampleRatesChk.blockSignals(False)
        self.checkIntegrity()

    def toggleAllSampleRates(self, state):
        if state == False and self.checkAllSampleRates():
            self.allSampleRatesChk.blockSignals(True)
            self.allSampleRatesChk.setChecked(True)
            self.allSampleRatesChk.blockSignals(False)
        else:
            for row in range(self.sampleRatesModel.rowCount()):
                self.sampleRatesModel.item(row).setCheckState(QtCore.Qt.Checked)

    def checkAllSampleRates(self):
        for row in range(self.sampleRatesModel.rowCount()):
            if not self.sampleRatesModel.item(row).checkState():
                return False
        else:
            return True

    def checkIntegrity(self):
        for row in range(self.formatModel.rowCount()):
            if self.formatModel.item(row).checkState():
                break
        else:
            self.okBtn.setEnabled(False)
            return
        for row in range(self.sampleRatesModel.rowCount()):
            if self.sampleRatesModel.item(row).checkState():
                self.okBtn.setEnabled(True)
                break
        else:
            self.okBtn.setEnabled(False)

    def checkSizeIntegrity(self, mode):
        spin = getattr(self, 'size{}Spin'.format(mode))
        combo = getattr(self, 'size{}Combo'.format(mode))
        currentSizeUnit = getattr(self, 'currentSize{}Unit'.format(mode))
        if combo.currentIndex() == currentSizeUnit:
            if combo.currentIndex == 2:
                spin.setDecimals(0)
            else:
                spin.setDecimals(2)
        else:
            newSizeUnit = combo.currentIndex()
            newSpinValue = spin.value() * (1024**(newSizeUnit - currentSizeUnit))
            spin.blockSignals(True)
            spin.setValue(newSpinValue)
            spin.blockSignals(False)
            setattr(self, 'currentSize{}Unit'.format(mode), newSizeUnit)

        newValue = spin.value() * 1024 ** (2 - combo.currentIndex())
        if mode=='Smaller':
            altMode = 'Bigger'
            cmp = '__le__'
            diff = -1
        else:
            altMode = 'Smaller'
            cmp = '__ge__'
            diff = 1
#        if not getattr(self, 'size{}Chk'.format(altMode)).isChecked():
#            return
        altSpin = getattr(self, 'size{}Spin'.format(altMode))
        altCombo = getattr(self, 'size{}Combo'.format(altMode))
        altValue = altSpin.value() * 1024 ** (2- altCombo.currentIndex())
        if getattr(newValue, cmp)(altValue):
            altCombo.blockSignals(True)
            altCombo.setCurrentIndex(currentSizeUnit)
            altCombo.blockSignals(False)
            altSpin.blockSignals(True)
            altSpin.setValue(spin.value() + diff)
            altSpin.blockSignals(False)
            setattr(self, 'currentSize{}Unit'.format(altMode), currentSizeUnit)

    def checkLengthIntegrity(self, mode):
        spin = getattr(self, 'length{}Spin'.format(mode))
        combo = getattr(self, 'length{}Combo'.format(mode))
        currentSizeUnit = getattr(self, 'currentLength{}Unit'.format(mode))
        if combo.currentIndex() != currentSizeUnit:
            newSizeUnit = combo.currentIndex()
            newSpinValue = spin.value() * (60**(newSizeUnit - currentSizeUnit))
            spin.blockSignals(True)
            spin.setValue(newSpinValue)
            spin.blockSignals(False)
            setattr(self, 'currentLength{}Unit'.format(mode), newSizeUnit)

        newValue = spin.value() * 60 ** (1 - combo.currentIndex())
        if mode=='Shorter':
            altMode = 'Longer'
            cmp = '__le__'
            diff = -1
        else:
            altMode = 'Shorter'
            cmp = '__ge__'
            diff = 1
#        if not getattr(self, 'length{}Chk'.format(altMode)).isChecked():
#            return
        altSpin = getattr(self, 'length{}Spin'.format(altMode))
        altCombo = getattr(self, 'length{}Combo'.format(altMode))
        altValue = altSpin.value() * 60 ** (1- altCombo.currentIndex())
        if getattr(newValue, cmp)(altValue):
            altCombo.blockSignals(True)
            altCombo.setCurrentIndex(currentSizeUnit)
            altCombo.blockSignals(False)
            altSpin.blockSignals(True)
            altSpin.setValue(spin.value() + diff)
            altSpin.blockSignals(False)
            setattr(self, 'currentLength{}Unit'.format(altMode), currentSizeUnit)

    def browse(self):
        filePath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select directory', self.dirPathEdit.text())
        if filePath:
            self.dirPathEdit.setText(filePath)

    def getFormats(self):
        if self.allFormatsChk.isChecked():
            return True
        formats = []
        for row in range(self.formatModel.rowCount()):
            item = self.formatModel.item(row)
            if item.checkState():
                formats.append(item.data(FormatRole))
        return formats

    def getSampleRates(self):
        if self.allSampleRatesChk.isChecked():
            return True
        sampleRates = []
        for row in range(self.sampleRatesModel.rowCount()):
            item = self.sampleRatesModel.item(row)
            if item.checkState():
                sampleRates.append(item.data(FormatRole))
        return sampleRates

    def getScanLimits(self):
        if self.sizeBiggerChk.isChecked():
            bigger = self.sizeBiggerSpin.value()
            if self.sizeBiggerCombo.currentIndex() == 0:
                bigger *= 1048576
            elif self.sizeBiggerCombo.currentIndex() == 1:
                bigger *= 1024
            bigger = int(bigger)
        else:
            bigger = None

        if self.sizeSmallerChk.isChecked():
            smaller = self.sizeSmallerSpin.value()
            if self.sizeSmallerCombo.currentIndex() == 0:
                smaller *= 1048576
            elif self.sizeSmallerCombo.currentIndex() == 1:
                smaller *= 1024
            smaller = int(smaller)
        else:
            smaller = None

        if self.lengthLongerChk.isChecked():
            longer = self.lengthLongerSpin.value()
            if self.lengthLongerCombo.currentIndex() == 0:
                longer *= 60
        else:
            longer = None

        if self.lengthShorterChk.isChecked():
            shorter = self.lengthShorterSpin.value()
            if self.lengthShorterCombo.currentIndex() == 0:
                shorter *= 60
        else:
            shorter = None

        return bigger, smaller, longer, shorter


