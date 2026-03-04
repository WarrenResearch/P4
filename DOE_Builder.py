import doepy







class DoE_builder (qt.QWidget):
    def __init__(self, parent=None, main=None):
        super(DoE_builder, self).__init__(parent)
        self.main = main
        self.initUI()

    def initUI(self):
        self.layout = QtWidgets.QGridLayout(self)
        self.setLayout(self.layout)

        # Create the DoE design
        design = pyDOE2.ccdesign(3)

