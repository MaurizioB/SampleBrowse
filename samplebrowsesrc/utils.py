from PyQt5 import QtWidgets

def setBold(item, bold=True):
    font = item.font()
    font.setBold(bold)
    item.setFont(font)

def setItalic(item, italic=True):
    font = item.font()
    font.setItalic(italic)
    item.setFont(font)

def menuSeparator(parent):
    sep = QtWidgets.QAction(parent)
    sep.setSeparator(True)
    return sep
