import os
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from samplebrowsesrc import utils

class StatsDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi('{}/stats.ui'.format(os.path.dirname(utils.__file__)), self)
        self.sampleDb = parent.sampleDb
        self.sampleDb.execute('SELECT * from samples')
        sampleCount = 0
        missing = 0
        dirs = set()
        totLength = 0
        totSize = 0
        formats = {}
        sampleRates = {}
        channelsDict = {}
        for filePath, fileName, length, format, sampleRate, channels, subtype, tags, preview in self.sampleDb.fetchall():
            sampleCount += 1
            fileInfo = QtCore.QFileInfo(filePath)
            if not fileInfo.exists():
                missing += 1
                continue
            dirs.add(fileInfo.absolutePath())
            totSize += fileInfo.size()
            totLength += length
            if not format in formats:
                formats[format] = 1
            else:
                formats[format] += 1
            if not sampleRate in sampleRates:
                sampleRates[sampleRate] = 1
            else:
                sampleRates[sampleRate] += 1
            if not channels in channelsDict:
                channelsDict[channels] = 1
            else:
                channelsDict[channels] += 1
        if not sampleCount:
            return
        self.entriesLbl.setText('{}{}'.format(sampleCount, '({} missing)'.format(missing) if missing else ''))
        self.dirsLbl.setText(str(len(dirs)))
        self.lengthLbl.setText(utils.timeStr(int(totLength), leading=1, trailing=0))
        self.sizeLbl.setText(utils.sizeStr(totSize))

        self.fillTable('Format', self.formatsTable, formats)
        self.fillTable('Rate', self.sampleRatesTable, sampleRates)
        self.fillTable('Chans', self.channelsTable, channelsDict)

    def fillTable(self, label, table, data):
        model = QtGui.QStandardItemModel()
        model.setHorizontalHeaderLabels([label, 'N'])
        table.setModel(model)
        for key in sorted(data.keys()):
            count = data[key]
            keyItem = QtGui.QStandardItem()
            keyItem.setData(key, QtCore.Qt.DisplayRole)
            countItem = QtGui.QStandardItem()
            countItem.setData(count, QtCore.Qt.DisplayRole)
            model.appendRow([keyItem, countItem])
        table.resizeColumnToContents(1)
        table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        table.sortByColumn(1, QtCore.Qt.DescendingOrder)


