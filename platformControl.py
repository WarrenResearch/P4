from PyQt5 import QtWidgets, QtCore
import pumpWidget as pw
import valveWidget as vw

### Class used to define all apparatus available for automated experiments ###

# All pumps and valves are controlled from other scripts by calling to the same instance of the PlatformControl class created in the GUI initialisation.

class PlatformControl(QtWidgets.QWidget):
    def __init__(self, parent, main):
        super(PlatformControl, self).__init__(parent)

        self.main = main
        self._layout = QtWidgets.QGridLayout()
        self.setLayout(self._layout)
        self.pumpsTuple = ("Teledyne", "MilliGAT LF", "MilliGAT HF", "Chemyx Nexus 4000", "Chemyx Fusion 6000X", "Chemyx Fusion 4000X", "Jasco PU2080")
        self.valvesTuple = ("BioChem 8way selection", "BioChem 6way selection", "BioChem 6way switching", "Rheodyne 2pos switching", "Vici 2pos switching")

        self.pumpsBox = QtWidgets.QGroupBox("Pumps")
        self.pumpsBox.setMaximumHeight(400)
        self.pumpsBox.setMaximumWidth(2000)
        self.pumpsLayout = QtWidgets.QGridLayout(self.pumpsBox)
        self._layout.addWidget(self.pumpsBox, 0, 0, QtCore.Qt.AlignTop)

        self.pump1 = pw.PumpControl(self, pumpName="Seed")
        self.pump1.setHidden(False)
        self.pump1.pumpModelCombo.setCurrentText(self.pumpsTuple[4])
        self.pump1.formatWidget(pump=self.pumpsTuple[4])
        self.pumpsLayout.addWidget(self.pump1, 0, 0, QtCore.Qt.AlignLeft)

        self.pump2 = pw.PumpControl(self, pumpName="Monomer 1")
        self.pump2.setHidden(False)
        self.pump2.pumpModelCombo.setCurrentText(self.pumpsTuple[0])
        self.pump2.formatWidget(pump=self.pumpsTuple[0])
        self.pumpsLayout.addWidget(self.pump2, 0, 1, QtCore.Qt.AlignLeft)

        self.pump3 = pw.PumpControl(self, pumpName="Monomer 2")
        self.pump3.setHidden(False)
        self.pump3.pumpModelCombo.setCurrentText(self.pumpsTuple[0])
        self.pump3.formatWidget(pump=self.pumpsTuple[0])
        self.pumpsLayout.addWidget(self.pump3, 0, 2, QtCore.Qt.AlignLeft)

        self.pump4 = pw.PumpControl(self, pumpName="Aqueous 1")
        self.pump4.setHidden(True)
        self.pump4.pumpModelCombo.setCurrentText(self.pumpsTuple[2])
        self.pump4.formatWidget(pump=self.pumpsTuple[2])
        self.pumpsLayout.addWidget(self.pump4, 0, 3, QtCore.Qt.AlignLeft)

        self.pump5 = pw.PumpControl(self, pumpName="Aqueous 2")
        self.pump5.setHidden(True)
        self.pump5.pumpModelCombo.setCurrentText(self.pumpsTuple[2])
        self.pump5.formatWidget(pump=self.pumpsTuple[2])
        self.pumpsLayout.addWidget(self.pump5, 0, 4, QtCore.Qt.AlignLeft)

        self.pump6 = pw.PumpControl(self, pumpName="Solvent")
        self.pump6.setHidden(True)
        self.pump6.pumpModelCombo.setCurrentText(self.pumpsTuple[0])
        self.pump6.formatWidget(pump=self.pumpsTuple[0])
        self.pumpsLayout.addWidget(self.pump6, 0, 13, QtCore.Qt.AlignLeft)

        self.pump7 = pw.PumpControl(self, pumpName="Org1")
        self.pump7.setHidden(True)
        self.pump7.pumpModelCombo.setCurrentText(self.pumpsTuple[2])
        self.pump7.formatWidget(pump=self.pumpsTuple[2])
        self.pumpsLayout.addWidget(self.pump7, 0, 6, QtCore.Qt.AlignLeft)

        self.pump8 = pw.PumpControl(self, pumpName="Org2")
        self.pump8.setHidden(True)
        self.pump8.pumpModelCombo.setCurrentText(self.pumpsTuple[0])
        self.pump8.formatWidget(pump=self.pumpsTuple[0])
        self.pumpsLayout.addWidget(self.pump8, 0, 7, QtCore.Qt.AlignLeft)

        self.pump9 = pw.PumpControl(self, pumpName="Water")
        self.pump9.setHidden(True)
        self.pump9.pumpModelCombo.setCurrentText(self.pumpsTuple[0])
        self.pump9.formatWidget(pump=self.pumpsTuple[0])
        self.pumpsLayout.addWidget(self.pump9, 0, 8, QtCore.Qt.AlignLeft)

        self.pump10 = pw.PumpControl(self, pumpName="DLS")
        self.pump10.setHidden(True)
        self.pump10.pumpModelCombo.setCurrentText(self.pumpsTuple[0])
        self.pump10.formatWidget(pump=self.pumpsTuple[0])
        self.pumpsLayout.addWidget(self.pump10, 0, 9, QtCore.Qt.AlignLeft)

        self.pump11 = pw.PumpControl(self, pumpName="Initiator")
        self.pump11.setHidden(True)
        self.pump11.pumpModelCombo.setCurrentText(self.pumpsTuple[1])
        self.pump11.formatWidget(pump=self.pumpsTuple[1])
        self.pumpsLayout.addWidget(self.pump11, 0, 10, QtCore.Qt.AlignLeft)

        self.pump12 = pw.PumpControl(self, pumpName="Surfactant")
        self.pump12.setHidden(True)
        self.pump12.pumpModelCombo.setCurrentText(self.pumpsTuple[1])
        self.pump12.formatWidget(pump=self.pumpsTuple[1])
        self.pumpsLayout.addWidget(self.pump12, 0, 11, QtCore.Qt.AlignLeft)

        self.pump13 = pw.PumpControl(self, pumpName="Macro-CTA")
        self.pump13.setHidden(True)
        self.pump13.pumpModelCombo.setCurrentText(self.pumpsTuple[1])
        self.pump13.formatWidget(pump=self.pumpsTuple[1])
        self.pumpsLayout.addWidget(self.pump13, 0, 12, QtCore.Qt.AlignLeft)


######################################## Valves ########################################
        self.valvesBox = QtWidgets.QGroupBox("Valves")
        self.valvesBox.setMaximumHeight(400)
        self.valvesBox.setMaximumWidth(1400)
        self.valvesLayout = QtWidgets.QGridLayout(self.valvesBox)
        self._layout.addWidget(self.valvesBox, 1, 0, QtCore.Qt.AlignTop)

        self.valve1 = vw.ValveControl(self, valveName="Solvent")
        self.valve1.valveTypeCombo.setCurrentText(self.valvesTuple[0])
        self.valve1.formatWidget(valve=self.valvesTuple[0])
        self.valvesLayout.addWidget(self.valve1, 0, 0, QtCore.Qt.AlignLeft)

        self.valve2 = vw.ValveControl(self, valveName="Emulsion")
        self.valve2.valveTypeCombo.setCurrentText(self.valvesTuple[1])
        self.valve2.formatWidget(valve=self.valvesTuple[1])
        self.valvesLayout.addWidget(self.valve2, 0, 1, QtCore.Qt.AlignLeft)

        self.valve3 = vw.ValveControl(self, valveName="Outlet")
        self.valve3.valveTypeCombo.setCurrentText(self.valvesTuple[0])
        self.valve3.formatWidget(valve=self.valvesTuple[0])
        self.valvesLayout.addWidget(self.valve3, 0, 2, QtCore.Qt.AlignLeft)

        self.valve4 = vw.ValveControl(self, valveName="DLS")
        self.valve4.valveTypeCombo.setCurrentText(self.valvesTuple[0])
        self.valve4.formatWidget(valve=self.valvesTuple[0])
        self.valvesLayout.addWidget(self.valve4, 0, 3, QtCore.Qt.AlignLeft)

        self.valve5 = vw.ValveControl(self, valveName="GPC")
        self.valve5.valveTypeCombo.setCurrentText(self.valvesTuple[4])
        self.valve5.formatWidget(valve=self.valvesTuple[4])
        self.valvesLayout.addWidget(self.valve5, 0, 4, QtCore.Qt.AlignLeft)

    def resetWidgets(self):
        self.pump1.setHidden(True)
        self.pump2.setHidden(True)
        self.pump3.setHidden(True)
        self.pump4.setHidden(True)
        self.pump5.setHidden(True)
        self.pump6.setHidden(True)
        self.pump7.setHidden(True)
        self.pump8.setHidden(True)
        self.pump9.setHidden(True)
        self.pump10.setHidden(True)
