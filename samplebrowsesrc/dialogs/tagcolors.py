from PyQt5 import QtCore, QtGui, QtWidgets
from samplebrowsesrc.widgets.colorlineedit import ColorLineEdit

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


