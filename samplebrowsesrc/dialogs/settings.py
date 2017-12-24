import os
from PyQt5 import QtCore, QtWidgets, uic

from samplebrowsesrc import utils
from samplebrowsesrc.dialogs.audiosettings import AudioSettingsDialog


class ClearDbMessageBox(QtWidgets.QMessageBox):
    def __init__(self, parent):
        self.sampleDb = parent.sampleDb
        self.sampleDb.execute('SELECT COUNT(*) FROM samples')
        entryCount = self.sampleDb.fetchone()[0]
        self.sampleDb.execute('SELECT COUNT(*) FROM tagColors')
        tagCount = self.sampleDb.fetchone()[0]
        if not (entryCount or tagCount):
            QtWidgets.QMessageBox.__init__(
                self, 
                QtWidgets.QMessageBox.Information, 
                'Database empty', 
                'The database is empty!', 
                parent=parent
                )
        else:
            QtWidgets.QMessageBox.__init__(
                self, 
                QtWidgets.QMessageBox.Critical, 
                'Clear database?', 
                '''Do you want to completely clear the database contents?<br/><br/>
                <b>WARNING</B>: This operation cannot be undone.<br/>&nbsp;''', 
                QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No, 
                parent=parent
                )
            self.button(QtWidgets.QMessageBox.Yes).setEnabled(False)
            self.setDefaultButton(QtWidgets.QMessageBox.No)
            self.clearDbChk = QtWidgets.QCheckBox()
            self.clearTagsChk = QtWidgets.QCheckBox('Clear tag colors ({} entr{})'.format(tagCount, 'y' if tagCount == 1 else 'ies'))
            self.clearDbChk.toggled.connect(self.checkCheckBoxes)
            self.clearTagsChk.toggled.connect(self.checkCheckBoxes)

            if entryCount:
                if entryCount == 1:
                    entryText = 'Remove one single entry'
                else:
                    entryText = ('Clear all {} entries'.format(entryCount))
                self.clearDbChk.setText(entryText)
                self.setCheckBox(self.clearDbChk)
                if tagCount:
                    row, col, rowSpan, colSpan = self.layout().getItemPosition(self.layout().indexOf(self.clearDbChk))
                    checkBoxLayout = QtWidgets.QVBoxLayout()
                    self.layout().addLayout(checkBoxLayout, row, col, rowSpan, colSpan)
                    self.layout().removeWidget(self.clearDbChk)
                    checkBoxLayout.addWidget(self.clearDbChk)
                    checkBoxLayout.addWidget(self.clearTagsChk)
            else:
                self.setCheckBox(self.clearTagsChk)

    def checkCheckBoxes(self, *args):
        if self.clearDbChk.isChecked() or self.clearTagsChk.isChecked():
            self.button(QtWidgets.QMessageBox.Yes).setEnabled(True)
        else:
            self.button(QtWidgets.QMessageBox.Yes).setEnabled(False)


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi('{}/settings.ui'.format(os.path.dirname(utils.__file__)), self)
        self.settings = QtCore.QSettings()
        self.sampleDb = parent.sampleDb

        self.startupViewGroup.setId(self.startupFsRadio, 0)
        self.startupViewGroup.setId(self.startupDbRadio, 1)
        self.startupViewGroup.setId(self.startupLastRadio, 2)

        self.clearDbBtn.clicked.connect(self.clearDb)

        self.defaultVolumeGroup.setId(self.defaultVolume100Radio, 0)
        self.defaultVolumeGroup.setId(self.defaultVolumePreviousRadio, 1)
        self.defaultVolumeGroup.setId(self.defaultVolumeCustomRadio, 2)
        self.audioDeviceBtn.clicked.connect(self.showAudioSettings)
        self.dbCleared = False

    def clearDb(self):
        clearDbMessageBox = ClearDbMessageBox(self)
        if clearDbMessageBox.exec_() == QtWidgets.QMessageBox.Yes:
            if clearDbMessageBox.clearDbChk.isChecked():
                self.sampleDb.execute('DELETE FROM samples')
            if clearDbMessageBox.clearTagsChk.isChecked():
                self.sampleDb.execute('DELETE FROM tagColors')
            self.dbCleared = True
            self.sampleDb.commit()

    def showAudioSettings(self):
        res = AudioSettingsDialog(self.parent(), self).exec_()
        if not res:
            return
        device, conversion = res
        self.parent().player.setAudioDevice(device)
        self.parent().player.setSampleRateConversion(conversion)

    def exec_(self):
        startupView = self.settings.value('startupView', 0, type=int)
        self.startupViewGroup.button(startupView).setChecked(True)
        self.scanAllChk.setChecked(self.settings.value('scanAll', False, type=bool))
        self.showAllChk.setChecked(self.settings.value('showAll', False, type=bool))

        self.dbBackupChk.setChecked(self.settings.value('dbBackup', True, type=bool))
        self.dbBackupSpin.setValue(self.settings.value('dbBackupInterval', 5, type=int))
        dataDir = QtCore.QDir(QtCore.QStandardPaths.standardLocations(QtCore.QStandardPaths.AppDataLocation)[0])
        dbFile = QtCore.QFile(dataDir.filePath('sample.sqlite'))
        self.dbPathEdit.setText(self.settings.value('dbPath', dbFile.fileName(), type=str))

        defaultVolumeMode = self.settings.value('defaultVolumeMode', 0, type=int)
        self.defaultVolumeGroup.button(defaultVolumeMode).setChecked(True)
        customVolume = self.settings.value('customVolume', self.parent().volumeSlider.value(), type=int)
        self.defaultVolumeCustomSpin.setValue(customVolume)

        res = QtWidgets.QDialog.exec_(self)
        if not res:
            return
        self.settings.setValue('startupView', self.startupViewGroup.checkedId())
        self.settings.setValue('defaultVolumeMode', self.defaultVolumeGroup.checkedId())
        self.settings.setValue('customVolume', self.defaultVolumeCustomSpin.value())
        if self.scanAllChk.isChecked():
            self.settings.setValue('scanAll', True)
        else:
            self.settings.remove('scanAll')
        if self.showAllChk.isChecked():
            self.settings.setValue('showAll', True)
        else:
            self.settings.remove('showAll')
        self.settings.setValue('dbBackup', self.dbBackupChk.isChecked())
        self.settings.setValue('dbBackupInterval', self.dbBackupSpin.value())
        self.settings.sync()


