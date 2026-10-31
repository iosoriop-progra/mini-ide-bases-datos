import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import sqlite3
import json
import db_connector
from db_connector import DatabaseConnector


class MiniIDEDatabase(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mini IDE - Database Manager")
        self.geometry("1100x700")

        self.colors = {
            "bg_main": "#1e1e1e",
            "bg_panel": "#252526",
            "accent": "#007acc",
            "text_light": "#d4d4d4",
            "text_dark": "#ffffff",
            "border": "#333333",
        }

        self.configure(bg=self.colors["bg_main"])
        self._setup_styles()
        self._build_ui()

        self.current_connection = None
        self.current_cursor = None
        self.db_manager = DatabaseConnector()

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=self.colors["bg_main"])
        style.configure("Panel.TFrame", background=self.colors["bg_panel"])
        style.configure("TLabel", background=self.colors["bg_panel"], foreground=self.colors["text_light"], font=("Segoe UI", 9))
        style.configure("TButton", background=self.colors["accent"], foreground=self.colors["text_dark"], borderwidth=0, font=("Segoe UI", 9, "bold"))
        style.map("TButton", background=[("active", "#005f9e")])
        style.configure("TNotebook", background=self.colors["bg_main"], borderwidth=0)
        style.configure("TNotebook.Tab", background=self.colors["bg_panel"], foreground=self.colors["text_light"], padding=[10, 5], font=("Segoe UI", 9))
        style.map("TNotebook.Tab", background=[("selected", self.colors["accent"])], foreground=[("selected", self.colors["text_dark"])])
        style.configure("Treeview", background=self.colors["bg_main"], foreground=self.colors["text_light"], fieldbackground=self.colors["bg_main"], rowheight=25)
        style.configure("Treeview.Heading", background=self.colors["bg_panel"], foreground=self.colors["text_light"], font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        conn_frame = ttk.Frame(main_paned, style="Panel.TFrame", width=250)
        main_paned.add(conn_frame, weight=0)

        ttk.Label(conn_frame, text="Configuración de Conexión", font=("Segoe UI", 10, "bold")).pack(pady=(10, 15), padx=10, anchor="w")
        ttk.Label(conn_frame, text="Tipo (SQL/NoSQL):").pack(padx=10, anchor="w")

        self.db_type_var = tk.StringVar(value="MySQL")
        db_combo = ttk.Combobox(conn_frame, textvariable=self.db_type_var, values=["MySQL", "PostgreSQL", "SQLite", "MongoDB (URI)"], state="readonly")
        db_combo.pack(fill=tk.X, padx=10, pady=(0, 10))
        db_combo.bind("<<ComboboxSelected>>", self._toggle_connection_fields)

        self.conn_entries = {}
        self.field_widgets = {}
        fields = [("Host / URI:", "host"), ("Puerto:", "port"), ("Usuario:", "user"), ("Contraseña:", "password"), ("Base de Datos:", "dbname")]

        for label_text, key in fields:
            lbl = ttk.Label(conn_frame, text=label_text)
            entry = ttk.Entry(conn_frame, show="*" if key == "password" else "")
            self.conn_entries[key] = entry
            self.field_widgets[key] = (lbl, entry)

        btn_frame = ttk.Frame(conn_frame, style="Panel.TFrame")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Probar Conexión", command=self.test_connection).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Conectar", command=self.connect_db).pack(fill=tk.X, pady=2)

        right_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(right_paned, weight=1)

        editor_frame = ttk.Frame(right_paned, style="Panel.TFrame")
        right_paned.add(editor_frame, weight=1)

        editor_header = ttk.Frame(editor_frame, style="Panel.TFrame")
        editor_header.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(editor_header, text="Consola de Comandos", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        ttk.Button(editor_header, text="Ejecutar (Ctrl+Enter)", command=self.execute_query).pack(side=tk.RIGHT)

        self.editor = scrolledtext.ScrolledText(editor_frame, bg=self.colors["bg_main"], fg=self.colors["text_light"], insertbackground=self.colors["text_light"], font=("Consolas", 11), borderwidth=0)
        self.editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        self.editor.bind("<Control-Return>", lambda event: self.execute_query())

        notebook_frame = ttk.Frame(right_paned)
        right_paned.add(notebook_frame, weight=1)
        self.notebook = ttk.Notebook(notebook_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_results = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.notebook.add(self.tab_results, text="Resultados")
        self.tree = ttk.Treeview(self.tab_results, show="headings")
        vsb = ttk.Scrollbar(self.tab_results, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.tab_results, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.tab_messages = ttk.Frame(self.notebook, style="Panel.TFrame")
        self.notebook.add(self.tab_messages, text="Mensajes")
        self.msg_console = scrolledtext.ScrolledText(self.tab_messages, bg=self.colors["bg_main"], fg=self.colors["text_light"], font=("Consolas", 10), borderwidth=0, state=tk.DISABLED)
        self.msg_console.pack(fill=tk.BOTH, expand=True)

        self._toggle_connection_fields()

    def _toggle_connection_fields(self, event=None):
        db_type = self.db_type_var.get()

        for key, (lbl, entry) in self.field_widgets.items():
            lbl.pack_forget()
            entry.pack_forget()

        if db_type == "SQLite":
            visible_fields = ["dbname"]
            self.field_widgets["dbname"][0].config(text="Archivo DB (.db) o :memory:")
        elif "MongoDB" in db_type:
            visible_fields = ["host", "password", "dbname"]
            self.field_widgets["host"][0].config(text="URI Completa (mongodb+srv://):")
            self.field_widgets["password"][0].config(text="Contraseña (si usaste <db_password>):")
            self.field_widgets["dbname"][0].config(text="Base de Datos (opcional):")
        else:
            visible_fields = ["host", "port", "user", "password", "dbname"]
            self.field_widgets["host"][0].config(text="Host / IP:")
            self.field_widgets["dbname"][0].config(text="Base de Datos (opcional):")
            self.field_widgets["password"][0].config(text="Contraseña:")

        for key in visible_fields:
            lbl, entry = self.field_widgets[key]
            lbl.pack(padx=10, anchor="w")
            entry.pack(fill=tk.X, padx=10, pady=(0, 10))

    def log_message(self, message, is_error=False, force_tab=True):
        self.msg_console.config(state=tk.NORMAL)
        prefix = "[ERROR] " if is_error else "[INFO] "
        self.msg_console.insert(tk.END, prefix + message + "\n")
        self.msg_console.see(tk.END)
        self.msg_console.config(state=tk.DISABLED)

        if force_tab or is_error:
            self.notebook.select(self.tab_messages)
        self.update_idletasks()  # Fuerza la actualización visual inmediata

    def _get_connection_params(self):
        return {
            "db_type": self.db_type_var.get(),
            "host": self.conn_entries["host"].get(),
            "port": self.conn_entries["port"].get(),
            "user": self.conn_entries["user"].get(),
            "password": self.conn_entries["password"].get(),
            "dbname": self.conn_entries["dbname"].get(),
        }

    def test_connection(self):
        params = self._get_connection_params()
        temp_manager = DatabaseConnector()
        try:
            self.log_message(f"Probando conexión a {params['db_type']}...", force_tab=True)
            temp_manager.connect(**params)
            temp_manager.close()
            self.log_message("Conexión de prueba exitosa.")
            messagebox.showinfo("Éxito", "Prueba de conexión exitosa.")
        except Exception as e:
            self.log_message(str(e), is_error=True)
            messagebox.showerror("Error de Conexión", str(e))

    def connect_db(self):
        params = self._get_connection_params()

        # Limpia cualquier conexión anterior para no ejecutar sobre una cerrada
        self.current_connection = None
        self.current_cursor = None

        try:
            self.log_message(f"Iniciando conexión a {params['db_type']}...", force_tab=True)
            self.db_manager.close()
            self.db_manager.connect(**params)

            # Candado estricto para evitar falsos positivos
            if self.db_manager.connection is None:
                raise Exception(
                    "Error interno: El conector falló en silencio. "
                    f"Archivo cargado: {db_connector.__file__}"
                )

            self.current_connection = self.db_manager.connection
            self.current_cursor = self.db_manager.cursor
            self.log_message(f"Conectado exitosamente a {params['db_type']}.")
        except Exception as e:
            self.log_message(str(e), is_error=True)

    def execute_query(self, event=None):
        if self.current_connection is None or self.current_cursor is None:
            self.log_message("No hay ninguna conexión activa. Haz clic en 'Conectar' primero.", is_error=True)
            return "break"

        query = self.editor.get("1.0", tk.END).strip()
        if not query:
            
            return "break"

        try:
            # === MONGODB ===
            if "MongoDB" in self.db_manager.db_type:
                db = self.current_cursor

                if query.startswith("db.") and ".find(" in query:
                    partes = query.replace("db.", "").split(".find(")
                    coleccion = partes[0]
                    filtro_str = partes[1].rstrip(")").strip()

                    try:
                        filtro = json.loads(filtro_str) if filtro_str else {}
                    except json.JSONDecodeError:
                        raise Exception("El filtro dentro de .find() debe ser un formato JSON válido (usa comillas dobles).")

                    documentos = list(db[coleccion].find(filtro).limit(100))

                    if not documentos:
                        self.log_message(f"Sin resultados en la colección '{coleccion}'.")
                        self.tree.delete(*self.tree.get_children())
                        return "break"

                    columnas = list(documentos[0].keys())
                    self.tree.delete(*self.tree.get_children())
                    self.tree["columns"] = columnas

                    for col in columnas:
                        self.tree.heading(col, text=col)
                        self.tree.column(col, width=120, anchor=tk.W)

                    for doc in documentos:
                        valores = [str(doc.get(col, "")) for col in columnas]
                        self.tree.insert("", tk.END, values=valores)

                    self.notebook.select(self.tab_results)
                    self.log_message(f"{len(documentos)} documentos obtenidos.", force_tab=False)

                elif query.startswith("db.") and ".insert(" in query:
                    partes = query.replace("db.", "").split(".insert(")
                    coleccion = partes[0]
                    doc_str = partes[1].rstrip(")").strip()

                    try:
                        documento = json.loads(doc_str)
                    except json.JSONDecodeError:
                        raise Exception("El documento dentro de .insert() debe ser un JSON válido (con comillas dobles en las claves).")

                    res = db[coleccion].insert_one(documento)
                    self.log_message(f"Documento insertado en '{coleccion}'. ID generado: {res.inserted_id}")
                else:
                    raise Exception("Comando NoSQL no soportado. Usa: db.coleccion.find() o db.coleccion.insert({...})")

            # === MYSQL / POSTGRESQL / SQLITE ===
            else:
                self.current_cursor.execute(query)
                query_upper = query.upper()

                es_lectura = any(query_upper.startswith(cmd) for cmd in ["SELECT", "SHOW", "DESCRIBE", "PRAGMA"])

                if es_lectura:
                    rows = self.current_cursor.fetchmany(100)
                    columns = [desc[0] for desc in self.current_cursor.description] if self.current_cursor.description else []

                    self.tree.delete(*self.tree.get_children())
                    self.tree["columns"] = columns

                    for col in columns:
                        self.tree.heading(col, text=col)
                        self.tree.column(col, width=100, anchor=tk.W)

                    for row in rows:
                        self.tree.insert("", tk.END, values=row)

                    self.notebook.select(self.tab_results)
                    self.log_message(f"Consulta ejecutada. {len(rows)} filas obtenidas.", force_tab=False)
                else:
                    self.current_connection.commit()
                    self.log_message(f"Comando ejecutado exitosamente. Filas afectadas: {self.current_cursor.rowcount}")

        except sqlite3.OperationalError as e:
            self.log_message(f"Error SQL: {e}", is_error=True)
        except Exception as e:
            self.log_message(f"Error: {str(e)}", is_error=True)

        return "break"


if __name__ == "__main__":
    app = MiniIDEDatabase()
    app.mainloop()
