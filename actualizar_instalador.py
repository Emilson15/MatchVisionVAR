# actualizar_instalador.py
"""
Script todo-en-uno para actualizar el instalador oficial 'Instalador_MatchVision_VAR.exe'.
1. Recompila el codigo Python a ejecutable con PyInstaller.
2. Empaqueta modelos y escudos (sin videos pesados).
3. Compila con Inno Setup en un unico Instalador_MatchVision_VAR.exe.
4. Limpia carpetas intermedias (build/, dist/, installer_output/).
"""
import os
import shutil
import subprocess
import sys

def find_iscc():
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # Buscar en PATH
    which = shutil.which("iscc")
    if which:
        return which
    return None

def clean_dir(d):
    import stat
    def remove_readonly(func, path, excinfo):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass
    if os.path.exists(d):
        for _ in range(5):
            try:
                shutil.rmtree(d, onerror=remove_readonly)
                break
            except Exception:
                import time
                time.sleep(0.5)

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist", "MatchVision_VAR")
    spec_file = os.path.join(base_dir, "MatchVision_VAR.spec")
    iss_file = os.path.join(base_dir, "installer_setup.iss")
    output_dir = os.path.join(base_dir, "installer_output")
    final_installer = os.path.join(base_dir, "Instalador_MatchVision_VAR.exe")

    print("==========================================================")
    print("      ACTUALIZADOR OFICIAL DE INSTALADOR MATCHVISION      ")
    print("==========================================================")

    # 1. Verificar ISCC (Inno Setup)
    iscc_path = find_iscc()
    if not iscc_path:
        print("\n[ERROR] No se encontro Inno Setup Compiler (ISCC.exe).")
        print("Instalalo desde https://jrsoftware.org/isdl.php o con: winget install JRSoftware.InnoSetup")
        sys.exit(1)
    print(f"\n[OK] Compilador Inno Setup detectado en:\n  {iscc_path}")

    # Limpieza previa para evitar bloqueos de OneDrive o Windows
    clean_dir(os.path.join(base_dir, "build"))
    clean_dir(os.path.join(base_dir, "dist"))
    clean_dir(output_dir)

    # 2. Ejecutar PyInstaller con el archivo .spec
    print("\n[Paso 1/4] Recompilando aplicacion con PyInstaller...")
    pyinstaller_cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        spec_file
    ]
    ret = subprocess.run(pyinstaller_cmd, cwd=base_dir)
    if ret.returncode != 0:
        print("\n[ERROR] Fallo la compilacion con PyInstaller.")
        sys.exit(ret.returncode)

    # 3. Copiar recursos esenciales (models/ y data/escudos/ sin videos pesados)
    print("\n[Paso 2/4] Copiando modelos de IA y escudos al paquete...")
    src_models = os.path.join(base_dir, "models")
    dst_models = os.path.join(dist_dir, "models")
    if os.path.exists(src_models):
        shutil.copytree(src_models, dst_models, dirs_exist_ok=True)
        print("  -> Modelos copiados.")

    src_escudos = os.path.join(base_dir, "data", "escudos")
    dst_escudos = os.path.join(dist_dir, "data", "escudos")
    if os.path.exists(src_escudos):
        shutil.copytree(src_escudos, dst_escudos, dirs_exist_ok=True)
        print("  -> Base de datos de escudos y ligas copiada.")

    src_zip = os.path.join(base_dir, "data", "dataset_ligas.zip")
    dst_zip = os.path.join(dist_dir, "data", "dataset_ligas.zip")
    if os.path.exists(src_zip):
        shutil.copy2(src_zip, dst_zip)
        print("  -> Respaldo dataset_ligas.zip copiado.")

    # Inicializar carpetas vacias de videos y reportes
    os.makedirs(os.path.join(dist_dir, "data", "raw_videos"), exist_ok=True)
    os.makedirs(os.path.join(dist_dir, "data", "reportes"), exist_ok=True)

    # Copiar archivos de logo del sistema
    for f in ["logo.png", "logo.ico"]:
        src_f = os.path.join(base_dir, f)
        if os.path.exists(src_f):
            shutil.copy2(src_f, os.path.join(dist_dir, f))
    print("  -> Logos del sistema copiados.")

    # 4. Generar el instalador con Inno Setup
    print("\n[Paso 3/4] Generando archivo unico 'Instalador_MatchVision_VAR.exe'...")
    iscc_cmd = [iscc_path, iss_file]
    ret_iscc = subprocess.run(iscc_cmd, cwd=base_dir)
    if ret_iscc.returncode != 0:
        print("\n[ERROR] Fallo la generacion del instalador con Inno Setup.")
        sys.exit(ret_iscc.returncode)

    # 5. Mover instalador a la raiz y limpiar carpetas intermedias
    print("\n[Paso 4/4] Limpiando carpetas temporales...")
    generated_setup = os.path.join(output_dir, "Setup_MatchVision_VAR_v1.0.exe")
    if os.path.exists(generated_setup):
        if os.path.exists(final_installer):
            try:
                os.remove(final_installer)
            except Exception:
                pass
        shutil.move(generated_setup, final_installer)

    # Limpiar temporales
    for folder in [os.path.join(base_dir, "build"), os.path.join(base_dir, "dist"), output_dir]:
        clean_dir(folder)

    print("\n==========================================================")
    print("   INSTALADOR ACTUALIZADO CON EXITO!                      ")
    print(f"   Archivo final: {final_installer}")
    print("==========================================================")

if __name__ == "__main__":
    main()
