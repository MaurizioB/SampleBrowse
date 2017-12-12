from PyQt5 import QtCore
import soundfile

availableFormats = tuple(f.lower() for f in soundfile.available_formats().keys())
availableExtensions = tuple('*.' + f for f in availableFormats)

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

fileNameColumn, dirColumn, lengthColumn, formatColumn, rateColumn, channelsColumn, subtypeColumn, tagsColumn, previewColumn = range(9)
allColumns = fileNameColumn, dirColumn, lengthColumn, formatColumn, rateColumn, channelsColumn, subtypeColumn, tagsColumn, previewColumn
_visibleColumns = fileNameColumn, lengthColumn, formatColumn, rateColumn, channelsColumn, subtypeColumn
_commonColumns = {c: True if c in _visibleColumns else False for c in allColumns}
browseColumns = _commonColumns.copy()
dbColumns = _commonColumns.copy()
dbColumns.update({
    dirColumn: True, 
    tagsColumn: True, 
#    previewColumn: True;
    })
sampleViewColumns = browseColumns, dbColumns

ValidRole = QtCore.Qt.UserRole + 1
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


