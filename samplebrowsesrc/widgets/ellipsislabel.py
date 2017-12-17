from PyQt5 import QtCore, QtWidgets

class EllipsisLabel(QtWidgets.QLabel):
    def __init__(self, *args, **kwargs):
        QtWidgets.QLabel.__init__(self, *args, **kwargs)
        self._text = self.text()

    def minimumSizeHint(self):
        default = QtWidgets.QLabel.minimumSizeHint(self)
        return QtCore.QSize(10, default.height())

    def setText(self, text):
        self.setToolTip(text)
        self._text = text
        QtWidgets.QLabel.setText(self, self.fontMetrics().elidedText(self._text, QtCore.Qt.ElideMiddle, self.width()))

    def resizeEvent(self, event):
        QtWidgets.QLabel.setText(self, self.fontMetrics().elidedText(self._text, QtCore.Qt.ElideMiddle, self.width()))
