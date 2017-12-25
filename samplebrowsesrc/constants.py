from PyQt5 import QtCore
import soundfile

availableFormats = tuple(f.lower() for f in soundfile.available_formats().keys())
availableExtensionsDot = []
availableExtensionsWildcard = []
for f in availableFormats:
    availableExtensionsDot.append('.' + f)
    availableExtensionsWildcard.append('*.' + f)
availableExtensionsWildcard = tuple('*.' + f for f in availableFormats)
availableExtensionsDot = tuple('*.' + f for f in availableFormats)

sampleRatesList = (192000, 176400, 96000, 88200, 48000, 44100, 32000, 22050, 16000, 8000)

subtypesDict = {
    'FLOAT': '32f', 
    'DOUBLE': '64f', 
    'DPCM_16': '16', 
    'PCM_S8': 'S8', 
    'ALAC_24': '24', 
    'DWVW_12': '12', 
    'PCM_U8': 'U8', 
    'ALAC_32': '32', 
    'PCM_32': '32', 
    'ALAC_16': '16', 
    'ALAC_20': '20', 
    'DWVW_16': '16', 
    'DWVW_24': '24', 
    'DPCM_8': '8', 
    'PCM_16': '16', 
    'PCM_24': '24',
    }

channelsLabels = {
    1: 'Mono', 
    2: 'Stereo', 
    3: 'Stereo + Central/Rear', 
    4: 'Quad/Surround', 
    5: 'Surround + Center', 
    6: '5.1', 
    7: '3 Front + 3 Rear + Sub', 
    8: '7.1'
    }

dbFields = ['filePath', 'fileName', 'length', 'format', 'sampleRate', 'channels', 'subtype', 'tags', 'preview']
dbFieldsOld = ['filePath', 'fileName', 'length', 'format', 'sampleRate', 'channels', 'tags', 'preview']

fileNameColumn, dirColumn, lengthColumn, formatColumn, rateColumn, channelsColumn, subtypeColumn, tagsColumn, previewColumn = range(9)
allColumns = fileNameColumn, dirColumn, lengthColumn, formatColumn, rateColumn, channelsColumn, subtypeColumn, tagsColumn, previewColumn
_visibleColumns = fileNameColumn, lengthColumn, formatColumn, rateColumn, channelsColumn, subtypeColumn
_commonColumns = {c: True if c in _visibleColumns else False for c in allColumns}
browseColumns = _commonColumns.copy()
dbViewColumns = _commonColumns.copy()
dbViewColumns.update({
    dirColumn: True, 
    tagsColumn: True, 
#    previewColumn: True;
    })
sampleViewColumns = browseColumns, dbViewColumns

ValidRole = QtCore.Qt.UserRole + 1
DataRole = QtCore.Qt.UserRole + 1
DeviceRole = ValidRole + 1
SampleRateRole = DeviceRole + 1
SampleSizeRole = SampleRateRole + 1
ChannelsRole = SampleSizeRole + 1
FormatRole = ChannelsRole + 1
HoverRole = FormatRole + 1
DirNameRole = HoverRole + 1
FileNameRole = DirNameRole + 1
FilePathRole = FileNameRole + 1
InfoRole = FilePathRole + 1
WaveRole = InfoRole + 1
TagsRole = WaveRole + 1
PreviewRole = TagsRole + 1

StatusBackup, StatusSamplesAdded, StatusSamplesRemoved, StatusSamplesTagsEdited, \
    StatusTagRenamed, StatusTagChanged, StatusTagRemoved, StatusFavAdded, StatusFavRemoved = range(9)

StatusDict = {
    StatusBackup: lambda done: 'Backup completed.' if done else 'Backup failed!', 
    StatusSamplesAdded: lambda n: '{} sample{} added to database'.format(n, 's' if n>1 else ''), 
    StatusSamplesRemoved: lambda n: '{} sample{} removed from database'.format(n, 's' if n>1 else ''), 
    StatusSamplesTagsEdited: lambda n: 'Tags edited for {} sample{}'.format(n, 's' if n>1 else ''), 
    StatusTagRenamed: lambda new, old: 'Tag "{}" renamed to "{}"'.format(old, new), 
    StatusTagChanged: lambda tag: 'Tag "{}" changed'.format(tag), 
    StatusTagRemoved: lambda tag: 'Tag "{}" removed'.format(tag), 
    StatusFavAdded: lambda fav: 'Favourite "{}" created'.format(fav), 
    StatusFavRemoved: lambda fav: 'Favourite "{}" removed'.format(fav), 
    }
