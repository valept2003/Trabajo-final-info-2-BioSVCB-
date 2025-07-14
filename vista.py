from PyQt5.QtWidgets import (QMainWindow, QDialog, QLabel, QPushButton, 
                            QComboBox, QTableWidget, QSlider, QTextEdit,
                            QMessageBox, QFrame, QVBoxLayout, QHBoxLayout,
                            QWidget, QToolBox, QSpinBox, QFileDialog)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
from PyQt5 import uic
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class Ventana_login(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("Ventana_login.ui", self)
        self.setWindowTitle("BioSVCB - Login")
        
    def mostrar_error(self, mensaje):
        QMessageBox.critical(self, "Error", mensaje)

class Ventana_expertoimagenes(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("Ventana_expertoimagenes.ui", self)
        self.setWindowTitle("BioSVCB - Experto en Imágenes")


class Ventana_expertosenales(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("Ventana_expertosenales.ui", self)
        self.setWindowTitle("BioSVCB - Experto en Señales")
        

class Ventana_imagenesdicom(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("Ventana_imagenesdicom.ui", self)
        self.setWindowTitle("Visualización DICOM/NIfTI")
       

class Ventana_senaless(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("Ventana_senaless.ui", self)
        self.setWindowTitle("Análisis de Señales Biomédicas")
        

class VentanaImagenesPNG(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Procesamiento de Imágenes JPG/PNG")
        self.setFixedSize(800, 600)