# app_desktop.py
import os
import sys

# Si la aplicación se ejecuta compilada con PyInstaller (.exe), fijar directorio base
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
    os.chdir(base_dir)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

from src.gui_app import VARInterface

def init_directories():
    """Inicializa la estructura de directorios requerida según Estructura.txt"""
    curr_base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    directories = [
        os.path.join(curr_base, "models"),
        os.path.join(curr_base, "data", "raw_videos"),
        os.path.join(curr_base, "data", "escudos"),
        os.path.join(curr_base, "data", "reportes")
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def main():
    print("==========================================================")
    print("   Plataforma MatchVision VAR (FIFA / LaLiga Standard)    ")
    print("==========================================================")
    init_directories()
    print("✅ Estructura de carpetas verificada (models/, data/raw_videos, data/reportes).")
    print("🚀 Cargando arquitectura modular e interfaz gráfica...")
    app = VARInterface()
    app.mainloop()

if __name__ == "__main__":
    main()