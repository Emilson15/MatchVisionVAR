# build_exe.py
"""
Script de compilacion automatizada para MatchVision VAR.
Compila el ejecutable independiente (.exe) usando PyInstaller y empaqueta
los modelos de IA, escudos de ligas y videos de prueba.
"""
import os
import shutil
import subprocess
import sys

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist", "MatchVision_VAR")
    spec_file = os.path.join(base_dir, "MatchVision_VAR.spec")
    exe_file = os.path.join(dist_dir, "MatchVision_VAR.exe")

    print("==========================================================")
    print("   Compilando MatchVision VAR a Ejecutable Independiente  ")
    print("==========================================================")

    force_rebuild = "--rebuild" in sys.argv
    if force_rebuild or not os.path.exists(exe_file):
        # 1. Ejecutar PyInstaller con el archivo .spec
        pyinstaller_cmd = [
            sys.executable,
            "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            spec_file
        ]

        print("\n[1/3] Ejecutando PyInstaller...")
        ret = subprocess.run(pyinstaller_cmd, cwd=base_dir)
        if ret.returncode != 0:
            print("\n[ERROR] Hubo un error durante la compilacion con PyInstaller.")
            sys.exit(ret.returncode)

        print("\n[OK] Compilacion base completada.")
    else:
        print(f"\n[1/3] Ejecutable base ya compilado encontrado en:\n  {exe_file}")

    # 2. Copiar carpetas esenciales a dist/MatchVision_VAR/
    print("\n[2/3] Copiando modelos de IA, datos y recursos al paquete...")
    
    # Copiar models/
    src_models = os.path.join(base_dir, "models")
    dst_models = os.path.join(dist_dir, "models")
    if os.path.exists(src_models):
        shutil.copytree(src_models, dst_models, dirs_exist_ok=True)
        print("  -> Carpeta 'models/' copiada.")

    # Copiar data/ (escudos y raw_videos)
    src_escudos = os.path.join(base_dir, "data", "escudos")
    dst_escudos = os.path.join(dist_dir, "data", "escudos")
    if os.path.exists(src_escudos):
        # Excluir dataset_ligas backup para no inflar el tamaño
        shutil.copytree(
            src_escudos, 
            dst_escudos, 
            ignore=shutil.ignore_patterns("dataset_ligas"),
            dirs_exist_ok=True
        )
        print("  -> Base de datos de escudos y ligas copiada.")

    # Inicializar carpeta data/raw_videos vacia para que el usuario ponga sus videos
    dst_videos = os.path.join(dist_dir, "data", "raw_videos")
    os.makedirs(dst_videos, exist_ok=True)
    print("  -> Carpeta 'data/raw_videos/' inicializada (sin videos de prueba pesados).")

    # Crear carpeta de reportes vacia
    dst_reports = os.path.join(dist_dir, "data", "reportes")
    os.makedirs(dst_reports, exist_ok=True)
    print("  -> Carpeta de reportes inicializada.")

    print("\n[3/3] Paquete ejecutable listo en:")
    print(f"  Carpeta: {dist_dir}")
    print(f"  Ejecutable: {exe_file}")
    print("\n==========================================================")
    print("   Compilacion exitosa de MatchVision VAR!               ")
    print("==========================================================")

if __name__ == "__main__":
    main()
