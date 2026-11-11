"""Shared dark palette; all artwork is bundled and drawn locally."""
STYLE = '''
QWidget { color: #c6d5e3; font-family: 'Segoe UI', 'DejaVu Sans'; font-size: 12px; }
QMainWindow, QDialog { background: #080f19; }
QWidget#Workspace, QWidget#Deck { background: #080f19; }
QWidget#DeviceCard { background: #101c2b; border-bottom: 1px solid #294055; }
QLabel#DeviceTitle { color: #ecf5ff; font-size: 14px; font-weight: 600; }
QFrame#Rail { background: #0b1522; border-right: 1px solid #1b2b3c; }
QFrame#Panel, QFrame#Metric { background: #101c2b; border: 1px solid #233346; border-radius: 12px; }
QFrame#Hero { background: qlineargradient(x1:0,y1:1,x2:1,y2:0,stop:0 #101f30,stop:0.6 #102538,stop:1 #132e3c); border: 1px solid #284656; border-radius: 14px; }
QFrame#Leader { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #24213c,stop:1 #171d30); border: 1px solid #635586; border-radius: 12px; }
QLabel { background: transparent; border: none; }
QLabel#Heading { font-size: 12px; font-weight: 600; color: #e0eaf3; padding-bottom: 4px; }
QLabel#Eyebrow { color: #75d7e5; font-size: 10px; font-weight: 600; }
QLabel#HeroTitle { color: #f0f6fb; font-size: 33px; font-weight: 700; }
QLabel#HeroStatus { color: #62d8b5; font-size: 9px; font-weight: 600; }
QLabel#Muted { color: #8da2b6; font-size: 11px; }
QLabel#Micro { color: #839aaf; font-size: 9px; font-weight: 600; }
QLabel#MetricValue { color: #eaf6ff; font-size: 28px; font-weight: 600; }
QLabel#Brand { color: #e9f4ff; font-size: 18px; font-weight: 700; }
QLabel#BrandMark { color: #69e5ee; font-size: 28px; font-weight: 800; }
QLabel#PageTitle { font-size: 22px; font-weight: 600; color: #ecf4ff; }
QLabel#SplashTitle { font-size: 24px; font-weight: 600; color: #eaf6ff; }
QLabel#Badge { color: #e8c682; background: #2e291f; border: 1px solid #655231; border-radius: 5px; padding: 6px 10px; font-size: 9px; font-weight: 600; }
QPushButton { background: #192c3f; border: 1px solid #304a60; border-radius: 6px; padding: 8px 11px; color: #d4e3ef; font-weight: 500; }
QPushButton:hover { background: #244354; border-color: #62e5f5; color: #e9fbff; }
QPushButton:pressed { background: #14313e; }
QPushButton:focus { border-color: #62e5f5; }
QPushButton:disabled { color: #627387; background: #172132; border-color: #2d364a; }
QPushButton#Primary { color: #061a22; background: #65dfed; border-color: #65dfed; font-weight: 600; }
QPushButton#Primary:hover { background: #96edf5; }
QPushButton#LeaderButton { color: #e3d8ff; background: #393052; border-color: #665485; }
QPushButton#LeaderButton:hover { background: #504069; border-color: #beabf5; }
QPushButton#LeaderButton:disabled { color: #827993; background: #29253c; border-color: #49405b; }
QPushButton#Danger { background: #31202d; border-color: #63384a; color: #f4a7ba; }
QPushButton#Danger:hover { background: #512938; border-color: #ef8fa6; }
QPushButton#Nav { text-align: left; border: none; background: transparent; color: #8299b0; padding: 12px; }
QPushButton#Nav:checked { color: #71e0ea; background: #16303d; border-left: 2px solid #62e5f5; }
QPushButton#Nav:hover { background: #142536; color: #d7e8f7; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #0b1522; color: #c8dbe9; border: 1px solid #2b4156; padding: 7px; border-radius: 5px; selection-background-color: #285c70; }
QComboBox QAbstractItemView { background: #102030; color: #d9e8f6; selection-background-color: #285c70; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #64dce9; }
QPlainTextEdit, QListWidget { background: #09121e; color: #8ac9c1; border: 1px solid #1f3346; border-radius: 6px; font-family: 'Consolas', 'DejaVu Sans Mono', monospace; font-size: 11px; padding: 7px; selection-background-color: #274f64; }
QListWidget::item { padding: 5px; }
QListWidget::item:selected { background: #204052; color: #d2f9ff; }
QTableWidget { background: #101c2b; alternate-background-color: #132131; gridline-color: #203244; border: none; selection-background-color: #24485a; }
QTableWidget::item { padding: 6px; border-bottom: 1px solid #213244; }
QHeaderView { background: #142333; }
QHeaderView::section { background: #142333; padding: 9px 5px; border: none; color: #7f9aaf; font-size: 10px; font-weight: 600; }
QCheckBox { color: #91a7ba; spacing: 7px; font-size: 11px; }
QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #3b5368; background: #0c1724; }
QCheckBox::indicator:checked { background: #62d7e4; border-color: #96ecf3; image: url(assets/check.svg); }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { width: 7px; background: #0b1522; margin: 0px; }
QScrollBar::handle:vertical { background: #30475c; min-height: 24px; border-radius: 3px; }
QScrollBar:horizontal { height: 7px; background: #0b1522; }
QScrollBar::handle:horizontal { background: #30475c; min-width: 24px; border-radius: 3px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0px; height: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QSplitter::handle { background: #080f19; height: 10px; width: 10px; }
QToolTip { background: #203348; color: #e3eff8; border: 1px solid #466078; padding: 5px; }
'''
