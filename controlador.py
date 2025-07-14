from PyQt5.QtWidgets import QMessageBox, QFileDialog, QApplication, QTableWidgetItem, QVBoxLayout
from PyQt5.QtGui import QPixmap, QImage
from PyQt5 import uic
from vista import Ventana_login, Ventana_expertoimagenes, Ventana_expertosenales, Ventana_imagenesdicom, Ventana_senaless
from modelo import ModeloDatos, ProcesadorImagenes, ProcesadorSenales, ProcesadorCSV
import sys
import os
import pydicom
import numpy as np
import matplotlib.pyplot as plt
import nibabel as nib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import cv2

class ControladorPrincipal:
    def __init__(self):
        self.modelo = ModeloDatos(db_type='mongodb')
        self.Ventana_login = Ventana_login()
        self.Ventana_login.Boton_acceder.clicked.connect(self.autenticar_usuario)
        
        # Inicializar otros controladores
        self.controlador_imagenes = None
        self.controlador_senales = None
    
    def autenticar_usuario(self):
        usuario = self.Ventana_login.usuario.toPlainText()
        contrasena = self.Ventana_login.contrasena.toPlainText()
        rol = self.Ventana_login.Combo_rol.currentText()
        
        if self.modelo.verificar_usuario(usuario, contrasena, rol):
            if rol == "experto_imagenes":
                self.mostrar_ventana_imagenes()
            elif rol=="experto_senales":
                self.mostrar_ventana_senales()
        else:
            self.Ventana_login.mostrar_error("Credenciales incorrectas")
    
    def mostrar_ventana_imagenes(self):
        self.Ventana_login.hide()
        self.Ventana_expertoimagenes = Ventana_expertoimagenes()
        self.controlador_imagenes = ControladorImagenes(self.Ventana_expertoimagenes)
        self.Ventana_expertoimagenes.show()
    
    def mostrar_ventana_senales(self):
        self.Ventana_login.hide()
        self.Ventana_expertosenales = Ventana_expertosenales()
        self.controlador_senales = ControladorSenales(self.Ventana_expertosenales)
        self.Ventana_expertosenales.show()

class ControladorImagenes:
    def __init__(self, ventana):
        self.ventana = ventana
        self.procesador = ProcesadorImagenes()
        self.modelo = ModeloDatos(db_type='mongodb')
        
        # Conectar señales
        self.ventana.Boton_cargarimagenesd.clicked.connect(self.mostrar_ventana_dicom)
        self.ventana.Boton_procesarimagenesj.clicked.connect(self.procesar_imagen)
        self.ventana.Boton_visualizarmetadatos.clicked.connect(self.mostrar_metadatos) 
        self.ventana.pushButton_5.clicked.connect(self.ventana.close)
    
    def mostrar_ventana_dicom(self):
        self.ventana_dicom = Ventana_imagenesdicom()
        self.controlador_dicom = ControladorDicom(self.ventana_dicom)
        self.ventana_dicom.exec_()
    
    def procesar_imagen(self):
        ruta, _ = QFileDialog.getOpenFileName(None, "Seleccionar imagen JPG/PNG", "", "Imágenes (*.jpg *.png)")
        if ruta:
            try:
                img = self.procesador.procesar_imagen(ruta, "ecualizacion", None)
                
                # Convertir numpy array a QImage
                height, width, channel = img.shape
                bytes_per_line = 3 * width
                q_img = QImage(img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
                
                # Mostrar imagen procesada
                pixmap = QPixmap.fromImage(q_img)
                self.ventana.label_imagen_procesada.setPixmap(pixmap)
                self.ventana.label_imagen_procesada.setScaledContents(True)
                
                # Guardar en base de datos
                self.modelo.guardar_procesamiento('imagen', os.path.basename(ruta), ruta)
                
            except Exception as e:
                QMessageBox.critical(self.ventana, "Error", f"Error al procesar imagen: {str(e)}")
    
    def mostrar_metadatos(self):
     try:
        
        resultado = self.modelo.conn['nombre_base']['imagenes_medicas'].find_one(sort=[('_id', -1)])

        if resultado and 'metadatos' in resultado:
            self.ventana_dicom = Ventana_imagenesdicom()
            self.ventana_dicom.Tabla_metadatos.setRowCount(1)
            self.ventana_dicom.Tabla_metadatos.setColumnCount(1)
            self.ventana_dicom.Tabla_metadatos.setItem(0, 0, QTableWidgetItem(str(resultado['metadatos'])))
            self.ventana_dicom.exec_()
        else:
            QMessageBox.information(self.ventana, "Información", "No hay metadatos disponibles")
     except Exception as e:
        QMessageBox.critical(self.ventana, "Error", f"Error al mostrar metadatos: {str(e)}")

class ControladorDicom:
    def __init__(self, ventana):
        self.ventana = ventana
        self.procesador = ProcesadorImagenes()
        self.modelo = ModeloDatos(db_type='mongodb')
        self.dicom_data = None
        self.volume = None
        
        # Conectar señales
        self.ventana.Boton_cargarcarpetad.clicked.connect(self.cargar_carpeta_dicom)
        self.ventana.Boton_convertir.clicked.connect(self.convertir_nifti)
        self.ventana.Boton_actualizar.clicked.connect(self.guardar_metadatos)
        
        # Conectar sliders
        self.ventana.horizontalSlider.valueChanged.connect(self.actualizar_corte_axial)
        self.ventana.horizontalSlider_2.valueChanged.connect(self.actualizar_corte_coronal)
        self.ventana.horizontalSlider_3.valueChanged.connect(self.actualizar_corte_sagital)
    
    def cargar_carpeta_dicom(self):
        ruta = QFileDialog.getExistingDirectory(None, "Seleccionar carpeta DICOM")
        if ruta:
            try:
                archivos = [f for f in os.listdir(ruta) if f.endswith('.dcm')]
                if not archivos:
                    raise Exception("No se encontraron archivos DICOM en la carpeta")
                
                # Leer el primer archivo para obtener metadatos
                primer_archivo = pydicom.dcmread(os.path.join(ruta, archivos[0]))
                self.ventana.Label_infopac.setText(f"Paciente: {primer_archivo.PatientName}")
                
                # Cargar todos los slices
                slices = [pydicom.dcmread(os.path.join(ruta, f)) for f in archivos]
                slices.sort(key=lambda x: float(x.ImagePositionPatient[2]))
                
                # Crear volumen 3D
                self.volume = np.stack([s.pixel_array for s in slices])
                self.dicom_data = slices
                
                # Configurar sliders
                self.ventana.horizontalSlider.setRange(0, self.volume.shape[0]-1)
                self.ventana.horizontalSlider_2.setRange(0, self.volume.shape[1]-1)
                self.ventana.horizontalSlider_3.setRange(0, self.volume.shape[2]-1)
                
                # Mostrar primer corte
                self.actualizar_corte_axial(0)
                self.actualizar_corte_coronal(0)
                self.actualizar_corte_sagital(0)
                
                # Guardar ruta
                self.ventana.Label_ruta.setText(ruta)
                
            except Exception as e:
                QMessageBox.critical(self.ventana, "Error", f"Error al cargar DICOM: {str(e)}")
    
    def actualizar_corte_axial(self, value):
        if self.volume is not None:
            img = self.volume[value, :, :]
            q_img = self.numpy_to_qimage(img)
            self.ventana.Label_corteaxial.setPixmap(QPixmap.fromImage(q_img))
    
    def actualizar_corte_coronal(self, value):
        if self.volume is not None:
            img = self.volume[:, value, :]
            q_img = self.numpy_to_qimage(img)
            self.ventana.Labelcortecoronal.setPixmap(QPixmap.fromImage(q_img))
    
    def actualizar_corte_sagital(self, value):
        if self.volume is not None:
            img = self.volume[:, :, value]
            q_img = self.numpy_to_qimage(img)
            self.ventana.Label_cortesagital.setPixmap(QPixmap.fromImage(q_img))
    
    def numpy_to_qimage(self, array):
        # Normalizar imagen
        array = (array - array.min()) / (array.max() - array.min()) * 255
        array = array.astype(np.uint8)
        
        height, width = array.shape
        bytes_per_line = width
        q_img = QImage(array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        return q_img
    
    def convertir_nifti(self):
        if self.volume is not None:
            try:
                ruta, _ = QFileDialog.getSaveFileName(None, "Guardar como NIfTI", "", "NIfTI Files (*.nii *.nii.gz)")
                if ruta:
                    # Crear imagen NIfTI
                    img = nib.Nifti1Image(self.volume, np.eye(4))
                    nib.save(img, ruta)
                    
                    # Guardar en base de datos
                    self.modelo.guardar_procesamiento('nifti', os.path.basename(ruta), ruta)
                    QMessageBox.information(self.ventana, "Éxito", "Conversión a NIfTI completada")
            except Exception as e:
                QMessageBox.critical(self.ventana, "Error", f"Error en conversión NIfTI: {str(e)}")
        else:
            QMessageBox.warning(self.ventana, "Advertencia", "No hay datos DICOM cargados")
    
    def guardar_metadatos(self):
        if self.dicom_data:
            try:
                metadatos = {}
                for tag in self.dicom_data[0]:
                    if tag.name != 'Pixel Data':
                        metadatos[tag.name] = str(tag.value)
                
                # Guardar metadatos en la base de datos
                self.modelo.guardar_metadatos_dicom({
                    'PatientID': self.dicom_data[0].get('PatientID', ''),
                    'PatientName': str(self.dicom_data[0].get('PatientName', '')),
                    'ruta_dicom': self.ventana.Label_ruta.text(),
                    **metadatos
                })
                
                QMessageBox.information(self.ventana, "Éxito", "Metadatos guardados correctamente")
            except Exception as e:
                QMessageBox.critical(self.ventana, "Error", f"Error al guardar metadatos: {str(e)}")
        else:
            QMessageBox.warning(self.ventana, "Advertencia", "No hay datos DICOM cargados")

class ControladorSenales:
    def __init__(self, ventana):
        self.ventana = ventana
        self.procesador = ProcesadorSenales()
        self.modelo = ModeloDatos(db_type='mongodb')
        self.senales = None
        self.df_csv = None

        self.ventana.Botton_graficarsenal.setDefault(True)
        self.ventana.Botton_graficarsenal.setFocus()
        
        # Conectar señales
        self.ventana.Boton_cargarsenales.clicked.connect(self.mostrar_ventana_senales)
        self.ventana.Boton_analizarsenales.clicked.connect(self.abrir_ventana_analisis)
        self.ventana.Boton_cargardatos.clicked.connect(self.abrir_ventana_analisis) 
        self.ventana.Boton_visualizarsenales.clicked.connect(self.mostrar_historial_senales)
        self.ventana.Boton_salir.clicked.connect(self.ventana.close)
    
    def mostrar_ventana_senales(self):
        self.ventana_senales = Ventana_senaless()
        self.controlador_ventana_senales = ControladorVentanaSenales(self.ventana_senales)
        self.ventana_senales.exec_()
    
    def abrir_ventana_analisis(self):
        """Crea y muestra la ventana de análisis de señales."""
        self.ventana_senales = Ventana_senaless()
        self.controlador_ventana_senales = ControladorVentanaSenales(self.ventana_senales)
        self.ventana_senales.exec_()

    def mostrar_historial_senales(self):
        """Muestra un historial de señales procesadas (funcionalidad pendiente)."""
        QMessageBox.information(self.ventana, "Historial", 
                                "Esta funcionalidad está en desarrollo. Aquí se mostrarían las señales guardadas en la base de datos.")

class ControladorVentanaSenales:
    def __init__(self, ventana):
        self.ventana = ventana
        self.procesador = ProcesadorSenales()
        self.modelo = ModeloDatos()
        self.senales = None
        self.df_csv = None
        
        # Configurar figura de matplotlib
        self.figura = plt.figure()
        self.canvas = FigureCanvas(self.figura)
        layout = self.ventana.pagina_cargarsenales.layout()
        if layout is None:
            layout = QVBoxLayout(self.ventana.pagina_cargarsenales)
            self.ventana.pagina_cargarsenales.setLayout(layout)

        layout.addWidget(self.canvas)
        
        
        # Conectar señales con los nombres CORRECTOS del archivo UI
        self.ventana.Botton_graficarsenal.clicked.connect(self.graficar_senal)  # Cambiado a Botton
        self.ventana.Boton_graficarseg.clicked.connect(self.graficar_segmento)
        self.ventana.Boton_promedio.clicked.connect(self.calcular_promedio)
        self.ventana.Boton_cargarcsv.clicked.connect(self.cargar_csv)
        self.ventana.Boton_graficardispersion.clicked.connect(self.graficar_dispersion)
        
        # Verificar que los widgets existen (para debug)
        print("Widgets disponibles:", [attr for attr in dir(self.ventana) if attr.startswith('Boton') or attr.startswith('Botton')])
    
    def cargar_mat(self):
        ruta, _ = QFileDialog.getOpenFileName(None, "Cargar archivo MAT", "", "MAT Files (*.mat)")
        if ruta:
            try:
                self.senales = self.procesador.cargar_mat(ruta)
                self.ventana.Combo_laves.clear()
                self.ventana.Combo_laves.addItems(self.senales.keys())
                self.modelo.guardar_procesamiento('mat', os.path.basename(ruta), ruta)
            except Exception as e:
                QMessageBox.critical(self.ventana, "Error", str(e))
    
    def graficar_senal(self):
        if self.senales is not None:
            try:
                llave = self.ventana.Combo_laves.currentText()
                datos = self.senales[llave]
                
                if not isinstance(datos, np.ndarray):
                    raise ValueError("La llave seleccionada no contiene un arreglo numpy")
                
                self.figura.clear()
                ax = self.figura.add_subplot(111)
                
                if datos.ndim == 1:
                    ax.plot(datos)
                elif datos.ndim == 2:
                    for i in range(min(5, datos.shape[0])):  # Mostrar solo 5 canales
                        ax.plot(datos[i,:], label=f"Canal {i+1}")
                    ax.legend()
                
                ax.set_title(f"Señal: {llave}")
                ax.set_xlabel("Muestras")
                ax.set_ylabel("Amplitud")
                self.canvas.draw()
                
            except Exception as e:
                QMessageBox.critical(self.ventana, "Error", f"No es un arreglo válido: {str(e)}")
        else:
            QMessageBox.warning(self.ventana, "Advertencia", "No hay datos MAT cargados")
    
    def graficar_segmento(self):
        if self.senales is not None:
            try:
                llave = self.ventana.Combo_laves.currentText()
                datos = self.senales[llave]
                
                if not isinstance(datos, np.ndarray):
                    raise ValueError("La llave seleccionada no contiene un arreglo numpy")
                
                inicio = self.ventana.SpinInicio.value()
                fin = self.ventana.SpinFin.value()
                
                if inicio >= fin:
                    raise ValueError("El inicio debe ser menor que el fin")
                
                self.figura.clear()
                ax = self.figura.add_subplot(111)
                
                if datos.ndim == 1:
                    ax.plot(datos[inicio:fin])
                elif datos.ndim == 2:
                    for i in range(min(5, datos.shape[0])):  # Mostrar solo 5 canales
                        ax.plot(datos[i, inicio:fin], label=f"Canal {i+1}")
                    ax.legend()
                
                ax.set_title(f"Segmento {inicio}-{fin} de {llave}")
                ax.set_xlabel("Muestras")
                ax.set_ylabel("Amplitud")
                self.canvas.draw()
                
            except Exception as e:
                QMessageBox.critical(self.ventana, "Error", str(e))
        else:
            QMessageBox.warning(self.ventana, "Advertencia", "No hay datos MAT cargados")
    
    def calcular_promedio(self):
        if self.senales is not None:
            try:
                llave = self.ventana.Combo_laves.currentText()
                datos = self.senales[llave]
                
                if not isinstance(datos, np.ndarray) or datos.ndim != 2:
                    raise ValueError("Se requiere un arreglo 2D para calcular el promedio")
                
                promedio = self.procesador.calcular_promedio(datos)
                
                self.figura.clear()
                ax = self.figura.add_subplot(111)
                ax.stem(promedio, use_line_collection=True)
                ax.set_title(f"Promedio de {llave}")
                ax.set_xlabel("Muestras")
                ax.set_ylabel("Amplitud promedio")
                self.canvas.draw()
                
            except Exception as e:
                QMessageBox.critical(self.ventana, "Error", str(e))
        else:
            QMessageBox.warning(self.ventana, "Advertencia", "No hay datos MAT cargados")
    
    def cargar_csv(self):
        ruta, _ = QFileDialog.getOpenFileName(None, "Cargar archivo CSV", "", "CSV Files (*.csv)")
        if ruta:
            try:
                self.df_csv = ProcesadorCSV.cargar_csv(ruta)
                
                # Configurar tabla
                self.ventana.Tablacsv.setRowCount(self.df_csv.shape[0])
                self.ventana.Tablacsv.setColumnCount(self.df_csv.shape[1])
                self.ventana.Tablacsv.setHorizontalHeaderLabels(self.df_csv.columns)
                
                for i in range(self.df_csv.shape[0]):
                    for j in range(self.df_csv.shape[1]):
                        self.ventana.Tablacsv.setItem(i, j, QTableWidgetItem(str(self.df_csv.iloc[i, j])))
                
                # Configurar comboboxes
                self.ventana.Combo_columnax.clear()
                self.ventana.Combo_columnay.clear()
                self.ventana.Combo_columnax.addItems(self.df_csv.columns)
                self.ventana.Combo_columnay.addItems(self.df_csv.columns)
                
                self.modelo.guardar_procesamiento('csv', os.path.basename(ruta), ruta)
                
            except Exception as e:
                QMessageBox.critical(self.ventana, "Error", str(e))
    
    def graficar_dispersion(self):
        if self.df_csv is not None:
            try:
                col_x = self.ventana.Combo_columnax.currentText()
                col_y = self.ventana.Combo_columnay.currentText()
                
                self.figura.clear()
                ax = self.figura.add_subplot(111)
                ax.scatter(self.df_csv[col_x], self.df_csv[col_y])
                ax.set_title(f"Dispersión: {col_x} vs {col_y}")
                ax.set_xlabel(col_x)
                ax.set_ylabel(col_y)
                self.canvas.draw()
                
            except Exception as e:
                QMessageBox.critical(self.ventana, "Error", str(e))
        else:
            QMessageBox.warning(self.ventana, "Advertencia", "No hay datos CSV cargados")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    controlador = ControladorPrincipal()
    controlador.Ventana_login.show()
    sys.exit(app.exec_())

from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QMessageBox

class ControladorImagenesPNG:
    def __init__(self, vista):
        self.vista = vista
        self.modelo = ProcesadorImagenes()
        self.imagen_original = None
        self.imagen_procesada = None
        
        # Conectar señales
        self.vista.btn_cargar.clicked.connect(self.cargar_imagen)
        self.vista.btn_procesar.clicked.connect(self.procesar_imagen)
        self.vista.btn_guardar.clicked.connect(self.guardar_imagen)
        self.vista.btn_canny.clicked.connect(self.aplicar_canny)
        self.vista.btn_watershed.clicked.connect(self.aplicar_watershed)
    
    def cargar_imagen(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self.vista, "Abrir Imagen", "", 
            "Imágenes (*.png *.jpg *.jpeg)")
        
        if ruta:
            self.imagen_original = self.modelo.cargar_imagen(ruta)
            if self.imagen_original is not None:
                qimg = self.modelo.convertir_a_qimage(self.imagen_original)
                self.vista.mostrar_imagen(qimg, original=True)
            else:
                QMessageBox.warning(self.vista, "Error", "No se pudo cargar la imagen")
    
    def procesar_imagen(self):
        if self.imagen_original is None:
            QMessageBox.warning(self.vista, "Error", "Primero cargue una imagen")
            return
        
        operacion = self.vista.cmb_operaciones.currentText()
        kernel_size = self.vista.spn_kernel.value()
        
        try:
            if operacion == "Ecualización":
                self.imagen_procesada = self.modelo.ecualizar_histograma(self.imagen_original)
            elif operacion == "Binarización":
                self.imagen_procesada = self.modelo.binarizar_imagen(self.imagen_original)
            elif operacion == "Cierre Morfológico":
                self.imagen_procesada = self.modelo.operacion_morfologica(
                    self.imagen_original, 'cierre', kernel_size)
            elif operacion == "Apertura Morfológica":
                self.imagen_procesada = self.modelo.operacion_morfologica(
                    self.imagen_original, 'apertura', kernel_size)
            elif operacion == "Conteo de Células":
                conteo, edges = self.modelo.contar_celulas(self.imagen_original, kernel_size)
                self.imagen_procesada = edges
                QMessageBox.information(
                    self.vista, "Resultado", 
                    f"Se detectaron {conteo} células/objetos")
            
            if self.imagen_procesada is not None:
                qimg = self.modelo.convertir_a_qimage(self.imagen_procesada)
                self.vista.mostrar_imagen(qimg, original=False)
        
        except Exception as e:
            QMessageBox.critical(self.vista, "Error", f"Error al procesar: {str(e)}")
    
    def guardar_imagen(self):
        if self.imagen_procesada is None:
            QMessageBox.warning(self.vista, "Error", "No hay imagen procesada para guardar")
            return
        
        ruta = self.vista.obtener_ruta_guardado()
        if ruta:
            cv2.imwrite(ruta, self.imagen_procesada)
            QMessageBox.information(self.vista, "Éxito", "Imagen guardada correctamente")
    
    def aplicar_canny(self):
        if self.imagen_original is None:
            QMessageBox.warning(self.vista, "Error", "Primero cargue una imagen")
            return
        
        umbral1 = self.vista.spn_canny1.value()
        umbral2 = self.vista.spn_canny2.value()
        
        self.imagen_procesada = self.modelo.deteccion_bordes_canny(
            self.imagen_original, umbral1, umbral2)
        
        qimg = self.modelo.convertir_a_qimage(self.imagen_procesada)
        self.vista.mostrar_imagen(qimg, original=False)
    
    def aplicar_watershed(self):
        if self.imagen_original is None:
            QMessageBox.warning(self.vista, "Error", "Primero cargue una imagen")
            return
        
        self.imagen_procesada = self.modelo.segmentacion_watershed(self.imagen_original)
        qimg = self.modelo.convertir_a_qimage(self.imagen_procesada)
        self.vista.mostrar_imagen(qimg, original=False)