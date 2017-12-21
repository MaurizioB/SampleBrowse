import sys
import os
import soundfile
from collections import namedtuple
from PyQt5 import QtCore, QtGui, QtWidgets, QtMultimedia, uic

from samplebrowsesrc import utils
from samplebrowsesrc.constants import *
from samplebrowsesrc.widgets.colorlineedit import ColorLineEdit
from samplebrowsesrc.widgets import TagsEditorTextEdit, AlignItemDelegate, TagListDelegate, SubtypeDelegate
from samplebrowsesrc.classes import SampleSortFilterProxyModel, Crawler
from samplebrowsesrc.info import __version__, __author__, __description__, __codeurl__
audioDevice = namedtuple('audioDevice', 'device name sampleRates sampleSizes channels')


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi('{}/settings.ui'.format(os.path.dirname(utils.__file__)), self)
        self.settings = QtCore.QSettings()

        self.startupViewGroup.setId(self.startupFsRadio, 0)
        self.startupViewGroup.setId(self.startupDbRadio, 1)
        self.startupViewGroup.setId(self.startupLastRadio, 2)

        self.defaultVolumeGroup.setId(self.defaultVolume100Radio, 0)
        self.defaultVolumeGroup.setId(self.defaultVolumePreviousRadio, 1)
        self.defaultVolumeGroup.setId(self.defaultVolumeCustomRadio, 2)
        self.audioDeviceBtn.clicked.connect(self.showAudioSettings)

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

        dataDir = QtCore.QDir(QtCore.QStandardPaths.standardLocations(QtCore.QStandardPaths.AppDataLocation)[0])
        dbFile = QtCore.QFile(dataDir.filePath('sample.sqlite'))
        self.dbPathEdit.setText(dbFile.fileName())

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
        self.settings.sync()


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
        self.lengthLbl.setText(utils.timeStr(int(totLength), trailing=0))
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


class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi('{}/about.ui'.format(os.path.dirname(utils.__file__)), self)
        self.iconLbl.setPixmap(QtGui.QIcon(':/icons/TangoCustom/64x64/samplebrowse.png').pixmap(64))
        self.descriptionLbl.setText(__description__)
        self.versionEntry.setText(__version__)
        self.authorEntry.setText(__author__)
        self.websiteEntry.setText('<a href="{}">Project on GitHub</a>'.format(__codeurl__))

        self.aboutQtBtn.setIcon(QtGui.QIcon(':/qt-project.org/qmessagebox/images/qtlogo-64.png'))
        self.aboutQtBtn.clicked.connect(lambda: QtWidgets.QMessageBox.aboutQt(self))

        baseHtml = '''
            SampleBrowse wouldn't have been possible without the following libraries and people...
            <h3>libsndfile</h3>
            Written by Erik de Castro Lopo: <a href="http://www.mega-nerd.com/libsndfile/">mega-nerd.com</a><br/>
            Python module written by <a href="http://www.mega-nerd.com/">Alex Roebel</a>:
                <a href="https://pypi.python.org/pypi/pysndfile">pysndfile</a>
            
            <h3><u>S</u>ecret <u>R</u>abbit <u>C</u>ode (aka libsamplerate)</h3>
            Written by Erik de Castro Lopo: <a href="http://www.mega-nerd.com/SRC/">mega-nerd.com</a><br/>
            Python module written by <a href="https://github.com/tuxu">Tino Wagner</a>: 
                <a href="https://pypi.python.org/pypi/samplerate">samplerate</a>
            
            {tango}
            
            <h3>Thanks to:</h3>
            Faber aka Fabio Vescarelli (<a href="http://www.faberbox.com/">faberbox.com</a>) for his great help in helping me
            to understand the secrets of Python... and his patience ;-)
            '''
        tangoHtml = '''
            <h3>Tango Icon Library</h3>
            This version of SampleBrowse uses icons from the <a href="http://tango.freedesktop.org/">Tango Desktop Project</a>
            '''
        self.aknTextBrowser.setHtml(baseHtml.format(tango=tangoHtml if 'linux' not in sys.platform else ''))
        self.shown = False

    #since there are some issues with QLabels in layouts, we set the minimum width
    def exec_(self):
        self.show()
        fontMetrics = QtGui.QFontMetrics(self.font())
        keySize = max([fontMetrics.width(w.text()) for w in (self.websiteLbl, self.authorLbl, self.versionLbl)])
        websiteDoc = QtGui.QTextDocument()
        websiteDoc.setHtml(self.websiteEntry.text())
        websiteDocSize = fontMetrics.width(websiteDoc.toPlainText())
        valueSize = max([fontMetrics.width(w.text()) for w in (self.authorEntry, self.versionEntry)] + [websiteDocSize])
        self.aboutTab.setMinimumWidth(
            self.iconLbl.minimumWidth() + 
            max((keySize + valueSize, fontMetrics.width(self.descriptionLbl.text()))) +
            self.aboutTab.layout().horizontalSpacing() + 
            self.aboutTab.layout().contentsMargins().left() + self.aboutTab.layout().contentsMargins().right() 
            )


class AudioDeviceProber(QtCore.QObject):
    deviceList = QtCore.pyqtSignal(object)
    def probe(self):
        deviceList = []
        for device in QtMultimedia.QAudioDeviceInfo.availableDevices(QtMultimedia.QAudio.AudioOutput):
            deviceInfo = audioDevice(device, device.deviceName(), device.supportedSampleRates(), device.supportedSampleSizes(), device.supportedChannelCounts())
            deviceList.append(deviceInfo)
        self.deviceList.emit(deviceList)


class AudioDevicesListView(QtWidgets.QListView):
    deviceSelected = QtCore.pyqtSignal(object)
    def currentChanged(self, current, previous):
        self.deviceSelected.emit(current)


class AudioSettingsDialog(QtWidgets.QDialog):
    def __init__(self, main, parent=None):
        if parent is None:
            parent = main
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi('{}/audiosettings.ui'.format(os.path.dirname(utils.__file__)), self)
        self.main = main
        self.settings = QtCore.QSettings()

        self.popup = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Information, 
            'Probing audio devices', 
            'Probing audio devices, please wait...', 
            parent=self)
        self.popup.setStandardButtons(self.popup.NoButton)
        self.deviceModel = QtGui.QStandardItemModel()
        self.deviceList.setModel(self.deviceModel)
        self.sampleRatesModel = QtGui.QStandardItemModel()
        self.sampleRatesList.setModel(self.sampleRatesModel)
        self.deviceList.deviceSelected.connect(self.deviceSelected)
        self.channelsModel = QtGui.QStandardItemModel()
        self.channelsList.setModel(self.channelsModel)

        for chk in (self.depth8Chk, self.depth16Chk, self.depth32Chk):
            chk.mousePressEvent = lambda *args: None
            chk.keyPressEvent = lambda *args: None

    def deviceSelected(self, index):
        self.sampleRatesModel.clear()
        device = index.data(DeviceRole)
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(True if index.data(ValidRole) != False else False)
        self.deviceInfoBox.setTitle(device.deviceName())
        preferredFormat = index.data(FormatRole)
        if not preferredFormat:
            preferredFormat = device.preferredFormat()
        for sampleRate in sorted(index.data(SampleRateRole), reverse=True):
            item = QtGui.QStandardItem('{:.1f} kHz'.format(sampleRate/1000.))
            if sampleRate == preferredFormat.sampleRate():
                utils.setBold(item)
            self.sampleRatesModel.appendRow(item)
        sampleSizes = index.data(SampleSizeRole)
        for sampleSize in (8, 16, 32):
            checkBox = getattr(self, 'depth{}Chk'.format(sampleSize))
            checkBox.setChecked(True if sampleSize in sampleSizes else False)
            utils.setBold(checkBox, True if sampleSize == preferredFormat.sampleSize() else False)
        self.channelsModel.clear()
        for channelCount in sorted(index.data(ChannelsRole)):
            item = QtGui.QStandardItem('{}: {}'.format(channelCount, channelsLabels.get(channelCount, '(unknown configuration)')))
            if channelCount == preferredFormat.channelCount():
                utils.setBold(item)
            self.channelsModel.appendRow(item)

    def probed(self, deviceList):
        self.popup.hide()
        default = QtMultimedia.QAudioDeviceInfo.defaultOutputDevice()
        current = None
        for device, name, sampleRates, sampleSizes, channels in deviceList:
            if device == default:
                name = '{} (default)'.format(name)
            deviceItem = QtGui.QStandardItem(name)
            if device == self.main.player.audioDevice:
                current = deviceItem
                utils.setBold(deviceItem)
            deviceItem.setData(device, DeviceRole)
            deviceItem.setData(sampleRates, SampleRateRole)
            deviceItem.setData(sampleSizes, SampleSizeRole)
            deviceItem.setData(channels, ChannelsRole)
            if not (sampleRates and sampleSizes and channels):
                deviceItem.setData(False, ValidRole)
            self.deviceModel.appendRow(deviceItem)
        currentDeviceName = self.settings.value('AudioDevice')
        if current:
            if currentDeviceName:
                match = self.deviceModel.match(self.deviceModel.index(0, 0), QtCore.Qt.DisplayRole, currentDeviceName, flags=QtCore.Qt.MatchExactly)
                if not match:
                    self.deviceList.setCurrentIndex(current.index())
                else:
                    self.deviceList.setCurrentIndex(match[0])
            else:
                self.deviceList.setCurrentIndex(current.index())

    def exec_(self):
        try:
            getattr(self, '{}Radio'.format(self.settings.value('SampleRateConversion', 'sinc_fastest'))).setChecked(True)
        except:
            self.sinc_fastestRadio.setChecked(True)

        prober = AudioDeviceProber()
        proberThread = QtCore.QThread()
        prober.moveToThread(proberThread)
        proberThread.started.connect(prober.probe)
        prober.deviceList.connect(self.probed)
        prober.deviceList.connect(lambda _: [proberThread.quit(), prober.deleteLater(), proberThread.deleteLater()])
        self.deviceModel.clear()
        self.show()
        self.popup.show()
        self.popup.setModal(True)
        proberThread.start()
        res = QtWidgets.QDialog.exec_(self)
        if not res:
            return res
        device = self.deviceList.currentIndex().data(DeviceRole)
        self.settings.setValue('AudioDevice', device.deviceName())
        conversion = self.sampleRateGroup.checkedButton().objectName()[:-len('Radio')]
        if conversion == 'sinc_fastest':
            self.settings.remove('SampleRateConversion')
        else:
            self.settings.setValue('SampleRateConversion', conversion)
        return device, conversion


class TagColorDialog(QtWidgets.QDialog):
    def __init__(self, parent, index):
        QtWidgets.QDialog.__init__(self, parent)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        layout.addWidget(QtWidgets.QLabel('Text color:'))
        self.foregroundColor = index.data(QtCore.Qt.ForegroundRole)
        self.backgroundColor = index.data(QtCore.Qt.BackgroundRole)
        self.foregroundEdit = ColorLineEdit()
        basePalette = self.foregroundEdit.palette()
        self.defaultForeground = basePalette.color(basePalette.Active, basePalette.Text)
        self.defaultBackground = basePalette.color(basePalette.Active, basePalette.Base)
        if self.foregroundColor is None:
            self.foregroundColor = self.defaultForeground
        else:
            basePalette.setColor(basePalette.Active, basePalette.Text, self.foregroundColor)
            basePalette.setColor(basePalette.Inactive, basePalette.Text, self.foregroundColor)
        if self.backgroundColor is None:
            self.backgroundColor = self.defaultBackground
        else:
            basePalette.setColor(basePalette.Active, basePalette.Base, self.backgroundColor)
            basePalette.setColor(basePalette.Inactive, basePalette.Base, self.backgroundColor)
        self.foregroundEdit.setText(self.foregroundColor.name())
        self.foregroundEdit.textChanged.connect(self.setForegroundColor)
        self.foregroundEdit.editBtnClicked.connect(self.foregroundSelect)
        self.foregroundEdit.setPalette(basePalette)
        layout.addWidget(self.foregroundEdit, 0, 1)
        autoBgBtn = QtWidgets.QPushButton('Autoset background')
        layout.addWidget(autoBgBtn, 0, 2)
        autoBgBtn.clicked.connect(lambda: self.setBackgroundColor(self.reverseColor(self.foregroundColor)))

        layout.addWidget(QtWidgets.QLabel('Background:'))
        self.backgroundEdit = ColorLineEdit()
        self.backgroundEdit.setText(self.backgroundColor.name())
        self.backgroundEdit.textChanged.connect(self.setBackgroundColor)
        self.backgroundEdit.editBtnClicked.connect(self.backgroundSelect)
        self.backgroundEdit.setPalette(basePalette)
        layout.addWidget(self.backgroundEdit, 1, 1)
        autoFgBtn = QtWidgets.QPushButton('Autoset text')
        layout.addWidget(autoFgBtn, 1, 2)
        autoFgBtn.clicked.connect(lambda: self.setForegroundColor(self.reverseColor(self.backgroundColor)))

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.RestoreDefaults)
        layout.addWidget(self.buttonBox, layout.rowCount(), 0, 1, layout.columnCount())
        self.okBtn = self.buttonBox.button(self.buttonBox.Ok)
        self.okBtn.clicked.connect(self.accept)
        self.buttonBox.button(self.buttonBox.Cancel).clicked.connect(self.reject)
        self.restoreBtn = self.buttonBox.button(self.buttonBox.RestoreDefaults)
        self.restoreBtn.setIcon(QtGui.QIcon.fromTheme('edit-undo'))
        self.restoreBtn.clicked.connect(lambda: [self.setBackgroundColor(), self.setForegroundColor()])

    def reverseColor(self, color):
        r, g, b, a = color.getRgb()
        return QtGui.QColor(r^255, g^255, b^255)

    def foregroundSelect(self):
        color = QtWidgets.QColorDialog.getColor(self.foregroundColor, self, 'Select text color')
        if color.isValid():
            self.foregroundEdit.setText(color.name())
            self.setForegroundColor(color)

    def setForegroundColor(self, color=None):
        if not color:
            color = self.defaultForeground
        elif isinstance(color, str):
            color = QtGui.QColor(color)
        self.foregroundColor = color
        palette = self.foregroundEdit.palette()
        palette.setColor(palette.Active, palette.Text, self.foregroundColor)
        palette.setColor(palette.Inactive, palette.Text, self.foregroundColor)
        self.foregroundEdit.setPalette(palette)
        self.backgroundEdit.setPalette(palette)

    def backgroundSelect(self):
        color = QtWidgets.QColorDialog.getColor(self.backgroundColor, self, 'Select background color')
        if color.isValid():
            self.backgroundEdit.setText(color.name())
            self.setBackgroundColor(color)

    def setBackgroundColor(self, color=None):
        if not color:
            color = self.defaultBackground
        elif isinstance(color, str):
            color = QtGui.QColor(color)
        self.backgroundColor = color
        palette = self.backgroundEdit.palette()
        palette.setColor(palette.Active, palette.Base, self.backgroundColor)
        palette.setColor(palette.Inactive, palette.Base, self.backgroundColor)
        self.foregroundEdit.setPalette(palette)
        self.backgroundEdit.setPalette(palette)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if self.foregroundColor == self.defaultForeground and self.backgroundColor == self.defaultBackground:
            self.foregroundColor = None
            self.backgroundColor = None
        return res


class ImportDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi('{}/importdialog.ui'.format(os.path.dirname(utils.__file__)), self)
        self.sampleModel = QtGui.QStandardItemModel()
        self.sampleProxyModel = SampleSortFilterProxyModel()
        self.sampleProxyModel.setSourceModel(self.sampleModel)
        self.sampleView.setModel(self.sampleProxyModel)
        self.sampleModel.setHorizontalHeaderLabels(['Name', 'Path', 'Length', 'Format', 'Rate', 'Ch.', 'Bits', 'Tags'])

        self.elidedItemDelegate = AlignItemDelegate(QtCore.Qt.AlignLeft, QtCore.Qt.ElideMiddle)
        self.sampleView.setItemDelegateForColumn(1, self.elidedItemDelegate)
        self.alignCenterDelegate = AlignItemDelegate(QtCore.Qt.AlignCenter)
        for c in range(2, channelsColumn + 1):
            self.sampleView.setItemDelegateForColumn(c, self.alignCenterDelegate)
        self.subtypeDelegate = SubtypeDelegate()
        self.sampleView.setItemDelegateForColumn(subtypeColumn, self.subtypeDelegate)
        self.tagListDelegate = TagListDelegate(self.parent().tagColorsDict)
        self.sampleView.setItemDelegateForColumn(tagsColumn, self.tagListDelegate)
        self.sampleView.setMouseTracking(True)

        fontMetrics = QtGui.QFontMetrics(self.font())

        self.sampleView.horizontalHeader().setSectionResizeMode(fileNameColumn, QtWidgets.QHeaderView.Stretch)
        self.sampleView.horizontalHeader().setSectionResizeMode(dirColumn, QtWidgets.QHeaderView.Stretch)
        self.sampleView.horizontalHeader().resizeSection(lengthColumn, fontMetrics.width('888.888') + 10)
        self.sampleView.horizontalHeader().setSectionResizeMode(lengthColumn, QtWidgets.QHeaderView.Fixed)
        self.sampleView.horizontalHeader().resizeSection(formatColumn, fontMetrics.width('Format') + 10)
        self.sampleView.horizontalHeader().setSectionResizeMode(formatColumn, QtWidgets.QHeaderView.Fixed)
        self.sampleView.horizontalHeader().resizeSection(rateColumn, fontMetrics.width('192000') + 10)
        self.sampleView.horizontalHeader().setSectionResizeMode(rateColumn, QtWidgets.QHeaderView.Fixed)
        self.sampleView.horizontalHeader().resizeSection(channelsColumn, fontMetrics.width('Ch.') + 10)
        self.sampleView.horizontalHeader().setSectionResizeMode(channelsColumn, QtWidgets.QHeaderView.Fixed)
        self.sampleView.horizontalHeader().resizeSection(subtypeColumn, fontMetrics.width('Bits') + 12)
        self.sampleView.horizontalHeader().setSectionResizeMode(subtypeColumn, QtWidgets.QHeaderView.Fixed)

        self.selectAllBtn.clicked.connect(self.sampleView.selectAll)
        self.checkSelectedBtn.clicked.connect(lambda: self.setSelectedCheckState(QtCore.Qt.Checked))
        self.uncheckSelectedBtn.clicked.connect(lambda: self.setSelectedCheckState(QtCore.Qt.Unchecked))
        self.sampleProxyModel.dataChanged.connect(self.checkChecked)
        self.sampleView.selectionModel().selectionChanged.connect(
            lambda *args: self.editTagsBtn.setEnabled(len(self.sampleView.selectionModel().selection().indexes())))
        self.editTagsBtn.clicked.connect(self.editTags)
        self.sampleView.customContextMenuRequested.connect(self.sampleContextMenu)

    def editTags(self):
        indexes = []
        tags = set()
        for index in self.sampleView.selectedIndexes():
            if index.column() == tagsColumn:
                indexes.append(index)
                tagList = index.data(TagsRole)
                if tagList:
                    tags.add(tuple(tagList))
        if not indexes:
            return
        uncommon = False
        if not tags:
            tags = []
        elif len(tags) == 1:
            tags = list(tags)[0]
        else:
            tags = sorted(set(tag for tagList in tags for tag in tagList))
            uncommon = True
        res = TagsEditorDialog(self, tags, uncommon=uncommon).exec_()
        if not isinstance(res, list):
            return
        for index in indexes:
            self.sampleProxyModel.setData(index, res, TagsRole)

    def sampleContextMenu(self, pos):
        menu = QtWidgets.QMenu()
        setCheckedAction = QtWidgets.QAction('Set for import', menu)
        unsetCheckedAction = QtWidgets.QAction('Unset for import', menu)
        editTagsAction = QtWidgets.QAction('Edit tags...', menu)

        selIndexes = self.sampleView.selectionModel().selection().indexes()
        if selIndexes:
            checked = 0
            for index in selIndexes:
                if index.column() == 0 and index.data(QtCore.Qt.CheckStateRole):
                    checked += 1
            setCheckedAction.setEnabled(checked != len(selIndexes) / self.sampleModel.columnCount())
            unsetCheckedAction.setEnabled(checked != 0)
        else:
            setCheckedAction.setEnabled(False)
            unsetCheckedAction.setEnabled(False)
            editTagsAction.setEnabled(False)
        selectAllAction = QtWidgets.QAction('Select all', menu)

        menu.addActions([setCheckedAction, unsetCheckedAction, editTagsAction, utils.menuSeparator(menu), selectAllAction])
        res = menu.exec_(self.sampleView.viewport().mapToGlobal(pos))
        if res == selectAllAction:
            self.sampleView.selectAll()
        elif res == setCheckedAction:
            self.setSelectedCheckState(QtCore.Qt.Checked)
        elif res == unsetCheckedAction:
            self.setSelectedCheckState(QtCore.Qt.Unchecked)
        elif res == editTagsAction:
            self.editTags()

    def setSelectedCheckState(self, state):
        self.sampleProxyModel.dataChanged.disconnect(self.checkChecked)
        for index in self.sampleView.selectedIndexes():
            if index.column() == 0:
                self.sampleProxyModel.setData(index, state, QtCore.Qt.CheckStateRole)
        self.sampleProxyModel.dataChanged.connect(self.checkChecked)
        self.checkChecked()

    def checkChecked(self, *args):
        checked = 0
        for row in range(self.sampleModel.rowCount()):
            if self.sampleModel.item(row, 0).checkState():
                checked += 1
        self.selectedLbl.setText(str(checked))

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if res:
            sampleList = []
            for row in range(self.sampleModel.rowCount()):
                fileItem = self.sampleModel.item(row, 0)
                if not fileItem.checkState():
                    continue
                fileName = fileItem.text()
                filePath = fileItem.data(FilePathRole)
                info = fileItem.data(InfoRole)
                tags = self.sampleModel.item(row, tagsColumn).data(TagsRole)
                sampleList.append((filePath, fileName, info, tags))
            return sampleList
        else:
            return res


class ImportDialogScan(ImportDialog):
    def __init__(self, parent, dirList, scanMode, formats, sampleRates, channels, scanLimits):
        ImportDialog.__init__(self, parent)
        self.crawler = Crawler(dirList, scanMode, formats, sampleRates, channels, scanLimits)
        self.crawlerThread = QtCore.QThread()
        self.crawler.moveToThread(self.crawlerThread)
        self.crawlerThread.started.connect(self.crawler.run)
        self.popup = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, 'Scanning...', 'Scanning disk, please wait.', QtWidgets.QMessageBox.Cancel, self)
        self.popup.setModal(True)
#        self.popup.rejected.connect(lambda: self.crawler.stop.set())
        self.popup.button(self.popup.Cancel).clicked.connect(lambda: self.crawler.stop.set())
        self.crawler.found.connect(self.found)
        self.crawler.done.connect(self.popup.close)
        self.crawler.done.connect(self.scanDone)
        self.defaultTags = []

    def updatePopupDir(self, dirPath):
        self.popup.setInformativeText('Current path:\n{}'.format(dirPath[:-24]))

    def found(self, fileInfo, info):
        fileItem = QtGui.QStandardItem(fileInfo.fileName())
        fileItem.setData(fileInfo.absoluteFilePath(), FilePathRole)
        fileItem.setData(info, InfoRole)
        fileItem.setToolTip(fileInfo.fileName())
        fileItem.setCheckable(True)
        fileItem.setCheckState(QtCore.Qt.Checked)
        dirItem = QtGui.QStandardItem(fileInfo.absolutePath())
        dirItem.setToolTip(fileInfo.absoluteFilePath())
        lengthItem = QtGui.QStandardItem('{:.3f}'.format(float(info.frames) / info.samplerate))
        formatItem = QtGui.QStandardItem(info.format)
        rateItem = QtGui.QStandardItem(str(info.samplerate))
        channelsItem = QtGui.QStandardItem(str(info.channels))
        subtypeItem = QtGui.QStandardItem(info.subtype)
        tagsItem = QtGui.QStandardItem()
        tagsItem.setData(self.defaultTags, TagsRole)
        self.sampleModel.appendRow([fileItem, dirItem, lengthItem, formatItem, rateItem, channelsItem, subtypeItem, tagsItem])
        if not self.sampleModel.rowCount() % 50:
            self.sampleView.scrollToBottom()
            found = str(self.sampleModel.rowCount())
            self.totalLbl.setText(found)
            self.selectedLbl.setText(found)
            self.popup.setInformativeText('Samples found: ' + found)
#        self.foundSamples.append(filePath)
#        self.popup.setDetailedText('Samples found: {}'.format(len(self.foundSamples)))

    def scanDone(self):
        try:
            self.sampleProxyModel.dataChanged.connect(self.checkChecked)
        except:
            pass
#        self.sampleView.resizeColumnsToContents()
        found = str(self.sampleModel.rowCount())
        self.totalLbl.setText(found)
        self.selectedLbl.setText(found)
        self.checkChecked()

    def exec_(self):
        self.sampleProxyModel.dataChanged.disconnect(self.checkChecked)
        self.show()
        self.popup.show()
        self.crawlerThread.start()
        return ImportDialog.exec_(self)


class ImportDialogScanDnD(ImportDialogScan):
    def __init__(self, parent, dirList, fileList, scanMode, formats, sampleRates, channels, scanLimits, tag):
        if dirList:
            ImportDialogScan.__init__(self, parent, dirList, scanMode, formats, sampleRates, channels, scanLimits)
            self.defaultTags = [tag]
        else:
            ImportDialog.__init__(self, parent)
        unknownFiles = []
        self.dirList = dirList
        for filePath in fileList:
            try:
                info = soundfile.info(filePath)
            except:
                unknownFiles.append(filePath)
                continue
            fileInfo = QtCore.QFileInfo(filePath)
            fileItem = QtGui.QStandardItem(fileInfo.fileName())
            fileItem.setData(filePath, FilePathRole)
            fileItem.setData(info, InfoRole)
            fileItem.setToolTip(fileInfo.fileName())
            fileItem.setCheckable(True)
            fileItem.setCheckState(QtCore.Qt.Checked)
            dirItem = QtGui.QStandardItem(fileInfo.absolutePath())
            dirItem.setToolTip(fileInfo.absoluteFilePath())
            lengthItem = QtGui.QStandardItem('{:.3f}'.format(float(info.frames) / info.samplerate))
            formatItem = QtGui.QStandardItem(info.format)
            rateItem = QtGui.QStandardItem(str(info.samplerate))
            channelsItem = QtGui.QStandardItem(str(info.channels))
            subtypeItem = QtGui.QStandardItem(info.subtype)
            tagsItem = QtGui.QStandardItem()
            tagsItem.setData([tag], TagsRole)
            self.sampleModel.appendRow([fileItem, dirItem, lengthItem, formatItem, rateItem, channelsItem, subtypeItem, tagsItem])

    def exec_(self):
        if self.sampleModel.rowCount() == 0 and not self.dirList:
            return 0
        if self.dirList:
            return ImportDialogScan.exec_(self)
        else:
            return ImportDialog.exec_(self)


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


class AddSamplesWithTagDialog(QtWidgets.QDialog):
    def __init__(self, parent, fileList):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Add samples to database')
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        layout.addWidget(QtWidgets.QLabel('The following samples are about to be added to the database'))
        sampleModel = QtGui.QStandardItemModel()
        sampleView = QtWidgets.QTableView()
        sampleView.setHorizontalScrollMode(sampleView.ScrollPerPixel)
        sampleView.setVerticalScrollMode(sampleView.ScrollPerPixel)
        sampleView.setMaximumHeight(100)
        layout.addWidget(sampleView)
        sampleView.setModel(sampleModel)
        sampleView.setEditTriggers(sampleView.NoEditTriggers)
        sampleView.horizontalHeader().setVisible(False)
        sampleView.verticalHeader().setVisible(False)
        if isinstance(fileList[0], str):
            for filePath in fileList:
                fileItem = QtGui.QStandardItem(QtCore.QFile(filePath).fileName())
                filePathItem = QtGui.QStandardItem(filePath)
                sampleModel.appendRow([fileItem, filePathItem])
        else:
            for index in fileList:
                fileItem = QtGui.QStandardItem(index.data())
                filePathItem = QtGui.QStandardItem(index.data(FilePathRole))
                sampleModel.appendRow([fileItem, filePathItem])
        sampleView.resizeColumnsToContents()
        sampleView.resizeRowsToContents()
#        sampleView.setStretchLastSection(True)
        layout.addWidget(QtWidgets.QLabel('Tags that will be applied to all of them (separate tags with commas):'))
        self.tagsEditor = TagsEditorTextEdit()
        self.tagsEditor.setMaximumHeight(100)
#        self.tagsEditor.setReadOnly(False)
        layout.addWidget(self.tagsEditor)
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.button(self.buttonBox.Ok).clicked.connect(self.accept)
        self.buttonBox.button(self.buttonBox.Cancel).clicked.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if res:
            return self.tagsEditor.tags()
        else:
            return res

class RemoveSamplesDialog(QtWidgets.QDialog):
    def __init__(self, parent, fileList):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Remove samples from database')
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        layout.addWidget(QtWidgets.QLabel('Remove the following samples from the database?'))
        sampleModel = QtGui.QStandardItemModel()
        sampleView = QtWidgets.QTableView()
        sampleView.setHorizontalScrollMode(sampleView.ScrollPerPixel)
        sampleView.setVerticalScrollMode(sampleView.ScrollPerPixel)
        sampleView.setMaximumHeight(100)
        layout.addWidget(sampleView)
        sampleView.setModel(sampleModel)
        sampleView.setEditTriggers(sampleView.NoEditTriggers)
        sampleView.horizontalHeader().setVisible(False)
        sampleView.verticalHeader().setVisible(False)
        if isinstance(fileList[0], str):
            for filePath in fileList:
                fileItem = QtGui.QStandardItem(QtCore.QFile(filePath).fileName())
                filePathItem = QtGui.QStandardItem(filePath)
                sampleModel.appendRow([fileItem, filePathItem])
        else:
            for index in fileList:
                fileItem = QtGui.QStandardItem(index.data())
                filePathItem = QtGui.QStandardItem(index.data(FilePathRole))
                sampleModel.appendRow([fileItem, filePathItem])
        sampleView.resizeColumnsToContents()
        sampleView.resizeRowsToContents()
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.button(self.buttonBox.Ok).clicked.connect(self.accept)
        self.buttonBox.button(self.buttonBox.Cancel).clicked.connect(self.reject)
        layout.addWidget(self.buttonBox)


class TagsEditorDialog(QtWidgets.QDialog):
    def __init__(self, parent, tags, fileName=None, uncommon=False):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Edit tags')
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        if fileName:
            headerLbl = QtWidgets.QLabel('Edit tags for sample "{}".\nSeparate tags with commas.'.format(fileName))
        else:
            text = 'Edit tags for selected samples.'
            if uncommon:
                text += '\nTags for selected samples do not match, be careful!'
            text += '\nSeparate tags with commas.'
            headerLbl = QtWidgets.QLabel(text)
        layout.addWidget(headerLbl)
        self.tagsEditor = TagsEditorTextEdit()
        self.tagsEditor.setTags(tags)
#        self.tagsEditor.setReadOnly(False)
        layout.addWidget(self.tagsEditor)
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.button(self.buttonBox.Ok).clicked.connect(self.accept)
        self.buttonBox.button(self.buttonBox.Cancel).clicked.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if res:
            return self.tagsEditor.tags()
        else:
            return res


