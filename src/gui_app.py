# src/gui_app.py
import sys
import customtkinter as ctk
from tkinter import Canvas, colorchooser, messagebox, filedialog
import glob
import os
import shutil
import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageTk

from src.database import MatchDatabase
from src.style import CSS
from src.rules_engine import VARPhysicsEngine
from src.team_classifier import TeamClassifier

# Carga y gestión de modelos YOLO desde la carpeta models/ (Estructura estándar del proyecto)
YOLO_AVAILABLE = False
yolo_model = None

try:
    from ultralytics import YOLO
    if getattr(sys, 'frozen', False):
        models_dir = os.path.join(os.path.dirname(sys.executable), "models")
    else:
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
    os.makedirs(models_dir, exist_ok=True)
    
    # Buscar el primer modelo .pt disponible en models/, priorizando yolov8n.pt
    model_path = os.path.join(models_dir, "yolov8n.pt")
    if not os.path.exists(model_path):
        pt_files = [f for f in os.listdir(models_dir) if f.endswith(".pt")]
        if pt_files:
            model_path = os.path.join(models_dir, pt_files[0])
            
    print(f"Cargando modelo YOLO desde: {model_path}")
    yolo_model = YOLO(model_path)
    YOLO_AVAILABLE = True
    print("✅ Modelo YOLO cargado exitosamente.")
except Exception as e:
    print(f"Aviso YOLO: No se pudo cargar el modelo YOLO desde la carpeta models/ ({e}). Se usará detector clásico por visión de computadora.")
    yolo_model = None

ctk.set_appearance_mode("dark")

class VARInterface(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MatchVision VAR - Plataforma Profesional de Asistencia Arbitral (FIFA / LaLiga Standard)")
        self.geometry("1280x760")
        self.configure(fg_color=CSS["bg_dark"])

        # Rutas del logo oficial del sistema (favicon/barra de tareas y cabeceras)
        self.app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.logo_ico_path = os.path.join(self.app_dir, "logo.ico")
        self.logo_png_path = os.path.join(self.app_dir, "logo.png")

        # Configurar icono en la barra de título y barra de tareas de Windows
        if os.path.exists(self.logo_ico_path):
            try:
                self.iconbitmap(self.logo_ico_path)
            except Exception as e:
                print(f"Aviso iconbitmap: {e}")
        elif os.path.exists(self.logo_png_path):
            try:
                self.iconphoto(False, ImageTk.PhotoImage(file=self.logo_png_path))
            except Exception as e:
                print(f"Aviso iconphoto: {e}")
        
        self.db = MatchDatabase()
        self.selected_league = None
        self.selected_video = None
        
        # Configuración por defecto de indumentaria y equipo defensor
        self.match_config = {
            "t0_c1": (255, 255, 255), "t0_c2": (200, 200, 200), "t0_gk": (50, 200, 50),
            "t1_c1": (80, 30, 50),    "t1_c2": (150, 40, 40),   "t1_gk": (30, 255, 255),
            "defending_team": 1, "defending_side": "Right"
        }
        
        self.container = ctk.CTkFrame(self, fg_color=CSS["bg_dark"], corner_radius=0)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        
        self.frames = {}
        for F in (LeagueSelectionPage, SetupPage, VideoSelectionPage, VARReviewPage):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            
        self.show_frame("LeagueSelectionPage")

    def show_frame(self, page_name):
        if "VideoSelectionPage" in self.frames:
            self.frames["VideoSelectionPage"].stop_preview()
        if "VARReviewPage" in self.frames and page_name != "VARReviewPage":
            self.frames["VARReviewPage"].stop_video()
            
        frame = self.frames[page_name]
        if hasattr(frame, "on_show"):
            frame.on_show()
        frame.tkraise()

    def draw_shield(self, canvas, img_path, cw, ch):
        """Dibuja el escudo de liga/equipo manteniendo proporciones o coloca el ícono predeterminado."""
        canvas.delete("all")
        if img_path and os.path.exists(img_path):
            try:
                img = Image.open(img_path).convert("RGBA")
                img.thumbnail((cw, ch), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                canvas.create_image(cw/2, ch/2, anchor="center", image=photo)
                canvas.image = photo 
                return
            except Exception:
                pass
        
        # Escudo por defecto (según maqueta PDF)
        points = [cw/2 - 50, ch/2 - 60, cw/2 + 50, ch/2 - 60, 
                  cw/2 + 50, ch/2 + 40, cw/2, ch/2 + 80, cw/2 - 50, ch/2 + 40]
        canvas.create_polygon(points, fill=CSS["bg_neutral"], outline="#666666", width=2)
        canvas.create_text(cw/2, ch/2, text="?", font=("Arial", 50, "bold"), fill="white")


# --- PÁGINA 1: SELECCIÓN DE LIGA (PDF PÁGINA 1) ---
class LeagueSelectionPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=CSS["bg_dark"], corner_radius=0)
        self.controller = controller
        self.leagues = [l for l in controller.db.get_leagues() if l != "Seleccionar Liga..."]
        self.current_idx = 0
        # Encabezado con el Logo oficial de MatchVision VAR
        if os.path.exists(controller.logo_png_path):
            try:
                pil_logo = Image.open(controller.logo_png_path).convert("RGBA")
                aspect = pil_logo.width / pil_logo.height
                logo_h = 55
                logo_w = int(logo_h * aspect)
                self.logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(logo_w, logo_h))
                self.lbl_logo = ctk.CTkLabel(self, text="", image=self.logo_img)
                self.lbl_logo.pack(pady=(12, 2))
            except Exception:
                pass
                
        ctk.CTkLabel(self, text="SELECCIONE LA LIGA", font=CSS["font_title"], text_color=CSS["text_light"]).pack(pady=(6, 12))
        
        card = ctk.CTkFrame(self, fg_color=CSS["bg_card"], corner_radius=20, width=500, height=400)
        card.pack(pady=10)
        card.pack_propagate(False)
        
        self.lbl_league_name = ctk.CTkLabel(card, text="Nombre de la Liga", font=CSS["font_subtitle"], text_color=CSS["text_dark"])
        self.lbl_league_name.pack(pady=(30, 20))
        
        f_mid = ctk.CTkFrame(card, fg_color="transparent")
        f_mid.pack(expand=True)
        
        ctk.CTkButton(f_mid, text="<", font=("Arial", 45, "bold"), fg_color="transparent", text_color=CSS["text_dark"], hover_color="#e0e0e0", width=50, command=self.prev_league).pack(side="left", padx=15)
        
        self.canvas_crest = Canvas(f_mid, width=220, height=220, bg=CSS["bg_card"], highlightthickness=0)
        self.canvas_crest.pack(side="left", padx=10)
        self.controller.draw_shield(self.canvas_crest, None, 220, 220)
        
        ctk.CTkButton(f_mid, text=">", font=("Arial", 45, "bold"), fg_color="transparent", text_color=CSS["text_dark"], hover_color="#e0e0e0", width=50, command=self.next_league).pack(side="left", padx=15)
        
        f_actions = ctk.CTkFrame(self, fg_color="transparent")
        f_actions.pack(pady=25)

        self.btn_import_leagues = ctk.CTkButton(
            f_actions,
            text="+ Añadir Ligas (.zip)",
            font=CSS["font_normal"],
            fg_color=CSS["btn_3d"],
            text_color=CSS["text_light"],
            hover_color="#117a8b",
            corner_radius=25,
            command=self.import_leagues
        )
        self.btn_import_leagues.pack(side="left", padx=15, ipadx=20, ipady=6)

        btn_next = ctk.CTkButton(
            f_actions,
            text="SIGUIENTE",
            font=CSS["font_title"],
            fg_color=CSS["btn_success"],
            text_color=CSS["text_light"],
            hover_color="#0da64a",
            corner_radius=30,
            command=self.go_next
        )
        btn_next.pack(side="left", padx=15, ipadx=45, ipady=8)
        
        self.update_display()

    def import_leagues(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo ZIP con Ligas y Equipos",
            filetypes=[("Archivos ZIP", "*.zip"), ("Todos los archivos", "*.*")]
        )
        if file_path:
            success, msg = self.controller.db.import_leagues_from_zip(file_path)
            if success:
                messagebox.showinfo("Ligas Añadidas", msg)
                self.leagues = [l for l in self.controller.db.get_leagues() if l != "Seleccionar Liga..."]
                self.current_idx = 0
                self.update_display()
            else:
                messagebox.showerror("Error al Añadir Ligas", msg)

    def on_show(self):
        self.leagues = [l for l in self.controller.db.get_leagues() if l != "Seleccionar Liga..."]
        self.update_display()

    def update_display(self):
        if not self.leagues:
            self.lbl_league_name.configure(text="Sin Ligas (Importe un archivo ZIP)")
            self.controller.draw_shield(self.canvas_crest, None, 220, 220)
            return
        self.current_idx = max(0, min(self.current_idx, len(self.leagues) - 1))
        league_name = self.leagues[self.current_idx]
        self.lbl_league_name.configure(text=league_name)
        logo_path = self.controller.db.get_league_logo(league_name)
        self.controller.draw_shield(self.canvas_crest, logo_path, 220, 220)

    def prev_league(self):
        if not self.leagues: return
        self.current_idx = (self.current_idx - 1) % len(self.leagues)
        self.update_display()

    def next_league(self):
        if not self.leagues: return
        self.current_idx = (self.current_idx + 1) % len(self.leagues)
        self.update_display()

    def go_next(self):
        if self.leagues:
            self.controller.selected_league = self.leagues[self.current_idx]
            self.controller.show_frame("SetupPage")
        else:
            messagebox.showwarning("Atención", "Debe añadir o seleccionar una liga antes de continuar.")


# --- PÁGINA 2: CONFIGURACIÓN DE EQUIPOS (PDF PÁGINA 2) ---
class SetupPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=CSS["bg_dark"], corner_radius=0)
        self.controller = controller
        
        f_top = ctk.CTkFrame(self, fg_color="transparent")
        f_top.pack(side="top", fill="x", pady=(12, 4))
        
        ctk.CTkLabel(f_top, text="LOCAL", font=CSS["font_title"], text_color=CSS["text_light"]).pack(side="left", expand=True)

        if os.path.exists(controller.logo_png_path):
            try:
                pil_logo = Image.open(controller.logo_png_path).convert("RGBA")
                aspect = pil_logo.width / pil_logo.height
                logo_h = 44
                logo_w = int(logo_h * aspect)
                self.logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(logo_w, logo_h))
                self.lbl_logo = ctk.CTkLabel(f_top, text="", image=self.logo_img)
                self.lbl_logo.pack(side="left", padx=10)
            except Exception:
                pass

        ctk.CTkLabel(f_top, text="VISITANTE", font=CSS["font_title"], text_color=CSS["text_light"]).pack(side="right", expand=True)
        
        # BARRA INFERIOR CON BOTONES ATRÁS Y SIGUIENTE
        f_bottom = ctk.CTkFrame(self, fg_color="transparent")
        f_bottom.pack(side="bottom", pady=20)

        btn_back = ctk.CTkButton(f_bottom, text="ATRÁS", font=CSS["font_title"], fg_color=CSS["btn_neutral"], text_color=CSS["text_light"], hover_color="#333344", corner_radius=30, command=lambda: controller.show_frame("LeagueSelectionPage"))
        btn_back.pack(side="left", padx=15, ipadx=35, ipady=8)

        btn_next = ctk.CTkButton(f_bottom, text="SIGUIENTE", font=CSS["font_title"], fg_color=CSS["btn_success"], text_color=CSS["text_light"], hover_color="#0da64a", corner_radius=30, command=lambda: controller.show_frame("VideoSelectionPage"))
        btn_next.pack(side="left", padx=15, ipadx=45, ipady=8)

        # CONTENIDO CENTRAL (SELECCIÓN SIMPLIFICADA DE EQUIPOS Y ESCUDOS DE CADA LIGA)
        f_cards = ctk.CTkFrame(self, fg_color="transparent")
        f_cards.pack(expand=True, fill="both", padx=30, pady=10)
        
        # --- TARJETA LOCAL ---
        card_local = ctk.CTkFrame(f_cards, fg_color=CSS["bg_card"], corner_radius=20, width=420, height=360)
        card_local.pack(side="left", expand=True, pady=5)
        card_local.pack_propagate(False)
        
        ctk.CTkLabel(card_local, text="Nombre del equipo", font=CSS["font_subtitle"], text_color=CSS["text_dark"]).pack(pady=(25,10))
        self.cb_local = ctk.CTkOptionMenu(card_local, values=["Seleccionar..."], font=CSS["font_normal"], fg_color="#eeeeee", text_color="black", button_color="#dddddd", button_hover_color="#cccccc", width=280, command=lambda e: self.update_crest(self.cb_local.get(), self.cv_crest_local))
        self.cb_local.pack(pady=10)
        
        self.cv_crest_local = Canvas(card_local, width=180, height=180, bg=CSS["bg_card"], highlightthickness=0)
        self.cv_crest_local.pack(pady=15)

        # --- TARJETA VISITANTE ---
        card_vis = ctk.CTkFrame(f_cards, fg_color=CSS["bg_card"], corner_radius=20, width=420, height=360)
        card_vis.pack(side="right", expand=True, pady=5)
        card_vis.pack_propagate(False)
        
        ctk.CTkLabel(card_vis, text="Nombre del equipo", font=CSS["font_subtitle"], text_color=CSS["text_dark"]).pack(pady=(25,10))
        self.cb_vis = ctk.CTkOptionMenu(card_vis, values=["Seleccionar..."], font=CSS["font_normal"], fg_color="#eeeeee", text_color="black", button_color="#dddddd", button_hover_color="#cccccc", width=280, command=lambda e: self.update_crest(self.cb_vis.get(), self.cv_crest_vis))
        self.cb_vis.pack(pady=10)
        
        self.cv_crest_vis = Canvas(card_vis, width=180, height=180, bg=CSS["bg_card"], highlightthickness=0)
        self.cv_crest_vis.pack(pady=15)

    def on_show(self):
        league = self.controller.selected_league
        if league:
            teams = self.controller.db.get_teams_by_league(league)
            self.cb_local.configure(values=teams)
            self.cb_vis.configure(values=teams)
            self.cb_local.set("Seleccionar Equipo...")
            self.cb_vis.set("Seleccionar Equipo...")
            self.controller.draw_shield(self.cv_crest_local, None, 180, 180)
            self.controller.draw_shield(self.cv_crest_vis, None, 180, 180)

    def update_crest(self, team, canvas):
        league = self.controller.selected_league
        path = self.controller.db.get_crest_path(league, team)
        self.controller.draw_shield(canvas, path, 180, 180)


# --- PÁGINA 3: SELECCIÓN Y PREVISUALIZACIÓN DE VIDEO (PDF PÁGINA 3) ---
class VideoSelectionPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=CSS["bg_dark"], corner_radius=0)
        self.controller = controller
        self.cap_preview = None
        self.preview_job = None
        
        f_header = ctk.CTkFrame(self, fg_color="transparent")
        f_header.pack(side="top", pady=(10, 4))

        if os.path.exists(controller.logo_png_path):
            try:
                pil_logo = Image.open(controller.logo_png_path).convert("RGBA")
                aspect = pil_logo.width / pil_logo.height
                logo_h = 38
                logo_w = int(logo_h * aspect)
                self.logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(logo_w, logo_h))
                ctk.CTkLabel(f_header, text="", image=self.logo_img).pack(side="left", padx=12)
            except Exception:
                pass

        ctk.CTkLabel(f_header, text="REPETICION", font=("Arial", 32, "bold"), text_color=CSS["text_light"]).pack(side="left")

        # BARRA INFERIOR CON BOTONES ATRÁS E IR A VAR (Empacado primero abajo para visibilidad garantizada)
        f_bottom = ctk.CTkFrame(self, fg_color="transparent")
        f_bottom.pack(side="bottom", pady=15)

        btn_back = ctk.CTkButton(f_bottom, text="ATRÁS", font=CSS["font_title"], fg_color=CSS["btn_neutral"], text_color=CSS["text_light"], hover_color="#333344", corner_radius=30, command=self.go_back)
        btn_back.pack(side="left", padx=15, ipadx=35, ipady=8)

        btn_var = ctk.CTkButton(f_bottom, text="IR A VAR", font=CSS["font_title"], fg_color=CSS["btn_success"], text_color=CSS["text_light"], hover_color="#0da64a", corner_radius=30, command=self.go_to_var)
        btn_var.pack(side="left", padx=15, ipadx=45, ipady=8)
        
        f_main = ctk.CTkFrame(self, fg_color="transparent")
        f_main.pack(fill="both", expand=True, padx=40, pady=5)
        
        f_player = ctk.CTkFrame(f_main, fg_color=CSS["bg_gray"], corner_radius=15)
        f_player.pack(side="left", expand=True, fill="both", padx=(0,20))
        
        self.cv_player = Canvas(f_player, bg=CSS["bg_gray"], highlightthickness=0)
        self.cv_player.pack(expand=True, fill="both", padx=10, pady=(10, 0))
        
        self.slider = ctk.CTkSlider(f_player, from_=0, to=100, command=self.on_slider_move, button_color="white", progress_color="white", fg_color="darkgray")
        self.slider.pack(fill="x", padx=20, pady=10)
        self.slider.set(0)
        
        f_list = ctk.CTkFrame(f_main, fg_color=CSS["bg_card"], corner_radius=15, width=320)
        f_list.pack(side="right", fill="y")
        f_list.pack_propagate(False)
        
        ctk.CTkLabel(f_list, text="VIDEOS", font=CSS["font_title"], text_color=CSS["text_dark"]).pack(pady=(15,5))
        ctk.CTkFrame(f_list, height=2, fg_color="black").pack(fill="x", padx=20) 

        self.btn_add_video = ctk.CTkButton(
            f_list, 
            text="+ Añadir Videos", 
            font=CSS["font_normal"], 
            fg_color=CSS["btn_3d"], 
            text_color=CSS["text_light"], 
            hover_color="#117a8b", 
            corner_radius=15, 
            height=36, 
            command=self.add_videos
        )
        self.btn_add_video.pack(fill="x", padx=15, pady=(8, 4))

        self.scrollable_list = ctk.CTkScrollableFrame(f_list, fg_color="transparent")
        self.scrollable_list.pack(fill="both", expand=True, pady=(2, 10))

    def add_videos(self):
        """Permite al usuario seleccionar uno o más videos desde su PC y los asigna al partido actual."""
        file_paths = filedialog.askopenfilenames(
            title="Seleccionar videos para el partido",
            filetypes=[
                ("Videos compatibles", "*.mp4 *.avi *.mov *.mkv *.webm"),
                ("Todos los archivos", "*.*")
            ]
        )
        if not file_paths:
            return

        # Obtener equipos del partido actual seleccionados en SetupPage
        local_team = ""
        vis_team = ""
        if "SetupPage" in self.controller.frames:
            local_team = self.controller.frames["SetupPage"].cb_local.get()
            vis_team = self.controller.frames["SetupPage"].cb_vis.get()
            if local_team in ("Seleccionar Equipo...", "Seleccionar..."):
                local_team = ""
            if vis_team in ("Seleccionar Equipo...", "Seleccionar..."):
                vis_team = ""

        # Si hay equipos seleccionados, guardarlos en su carpeta de partido; si no, en la raíz de raw_videos
        raw_base = os.path.join("data", "raw_videos")
        if local_team and vis_team:
            target_folder = os.path.join(raw_base, f"{local_team} vs {vis_team}")
        elif local_team:
            target_folder = os.path.join(raw_base, local_team)
        else:
            target_folder = raw_base

        os.makedirs(target_folder, exist_ok=True)

        added_count = 0
        last_copied_path = None
        for src_path in file_paths:
            if not os.path.exists(src_path):
                continue
            filename = os.path.basename(src_path)
            dest_path = os.path.join(target_folder, filename)

            # Si el archivo seleccionado ya está en esa ubicación, no hace falta duplicarlo
            if os.path.abspath(src_path) != os.path.abspath(dest_path):
                try:
                    shutil.copy2(src_path, dest_path)
                    last_copied_path = dest_path
                    added_count += 1
                except Exception as e:
                    print(f"Error al copiar {filename}: {e}")
            else:
                last_copied_path = dest_path
                added_count += 1

        if added_count > 0:
            match_name = f"{local_team} vs {vis_team}" if (local_team and vis_team) else "la galería"
            messagebox.showinfo(
                "Videos Añadidos",
                f"Se añadieron exitosamente {added_count} video(s) a {match_name}."
            )
            # Refrescar la lista de videos y preseleccionar el último video añadido
            self.on_show()
            if last_copied_path and os.path.exists(last_copied_path):
                self.select_video(last_copied_path)

    def on_show(self):
        raw_base = os.path.join("data", "raw_videos")
        os.makedirs(raw_base, exist_ok=True)
        for widget in self.scrollable_list.winfo_children():
            widget.destroy()

        # Obtener equipos seleccionados en SetupPage
        local_team = ""
        vis_team = ""
        if "SetupPage" in self.controller.frames:
            local_team = self.controller.frames["SetupPage"].cb_local.get()
            vis_team = self.controller.frames["SetupPage"].cb_vis.get()
            if local_team in ("Seleccionar Equipo...", "Seleccionar..."):
                local_team = ""
            if vis_team in ("Seleccionar Equipo...", "Seleccionar..."):
                vis_team = ""

        # Recorrer recursivamente todos los videos en subcarpetas de equipos/partidos y raíz
        all_videos = []
        for root, dirs, files in os.walk(raw_base):
            for f in sorted(files):
                if f.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                    full_p = os.path.join(root, f)
                    rel_folder = os.path.relpath(root, raw_base)
                    all_videos.append({
                        "path": full_p,
                        "filename": f,
                        "folder": "" if rel_folder == "." else rel_folder
                    })

        if not all_videos:
            ctk.CTkLabel(self.scrollable_list, text="No hay videos en data/raw_videos/", text_color=CSS["text_dark"]).pack(pady=20)
            return

        def matches_selection(item):
            if not local_team and not vis_team:
                return False
            def clean_words(name):
                return [w.lower() for w in name.replace("FC", "").replace("CF", "").split() if len(w) > 3]

            kw_local = clean_words(local_team)
            kw_vis = clean_words(vis_team)
            target_text = (item["folder"] + " " + item["filename"]).lower()

            match_loc = any(k in target_text for k in kw_local) if kw_local else False
            match_vis = any(k in target_text for k in kw_vis) if kw_vis else False
            return match_loc or match_vis

        match_videos = [v for v in all_videos if matches_selection(v)]
        other_videos = [v for v in all_videos if v not in match_videos]

        # 1. Sección de videos que coinciden con los equipos del partido seleccionado
        if match_videos:
            match_title = f"⚽ PARTIDO: {local_team or 'Local'} vs {vis_team or 'Visitante'}"
            lbl_match = ctk.CTkLabel(self.scrollable_list, text=match_title, font=CSS["font_small"], text_color=CSS["btn_success"], anchor="w")
            lbl_match.pack(fill="x", padx=5, pady=(5, 3))

            for v in match_videos:
                display_name = v["filename"]
                if len(display_name) > 36:
                    display_name = display_name[:33] + "..."
                folder_badge = f"[{v['folder']}] " if v["folder"] else ""
                btn_text = f"▶ {folder_badge}{display_name}"
                btn = ctk.CTkButton(
                    self.scrollable_list,
                    text=btn_text,
                    font=CSS["font_small"],
                    fg_color="#00552b",
                    text_color="white",
                    hover_color="#008040",
                    corner_radius=10,
                    anchor="w",
                    command=lambda p=v["path"]: self.select_video(p)
                )
                btn.pack(pady=3, padx=5, fill="x")

        # 2. Sección de otros videos organizados por carpetas de equipos
        if other_videos:
            if match_videos:
                lbl_other = ctk.CTkLabel(self.scrollable_list, text="📁 OTROS PARTIDOS / VIDEOS", font=CSS["font_small"], text_color=CSS["text_dark"], anchor="w")
                lbl_other.pack(fill="x", padx=5, pady=(15, 3))

            current_folder = None
            for v in other_videos:
                if v["folder"] != current_folder:
                    current_folder = v["folder"]
                    if current_folder:
                        lbl_sub = ctk.CTkLabel(self.scrollable_list, text=f"📂 {current_folder}", font=("Arial", 11, "bold"), text_color="#555555", anchor="w")
                        lbl_sub.pack(fill="x", padx=8, pady=(6, 2))

                display_name = v["filename"]
                if len(display_name) > 36:
                    display_name = display_name[:33] + "..."
                btn = ctk.CTkButton(
                    self.scrollable_list,
                    text=f"▶ {display_name}",
                    font=CSS["font_small"],
                    fg_color=CSS["bg_dark"],
                    text_color="white",
                    hover_color="#1a1a4a",
                    corner_radius=10,
                    anchor="w",
                    command=lambda p=v["path"]: self.select_video(p)
                )
                btn.pack(pady=3, padx=5, fill="x")

        # Seleccionar automáticamente el primer video del partido seleccionado
        initial_video = match_videos[0]["path"] if match_videos else all_videos[0]["path"]
        self.select_video(initial_video)

    def draw_video_frame(self, canvas, frame):
        cw, ch = canvas.winfo_width(), canvas.winfo_height()
        if cw > 10 and ch > 10:
            h, w = frame.shape[:2]
            ratio = min(cw/w, ch/h)
            new_w, new_h = int(w * ratio), int(h * ratio)
            frame = cv2.resize(frame, (new_w, new_h))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(Image.fromarray(frame))
            canvas.create_image(cw/2, ch/2, anchor="center", image=img)
            canvas.image = img

    def select_video(self, video_path):
        if not os.path.isabs(video_path) and not os.path.exists(video_path):
            video_path = os.path.join("data", "raw_videos", video_path)
        self.controller.selected_video = os.path.abspath(video_path)
        self.stop_preview()
        
        self.cap_preview = cv2.VideoCapture(self.controller.selected_video)
        total_frames = int(self.cap_preview.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames > 0:
            self.slider.configure(to=total_frames)
        
        self.play_preview()

    def play_preview(self):
        if self.cap_preview and self.cap_preview.isOpened():
            ret, frame = self.cap_preview.read()
            if ret:
                self.draw_video_frame(self.cv_player, frame)
                current = self.cap_preview.get(cv2.CAP_PROP_POS_FRAMES)
                self.slider.set(current)
                self.preview_job = self.after(30, self.play_preview)
            else:
                self.cap_preview.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.play_preview()

    def on_slider_move(self, value):
        if self.cap_preview:
            self.cap_preview.set(cv2.CAP_PROP_POS_FRAMES, int(value))

    def stop_preview(self):
        if self.preview_job:
            self.after_cancel(self.preview_job)
            self.preview_job = None
        if self.cap_preview:
            self.cap_preview.release()
            self.cap_preview = None
        self.cv_player.delete("all")

    def go_back(self):
        self.stop_preview()
        self.controller.show_frame("SetupPage")

    def go_to_var(self):
        if self.controller.selected_video:
            self.stop_preview()
            self.controller.frames["VARReviewPage"].start_video(self.controller.selected_video)
            self.controller.show_frame("VARReviewPage")
        else:
            messagebox.showwarning("Atención", "Seleccione un video de la lista haciendo clic sobre él.")


# --- PÁGINA 4: REVISIÓN VAR CON IA YOLO & FÍSICA 3D (PDF PÁGINA 4) ---
class VARReviewPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color=CSS["bg_dark"], corner_radius=0)
        self.controller = controller
        self.cap = None
        self.is_paused = False
        self.use_yolo = True
        
        self.physics = VARPhysicsEngine()
        self.team_classifier = None
        self.update_job = None
        
        # Puntos seleccionados con clic de mouse para Fuera de Juego 3D
        self.click_points = []
        self.last_detections = []
        self.current_frame_cache = None
        self.last_saot_snapshot = None

        f_header = ctk.CTkFrame(self, fg_color="transparent")
        f_header.pack(side="top", pady=(4, 2))

        if os.path.exists(controller.logo_png_path):
            try:
                pil_logo = Image.open(controller.logo_png_path).convert("RGBA")
                aspect = pil_logo.width / pil_logo.height
                logo_h = 34
                logo_w = int(logo_h * aspect)
                self.logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(logo_w, logo_h))
                ctk.CTkLabel(f_header, text="", image=self.logo_img).pack(side="left", padx=10)
            except Exception:
                pass

        ctk.CTkLabel(f_header, text="REVISION VAR", font=("Arial", 28, "bold"), text_color=CSS["text_light"]).pack(side="left")
        
        f_center = ctk.CTkFrame(self, fg_color="transparent")
        f_center.pack(expand=True, fill="both", padx=20, pady=2)
        
        # --- REPRODUCTOR PRINCIPAL ---
        f_player = ctk.CTkFrame(f_center, fg_color=CSS["bg_gray"], corner_radius=15)
        f_player.pack(side="left", expand=True, fill="both")
        
        self.canvas = Canvas(f_player, bg=CSS["bg_gray"], highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")
        
        # BINDINGS DE MOUSE EN CANVAS
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Double-Button-1>", self.clear_click_points)
        
        self.slider = ctk.CTkSlider(f_player, from_=0, to=100, command=self.on_slider_move, button_color="white", progress_color="white", fg_color="darkgray")
        self.slider.pack(fill="x", padx=20, pady=8)
        self.slider.set(0)
        
        # --- PANEL DERECHO DE ACCIONES (PDF PÁGINA 4 + NAVEGACIÓN) ---
        f_right = ctk.CTkFrame(f_center, fg_color="transparent")
        f_right.pack(side="right", padx=15, fill="y")
        
        # BOTONES OFICIALES SEGÚN PDF Y HERRAMIENTAS 3D
        ctk.CTkButton(f_right, text="MARCAR OFFSIDE", font=CSS["font_normal"], fg_color=CSS["btn_offside"], text_color=CSS["text_light"], hover_color="#d32f2f", corner_radius=25, width=210, height=48, command=self.trigger_offside_saot).pack(pady=5)
        ctk.CTkButton(f_right, text="GENERAR PLANO 3D", font=CSS["font_normal"], fg_color=CSS["btn_3d"], text_color=CSS["text_light"], hover_color="#117a8b", corner_radius=25, width=210, height=48, command=self.generate_3d_plane).pack(pady=5)
        ctk.CTkButton(f_right, text="MARCAR FALTA", font=CSS["font_normal"], fg_color=CSS["btn_foul"], text_color=CSS["text_light"], hover_color="#1e7e34", corner_radius=25, width=210, height=48, command=self.trigger_foul_wall_3d).pack(pady=5)
        
        # BOTÓN CALIBRAR CÉSPED 4P
        ctk.CTkButton(f_right, text="CALIBRAR CÉSPED (4P)", font=CSS["font_small"], fg_color="#6f42c1", text_color="white", hover_color="#593196", width=210, height=32, command=self.enable_4p_calibration).pack(pady=3)

        # BOTÓN LIMPIAR PUNTOS MANUALES
        ctk.CTkButton(f_right, text="LIMPIAR PUNTOS (P1-P6)", font=CSS["font_small"], fg_color=CSS["btn_neutral"], text_color="white", width=210, height=30, command=self.clear_click_points).pack(pady=3)
        
        # TOGGLE DE YOLO
        self.btn_yolo_toggle = ctk.CTkButton(f_right, text="DETECCION YOLO: ON", font=CSS["font_small"], fg_color=CSS["btn_neutral"], text_color="white", width=210, height=30, command=self.toggle_yolo)
        self.btn_yolo_toggle.pack(pady=3)

        # CANVAS DE RADAR TÁCTICO 2D
        ctk.CTkLabel(f_right, text="RADAR TÁCTICO 3D", font=CSS["font_small"], text_color="white").pack(pady=(2,0))
        self.cv_radar = Canvas(f_right, width=210, height=125, bg="black", highlightthickness=1, highlightbackground="#333333")
        self.cv_radar.pack(pady=3)
        
        # BOTONES DE ATRÁS Y FINALIZAR
        f_nav_btns = ctk.CTkFrame(f_right, fg_color="transparent")
        f_nav_btns.pack(fill="x", pady=6)
        
        btn_back = ctk.CTkButton(f_nav_btns, text="ATRÁS", font=CSS["font_small"], fg_color=CSS["btn_neutral"], text_color="white", hover_color="#333344", width=100, height=38, corner_radius=15, command=self.go_back)
        btn_back.pack(side="left", padx=2)

        btn_finish = ctk.CTkButton(f_nav_btns, text="FINALIZAR", font=CSS["font_small"], fg_color="#ff9800", text_color="black", hover_color="#e68a00", width=100, height=38, corner_radius=15, command=self.finish_match_report)
        btn_finish.pack(side="right", padx=2)

        # CONTROLES DE REPRODUCCIÓN (LÍNEA INFERIOR PDF PÁGINA 4)
        f_time = ctk.CTkFrame(self, fg_color="transparent")
        f_time.pack(side="bottom", pady=10)
        
        ctk.CTkButton(f_time, text="⏪ -10", font=("Arial", 16, "bold"), fg_color="transparent", text_color="white", hover_color="#1a1a4a", command=lambda: self.skip(-300)).pack(side="left", padx=20)
        self.btn_play = ctk.CTkButton(f_time, text="||", font=("Arial", 26, "bold"), fg_color="transparent", text_color="white", hover_color="#1a1a4a", command=self.toggle_pause)
        self.btn_play.pack(side="left", padx=20)
        ctk.CTkButton(f_time, text="+10 ⏩", font=("Arial", 16, "bold"), fg_color="transparent", text_color="white", hover_color="#1a1a4a", command=lambda: self.skip(300)).pack(side="left", padx=20)

    def reset_match_state(self):
        if self.update_job:
            try:
                self.after_cancel(self.update_job)
            except Exception:
                pass
            self.update_job = None
        self.is_paused = True
        if self.cap:
            self.cap.release()
            self.cap = None
        self.click_points = []
        self.last_detections = []
        self.current_frame_cache = None
        self.last_saot_snapshot = None
        self.physics = VARPhysicsEngine()
        if hasattr(self, 'canvas') and self.canvas:
            self.canvas.delete("all")
        if hasattr(self, 'cv_radar') and self.cv_radar:
            self.cv_radar.delete("all")
        if hasattr(self, 'slider') and self.slider:
            self.slider.set(0)
        if hasattr(self, 'btn_play') and self.btn_play:
            self.btn_play.configure(text="▶")

    def start_video(self, path):
        self.reset_match_state()
        self.cap = cv2.VideoCapture(path)
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames > 0:
            self.slider.configure(to=total_frames)
            
        self.team_classifier = TeamClassifier(self.controller.match_config)
        self.is_paused = False
        self.btn_play.configure(text="||")
        self.update_frame()

    def stop_video(self):
        self.is_paused = True
        if self.update_job:
            try:
                self.after_cancel(self.update_job)
            except Exception:
                pass
            self.update_job = None
        if self.cap:
            self.cap.release()
            self.cap = None

    def go_back(self):
        self.reset_match_state()
        self.controller.show_frame("VideoSelectionPage")

    def update_frame(self):
        if self.update_job is not None:
            try:
                self.after_cancel(self.update_job)
            except Exception:
                pass
            self.update_job = None

        if self.cap and not self.is_paused:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame_cache = frame.copy()
                processed, detections = self.process_frame_ai(frame)
                self.last_detections = detections
                self.draw_video_frame(self.canvas, processed)
                self.render_radar(detections)
                
                current = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                self.slider.set(current)
            else:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                
            self.update_job = self.after(30, self.update_frame)

    def process_frame_ai(self, frame):
        detections = []
        display_frame = frame.copy()
        
        if self.use_yolo and YOLO_AVAILABLE and yolo_model is not None:
            results = yolo_model(display_frame, verbose=False)[0]
            for box in results.boxes:
                cls_id = int(box.cls[0])
                if cls_id == 0: # Jugadores / Árbitros
                    bbox = box.xyxy[0].cpu().numpy()
                    team_id, is_gk = self.team_classifier.predict_team(display_frame, bbox)
                    
                    x1, y1, x2, y2 = map(int, bbox)
                    foot_pt = (int((x1 + x2) / 2), y2)
                    
                    # Eliminados los cuadros rojos/azules sobre los jugadores a petición del usuario.
                    # El tracking se mantiene internamente para el radar táctico y la detección automática de fuera de juego.
                    
                    detections.append({'pt_px': foot_pt, 'team': team_id, 'is_gk': is_gk, 'is_ball': False, 'bbox': bbox})
                elif cls_id == 32: # Balón
                    bbox = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = map(int, bbox)
                    center = (int((x1 + x2) / 2), int((y1 + y2) / 2))
                    detections.append({'pt_px': center, 'team': -1, 'is_gk': False, 'is_ball': True})
        
        return display_frame, detections

    def render_radar(self, detections):
        radar_img = self.physics.render_tactical_radar(detections, width=210, height=125)
        radar_img = cv2.cvtColor(radar_img, cv2.COLOR_BGR2RGB)
        img = ImageTk.PhotoImage(Image.fromarray(radar_img))
        self.cv_radar.create_image(105, 62, anchor="center", image=img)
        self.cv_radar.image = img

    def draw_video_frame(self, canvas, frame):
        cw, ch = canvas.winfo_width(), canvas.winfo_height()
        if cw <= 10 or ch <= 10:
            cw, ch = 480, 320 # Dimensiones por defecto si la ventana aún se está renderizando
            
        h, w = frame.shape[:2]
        ratio = min(cw/w, ch/h)
        new_w, new_h = max(1, int(w * ratio)), max(1, int(h * ratio))
        frame = cv2.resize(frame, (new_w, new_h))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = ImageTk.PhotoImage(Image.fromarray(frame))
        canvas.create_image(cw/2, ch/2, anchor="center", image=img)
        canvas.image = img

    def enable_4p_calibration(self):
        """
        CALIBRAR CÉSPED (4P):
        Al presionar el botón, toma los 4 puntos amarillos marcados previamente en el césped,
        recalcula la homografía 3D y genera la malla cuadricular (hoja cuadriculada).
        """
        if self.current_frame_cache is None: return
        self.is_paused = True
        
        if len(self.click_points) >= 4:
            pts_4 = self.click_points[:4]
            success = self.physics.calibrate_custom_4pts(pts_4)
            if success:
                marked_frame = self.physics.draw_3d_perspective_grid(self.current_frame_cache.copy())
                self.draw_video_frame(self.canvas, marked_frame)
                messagebox.showinfo("Calibración Exitosa", "Malla cuadricular 3D calibrada al 100% con los 4 puntos amarillos.\n\nAhora marca el punto P5 (Defensor) y P6 (Atacante) en el video y presiona 'MARCAR OFFSIDE'.")
            else:
                messagebox.showerror("Error de Calibración", "No se pudo calcular la perspectiva con los puntos seleccionados.")
        else:
            messagebox.showinfo("Guía de Calibración 4P", f"Llevas {len(self.click_points)} de 4 puntos amarillos seleccionados.\n\nHaz clic en las 4 esquinas de un recuadro de césped y vuelve a presionar 'CALIBRAR CÉSPED (4P)'.")

    def on_canvas_click(self, event):
        """
        PERMITE SELECCIONAR HASTA 6 PUNTOS MANUEALES:
        - P1, P2, P3, P4: Puntos AMARILLOS guía para la geometría y calibración 3D del césped.
        - P5: Punto CIAN/AZUL (Defensor).
        - P6: Punto ROJO (Atacante).
        """
        if not self.is_paused or self.current_frame_cache is None:
            return
            
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        fh, fw = self.current_frame_cache.shape[:2]
        
        ratio = min(cw/fw, ch/fh)
        render_w, render_h = fw * ratio, fh * ratio
        offset_x = (cw - render_w) / 2
        offset_y = (ch - render_h) / 2
        
        click_x = int((event.x - offset_x) / ratio)
        click_y = int((event.y - offset_y) / ratio)
        
        if 0 <= click_x < fw and 0 <= click_y < fh:
            if len(self.click_points) >= 6:
                self.click_points = [] # Reiniciar si se exceden los 6 puntos
                
            self.click_points.append((click_x, click_y))
            
            marked_frame = self.current_frame_cache.copy()
            
            for idx, pt in enumerate(self.click_points):
                if idx < 4:
                    color = (0, 255, 255) # Amarillo césped 3D
                    label = f"P{idx+1} (Césped 3D)"
                elif idx == 4:
                    color = (255, 220, 0) # Cian/Azul Defensor
                    label = "P5 (Defensor)"
                else:
                    color = (0, 0, 255) # Rojo Atacante
                    label = "P6 (Atacante)"

                cv2.circle(marked_frame, pt, 7, color, -1)
                cv2.circle(marked_frame, pt, 11, (0, 0, 0), 2)
                cv2.putText(marked_frame, label, (pt[0]+12, pt[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.60, color, 2)

            self.draw_video_frame(self.canvas, marked_frame)


    def clear_click_points(self, event=None):
        self.click_points = []
        if self.current_frame_cache is not None:
            processed, _ = self.process_frame_ai(self.current_frame_cache)
            self.draw_video_frame(self.canvas, processed)

    def trigger_offside_saot(self):
        if self.current_frame_cache is None: return
        self.is_paused = True
        
        if len(self.click_points) >= 6:
            def_px = self.click_points[4]
            att_px = self.click_points[5]
        elif len(self.click_points) >= 2:
            def_px = self.click_points[0]
            att_px = self.click_points[1]
        elif len(self.last_detections) > 0:
            defenders = [d['pt_px'] for d in self.last_detections if d.get('team') == 1 and not d.get('is_ball')]
            attackers = [d['pt_px'] for d in self.last_detections if d.get('team') == 0 and not d.get('is_ball')]
            
            if len(defenders) > 0 and len(attackers) > 0:
                defenders_pitch = [(pt, self.physics.pixel_to_pitch(pt[0], pt[1])[0]) for pt in defenders]
                attackers_pitch = [(pt, self.physics.pixel_to_pitch(pt[0], pt[1])[0]) for pt in attackers]
                defenders_pitch.sort(key=lambda x: x[1])
                attackers_pitch.sort(key=lambda x: x[1])
                
                def_px = defenders_pitch[0][0]
                att_px = attackers_pitch[-1][0]
            else:
                h, w = self.current_frame_cache.shape[:2]
                def_px = (int(w * 0.45), int(h * 0.75))
                att_px = (int(w * 0.52), int(h * 0.70))
        else:
            h, w = self.current_frame_cache.shape[:2]
            def_px = (int(w * 0.45), int(h * 0.75))
            att_px = (int(w * 0.52), int(h * 0.70))
            
        saot_frame, is_offside, diff_cm = self.physics.calculate_and_draw_saot_offside(self.current_frame_cache.copy(), def_px, att_px, use_opaque_pitch=True)
        self.last_saot_snapshot = saot_frame.copy()
        self.draw_video_frame(self.canvas, saot_frame)
        
        event_str = "OFFSIDE (Fuera de Juego)" if is_offside else "ONSIDE (Habilitado)"
        details = f"SAOT 3D (Guía Césped): Margen de {diff_cm:+.1f} cm"
        self.log_event_with_details(event_str, details)

    def generate_3d_plane(self):
        if self.current_frame_cache is None: return
        self.is_paused = True
        grid_frame = self.physics.draw_3d_perspective_grid(self.current_frame_cache.copy())
        self.draw_video_frame(self.canvas, grid_frame)

    def trigger_foul_wall_3d(self):
        if self.current_frame_cache is None: return
        self.is_paused = True
        
        foul_pt = self.click_points[-1] if len(self.click_points) > 0 else (int(self.current_frame_cache.shape[1] * 0.5), int(self.current_frame_cache.shape[0] * 0.6))
        foul_frame = self.physics.draw_free_kick_wall_3d(self.current_frame_cache.copy(), foul_pt, radius_m=9.15)
        self.draw_video_frame(self.canvas, foul_frame)
        self.log_event_with_details("Falta Registrada", "Barrera 3D calibrada a 9.15m")

    def toggle_yolo(self):
        self.use_yolo = not self.use_yolo
        self.btn_yolo_toggle.configure(text=f"DETECCION YOLO: {'ON' if self.use_yolo else 'OFF'}")

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_play.configure(text="▶" if self.is_paused else "||")
        if not self.is_paused:
            self.update_frame()

    def skip(self, frames):
        if self.cap:
            current = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            new_pos = max(0, current + frames)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_pos)
            self.slider.set(new_pos)

    def on_slider_move(self, value):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, int(value))
            if self.is_paused:
                ret, frame = self.cap.read()
                if ret:
                    self.current_frame_cache = frame.copy()
                    processed, _ = self.process_frame_ai(frame)
                    self.draw_video_frame(self.canvas, processed)

    def log_event_with_details(self, event_type, details=""):
        if not self.cap: return
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        current = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        mins, secs = divmod(int(current / fps), 60)
        min_str = f"{mins:02d}:{secs:02d}"
        
        clip_name = f"{event_type.split()[0]}_{min_str.replace(':','')}.mp4"
        clip_path = os.path.join(self.controller.db.reports_dir, clip_name)
        
        self.extract_clip(current, fps, clip_path)
        
        match_id = f"{self.controller.frames['SetupPage'].cb_local.get()} vs {self.controller.frames['SetupPage'].cb_vis.get()}"
        self.controller.db.log_event(match_id, event_type, min_str, clip_path, details=details)
        messagebox.showinfo("Reporte Oficial VAR", f"Decisión: {event_type}\nMinuto: {min_str}\n{details}\n\nClip e informe Excel guardados.")

    def finish_match_report(self):
        """Muestra la ventana emergente con el informe final del partido, plano 3D, reproductor de clip MP4 y resumen de decisiones."""
        self.stop_video()
        
        match_id = f"{self.controller.frames['SetupPage'].cb_local.get()} vs {self.controller.frames['SetupPage'].cb_vis.get()}"
        excel_file = self.controller.db.excel_path
        
        report_win = ctk.CTkToplevel(self)
        report_win.title("MATCHVISION VAR - INFORME FINAL DEL PARTIDO")
        report_win.geometry("980x680")
        report_win.configure(fg_color=CSS["bg_dark"])
        report_win.attributes("-topmost", True)
        
        ctk.CTkLabel(report_win, text="INFORME ARBITRAL Y RESUMEN 3D SAOT", font=("Arial", 24, "bold"), text_color=CSS["text_light"]).pack(pady=(15, 5))
        ctk.CTkLabel(report_win, text=f"Partido: {match_id} | Liga: {self.controller.selected_league or 'N/A'}", font=CSS["font_normal"], text_color=CSS["accent_yellow"]).pack(pady=(0, 10))
        
        f_content = ctk.CTkFrame(report_win, fg_color="transparent")
        f_content.pack(fill="both", expand=True, padx=25, pady=5)
        
        # --- PLANO Y ESQUEMA 3D DE FUERA DE JUEGO (IZQUIERDA) ---
        f_left = ctk.CTkFrame(f_content, fg_color=CSS["bg_gray"], corner_radius=15)
        f_left.pack(side="left", expand=True, fill="both", padx=(0, 15))
        
        ctk.CTkLabel(f_left, text="ESQUEMA Y PLANO 3D DE FUERA DE JUEGO (SAOT)", font=CSS["font_small"], text_color="white").pack(pady=8)
        cv_snap = Canvas(f_left, bg="black", highlightthickness=0)
        cv_snap.pack(expand=True, fill="both", padx=10, pady=(5, 5))
        
        # Indicador de tecnología 3D SAOT Rotatoria
        ctk.CTkLabel(f_left, text="📐 VISTA 3D ROTATORIA 360° (ARRASTRA EL MOUSE)", font=("Arial", 11, "bold"), text_color=CSS["accent_yellow"]).pack(pady=(0, 10))

        # --- RESUMEN DE DECISIONES DE BASE DE DATOS (DERECHA) ---
        f_right_rep = ctk.CTkFrame(f_content, fg_color=CSS["bg_card"], corner_radius=15, width=400)
        f_right_rep.pack(side="right", fill="y")
        f_right_rep.pack_propagate(False)
        
        ctk.CTkLabel(f_right_rep, text="REGISTRO DE DECISIONES", font=CSS["font_subtitle"], text_color=CSS["text_dark"]).pack(pady=15)
        
        scroll_rep = ctk.CTkScrollableFrame(f_right_rep, fg_color="transparent")
        scroll_rep.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Cargar datos guardados del Excel si existe
        if os.path.exists(excel_file):
            try:
                df = pd.read_excel(excel_file)
                match_df = df[df["Partido"] == match_id] if "Partido" in df.columns else df
                if match_df.empty: match_df = df.tail(10)
                
                for idx, row in match_df.iterrows():
                    item_str = f"⏱ {row.get('Minuto', '00:00')} - {row.get('Decisión VAR', row.get('Evento', 'Evento'))}\n{row.get('Detalles Tácticos / SAOT', '')}"
                    lbl_item = ctk.CTkLabel(scroll_rep, text=item_str, font=("Arial", 12), text_color="black", justify="left", fg_color="#f0f2f5", corner_radius=8, padx=10, pady=8)
                    lbl_item.pack(fill="x", pady=4)
            except Exception as e:
                ctk.CTkLabel(scroll_rep, text=f"Excel actualizado en:\n{excel_file}", text_color="black").pack(pady=20)
        else:
            ctk.CTkLabel(scroll_rep, text="No se registraron revisiones en este partido.", text_color="black").pack(pady=20)

        # PIE CON BOTONES DE SALIDA
        f_actions = ctk.CTkFrame(report_win, fg_color="transparent")
        f_actions.pack(side="bottom", pady=15)
        
        btn_close = ctk.CTkButton(f_actions, text="CERRAR VENTANA", font=CSS["font_normal"], fg_color=CSS["btn_neutral"], text_color="white", corner_radius=20, width=180, command=report_win.destroy)
        btn_close.pack(side="left", padx=10)

        btn_home = ctk.CTkButton(f_actions, text="NUEVO PARTIDO ⚽", font=CSS["font_normal"], fg_color=CSS["btn_success"], text_color="white", corner_radius=20, width=220, command=lambda: [report_win.destroy(), self.reset_match_state(), self.controller.show_frame("LeagueSelectionPage")])
        btn_home.pack(side="left", padx=10)

        # VARIABLES DE ROTACIÓN 360° CON MOUSE
        report_win.rot_x = 35.0
        report_win.rot_y = 25.0
        report_win.last_mouse_x = 0
        report_win.last_mouse_y = 0

        def on_mouse_down(event):
            report_win.last_mouse_x = event.x
            report_win.last_mouse_y = event.y

        def on_mouse_drag(event):
            dx = event.x - report_win.last_mouse_x
            dy = event.y - report_win.last_mouse_y
            report_win.last_mouse_x = event.x
            report_win.last_mouse_y = event.y
            
            report_win.rot_y = (report_win.rot_y + dx * 0.6) % 360.0
            report_win.rot_x = max(10.0, min(80.0, report_win.rot_x - dy * 0.6))
            render_report_3d_schema()

        cv_snap.bind("<ButtonPress-1>", on_mouse_down)
        cv_snap.bind("<B1-Motion>", on_mouse_drag)

        # RENDERIZAR EL ESQUEMA 3D ROTATORIO DE FORMA GARANTIZADA AL ABRIR LA VENTANA
        def render_report_3d_schema():
            report_win.update_idletasks()
            def_x, att_x = 48.0, 55.0
            
            if len(self.click_points) >= 6:
                def_px = self.click_points[4]
                att_px = self.click_points[5]
                def_x, _ = self.physics.pixel_to_pitch(def_px[0], def_px[1])
                att_x, _ = self.physics.pixel_to_pitch(att_px[0], att_px[1])
            elif len(getattr(self, 'last_detections', [])) > 0:
                defenders = [d['pt_px'] for d in self.last_detections if d.get('team') == 1 and not d.get('is_ball')]
                attackers = [d['pt_px'] for d in self.last_detections if d.get('team') == 0 and not d.get('is_ball')]
                if len(defenders) > 0 and len(attackers) > 0:
                    defenders_pitch = [(pt, self.physics.pixel_to_pitch(pt[0], pt[1])[0]) for pt in defenders]
                    attackers_pitch = [(pt, self.physics.pixel_to_pitch(pt[0], pt[1])[0]) for pt in attackers]
                    defenders_pitch.sort(key=lambda x: x[1])
                    attackers_pitch.sort(key=lambda x: x[1])
                    def_x = defenders_pitch[0][1]
                    att_x = attackers_pitch[-1][1]

            diff_cm = (att_x - def_x) * 100.0
            is_offside = diff_cm > 0.0

            cw = max(480, cv_snap.winfo_width())
            ch = max(320, cv_snap.winfo_height())
            
            rot_3d_frame = self.physics.render_rotatable_3d_offside_scene(
                def_pitch_x=def_x,
                att_pitch_x=att_x,
                rot_x_deg=report_win.rot_x,
                rot_y_deg=report_win.rot_y,
                width=cw,
                height=ch,
                is_offside=is_offside,
                diff_cm=diff_cm
            )
            self.draw_video_frame(cv_snap, rot_3d_frame)

        # Ejecutar renderizado garantizado inmediatamente y tras 50ms para asegurar que el canvas tenga dimensiones finales
        render_report_3d_schema()
        report_win.after(60, render_report_3d_schema)

    def extract_clip(self, center_frame, fps, out_path):
        start = max(0, center_frame - (5 * fps))
        end = center_frame + (5 * fps)
        orig_pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        
        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        while self.cap.get(cv2.CAP_PROP_POS_FRAMES) <= end:
            ret, f = self.cap.read()
            if not ret: break
            out.write(f)
            
        out.release()
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, orig_pos)