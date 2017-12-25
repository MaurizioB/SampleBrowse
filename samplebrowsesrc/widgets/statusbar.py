from queue import Queue
from PyQt5 import QtCore, QtWidgets

from samplebrowsesrc.constants import *

class StatusBar(QtWidgets.QStatusBar):
    fullTimer = 5000
    nextTimer = 2000
    def __init__(self, *args, **kwargs):
        QtWidgets.QStatusBar.__init__(self, *args, **kwargs)
        self.label = QtWidgets.QLabel()
        self.addPermanentWidget(self.label)
        self.messageQueue = Queue()
        self.messageTimer = QtCore.QTimer()
        self.messageTimer.setInterval(self.fullTimer)
        self.messageTimer.setSingleShot(True)
        self.messageTimer.timeout.connect(self.processMessages)
        self.hoverWidgets = {}

    def addHoverWidget(self, widget):
        try:
            widget.hoverMessage.connect(self.setHoverMessage)
        except:
            pass
        while True:
            try:
                for child in widget.hoverWidgets:
                    self.addHoverWidget(child)
                break
            except:
                break

    def setHoverMessage(self, message):
        if message:
            self.showMessage(message)
        else:
            self.clearMessage()

    def processMessages(self):
        if self.messageQueue.empty():
            self.label.setText('')
            return
        msgType, args = self.messageQueue.get()
        self.label.setText(StatusDict[msgType](*args))
        if self.messageQueue.empty():
            self.messageTimer.setInterval(self.fullTimer)
        else:
            self.messageTimer.setInterval(self.nextTimer)
        self.messageTimer.start()

    def addMessage(self, msgType, *args):
        self.messageQueue.put((msgType, args))
        if self.messageQueue.qsize() == 1 and not self.messageTimer.isActive():
            self.processMessages()
        else:
            self.messageTimer.setInterval(self.nextTimer)
            self.messageTimer.start()
