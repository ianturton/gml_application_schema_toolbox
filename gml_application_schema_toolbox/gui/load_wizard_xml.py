import os
from PyQt5 import uic

from qgis.PyQt.QtCore import (
    pyqtSlot, QRegExp, QVariant
)
from qgis.PyQt.QtWidgets import (
    QWizardPage, QComboBox, QLineEdit, QTableWidgetItem
)
from qgis.PyQt.QtGui import QRegExpValidator

from qgis.core import (
    QgsProject, QgsEditorWidgetSetup
)

from ..core.load_gml_as_xml import load_as_xml_layer
from ..gui.progress_bar import ProgressBarLogger
from ..gui import qgis_form_custom_widget

PAGE_3_W, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), '..', 'ui', 'load_wizard_xml_options.ui'))

class LoadWizardXML(QWizardPage, PAGE_3_W):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setFinalPage(True)

        self.attributeTable.selectionModel().selectionChanged.connect(self.onSelectMapping)
        self.geometryColumnCheck.stateChanged.connect(self.geometryColumnEdit.setEnabled)

    def nextId(self):
        return -1

    def validatePage(self):
        gml_path = self.wizard().gml_path()

        # get attribute mapping
        mapping = {}
        for i in range(self.attributeTable.rowCount()):
            attr = self.attributeTable.cellWidget(i, 0).text()
            xpath = self.attributeTable.item(i, 2).text()
            combo = self.attributeTable.cellWidget(i, 1)
            type = combo.itemData(combo.currentIndex())
            mapping[attr] = (xpath, type)

        # get geometry mapping
        gmapping = None
        if self.geometryColumnCheck.isChecked() and self.geometryColumnEdit.text():
            gmapping = self.geometryColumnEdit.text()

        # add a progress bar during import
        lyrs = load_as_xml_layer(gml_path,
                                 is_remote=gml_path.startswith('http://') or gml_path.startswith('https://'),
                                 attributes=mapping,
                                 geometry_mapping=gmapping,
                                 logger=ProgressBarLogger("Importing features ..."),
                                 swap_xy=self.swapXYCheck.isChecked())

        for lyr in lyrs.values():
            # install an XML tree widget
            qgis_form_custom_widget.install_xml_tree_on_feature_form(lyr)

            # id column
            lyr.setEditorWidgetSetup(0, QgsEditorWidgetSetup("Hidden", {}))
            # _xml_ column
            lyr.setEditorWidgetSetup(2, QgsEditorWidgetSetup("XML", {}))
            lyr.setDisplayExpression("fid")

        QgsProject.instance().addMapLayers(lyrs.values())

        return True

    @pyqtSlot()
    def on_addMappingBtn_clicked(self):
        lastRow = self.attributeTable.rowCount()
        self.attributeTable.insertRow(lastRow)
        combo = QComboBox(self.attributeTable)
        combo.addItem("String", QVariant.String)
        combo.addItem("Integer", QVariant.Int)
        combo.addItem("Real", QVariant.Double)
        combo.addItem("Date/Time", QVariant.DateTime)
        self.attributeTable.setCellWidget(lastRow, 1, combo)

        lineEdit = QLineEdit(self.attributeTable)
        # exclude id, fid and _xml from allowed field names
        lineEdit.setValidator(QRegExpValidator(QRegExp("(?!(id|fid|_xml_)).*")))
        self.attributeTable.setCellWidget(lastRow, 0, lineEdit)

        self.attributeTable.setItem(lastRow, 2, QTableWidgetItem())

    @pyqtSlot()
    def on_removeMappingBtn_clicked(self):
        idx = self.attributeTable.currentIndex()
        self.attributeTable.removeRow(idx.row())

    def onSelectMapping(self, selected, deselected):
        self.removeMappingBtn.setEnabled(selected != -1)
