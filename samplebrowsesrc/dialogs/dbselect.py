import os
import sqlite3
from PyQt5 import QtCore, QtWidgets, uic

from samplebrowsesrc import utils
from samplebrowsesrc.constants import *

class BrowseCustomPathDialog(QtWidgets.QFileDialog):
    def __init__(self, *args, **kwargs):
        QtWidgets.QFileDialog.__init__(self, *args, **kwargs)
        self.setAcceptMode(self.AcceptOpen)
        self.setFileMode(self.Directory)
        self.setOption(self.DontUseNativeDialog, True)
        self.setOption(self.ShowDirsOnly, True)
        self.directoryEntered.connect(self.dirChanged)
        self.buttonBox = self.findChild(QtWidgets.QDialogButtonBox)
        self.OpenButton = self.buttonBox.button(self.buttonBox.Open)
        #fix for history buttons not emitting signals
        self.backButton = self.findChild(QtWidgets.QToolButton, 'backButton')
        if self.backButton:
            self.backButton.clicked.connect(lambda: self.directoryEntered.emit(self.directory().absolutePath()))
        self.fwdButton = self.findChild(QtWidgets.QToolButton, 'forwardButton')
        if self.fwdButton:
            self.fwdButton.clicked.connect(lambda: self.directoryEntered.emit(self.directory().absolutePath()))
        self.fileNameEdit = self.findChild(QtWidgets.QLineEdit, 'fileNameEdit')

        self.directoryEntered.emit(self.directory().absolutePath())
        self.currentChanged.connect(self.dirChanged)

    def dirChanged(self, dirPath):
        #override default behavior to inhibit unwritable directory
        QtCore.QTimer.singleShot(0, lambda: self.OpenButton.setEnabled(QtCore.QFileInfo(dirPath).isWritable()))


class DbSelectDialog(QtWidgets.QDialog):
    dbOk, dbWillCreate, dbNotExists, dbError, dbFileWriteError, dbFileFormatError, dbSpaceWarning = range(7)
    statusInfo = {
        dbOk: ('dialog-information', 'Database is ok'), 
        dbWillCreate: ('dialog-information', 'Database will be created'), 
        dbNotExists: ('dialog-error', 'No database file selected'), 
        dbError: ('dialog-error', 'Database is invalid'), 
        dbFileWriteError: ('dialog-error', 'File write error'), 
        dbFileFormatError: ('dialog-error', 'Database file format error'), 
        dbSpaceWarning: ('dialog-warning', 'File space insufficient'), 
        }

    def __init__(self, parent=None, pathMode=0):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi('{}/dbselect.ui'.format(os.path.dirname(utils.__file__)), self)
        self.customDbFilePath = QtCore.QFileInfo(QtCore.QDir(QtCore.QStandardPaths.standardLocations(QtCore.QStandardPaths.HomeLocation)[0]).filePath('sample.sqlite'))
        self.tempDbFilePath = QtCore.QFileInfo(QtCore.QDir(QtCore.QStandardPaths.standardLocations(QtCore.QStandardPaths.TempLocation)[0]).filePath('sample.sqlite'))
        self.existingDbFilePath = QtCore.QFileInfo()
        self.dbPathCombo.currentIndexChanged.connect(self.updateDbPath)
        self.dbBrowseFunc = self.dbBrowseCustomPath
        self.dbBrowseBtn.clicked.connect(lambda: self.dbBrowseFunc())
        self.OkBtn = self.buttonBox.button(self.buttonBox.Ok)
        self.dbPathCombo.setCurrentIndex(pathMode)
        self.state = self.dbError
        self.updateDbPath(pathMode)

    def setStatus(self, state):
        self.state = state
        self.dbStatusLbl.setText('<img src=":/icons/TangoCustom/16x16/{}.png"> {}'.format(*self.statusInfo[state]))

    def dbBrowseCustomPath(self):
        browseDialog = BrowseCustomPathDialog(self, 'Select custom path', self.customDbFilePath.absolutePath())
        if browseDialog.exec_():
            self.customDbFilePath.setFile(QtCore.QDir(browseDialog.selectedFiles()[0]), 'sample.sqlite')
            state = self.testDbFile(self.customDbFilePath, True)
            self.dbPathEdit.setText(self.customDbFilePath.absoluteFilePath())
            if state in (self.dbOk, self.dbSpaceWarning, self.dbNotExists):
                self.OkBtn.setEnabled(True)
            else:
                self.OkBtn.setEnabled(False)
            self.setStatus(state)

    def dbBrowseExistingFile(self):
        res = QtWidgets.QFileDialog.getOpenFileName(
            self, 
            'Select existing file', 
            QtCore.QStandardPaths.standardLocations(QtCore.QStandardPaths.HomeLocation)[0]
            )
        if res and QtCore.QFile.exists(res[0]):
            self.existingDbFilePath.setFile(res[0])
            state = self.testDbFile(self.existingDbFilePath, True)
            self.dbPathEdit.setText(self.existingDbFilePath.absoluteFilePath())
            if state in (self.dbOk, self.dbSpaceWarning):
                self.OkBtn.setEnabled(True)
            else:
                self.OkBtn.setEnabled(False)
            self.setStatus(state)

    def testDbFile(self, dbFile, willCreate=False):
        if not QtCore.QFileInfo(dbFile.absolutePath()).isWritable():
            return self.dbFileWriteError
        if QtCore.QStorageInfo(dbFile.absoluteDir()).bytesFree() < 10485760:
            return self.dbSpaceWarning
        if not dbFile.exists():
            return self.dbWillCreate if willCreate else self.dbNotExists 
        try:
            dbConn = sqlite3.connect(dbFile.absoluteFilePath())
            dbCursor = dbConn.cursor()
            dbCursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
            tables = [table[0] for table in dbCursor.fetchall()]
            if not tables:
                return self.dbOk
            fields = [f[1] for f in dbCursor.execute('PRAGMA table_info(samples)').fetchall()]
            if fields != dbFields and fields != dbFieldsOld:
                return self.dbError
            return self.dbOk
        except:
            return self.dbFileFormatError

    def updateDbPath(self, index):
        if index == 0:
            dataDir, defaultDbFile = self.getDefaults()
            self.dbPathEdit.setText(defaultDbFile.absoluteFilePath())
            self.dbBrowseBtn.setEnabled(False)
            state = self.testDbFile(defaultDbFile, True)
        elif index == 1:
            self.dbPathEdit.setText(self.tempDbFilePath.absoluteFilePath())
            self.dbBrowseBtn.setEnabled(False)
            state = self.testDbFile(self.tempDbFilePath, True)
        elif index == 2:
            self.dbPathEdit.setText(self.customDbFilePath.absoluteFilePath())
            self.dbBrowseBtn.setEnabled(True)
            self.dbBrowseFunc = self.dbBrowseCustomPath
            state = self.testDbFile(self.customDbFilePath, True)
        else:
            self.dbPathEdit.setText(self.existingDbFilePath.absoluteFilePath())
            self.dbBrowseBtn.setEnabled(True)
            self.dbBrowseFunc = self.dbBrowseExistingFile
            state = self.testDbFile(self.existingDbFilePath, False)
        self.setStatus(state)
        self.OkBtn.setEnabled(state in (self.dbOk, self.dbSpaceWarning, self.dbNotExists, self.dbWillCreate))

    def getDefaults(self):
        dataDir = QtCore.QDir(QtCore.QStandardPaths.standardLocations(QtCore.QStandardPaths.AppDataLocation)[0])
        defaultDbFile = QtCore.QFileInfo(dataDir.filePath('sample.sqlite'))
        return dataDir, defaultDbFile

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            event.ignore()
            return
        QtWidgets.QDialog.keyPressEvent(self, event)

    def closeEvent(self, event):
        event.ignore()

    def exec_(self):
        QtWidgets.QDialog.exec_(self)
        if self.dbPathCombo.currentIndex() == 0:
            return 0, self.getDefaults()[1]
        elif self.dbPathCombo.currentIndex() == 1:
            return 1, self.tempDbFilePath
        elif self.dbPathCombo.currentIndex() == 2:
            return 2, self.customDbFilePath
        else:
            return 3, self.existingDbFilePath
