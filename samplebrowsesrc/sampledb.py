import sqlite3
from threading import Lock
from PyQt5 import QtCore, QtGui

from samplebrowsesrc.constants import *

class SampleDb(QtCore.QObject):
    backupDone = QtCore.pyqtSignal(bool)
    def __init__(self, parent):
        QtCore.QObject.__init__(self, parent)
        self.lock = Lock()
        self.dbFile = None
        self.dbConn = None
        self.dbCursor = None
        self.initialized = False
        self.tagColorsDict = {}
        self.settings = QtCore.QSettings()
        self.dbBackupTimer = QtCore.QTimer()
        self.dbBackupTimer.timeout.connect(self.doDbBackup)
        dataDir = QtCore.QDir(QtCore.QStandardPaths.standardLocations(QtCore.QStandardPaths.AppDataLocation)[0])
        defaultDbFile = QtCore.QFileInfo(dataDir.filePath('sample.sqlite'))
        dbFile = QtCore.QFileInfo(self.settings.value('dbPath', defaultDbFile.absoluteFilePath(), type=str))
        self.loadDb(dbFile)

    def doDbBackup(self):
        if not self.settings.value('dbBackup', True, type=bool):
            self.dbBackupTimer.stop()
            return
        self.lock.acquire()
        dbFilePath = self.dbFile.absoluteFilePath()
        bkpFilePath = dbFilePath + '.bkp'
        bkpPrevFilePath = bkpFilePath + '.old'
        try:
            if QtCore.QFile.exists(bkpFilePath):
                try:
                    if QtCore.QFile.exists(bkpPrevFilePath):
                        assert QtCore.QFile.remove(bkpPrevFilePath)
                    assert QtCore.QFile.copy(bkpFilePath, bkpPrevFilePath)
                except:
                    self.backupDone.emit(False)
                    print('Db backup: write error for second backup')
                assert QtCore.QFile.remove(bkpFilePath)
            assert QtCore.QFile.copy(dbFilePath, bkpFilePath)
        except:
            self.backupDone.emit(False)
            print('Db backup: write error')
        self.backupDone.emit(True)
        self.lock.release()

    def initialize(self, dbFile, dbConn=None):
        if self.dbConn:
            self.dbConn.close()
        if not dbConn:
            dbConn = sqlite3.connect(dbFile.absoluteFilePath())
        dbCursor = dbConn.cursor()
        if not self.createTables(dbCursor):
            self.initialized = False
            self.dbBackupTimer.stop()
            return False
        self.dbConn = dbConn
        self.dbCursor = dbCursor
        self.dbFile = dbFile
        self.fetchall = self.dbCursor.fetchall
        self.fetchone = self.dbCursor.fetchone
        self.commit = self.dbConn.commit
        self.close = self.dbConn.close
        self.tagColorsDict.clear()
        self.dbCursor.execute('SELECT tag,foreground,background FROM tagColors')
        for res in self.dbCursor.fetchall():
            tag, foreground, background = res
            self.tagColorsDict[tag] = QtGui.QColor(foreground), QtGui.QColor(background)
        if self.settings.value('dbBackup', True, type=bool):
            self.dbBackupTimer.setInterval(self.settings.value('dbBackupInterval', 5, type=int) * 60000)
            self.dbBackupTimer.start()
        else:
            self.dbBackupTimer.stop()
        self.initialized = True
        self.dbConn.commit()
        return True

    def setBackup(self, state, interval=300000):
        self.dbBackupTimer.setInterval(interval)
        if not state:
            self.dbBackupTimer.stop()
        else:
            self.dbBackupTimer.start()

    def loadDb(self, dbFile):
        if isinstance(dbFile, str):
            dbFile = QtCore.QFileInfo(dbFile)
        if dbFile.exists():
            try:
                dbConn = sqlite3.connect(dbFile.absoluteFilePath())
                dbCursor = dbConn.cursor()
                dbCursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
                tables = [table[0] for table in dbCursor.fetchall()]
                #check that we don't have foreign tables in here
                base = set(('samples', 'tagColors'))
                assert not (set(tables) | base) ^ base
                assert self.initialize(dbFile, dbConn)
            except Exception as e:
                print(e, 'load')

    def createDb(self, dbFile, default=False):
        if isinstance(dbFile, str):
            dbFile = QtCore.QFileInfo(dbFile)
        try:
            dbDir = QtCore.QDir(dbFile.absolutePath())
            if not dbDir.exists():
                dbDir.mkpath(dbDir.absolutePath())
        except Exception as e:
            return False
        return self.initialize(dbFile)

    def createTables(self, dbCursor):
        if not dbCursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="samples"').fetchone():
            try:
                dbCursor.execute('CREATE table samples(filePath varchar primary key, fileName varchar, length float, format varchar, sampleRate int, channels int, tags varchar, preview blob)')
            except Exception as e:
                print(e)
                return False
        #migrate from _very_ early version (someday we will remove this
        elif len(dbCursor.execute('PRAGMA table_info(samples)').fetchall()) != len(allColumns):
            try:
                dbCursor.execute('ALTER TABLE samples RENAME TO oldsamples')
                dbCursor.execute('CREATE table samples(filePath varchar primary key, fileName varchar, length float, format varchar, sampleRate int, channels int, subtype varchar, tags varchar, preview blob)')
                dbCursor.execute('INSERT INTO samples (filePath, fileName, length, format, sampleRate, channels, tags, preview) SELECT filePath, fileName, length, format, sampleRate, channels, tags, preview FROM oldsamples')
                dbCursor.execute('DROP TABLE oldsamples')
            except Exception as e:
                print(e)
                return False
        if not dbCursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="tagColors"').fetchone():
            try:
                dbCursor.execute('CREATE table tagColors(tag varchar primary key, foreground varchar, background varchar)')
            except Exception as e:
                print(e)
                return False
        return True

    def execute(self, *args, **kwargs):
        self.lock.acquire()
        try:
            return self.dbCursor.execute(*args, **kwargs)
        finally:
            self.lock.release()

