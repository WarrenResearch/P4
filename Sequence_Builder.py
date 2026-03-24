from PyQt5 import QtWidgets


class Sequence_builder(QtWidgets.QWidget):
    def __init__(self, parent=None, main=None):
        super(Sequence_builder, self).__init__(parent)
        self.main = main
        self.initUI()

    def initUI(self):
        self.layout = QtWidgets.QGridLayout(self)
        self.setLayout(self.layout)
        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 1)
        self.layout.setRowStretch(0, 1)

        self.targetsBox = QtWidgets.QGroupBox("Sequence targets")
        self.targetsBox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.targetsBoxLayout = QtWidgets.QVBoxLayout(self.targetsBox)
        self.layout.addWidget(self.targetsBox, 0, 0)

        self.rightSpacer = QtWidgets.QWidget(self)
        self.rightSpacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.layout.addWidget(self.rightSpacer, 0, 1)

        self.targetsTable = QtWidgets.QTableWidget(0, 2)
        self.targetsTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.targetsBoxLayout.addWidget(self.targetsTable)

        self.tableButtonsLayout = QtWidgets.QHBoxLayout()
        self.addRowButton = QtWidgets.QPushButton("Add row")
        self.removeRowButton = QtWidgets.QPushButton("Remove row")
        self.tableButtonsLayout.addWidget(self.addRowButton)
        self.tableButtonsLayout.addWidget(self.removeRowButton)
        self.tableButtonsLayout.addStretch(1)
        self.targetsBoxLayout.addLayout(self.tableButtonsLayout)

        self.addRowButton.clicked.connect(self.add_row)
        self.removeRowButton.clicked.connect(self.remove_selected_rows)

        self._connect_platform_signals()
        self.refresh_target_columns()

    def _connect_platform_signals(self):
        controller = getattr(self.main, "controller", None)
        if controller is None:
            return

        if hasattr(controller, "addPumpButton"):
            controller.addPumpButton.clicked.connect(self.refresh_target_columns)
        if hasattr(controller, "loadPlatformButton"):
            controller.loadPlatformButton.clicked.connect(self.refresh_target_columns)

    def _get_table_headers(self):
        headers = []
        controller = getattr(self.main, "controller", None)

        if controller is not None and hasattr(controller, "pump_widgets"):
            for index, pump_widget in enumerate(controller.pump_widgets, start=1):
                if not hasattr(pump_widget, "_sequence_name_sync_connected"):
                    pump_widget.nameEdit.textChanged.connect(self.refresh_target_columns)
                    pump_widget._sequence_name_sync_connected = True

                pump_name = pump_widget.nameEdit.text().strip()
                if not pump_name:
                    pump_name = f"Pump {index}"
                headers.append(f"{pump_name} target flowrate [mL/min]")

        if not headers:
            headers.append("Target flowrate (pump) [mL/min]")

        headers.append("Temperature [°C]")
        return headers

    def refresh_target_columns(self):
        old_headers = []
        for col in range(self.targetsTable.columnCount()):
            header_item = self.targetsTable.horizontalHeaderItem(col)
            old_headers.append(header_item.text() if header_item else f"Column {col}")

        old_data = []
        for row in range(self.targetsTable.rowCount()):
            row_data = {}
            for col, header in enumerate(old_headers):
                item = self.targetsTable.item(row, col)
                row_data[header] = item.text() if item else ""
            old_data.append(row_data)

        new_headers = self._get_table_headers()
        self.targetsTable.setColumnCount(len(new_headers))
        self.targetsTable.setHorizontalHeaderLabels(new_headers)

        for row in range(self.targetsTable.rowCount()):
            row_values = old_data[row] if row < len(old_data) else {}
            for col, header in enumerate(new_headers):
                value = row_values.get(header, "")
                self.targetsTable.setItem(row, col, QtWidgets.QTableWidgetItem(value))

    def add_row(self):
        row_index = self.targetsTable.rowCount()
        self.targetsTable.insertRow(row_index)
        for column_index in range(self.targetsTable.columnCount()):
            self.targetsTable.setItem(row_index, column_index, QtWidgets.QTableWidgetItem(""))

    def remove_selected_rows(self):
        selected_rows = sorted({index.row() for index in self.targetsTable.selectedIndexes()}, reverse=True)
        for row in selected_rows:
            self.targetsTable.removeRow(row)






