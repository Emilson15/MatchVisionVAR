# src/database.py
import pandas as pd
import os
import sys
import json
import zipfile
from datetime import datetime

class MatchDatabase:
    def __init__(self):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.abspath(os.path.join(base_dir, "data"))
        self.escudos_dir = os.path.join(self.data_dir, "escudos")
        self.reports_dir = os.path.join(self.data_dir, "reportes")
        self.zip_path = os.path.join(self.data_dir, "dataset_ligas.zip")
        self.db_file = os.path.join(self.escudos_dir, "leagues_db.json")
        
        os.makedirs(self.reports_dir, exist_ok=True)
        self.excel_path = os.path.join(self.reports_dir, "VAR_Reports.xlsx")
        self.leagues_db = {}
        
        self._load_offline_database()

    def _load_offline_database(self):
        if not os.path.exists(self.escudos_dir) or not os.listdir(self.escudos_dir):
            print("Instalando base de datos offline desde dataset_ligas.zip...")
            if os.path.exists(self.zip_path):
                with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.escudos_dir)
                print("Extracción de escudos completada.")
            else:
                print(f"ADVERTENCIA: No se encontró {self.zip_path} en la carpeta data/.")
                os.makedirs(self.escudos_dir, exist_ok=True)
                return

        self.leagues_db = {}
        valid_img_exts = ('.png', '.webp', '.jpg', '.jpeg', '.avif', '.bmp')
        
        # 1. Prioridad: Buscar ligas directamente en data/escudos/
        direct_leagues = [
            d for d in os.listdir(self.escudos_dir) 
            if os.path.isdir(os.path.join(self.escudos_dir, d)) and d not in ("dataset_ligas", "__pycache__")
        ]
        
        if direct_leagues:
            for league_name in direct_leagues:
                league_path = os.path.join(self.escudos_dir, league_name)
                self.leagues_db[league_name] = {"teams": {}, "logo": None}
                
                for item in sorted(os.listdir(league_path)):
                    item_path = os.path.join(league_path, item)
                    
                    if os.path.isdir(item_path):
                        team_name = item
                        img_files = [f for f in os.listdir(item_path) if f.lower().endswith(valid_img_exts)]
                        img_files.sort(key=lambda x: 0 if x.lower().endswith(('.png', '.webp', '.jpg')) else 1)
                        if img_files:
                            self.leagues_db[league_name]["teams"][team_name] = os.path.abspath(os.path.join(item_path, img_files[0]))
                    elif os.path.isfile(item_path) and item.lower().endswith(valid_img_exts):
                        self.leagues_db[league_name]["logo"] = os.path.abspath(item_path)
        else:
            # 2. Respaldo: Buscar en la estructura extraída de dataset_ligas
            base_path = os.path.join(self.escudos_dir, "dataset_ligas", "Ligas de futbol")
            if not os.path.exists(base_path):
                base_path = self.escudos_dir
            if os.path.exists(base_path):
                for league_folder in os.listdir(base_path):
                    league_path = os.path.join(base_path, league_folder)
                    if os.path.isdir(league_path) and league_folder not in ("dataset_ligas", "__pycache__"):
                        self.leagues_db[league_folder] = {"teams": {}, "logo": None}
                        for item in os.listdir(league_path):
                            item_path = os.path.join(league_path, item)
                            if os.path.isdir(item_path):
                                team_name = item
                                img_files = [f for f in os.listdir(item_path) if f.lower().endswith(valid_img_exts)]
                                img_files.sort(key=lambda x: 0 if x.lower().endswith(('.png', '.webp', '.jpg')) else 1)
                                if img_files:
                                    self.leagues_db[league_folder]["teams"][team_name] = os.path.abspath(os.path.join(item_path, img_files[0]))
                            elif os.path.isfile(item_path) and item.lower().endswith(valid_img_exts):
                                self.leagues_db[league_folder]["logo"] = os.path.abspath(item_path)

        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.leagues_db, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # En entornos restringidos como C:\Program Files, no bloquear si falla la escritura en disco
            print(f"[AVISO] No se pudo guardar cache leagues_db.json en disco ({e}). Base de datos en memoria lista.")

    def import_leagues_from_zip(self, zip_filepath):
        """
        Importa ligas y equipos desde un archivo ZIP seleccionado por el usuario.
        Soporta estructuras directas o anidadas (ej. Ligas de futbol/).
        """
        if not os.path.exists(zip_filepath):
            return False, "El archivo ZIP seleccionado no existe."
            
        import shutil
        import tempfile

        temp_dir = tempfile.mkdtemp(prefix="mv_import_")
        valid_img_exts = ('.png', '.webp', '.jpg', '.jpeg', '.avif', '.bmp')
        imported_count = 0

        try:
            with zipfile.ZipFile(zip_filepath, 'r') as z:
                z.extractall(temp_dir)

            # Buscar carpetas de ligas dentro del ZIP
            league_dirs = []
            for root, dirs, files in os.walk(temp_dir):
                folder_name = os.path.basename(root)
                if folder_name.lower() in ("ligas de futbol", "ligas"):
                    for d in dirs:
                        league_dirs.append(os.path.join(root, d))
                    break

            if not league_dirs:
                for item in os.listdir(temp_dir):
                    item_path = os.path.join(temp_dir, item)
                    if os.path.isdir(item_path) and item not in ("__pycache__", "dataset_ligas"):
                        subdirs = [sd for sd in os.listdir(item_path) if os.path.isdir(os.path.join(item_path, sd))]
                        if subdirs:
                            league_dirs.append(item_path)

            if not league_dirs:
                return False, "No se detectaron carpetas de ligas válidas dentro del archivo ZIP."

            try:
                os.makedirs(self.escudos_dir, exist_ok=True)
            except Exception:
                pass

            for ldir in league_dirs:
                orig_name = os.path.basename(ldir)
                clean_name = orig_name
                if "espa" in orig_name.lower():
                    clean_name = "LaLiga"
                elif "seria" in orig_name.lower() or "serie a" in orig_name.lower():
                    clean_name = "Serie A"
                elif "premier" in orig_name.lower():
                    clean_name = "Premier League"
                elif "bundesliga" in orig_name.lower():
                    clean_name = "Bundesliga"
                elif "ligue 1" in orig_name.lower() or "ligue1" in orig_name.lower():
                    clean_name = "Ligue 1"

                dest_league_dir = os.path.join(self.escudos_dir, clean_name)
                os.makedirs(dest_league_dir, exist_ok=True)

                for subitem in os.listdir(ldir):
                    s_path = os.path.join(ldir, subitem)
                    clean_subitem = subitem
                    if "m" in subitem.lower() and "naco" in subitem.lower():
                        clean_subitem = "AS Monaco"
                    elif "par" in subitem.lower() and "germain" in subitem.lower():
                        clean_subitem = "Paris Saint-Germain (PSG)"
                    elif subitem.lower() == "milan":
                        clean_subitem = "AC Milan"
                    elif "unite" in subitem.lower():
                        clean_subitem = "Manchester United"
                    elif "atletico" in subitem.lower() or "altletico" in subitem.lower():
                        clean_subitem = "Atletico de Madrid"
                    elif "bayern" in subitem.lower():
                        clean_subitem = "Bayern Munich"
                    elif "leverkusen" in subitem.lower():
                        clean_subitem = "Bayer Leverkusen"
                    elif "dortmund" in subitem.lower():
                        clean_subitem = "Borussia Dortmund"

                    d_path = os.path.join(dest_league_dir, clean_subitem)

                    if os.path.isdir(s_path):
                        shutil.copytree(s_path, d_path, dirs_exist_ok=True)
                    elif os.path.isfile(s_path):
                        if len(subitem) < 120 and subitem.lower().endswith(valid_img_exts):
                            shutil.copy2(s_path, d_path)

                imported_count += 1

            # Recargar base de datos con los nuevos escudos
            self._load_offline_database()

            return True, f"¡Éxito! Se importaron {imported_count} ligas a la base de datos."
        except PermissionError:
            return False, "Permiso denegado al escribir en la carpeta de escudos. Ejecute como Administrador o reinstale la aplicación."
        except Exception as e:
            return False, f"Error durante la importación: {e}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def get_leagues(self):
        if not self.leagues_db: return ["Seleccionar Liga..."]
        return ["Seleccionar Liga..."] + sorted(list(self.leagues_db.keys()))

    def get_league_logo(self, league_name):
        """Devuelve la ruta absoluta del escudo oficial de la Liga"""
        if league_name in self.leagues_db:
            logo = self.leagues_db[league_name].get("logo")
            if logo and os.path.exists(logo):
                return logo
            # Respaldo de búsqueda en la carpeta de la liga
            lpath = os.path.join(self.escudos_dir, league_name)
            if os.path.isdir(lpath):
                valid_img_exts = ('.png', '.webp', '.jpg', '.jpeg', '.avif', '.bmp')
                for f in sorted(os.listdir(lpath)):
                    fp = os.path.join(lpath, f)
                    if os.path.isfile(fp) and f.lower().endswith(valid_img_exts):
                        return os.path.abspath(fp)
        return None

    def get_teams_by_league(self, league_name):
        if league_name in self.leagues_db:
            teams = self.leagues_db[league_name].get("teams", {})
            return ["Seleccionar Equipo..."] + sorted(list(teams.keys()))
        return ["Seleccionar Equipo..."]

    def get_crest_path(self, league_name, team_name):
        if league_name in self.leagues_db:
            teams = self.leagues_db[league_name].get("teams", {})
            crest = teams.get(team_name)
            if crest and os.path.exists(crest):
                return crest
            # Respaldo de búsqueda en la carpeta del equipo
            tpath = os.path.join(self.escudos_dir, league_name, team_name)
            if os.path.isdir(tpath):
                valid_img_exts = ('.png', '.webp', '.jpg', '.jpeg', '.avif', '.bmp')
                for f in sorted(os.listdir(tpath)):
                    fp = os.path.join(tpath, f)
                    if os.path.isfile(fp) and f.lower().endswith(valid_img_exts):
                        return os.path.abspath(fp)
        return None

    def log_event(self, match_id, event_type, minute_str, clip_path, details=""):
        new_data = pd.DataFrame([{
            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Partido": match_id,
            "Decisión VAR": event_type,
            "Minuto": minute_str,
            "Detalles Tácticos / SAOT": details,
            "Ruta Clip Video": clip_path
        }])

        if os.path.exists(self.excel_path):
            try:
                df = pd.read_excel(self.excel_path)
                df = pd.concat([df, new_data], ignore_index=True)
            except Exception:
                df = new_data
        else:
            df = new_data
            
        try:
            df.to_excel(self.excel_path, index=False)
        except Exception:
            # Respaldo si Program Files restringe la escritura del Excel
            alt_dir = os.path.join(os.path.expanduser("~"), "Documents", "MatchVision_VAR_Reports")
            try:
                os.makedirs(alt_dir, exist_ok=True)
                alt_excel = os.path.join(alt_dir, "VAR_Reports.xlsx")
                if os.path.exists(alt_excel):
                    old_df = pd.read_excel(alt_excel)
                    df = pd.concat([old_df, new_data], ignore_index=True)
                df.to_excel(alt_excel, index=False)
            except Exception:
                pass