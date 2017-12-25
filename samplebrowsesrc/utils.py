from PyQt5 import QtCore, QtWidgets

def sizeStr(size):
    if size < 1024:
        return '{}B'.format(size)
    if size < 1048576:
        return '{:.0f}KB'.format(size/1024)
    if size < 1073741824:
        return '{:.0f}MB'.format(size/1048576)
    return '{:.0f}GB'.format(size/1073741824)

def secondsLeading(seconds, leading=0, trailing=3, trailingAlways=False):
    fmt = '{{:0{}.{}f}}'.format(leading + trailing + 1, trailing)
    return fmt.format(seconds) if trailingAlways else fmt.format(seconds).rstrip('0').rstrip('.')

def timeStr(seconds, leading=0, trailing=3, trailingAlways=False, multiple=True, leadingMultiple=False, full=False):
    if not multiple:
        return secondsLeading(seconds, leading, trailing, trailingAlways)
    mins, secs = divmod(seconds, 60)
    if mins < 60 and not full:
        text = '{:02.0f}:{}'.format(mins, secondsLeading(secs, leading, trailing, trailingAlways))
        return text if leadingMultiple else text.lstrip('0').lstrip('.:')
    hours, mins = divmod(mins, 60)
    text = '{:01.0f}:{:02.0f}:{}'.format(hours, mins, secondsLeading(secs, leading, trailing, trailingAlways))
    return text if leadingMultiple or full else text.lstrip('0').lstrip('.:')

def setBold(item, bold=True):
    try:
        font = item.font()
        font.setBold(bold)
        item.setFont(font)
    except:
        try:
            font = item.data(QtCore.Qt.FontRole)
            font.setBold(bold)
            item.model().setData(item, font, QtCore.Qt.FontRole)
        except:
            try:
                model = item.model()
                setBold(model.itemFromIndex(item), bold)
            except:
                setBold(model.sourceModel().itemFromIndex(model.mapToSource(item)), bold)

def setItalic(item, italic=True):
    try:
        font = item.font()
        font.setItalic(italic)
        item.setFont(font)
    except:
        try:
            font = item.data(QtCore.Qt.FontRole)
            font.setItalic(italic)
            item.model().setData(item, font, QtCore.Qt.FontRole)
        except:
            try:
                model = item.model()
                setItalic(model.itemFromIndex(item), italic)
            except:
                setItalic(model.sourceModel().itemFromIndex(model.mapToSource(item)), italic)

def menuSeparator(parent):
    sep = QtWidgets.QAction(parent)
    sep.setSeparator(True)
    return sep

def HoverDecorator(QtClass):
    '''
    Special QWidget decorator for mouse over "tooltip" in statusbar
    '''

    class HoverWidget(QtClass):
        hoverMessage = QtCore.pyqtSignal(str)

        def __init__(self, hoverText=None, *args, **kwargs):
            self.hoverText = hoverText
            QtClass.__init__(self, *args, **kwargs)

        def setHoverText(self, text):
            self.hoverText = text

        def enterEvent(self, event):
            if self.isEnabled():
                self.hoverMessage.emit(self.hoverText)
            QtClass.enterEvent(self, event)

        def leaveEvent(self, event):
            self.hoverMessage.emit('')
            QtClass.leaveEvent(self, event)

    return HoverWidget


