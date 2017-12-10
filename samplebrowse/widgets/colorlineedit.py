from PyQt5 import QtCore, QtWidgets

class ColorLineEdit(QtWidgets.QLineEdit):
    editBtnClicked = QtCore.pyqtSignal()
    def __init__(self, *args, **kwargs):
        QtWidgets.QLineEdit.__init__(self, *args, **kwargs)
        self.editBtn = QtWidgets.QPushButton('...', self)
        self.editBtn.setCursor(QtCore.Qt.ArrowCursor)
        self.editBtn.clicked.connect(self.editBtnClicked.emit)

    def resizeEvent(self, event):
        size = self.height() - 8
        self.editBtn.resize(size, size)
        self.editBtn.move(self.width() - size - 4, (self.height() - size) / 2)

