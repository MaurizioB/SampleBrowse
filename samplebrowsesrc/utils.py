from PyQt5 import QtWidgets

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
