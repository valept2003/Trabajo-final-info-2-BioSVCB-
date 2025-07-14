import pydicom
import nibabel as nib
import numpy as np
import cv2
import scipy.io
import pandas as pd
from pymongo import MongoClient
import sqlite3
from datetime import datetime
from PyQt5.QtGui import QImage
import bcrypt
import os
import dicom2nifti  # Necesario para conversión DICOM a NIfTI


class ModeloDatos:
    def __init__(self, db_type='sqlite'):
        self.db_type = db_type
        if db_type == 'mongodb':
            self.client = MongoClient('mongodb://localhost:27017/')
            self.db = self.client['BioSVCB_db']
            self.inicializar_bd_mongodb()
        else:  # SQLite por defecto
            self.conn = sqlite3.connect('biosvcb.db', check_same_thread=False)
            self.crear_tablas()

    def inicializar_bd_mongodb(self):
        """Inicializa la estructura de la base de datos MongoDB"""
        # Crear índices para colecciones
        self.db.usuarios.create_index("usuario", unique=True)
        self.db.imagenes_medicas.create_index("ruta_dicom", unique=True)
        self.db.imagenes_medicas.create_index("ruta_nifti", unique=True)
        self.db.archivos_procesados.create_index("ruta_archivo", unique=True)
    # Agregar usuarios por defecto si no existen
        usuarios_existentes = list(self.db.usuarios.find())
        if not usuarios_existentes:
         self.db.usuarios.insert_many([
            {"usuario": "experto_imagenes", "password": "1234", "rol": "experto_imagenes"},
            {"usuario": "experto_senales", "password": "abcd", "rol": "experto_senales"}
         ])

    def crear_tablas(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                contrasena TEXT NOT NULL,
                rol TEXT NOT NULL
            )''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS imagenes_medicas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_paciente TEXT,
                nombre TEXT,
                ruta_dicom TEXT UNIQUE,
                ruta_nifti TEXT UNIQUE,
                fecha_procesamiento DATETIME,
                metadatos TEXT
            )''')

            cursor.execute('''CREATE TABLE IF NOT EXISTS archivos_procesados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_archivo TEXT NOT NULL,
                nombre_archivo TEXT NOT NULL,
                ruta_archivo TEXT UNIQUE,
                fecha_procesamiento DATETIME,
                parametros TEXT
            )''')
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error al crear tablas: {e}")

    def verificar_usuario(self, usuario, contrasena, rol):
     if self.db_type == 'mongodb':
        try:
            # Asegúrate de que los campos coincidan con los de la BD
            user = self.db.usuarios.find_one({
                "usuario": usuario,
                "password": contrasena,
                "rol": rol
            })
            return user is not None
        except Exception as e:
            print(f"Error al verificar usuario en MongoDB: {e}")
            return False
     else:  # SQLite
        try:
            cursor = self.conn.cursor()
            cursor.execute('''SELECT * FROM usuarios 
                              WHERE usuario=? AND contrasena=? AND rol=?''',
                           (usuario, contrasena, rol))
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"Error al verificar usuario en SQLite: {e}")
            return False

    def guardar_metadatos_dicom(self, datos_dicom):
        if self.db_type == 'mongodb':
            try:
                result = self.db.imagenes_medicas.insert_one({
                    "id_paciente": datos_dicom.get('PatientID', ''),
                    "nombre": datos_dicom.get('PatientName', ''),
                    "ruta_dicom": datos_dicom.get('ruta_dicom', ''),
                    "fecha_procesamiento": datetime.now(),
                    "metadatos": datos_dicom
                })
                return result.inserted_id
            except Exception as e:
                print(f"Error al guardar metadatos DICOM en MongoDB: {e}")
                return None
        else:  # SQLite
            try:
                cursor = self.conn.cursor()
                cursor.execute('''INSERT INTO imagenes_medicas 
                    (id_paciente, nombre, ruta_dicom, fecha_procesamiento, metadatos)
                    VALUES (?, ?, ?, ?, ?)''',
                    (
                        datos_dicom.get('PatientID', ''),
                        datos_dicom.get('PatientName', ''),
                        datos_dicom.get('ruta_dicom', ''),
                        datetime.now(),
                        str(datos_dicom)
                    ))
                self.conn.commit()
                return cursor.lastrowid
            except sqlite3.Error as e:
                print(f"Error al guardar metadatos DICOM: {e}")
                return None

def guardar_procesamiento(self, tipo_archivo, nombre_archivo, ruta_archivo, parametros=None):
    if self.db_type == 'mongodb':
        try:
            result = self.db.archivos_procesados.insert_one({
                "tipo_archivo": tipo_archivo,
                "nombre_archivo": nombre_archivo,
                "ruta_archivo": ruta_archivo,
                "fecha_procesamiento": datetime.now(),
                "parametros": parametros
            })
            return result.inserted_id
        except Exception as e:
            print(f"Error al guardar procesamiento en MongoDB: {e}")
            return None
    else:  # SQLite
        try:
            cursor = self.conn.cursor()
            cursor.execute('''INSERT INTO archivos_procesados 
                (tipo_archivo, nombre_archivo, ruta_archivo, fecha_procesamiento, parametros)
                VALUES (?, ?, ?, ?, ?)''',
                (
                    tipo_archivo,
                    nombre_archivo,
                    ruta_archivo,
                    datetime.now(),
                    str(parametros) if parametros else None
                ))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error al guardar procesamiento: {e}")
            return None

import cv2
import numpy as np
from skimage.segmentation import watershed
from skimage.feature import peak_local_max
from skimage.morphology import local_maxima
from scipy import ndimage

class ProcesadorImagenes:
    @staticmethod
    def cargar_imagen(ruta):
        return cv2.imread(ruta)
    
    @staticmethod
    def convertir_a_qimage(cv_img):
        height, width, channel = cv_img.shape
        bytes_per_line = 3 * width
        cv_img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        return QImage(cv_img_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
    
    @staticmethod
    def ecualizar_histograma(imagen):
        if len(imagen.shape) == 3:
            img_ycrcb = cv2.cvtColor(imagen, cv2.COLOR_BGR2YCrCb)
            img_ycrcb[:,:,0] = cv2.equalizeHist(img_ycrcb[:,:,0])
            return cv2.cvtColor(img_ycrcb, cv2.COLOR_YCrCb2BGR)
        else:
            return cv2.equalizeHist(imagen)
    
    @staticmethod
    def binarizar_imagen(imagen, umbral=128):
        gray = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
        _, binaria = cv2.threshold(gray, umbral, 255, cv2.THRESH_BINARY)
        return cv2.cvtColor(binaria, cv2.COLOR_GRAY2BGR)
    
    @staticmethod
    def operacion_morfologica(imagen, operacion='cierre', kernel_size=3):
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        
        if operacion == 'cierre':
            return cv2.morphologyEx(imagen, cv2.MORPH_CLOSE, kernel)
        elif operacion == 'apertura':
            return cv2.morphologyEx(imagen, cv2.MORPH_OPEN, kernel)
        return imagen
    
    @staticmethod
    def contar_celulas(imagen, kernel_size=3):
        gray = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)
        edges = cv2.Canny(blurred, 30, 150)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return len(contours), edges
    
    # Métodos avanzados
    @staticmethod
    def deteccion_bordes_canny(imagen, umbral1=100, umbral2=200):
        gray = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, umbral1, umbral2)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    
    @staticmethod
    def segmentacion_watershed(imagen):
        gray = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Eliminar ruido
        kernel = np.ones((3,3), np.uint8)
        opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=2)
        
        # Área de fondo segura
        sure_bg = cv2.dilate(opening, kernel, iterations=3)
        
        # Transformada de distancia
        dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
        _, sure_fg = cv2.threshold(dist_transform, 0.7*dist_transform.max(), 255, 0)
        
        # Encontrar región desconocida
        sure_fg = np.uint8(sure_fg)
        unknown = cv2.subtract(sure_bg, sure_fg)
        
        # Etiquetado de marcadores
        _, markers = cv2.connectedComponents(sure_fg)
        markers = markers + 1
        markers[unknown == 255] = 0
        
        # Aplicar Watershed
        markers = cv2.watershed(imagen, markers)
        imagen[markers == -1] = [255,0,0]  # Marcas en azul
        
        return imagen

class ProcesadorSenales:
    @staticmethod
    def cargar_mat(ruta):
        try:
            data = scipy.io.loadmat(ruta)
            return {k: v for k, v in data.items() if isinstance(v, np.ndarray)}
        except Exception as e:
            raise Exception(f"Error al cargar archivo .mat: {str(e)}")

    @staticmethod
    def calcular_promedio(senal):
        try:
            if not isinstance(senal, np.ndarray):
                raise ValueError("La señal debe ser un array numpy")
            if senal.ndim != 2:
                raise ValueError("La señal debe ser 2D (canales x muestras)")
            return np.mean(senal, axis=0)
        except Exception as e:
            raise Exception(f"Error al calcular promedio: {str(e)}")

    @staticmethod
    def graficar_segmento(senal, inicio, fin, canal=None):
        try:
            if not isinstance(senal, np.ndarray):
                raise ValueError("La señal debe ser un array numpy")

            if senal.ndim == 1:
                segmento = senal[inicio:fin]
            elif senal.ndim == 2:
                if canal is not None and 0 <= canal < senal.shape[0]:
                    segmento = senal[canal, inicio:fin]
                else:
                    segmento = senal[:, inicio:fin]
            else:
                raise ValueError("Dimensión de señal no soportada")

            return segmento
        except Exception as e:
            raise Exception(f"Error al obtener segmento: {str(e)}")


class ProcesadorCSV:
    @staticmethod
    def cargar_csv(ruta):
        try:
            return pd.read_csv(ruta)
        except Exception as e:
            raise Exception(f"Error al cargar CSV: {str(e)}")

    @staticmethod
    def graficar_dispersion(df, col_x, col_y):
        try:
            if not isinstance(df, pd.DataFrame):
                raise ValueError("Se requiere un DataFrame")
            if col_x not in df.columns or col_y not in df.columns:
                raise ValueError("Columnas no encontradas en el DataFrame")

            x = pd.to_numeric(df[col_x], errors='coerce')
            y = pd.to_numeric(df[col_y], errors='coerce')

            mask = np.isfinite(x) & np.isfinite(y)
            return x[mask], y[mask]

        except Exception as e:
            raise Exception(f"Error al preparar datos para dispersión: {str(e)}")

