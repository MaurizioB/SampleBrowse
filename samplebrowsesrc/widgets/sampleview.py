import soundfile
from PyQt5 import QtCore, QtGui, QtWidgets

from samplebrowsesrc.utils import HoverDecorator, sizeStr
from samplebrowsesrc.constants import *

@HoverDecorator
class SampleView(QtWidgets.QTableView):
    fileReadable = QtCore.pyqtSignal(object, bool)

    def viewportEvent(self, event):
        if event.type() == QtCore.QEvent.ToolTip:
            index = self.indexAt(event.pos())
            if index.isValid():
                fileIndex = index.sibling(index.row(), 0)
                fileName = fileIndex.data()
                filePath = fileIndex.data(FilePathRole)
                dirIndex = index.sibling(index.row(), dirColumn)
                dir = dirIndex.data() if dirIndex.data() else '?'
                info = fileIndex.data(InfoRole)
                tags = index.sibling(index.row(), tagsColumn).data(TagsRole)
                if tags:
                    tagsText = '''
                        <h4 style="margin-bottom: 0px;">Tags</h4>
                        <ul style="margin-top: 0px; margin-bottom: 0px; margin-left: 0px; margin-right: 0px; -qt-list-indent: 0;">
                            <li style="margin-left:16px; -qt-block-indent:0; text-indent:0px;">
                            {}
                            </li>
                        </ul>
                        '''.format('</li><li style="margin-left:16px; -qt-block-indent:0; text-indent:0px;">'.join(tags))
                else:
                    tagsText = ''
                try:
                    if not info:
                        info = soundfile.info(filePath)
                    self.fileReadable.emit(fileIndex, True)
                    size = QtCore.QFileInfo(filePath).size()
                    self.setToolTip('''
                        <h3>{fileName}</h3>
                        <table>
                            <tr>
                                <td>Size:</td>
                                <td>{size}{sizeFull}</td>
                            </tr>
                            <tr>
                                <td>Path:</td>
                                <td>{dir}</td>
                            </tr>
                            <tr>
                                <td>Length:</td>
                                <td>{length:.03f}</td>
                            </tr>
                            <tr>
                                <td>Format:</td>
                                <td>{format} ({subtype})</td>
                            </tr>
                            <tr>
                                <td>Sample rate:</td>
                                <td>{sampleRate}</td>
                            </tr>
                            <tr>
                                <td>Channels:</td>
                                <td>{channels}</td>
                            </tr>
                        </table>
                        {tags}
                        '''.format(
                            fileName=fileName, 
                            size=sizeStr(size), 
                            sizeFull=' ({}B)'.format(size) if size > 1024 else '', 
                            dir=dir, 
                            length=float(info.frames) / info.samplerate, 
                            format=info.format, 
                            sampleRate=info.samplerate, 
                            channels=info.channels, 
                            subtype=subtypesDict.get(info.subtype, info.subtype), 
                            tags=tagsText, 
                            )
                        )
                except:
                    self.setToolTip('<h3>{}</h3>(file not available or unreadable)'.format(fileName))
                    self.fileReadable.emit(fileIndex, False)
            else:
                self.setToolTip('')
                QtWidgets.QToolTip.showText(event.pos(), '')
        return QtWidgets.QTableView.viewportEvent(self, event)

    def startDrag(self, actions):
        drag = QtGui.QDrag(self)
        mimeData = QtCore.QMimeData()
        bytearray = QtCore.QByteArray()
        stream = QtCore.QDataStream(bytearray, QtCore.QIODevice.WriteOnly)
        fileList = []
        for fileIndex in self.selectionModel().selectedRows():
            filePath = fileIndex.data(FilePathRole)
            fileList.append(filePath)
            stream.writeInt32(fileIndex.row())
            stream.writeInt32(fileIndex.column())
            #field number, might want to implement other roles too
            stream.writeInt32(1)
            #key
            stream.writeInt32(FilePathRole)
            #value
            stream.writeQVariant(filePath)
        mimeData.setData('application/x-qabstractitemmodeldatalist', bytearray)
        mimeData.setUrls([QtCore.QUrl.fromLocalFile(filePath) for filePath in fileList])
        drag.setMimeData(mimeData)
        drag.setPixmap(self.createDragPixmap(fileList))
        drag.setHotSpot(QtCore.QPoint(32, 10))
#        drag.exec_(actions, QtCore.Qt.CopyAction)
        drag.exec_(QtCore.Qt.CopyAction)


    def createDragPixmap(self, fileList):
        fontMetrics = QtGui.QFontMetrics(self.font())
        fontHeight = fontMetrics.height()
        if len(fileList) == 1:
            filePath = fileList[0]
            pixmap = QtGui.QPixmap(128, 38 + fontHeight)
            pixmap.fill(QtCore.Qt.transparent)
            qp = QtGui.QPainter(pixmap)
            qp.setRenderHints(qp.Antialiasing)
            qp.drawPixmap(48, 0, QtGui.QIcon(':/icons/TangoCustom/32x32/samplebrowse.png').pixmap(32))
            qp.setPen(QtCore.Qt.lightGray)
            qp.drawRoundedRect(48, 0, 32, 32, 8, 8)
            qp.setPen(QtCore.Qt.darkGray)
            qp.setBrush(QtCore.Qt.lightGray)
            qp.drawRoundedRect(0, 38, 128, fontHeight, 4, 4)
            qp.setPen(QtCore.Qt.black)
            qp.drawText(0, 38, 128, fontHeight, QtCore.Qt.AlignCenter, fontMetrics.elidedText(filePath, QtCore.Qt.ElideLeft, 128))
            del qp
            return pixmap
        pixmap = QtGui.QPixmap(128, 38 + fontHeight * 5)
        pixmap.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(pixmap)
        qp.setRenderHints(qp.Antialiasing)
        qp.drawPixmap(48, 0, QtGui.QIcon(':/icons/TangoCustom/32x32/samplebrowse.png').pixmap(32))
        qp.setPen(QtCore.Qt.lightGray)
        qp.drawRoundedRect(48, 0, 32, 32, 8, 8)
        qp.setPen(QtCore.Qt.darkGray)
        qp.setBrush(QtCore.Qt.lightGray)
        listLength = len(fileList)
        qp.drawRoundedRect(0, 38, 128, fontHeight * listLength if listLength <= 5 else fontHeight * 5, 4, 4)
        qp.setPen(QtCore.Qt.black)
        qp.translate(0, 38)
        for filePath in fileList[:4]:
            qp.drawText(0, 0, 128, fontHeight, QtCore.Qt.AlignLeft, fontMetrics.elidedText(filePath, QtCore.Qt.ElideLeft, 128))
            qp.translate(0, fontHeight)
        if listLength == 5:
            qp.drawText(0, 0, 128, fontHeight, QtCore.Qt.AlignLeft, fontMetrics.elidedText(fileList[4], QtCore.Qt.ElideLeft, 128))
        elif listLength > 5:
            qp.drawText(0, 0, 128, fontHeight, QtCore.Qt.AlignLeft, 'and {} more files...'.format(listLength - 4))
        del qp
        return pixmap
