# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'config_editor.ui'
#
# Created by: PyQt5 UI code generator 5.14.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_config_dialog(object):
    def setupUi(self, config_dialog):
        config_dialog.setObjectName("config_dialog")
        config_dialog.setStyleSheet('/* Technic / Midnight Command. Qt 5 QSS, no assets or behavioural properties.\n   Light data surfaces deliberately retain dark text: model status brushes include\n   saturated yellow, green, cyan, white and red. Never override item backgrounds. */\nQMainWindow, QDialog {\n    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,\n        stop:0 #152237, stop:0.5 #0e192a, stop:1 #0a1321);\n}\nQWidget {\n    font-family: "Segoe UI", "Tahoma", sans-serif;\n    font-size: 12px;\n    color: #dbe6f3;\n}\nQWidget#centralwidget { background: transparent; }\nQLabel, QCheckBox { background: transparent; }\nQLabel { color: #9fb3ca; }\nQPushButton {\n    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,\n        stop:0 #263950, stop:1 #1b2b40);\n    color: #dce8f5;\n    border: 1px solid #3a506b;\n    border-top-color: #4c6380;\n    border-radius: 6px;\n    padding: 5px 12px;\n    font-weight: 600;\n}\nQPushButton:hover {\n    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,\n        stop:0 #304b66, stop:1 #233c55);\n    border-color: #4d9baa; color: #ffffff;\n}\nQPushButton:pressed { background: #13273c; border-color: #54d7df; }\nQPushButton:focus { border-color: #75e6ef; }\nQPushButton:default { border-color: #61d7e2; }\n/* Filled primary: preparation check. */\nQPushButton#check_button {\n    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,\n        stop:0 #188b9f, stop:1 #126276);\n    color: #ffffff; border-color: #36a9b8; border-top-color: #66c9d3;\n}\nQPushButton#check_button:hover { background: #1b94a5; border-color: #85e3e8; }\nQPushButton#check_button:pressed { background: #105265; }\n/* Flight actions: muted emerald, not an indication of readiness. */\nQPushButton#start_button, QPushButton#takeoff_button {\n    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,\n        stop:0 #226756, stop:1 #184b42);\n    color: #defbf0; border-color: #378a73; border-top-color: #56a88e;\n}\nQPushButton#start_button:hover, QPushButton#takeoff_button:hover {\n    background: #287e66; border-color: #74cfaa;\n}\nQPushButton#start_button:pressed, QPushButton#takeoff_button:pressed { background: #133f36; }\nQPushButton#pause_button, QPushButton#flip_button {\n    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,\n        stop:0 #493c26, stop:1 #332e24);\n    color: #f3d59c; border-color: #7a653f; border-top-color: #9a7d4d;\n}\nQPushButton#pause_button:hover, QPushButton#flip_button:hover {\n    background: #59482b; border-color: #c3a164;\n}\nQPushButton#pause_button:pressed, QPushButton#flip_button:pressed { background: #2c261e; }\nQPushButton#land_selected_button { color: #b7deec; border-color: #4a7187; }\nQPushButton#land_all_button, QPushButton#disarm_all_button,\nQPushButton#disarm_selected_button {\n    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,\n        stop:0 #442c3a, stop:1 #302333);\n    color: #f3b6c1; border-color: #7c485c; border-top-color: #9b5b6e;\n}\nQPushButton#land_all_button:hover, QPushButton#disarm_all_button:hover,\nQPushButton#disarm_selected_button:hover { background: #593244; border-color: #c47b8e; }\nQPushButton#land_all_button:pressed, QPushButton#disarm_all_button:pressed,\nQPushButton#disarm_selected_button:pressed { background: #291b25; }\n/* Emergency remains distinct. Command scope and confirmation logic unchanged. */\nQPushButton#emergency_land_button {\n    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,\n        stop:0 #c23b50, stop:1 #94263d);\n    color: #ffffff; border-color: #e06a7b; border-top-color: #f18b96;\n    font-weight: 700;\n}\nQPushButton#emergency_land_button:hover { background: #d1475c; border-color: #ffb0bb; }\nQPushButton#emergency_land_button:pressed { background: #782236; }\n/* ID specificity is required so disabled operational buttons stay subdued. */\nQPushButton:disabled, QPushButton#check_button:disabled,\nQPushButton#start_button:disabled, QPushButton#takeoff_button:disabled,\nQPushButton#pause_button:disabled, QPushButton#flip_button:disabled,\nQPushButton#land_selected_button:disabled, QPushButton#land_all_button:disabled,\nQPushButton#disarm_all_button:disabled, QPushButton#disarm_selected_button:disabled,\nQPushButton#emergency_land_button:disabled {\n    background: #182337; color: #65778d;\n    border-color: #2b3b50; border-top-color: #2b3b50;\n}\nQLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {\n    background: #0c1727; color: #e4eef9;\n    border: 1px solid #3a526c; border-radius: 5px;\n    padding: 4px; selection-background-color: #236d87; selection-color: #ffffff;\n}\nQLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #54d1dc; }\nQLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {\n    background: #172132; color: #65778d; border-color: #2b3b50;\n}\nQComboBox QAbstractItemView {\n    background: #1a2b41; color: #e4eef9; border: 1px solid #44617d;\n    selection-background-color: #25506c; selection-color: #ffffff;\n}\nQCheckBox { spacing: 5px; color: #b8c9dc; }\nQCheckBox:disabled { color: #65778d; }\n/* Do not style ::item backgrounds/hover: retain original diagnostic brushes.\n   This also reaches the CopterTableWidget created at runtime. */\nQTableView, QTreeView, QListView {\n    background: #edf2f7; alternate-background-color: #e6edf5; color: #17283b;\n    border: 1px solid #3c617c; border-top: 2px solid #36acbb;\n    border-radius: 5px; gridline-color: #c6d2e0;\n    selection-background-color: #b8dce9; selection-color: #102d43;\n}\nQTableView QLineEdit, QTreeView QLineEdit {\n    background: #ffffff; color: #17283b; border-color: #2492a5;\n    selection-background-color: #b8dce9; selection-color: #102d43;\n}\nQHeaderView { background: #182c43; }\nQHeaderView::section {\n    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,\n        stop:0 #233d56, stop:1 #172c43);\n    color: #d9edf7; font-weight: 600;\n    padding: 6px 5px; border: none;\n    border-right: 1px solid #35516c; border-bottom: 1px solid #3d778b;\n}\nQHeaderView::section:hover { background: #2b506a; color: #ffffff; }\nQTableCornerButton::section { background: #1b324b; border: 1px solid #35516c; }\nQMenuBar {\n    background: #0a1423; color: #b9cde3;\n    border-bottom: 1px solid #2f566c; padding: 3px;\n}\nQMenuBar::item { background: transparent; padding: 6px 12px; border-radius: 4px; }\nQMenuBar::item:selected { background: #203d55; color: #8aebf0; }\nQMenuBar::item:pressed { background: #2b526b; color: #ffffff; }\nQMenu {\n    background: #17283d; color: #dbe6f3;\n    border: 1px solid #44617d; padding: 4px;\n}\nQMenu::item { padding: 6px 24px; border-radius: 3px; }\nQMenu::item:selected { background: #28516a; color: #ffffff; }\nQMenu::item:disabled { color: #65778d; }\nQMenu::separator { height: 1px; background: #354c65; margin: 5px 8px; }\nQStatusBar { background: #0a1423; color: #9fb7cf; border-top: 1px solid #2b455e; }\nQStatusBar::item { border: none; }\nQStatusBar QLabel { color: #a7c0d8; }\nQFrame[frameShape="4"], QFrame[frameShape="5"] { color: #344b64; }\nQToolTip { background: #213951; color: #f0f7ff; border: 1px solid #54869b; padding: 6px; }\n')
        config_dialog.resize(600, 700)
        config_dialog.setModal(False)
        self.gridLayout = QtWidgets.QGridLayout(config_dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.config_view = QtWidgets.QTreeView(config_dialog)
        self.config_view.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked|QtWidgets.QAbstractItemView.EditKeyPressed|QtWidgets.QAbstractItemView.SelectedClicked)
        self.config_view.setObjectName("config_view")
        self.config_view.header().setCascadingSectionResizes(False)
        self.config_view.header().setDefaultSectionSize(250)
        self.gridLayout.addWidget(self.config_view, 0, 0, 1, 1)
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem, 0, 2, 1, 1)
        self.do_restart = QtWidgets.QCheckBox(config_dialog)
        self.do_restart.setObjectName("do_restart")
        self.gridLayout_2.addWidget(self.do_restart, 0, 1, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(config_dialog)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout_2.addWidget(self.buttonBox, 0, 4, 1, 1)
        self.do_coloring = QtWidgets.QCheckBox(config_dialog)
        self.do_coloring.setChecked(True)
        self.do_coloring.setObjectName("do_coloring")
        self.gridLayout_2.addWidget(self.do_coloring, 0, 0, 1, 1)
        self.save_as_button = QtWidgets.QPushButton(config_dialog)
        self.save_as_button.setObjectName("save_as_button")
        self.gridLayout_2.addWidget(self.save_as_button, 0, 3, 1, 1)
        self.gridLayout.addLayout(self.gridLayout_2, 2, 0, 1, 1)
        self.line = QtWidgets.QFrame(config_dialog)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.gridLayout.addWidget(self.line, 1, 0, 1, 1)

        self.retranslateUi(config_dialog)
        self.buttonBox.accepted.connect(config_dialog.accept)
        self.buttonBox.rejected.connect(config_dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(config_dialog)

    def retranslateUi(self, config_dialog):
        _translate = QtCore.QCoreApplication.translate
        config_dialog.setWindowTitle(_translate("config_dialog", "Config Editor"))
        self.do_restart.setText(_translate("config_dialog", "Restart"))
        self.do_restart.setShortcut(_translate("config_dialog", "R"))
        self.do_coloring.setText(_translate("config_dialog", "Color Indication"))
        self.save_as_button.setText(_translate("config_dialog", "Save as"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    config_dialog = QtWidgets.QDialog()
    ui = Ui_config_dialog()
    ui.setupUi(config_dialog)
    config_dialog.show()
    sys.exit(app.exec_())
