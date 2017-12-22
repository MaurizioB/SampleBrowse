from PyQt5 import QtWidgets
from samplebrowsesrc.widgets import TagsEditorTextEdit

class TagsEditorDialog(QtWidgets.QDialog):
    def __init__(self, parent, tags, fileName=None, uncommon=False):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle('Edit tags')
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        if fileName:
            headerLbl = QtWidgets.QLabel('Edit tags for sample "{}".\nSeparate tags with commas.'.format(fileName))
        else:
            text = 'Edit tags for selected samples.'
            if uncommon:
                text += '\nTags for selected samples do not match, be careful!'
            text += '\nSeparate tags with commas.'
            headerLbl = QtWidgets.QLabel(text)
        layout.addWidget(headerLbl)
        self.tagsEditor = TagsEditorTextEdit()
        self.tagsEditor.setTags(tags)
#        self.tagsEditor.setReadOnly(False)
        layout.addWidget(self.tagsEditor)
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.button(self.buttonBox.Ok).clicked.connect(self.accept)
        self.buttonBox.button(self.buttonBox.Cancel).clicked.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def exec_(self):
        res = QtWidgets.QDialog.exec_(self)
        if res:
            return self.tagsEditor.tags()
        else:
            return res
