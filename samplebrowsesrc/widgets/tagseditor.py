import re
from PyQt5 import QtCore, QtWidgets

class TagsEditorTextEdit(QtWidgets.QTextEdit):
    tagsApplied = QtCore.pyqtSignal(object)
    def __init__(self, *args, **kwargs):
        QtWidgets.QTextEdit.__init__(self, *args, **kwargs)
        self.document().setDefaultStyleSheet('''
            span {
                background-color: rgba(200,200,200,150);
            }
            span.sep {
                color: transparent;
                background-color: transparent;
                }
            ''')
        self.textChanged.connect(self.checkText)
        self.applyBtn = QtWidgets.QToolButton(self)
        self.applyBtn.setText('Apply')
        self.applyBtn.setVisible(False)
        self.applyBtn.clicked.connect(self.applyTags)
        self._applyMode = False
        self._tagList = ''
        self.viewport().setCursor(QtCore.Qt.IBeamCursor)

    @QtCore.pyqtProperty(bool)
    def applyMode(self):
        return self._applyMode

    @applyMode.setter
    def applyMode(self, mode):
        self._applyMode = mode

    @QtCore.pyqtSlot(bool)
    def setApplyMode(self, mode):
        self.applyMode = mode

    def keyPressEvent(self, event):
        if not self.applyMode:
            if event.key() == QtCore.Qt.Key_Tab:
                event.ignore()
                return
            return QtWidgets.QTextEdit.keyPressEvent(self, event)
        else:
            if event.key() == QtCore.Qt.Key_Escape:
                self.textChanged.disconnect(self.checkText)
                self._setTags(self._tagList)
                cursor = self.textCursor()
                cursor.movePosition(cursor.End)
                self.setTextCursor(cursor)
                self.textChanged.connect(self.checkText)
            elif event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
                self.clearFocus()
                self.applyTags()
            else:
                return QtWidgets.QTextEdit.keyPressEvent(self, event)

    def applyTags(self):
        self.checkText()
        self._tagList = self.toPlainText()
        self.tagsApplied.emit(self.tags())

    def checkText(self):
        pos = self.textCursor().position()
        self.textChanged.disconnect(self.checkText)
        if pos == 1 and self.toPlainText().startswith(','):
            pos = 0
        self._setTags(re.sub(r'\/,', ',', re.sub(r'[\n\t]+', ',', self.toPlainText())))
        self.textChanged.connect(self.checkText)
        cursor = self.textCursor()
        if len(self.toPlainText()) < pos:
            pos = len(self.toPlainText())
        cursor.setPosition(pos)
        self.setTextCursor(cursor)

    def _setTags(self, tagList):
        tagList = re.sub(r'\,\,+', ',', tagList.lstrip(','))
        tags = []
        for tag in tagList.split(','):
            tags.append(tag.lstrip().lstrip('/').strip('\n'))
        QtWidgets.QTextEdit.setHtml(self, '<span>{}</span>'.format('</span><span class="sep">,</span><span>'.join(tags)))

    def setTags(self, tagList):
        self._tagList = [tag for tag in tagList if tag is not None]
        self._setTags(','.join(self._tagList))
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        self.setTextCursor(cursor)

    def tags(self):
        tags = re.sub(r'\,\,+', ',', self.toPlainText()).replace('\n', ',').strip(',').split(',')
        tags = set(tag.strip('/') for tag in tags if tag)
        return sorted(tags) if tags else []

    def enterEvent(self, event):
        if not self.applyMode:
            return
        self.applyBtn.setVisible(True)
        self.moveApplyBtn()

    def moveApplyBtn(self):
        self.applyBtn.setMaximumSize(self.applyBtn.fontMetrics().width('Apply') + 12, self.applyBtn.fontMetrics().height() + 2)
        self.applyBtn.move(self.width() - self.applyBtn.width() - 2, self.height() - self.applyBtn.height() - 2)

    def leaveEvent(self, event):
        self.applyBtn.setVisible(False)

    def resizeEvent(self, event):
        QtWidgets.QTextEdit.resizeEvent(self, event)
        self.moveApplyBtn()
