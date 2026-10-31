import re
import sqlite3
from urllib.parse import quote_plus

import pymysql
import psycopg2
from pymongo import MongoClient


class DatabaseConnector:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.db_type = None

    def _reset(self):
        """Deja el conector en estado limpio tras un fallo."""
        try:
            if (
                self.connection is not None
                and self.db_type
                and "MongoDB" in self.db_type
            ):
                self.connection.close()
        except Exception:
            pass
        self.connection = None
        self.cursor = None

    def connect(self, db_type, host, port, user, password, dbname):
        self.db_type = db_type

        # Limpieza básica de espacios en blanco accidentales
        host = host.strip() if host else ""
        port = port.strip() if port else ""
        user = user.strip() if user else ""
        password = password.strip() if password else ""
        dbname = dbname.strip() if dbname else ""

        try:
            if db_type == "SQLite":
                if not dbname:
                    raise ValueError("Debe especificar una ruta de archivo o ':memory:'")
                self.connection = sqlite3.connect(dbname)
                self.cursor = self.connection.cursor()

            elif db_type == "MySQL":
                self.connection = pymysql.connect(
                    host=host if host else "localhost",
                    port=int(port) if port else 3306,
                    user=user,
                    password=password,
                    database=dbname if dbname else None,  # Evita errores si se deja en blanco
                    connect_timeout=10,
                )
                self.cursor = self.connection.cursor()

            elif db_type == "PostgreSQL":
                self.connection = psycopg2.connect(
                    host=host if host else "localhost",
                    port=port if port else "5432",
                    user=user,
                    password=password,
                    dbname=dbname if dbname else "postgres",
                    connect_timeout=10,
                )
                self.cursor = self.connection.cursor()

            # Atrapa cualquier variación de texto de Mongo ("MongoDB (URI)", etc.)
            elif "MongoDB" in db_type:
                if not host.startswith("mongodb"):
                    raise ValueError(
                        "La URI debe comenzar con 'mongodb://' o 'mongodb+srv://'"
                    )

                uri = host
                # Colapsa prefijos repetidos: mongodb+srv://mongodb+srv://... -> mongodb+srv://...
                uri = re.sub(
                    r"^(mongodb(?:\+srv)?://)(?:mongodb(?:\+srv)?://)+", r"\1", uri
                )

                # quote_plus evita que caracteres como @ / : rompan la URI
                if password and "<db_password>" in uri:
                    uri = uri.replace("<db_password>", quote_plus(password))

                self.connection = MongoClient(uri, serverSelectionTimeoutMS=5000)
                self.connection.server_info()  # Valida la conexión con un ping

                db_name_to_use = dbname if dbname else "test"
                self.cursor = self.connection[db_name_to_use]

            else:
                # Si no reconoce el motor, falla explícitamente.
                raise ValueError(
                    f"Motor de base de datos no soportado o nombre incorrecto: {db_type}"
                )

            return True

        except pymysql.err.OperationalError as e:
            self._reset()
            raise Exception(
                f"Error MySQL: Verifica que el servidor (XAMPP/Local) esté encendido. Detalle: {e}"
            )
        except psycopg2.OperationalError as e:
            self._reset()
            raise Exception(
                f"Error PostgreSQL: Verifique credenciales o servicio. Detalle: {e}"
            )
        except Exception as e:
            self._reset()
            raise Exception(f"Fallo de conexión en {db_type}: {str(e)}")

    def close(self):
        if self.connection is not None:
            try:
                if self.db_type and "MongoDB" in self.db_type:
                    self.connection.close()
                else:
                    if self.cursor is not None:
                        self.cursor.close()
                    self.connection.close()
            finally:
                self.connection = None
                self.cursor = None