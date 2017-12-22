import sys
import os
from PyQt5 import QtGui, QtWidgets, uic
from samplebrowsesrc import utils
from samplebrowsesrc.info import __version__, __author__, __description__, __codeurl__

class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi('{}/about.ui'.format(os.path.dirname(utils.__file__)), self)
        self.iconLbl.setPixmap(QtGui.QIcon(':/icons/TangoCustom/64x64/samplebrowse.png').pixmap(64))
        self.descriptionLbl.setText(__description__)
        self.versionEntry.setText(__version__)
        self.authorEntry.setText(__author__)
        self.websiteEntry.setText('<a href="{}">Project on GitHub</a>'.format(__codeurl__))

        self.aboutQtBtn.setIcon(QtGui.QIcon(':/qt-project.org/qmessagebox/images/qtlogo-64.png'))
        self.aboutQtBtn.clicked.connect(lambda: QtWidgets.QMessageBox.aboutQt(self))

        baseHtml = '''
            SampleBrowse wouldn't have been possible without the following libraries and people...
            <h3>libsndfile</h3>
            Written by Erik de Castro Lopo: <a href="http://www.mega-nerd.com/libsndfile/">mega-nerd.com</a><br/>
            Python module written by <a href="http://www.mega-nerd.com/">Alex Roebel</a>:
                <a href="https://pypi.python.org/pypi/pysndfile">pysndfile</a>
            
            <h3><u>S</u>ecret <u>R</u>abbit <u>C</u>ode (aka libsamplerate)</h3>
            Written by Erik de Castro Lopo: <a href="http://www.mega-nerd.com/SRC/">mega-nerd.com</a><br/>
            Python module written by <a href="https://github.com/tuxu">Tino Wagner</a>: 
                <a href="https://pypi.python.org/pypi/samplerate">samplerate</a>
            
            {tango}
            
            <h3>Thanks to:</h3>
            Faber aka Fabio Vescarelli (<a href="http://www.faberbox.com/">faberbox.com</a>) for his great help in helping me
            to understand the secrets of Python... and his patience ;-)
            '''
        tangoHtml = '''
            <h3>Tango Icon Library</h3>
            This version of SampleBrowse uses icons from the <a href="http://tango.freedesktop.org/">Tango Desktop Project</a>
            '''
        self.aknTextBrowser.setHtml(baseHtml.format(tango=tangoHtml if 'linux' not in sys.platform else ''))
        self.shown = False

    #since there are some issues with QLabels in layouts, we set the minimum width
    def exec_(self):
        self.show()
        fontMetrics = QtGui.QFontMetrics(self.font())
        keySize = max([fontMetrics.width(w.text()) for w in (self.websiteLbl, self.authorLbl, self.versionLbl)])
        websiteDoc = QtGui.QTextDocument()
        websiteDoc.setHtml(self.websiteEntry.text())
        websiteDocSize = fontMetrics.width(websiteDoc.toPlainText())
        valueSize = max([fontMetrics.width(w.text()) for w in (self.authorEntry, self.versionEntry)] + [websiteDocSize])
        self.aboutTab.setMinimumWidth(
            self.iconLbl.minimumWidth() + 
            max((keySize + valueSize, fontMetrics.width(self.descriptionLbl.text()))) +
            self.aboutTab.layout().horizontalSpacing() + 
            self.aboutTab.layout().contentsMargins().left() + self.aboutTab.layout().contentsMargins().right() 
            )


