from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QPushButton,
    QFileDialog, QMessageBox, QListWidgetItem, QLabel, QComboBox
)
from qgis.core import QgsProject, QgsVectorFileWriter
import os


class SaveLayersToFileDialog(QDialog):
    FORMAT_MAP = {
        "GeoJSON": ("GeoJSON", ".geojson"),
        "CSV": ("CSV", ".csv"),
        "ESRI Shapefile": ("ESRI Shapefile", ".shp"),
        "KML": ("KML", ".kml")
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Export Layers")
        self.resize(400, 350)

        self.output_folder = ""

        layout = QVBoxLayout()

        # Vector layers list
        self.layer_list = self._create_layer_list()
        layout.addWidget(self.layer_list)

        # Output format selection
        layout.addWidget(QLabel("Select output format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(self.FORMAT_MAP.keys())
        layout.addWidget(self.format_combo)

        # Destination folder button
        self.select_folder_btn = QPushButton("Select destination folder")
        self.select_folder_btn.clicked.connect(self._choose_folder)
        layout.addWidget(self.select_folder_btn)

        # Export button
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self._export_layers)
        layout.addWidget(self.export_btn)

        self.setLayout(layout)

    def _create_layer_list(self):
        """Create and populate the list of vector layers."""
        layer_list = QListWidget()
        layer_list.setSelectionMode(QListWidget.MultiSelection)

        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == layer.VectorLayer:
                item = QListWidgetItem(layer.name())
                item.setData(1000, layer.id())
                layer_list.addItem(item)
        return layer_list

    def _choose_folder(self):
        """Open a dialog to select the output folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select folder")
        if folder:
            self.output_folder = folder
            self.select_folder_btn.setText(f"Folder: {folder}")

    def _export_layers(self):
        """Export the selected layers."""
        if not self._validate_export_conditions():
            return

        selected_format = self.format_combo.currentText()
        driver, file_ext = self.FORMAT_MAP[selected_format]

        for item in self.layer_list.selectedItems():
            layer_id = item.data(1000)
            layer = QgsProject.instance().mapLayer(layer_id)
            if not self._validate_layer(layer):
                continue

            if not self._validate_geometry(layer, selected_format):
                continue

            filename = os.path.join(self.output_folder, self._sanitize_filename(layer.name()) + file_ext)
            self._save_layer(layer, filename, driver)

        QMessageBox.information(self, "Success", "Export completed successfully.")
        self.accept()

    def _validate_export_conditions(self):
        """Check if a folder is selected and if at least one layer is chosen."""
        if not self.output_folder:
            QMessageBox.warning(self, "Warning", "Please select a destination folder first.")
            return False

        if not self.layer_list.selectedItems():
            QMessageBox.warning(self, "Warning", "Please select at least one layer.")
            return False

        return True

    def _validate_layer(self, layer):
        """Check if the layer is valid."""
        if not layer or not layer.isValid():
            QMessageBox.warning(self, "Error", "The layer is invalid.")
            return False
        return True

    def _validate_geometry(self, layer, selected_format):
        """Check geometry validity (not required for CSV)."""
        if selected_format == "CSV":
            return True

        invalid_features = [f.id() for f in layer.getFeatures() if not f.geometry() or not f.geometry().isGeosValid()]
        if invalid_features:
            QMessageBox.critical(
                self,
                "Error",
                f"The layer {layer.name()} contains invalid or null geometries (IDs: {invalid_features[:5]}...).\n"
                "Please fix them before exporting."
            )
            return False
        return True

    def _sanitize_filename(self, name):
        """Clean the filename."""
        return "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip()

    def _save_layer(self, layer, filename, driver):
        """Save the layer to disk and handle errors."""
        error, error_message = QgsVectorFileWriter.writeAsVectorFormat(
            layer,
            filename,
            "utf-8",
            layer.crs(),
            driver
        )

        if error != QgsVectorFileWriter.NoError:
            QMessageBox.critical(
                self,
                "Error",
                f"Error {error} while saving the layer {layer.name()}: {error_message}"
            )


# Launch the dialog from QGIS Python console:
dialog = SaveLayersToFileDialog()
dialog.exec_()
