#!/usr/bin/env python
# coding: utf-8

# In[1]:


pip install pymongo


# In[7]:


from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, CollectionInvalid, OperationFailure
import os
from datetime import datetime 


MONGO_HOST = 'localhost' 
MONGO_PORT = 27017       
DB_NAME = 'BioSVCB_db' 

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None

    def connect(self):
        
        try:
            self.client = MongoClient(MONGO_HOST, MONGO_PORT, serverSelectionTimeoutMS=5000)
            
            self.client.admin.command('ping')
            self.db = self.client[DB_NAME]
            print(f"Conexión a MongoDB '{MONGO_HOST}:{MONGO_PORT}/{DB_NAME}' establecida.")
            return True
        except ConnectionFailure as e:
            print(f"Error de conexión a MongoDB: {e}. Asegúrate de que el servidor MongoDB esté corriendo.")
            self.client = None
            self.db = None
            return False
        except Exception as e:
            print(f"Error inesperado al conectar a MongoDB: {e}")
            self.client = None
            self.db = None
            return False

    def close(self):
        
        if self.client:
            self.client.close()
            print("Conexión a MongoDB cerrada.")

    def get_collection(self, collection_name):
       
        if self.db is None: 
            if not self.connect():
                print("No se pudo obtener la conexión a la base de datos.")
                return None
        return self.db[collection_name]

    def create_collections(self):
        if self.db is None: 
            if not self.connect():
                print("No se pudo crear colecciones: Sin conexión a la base de datos.")
                return

        collections_to_create = ['users', 'dicom_nifti_data', 'other_files_data']
        for col_name in collections_to_create:
            try:
                collection = self.db[col_name]
                print(f"Colección '{col_name}' verificada/obtenida.")
            except Exception as e:
                print(f"Error al verificar/obtener colección '{col_name}': {e}")

        try:
            self.db.users.create_index("username", unique=True)
            print("Índice único para 'username' en la colección 'users' creado.")
        except CollectionInvalid:
            pass 
        except OperationFailure as e:
            print(f"Advertencia: No se pudo crear el índice único para 'username' (ya existe o duplicados): {e}")

        try:
            self.db.other_files_data.create_index("file_code", unique=True)
            print("Índice único para 'file_code' en la colección 'other_files_data' creado.")
        except CollectionInvalid:
            pass
        except OperationFailure as e:
            print(f"Advertencia: No se pudo crear el índice único para 'file_code' (ya existe o duplicados): {e}")


if __name__ == "__main__":
    db_manager = DatabaseManager()
    if db_manager.connect():
        db_manager.create_collections()

        users_collection = db_manager.get_collection('users')
        if users_collection is not None: 
            if users_collection.count_documents({"username": "imagen_user"}) == 0:
                try:
                    users_collection.insert_one({
                        "username": "imagen_user",
                        "password": "pass123", 
                        "user_type": "experto_imagenes"
                    })
                    print("Usuario 'imagen_user' insertado.")
                except OperationFailure as e:
                    print(f"Error al insertar 'imagen_user': {e}")

            if users_collection.count_documents({"username": "senal_user"}) == 0:
                try:
                    users_collection.insert_one({
                        "username": "senal_user",
                        "password": "pass321",
                        "user_type": "experto_senales"
                    })
                    print("Usuario 'senal_user' insertado.")
                except OperationFailure as e:
                    print(f"Error al insertar 'senal_user': {e}")

            print("\nUsuarios en la DB:")
            for user in users_collection.find():
                print(user)

        db_manager.close()
    else:
        print("No se pudo conectar a MongoDB. Asegúrate de que el servidor esté corriendo.")

