# page_dashboard.py
# Dashboard principal : detection, capture automatique et profils locaux.

import customtkinter as ctk
from tkinter import messagebox, filedialog, simpledialog
import os
import time
import threading
from datetime import datetime
from random import choice

try:
    import tkintermapview
except ImportError:
    tkintermapview = None

try:
    import cv2
    from PIL import Image, ImageTk
except ImportError:
    cv2 = None
    Image = None
    ImageTk = None

# Assure-toi que ces imports correspondent à ton projet
from config import FONT_NORMAL, FONT_BOLD, ACCENT_COLOR, TABLE_PERSONNE, TABLE_LOGS, TABLE_INTRUS
import db
from face_utils import compare_face_ids, extract_face_id, extract_face_id_from_path

# --- Palette de couleurs (Design de l'image) ---
PAGE_BG = "#1a232c"
PANEL_BG = "#151d24"
SEPARATOR_COLOR = "#293744"
FIELD_BG = "#11171d"
FIELD_BORDER = "#2a3947"
TEXT_MAIN = "#ffffff"
TEXT_MUTED = "#8795a1"
TEAL = "#2b585a"
TEAL_HOVER = "#3a7174"
SUCCESS_GREEN = "#27ae60"
SUCCESS_HOVER = "#219653"
DANGER_RED = "#922b21"
WELCOME_GREEN = "#2ecc71"


def generate_person_pdf_report(person_data, output_dir=None):
    """
    Génère un rapport PDF individuel complet avec la photo de la personne
    positionnée côte à côte avec ses informations personnelles.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        return None

    if not output_dir:
        output_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(output_dir, exist_ok=True)

    cni = str(person_data.get("cni", "INCONNU")).strip()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"Rapport_Detection_{cni}_{ts}.pdf")

    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter

    # En-tête / Banner principal
    c.setFillColorRGB(0.06, 0.12, 0.22)
    c.rect(0, height - 85, width, 85, fill=True, stroke=False)

    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 35, "C.H.R.A.C.E.R.H ACCES CONTROL")
    c.setFont("Helvetica", 11)
    c.drawString(40, height - 55, "Rapport Automatique de Détection Faciale & Supervision Biométrique")

    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, height - 105, f"Date de Détection : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")
    c.drawString(340, height - 105, "Statut : ACCÈS AUTORISÉ (Membre de la BD)")

    c.setLineWidth(1)
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.line(40, height - 115, width - 40, height - 115)

    # Zone Photo + Informations côte à côte
    y_start = height - 145
    photo_path = person_data.get("photo_path", "")
    if photo_path and not os.path.isabs(photo_path):
        photo_path = os.path.join(os.path.dirname(__file__), photo_path)

    if photo_path and os.path.isfile(photo_path):
        try:
            c.drawImage(photo_path, width - 175, y_start - 130, width=130, height=140, preserveAspectRatio=True)
            c.setStrokeColorRGB(0.18, 0.43, 0.89)
            c.setLineWidth(2)
            c.rect(width - 175, y_start - 130, 130, 140, fill=False, stroke=True)
        except Exception as e:
            print(f"[PDF Draw Photo Error] {e}")

    c.setFont("Helvetica-Bold", 13)
    c.setFillColorRGB(0.18, 0.43, 0.89)
    c.drawString(40, y_start, "INFORMATIONS PERSONNELLES")

    c.setFillColorRGB(0.1, 0.1, 0.1)

    details = [
        ("Matricule CNI / ID :", str(person_data.get("cni", "----"))),
        ("Nom :", str(person_data.get("nom", "----"))),
        ("Prénom :", str(person_data.get("prenom", "----"))),
        ("Poste Hospitalier :", str(person_data.get("poste", "Accueil / Surveillance"))),
        ("Ville de résidence :", str(person_data.get("ville", "Non spécifiée"))),
        ("Quartier :", str(person_data.get("quartier", "Non spécifié"))),
        ("Date Enregistrement :", str(person_data.get("date_enregistrement", datetime.now().strftime("%d/%m/%Y")))),
    ]

    curr_y = y_start - 25
    for label, val in details:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(40, curr_y, label)
        c.setFont("Helvetica", 10)
        c.drawString(160, curr_y, val)
        curr_y -= 18

    curr_y -= 15
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.line(40, curr_y, width - 40, curr_y)
    curr_y -= 25

    c.setFont("Helvetica-Bold", 11)
    c.setFillColorRGB(0.08, 0.63, 0.29)
    c.drawString(40, curr_y, "● VALIDATION BIOMÉTRIQUE : PROFIL FACIAL CONFIRMÉ AVEC SUCCÈS")

    curr_y -= 20
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(40, curr_y, "Ce rapport a été généré automatiquement par le système CHRACERH lors de la détection caméra.")

    c.showPage()
    c.save()
    return filepath


class WebcamPanel:
    def __init__(self, parent, size=(640, 360), fallback_text="[ Caméra inactive ]", auto_start=False):
        self.parent = parent
        self.size = size
        self.fallback_text = fallback_text
        self.cap = None
        self.label = ctk.CTkLabel(parent, text=fallback_text, text_color="gray")
        self.label.pack(fill="both", expand=True, padx=4, pady=4)
        self.overlay_rect = None  # normalized rect (x_norm, y_norm, w_norm, h_norm)
        self.overlay_color = None
        self.show_scan_grid = False
        self.focus_frame = None
        self.latest_frame = None
        if auto_start:
            self.start()

    def start(self):
        for idx in (0, 1, 2):
            try:
                cap = cv2.VideoCapture(
                    idx,
                    cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else cv2.CAP_ANY,
                )
                if cap is not None and cap.isOpened():
                    self.cap = cap
                    self.update()
                    return
                if cap is not None:
                    cap.release()
            except Exception:
                pass
        self.label.configure(text=self.fallback_text)

    def update(self):
        if self.cap is None or not self.cap.isOpened():
            return

        frame = self.latest_frame
        ret = frame is not None
        if self.focus_frame is not None:
            frame = self.focus_frame
            ret = True
        if ret and frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb).resize(self.size)
            # dessiner overlay si présent (coords normalisées)
            try:
                if self.overlay_rect and Image:
                    from PIL import ImageDraw
                    draw = ImageDraw.Draw(img)
                    x_norm, y_norm, w_norm, h_norm = self.overlay_rect
                    x = int(x_norm * img.width)
                    y = int(y_norm * img.height)
                    w = int(w_norm * img.width)
                    h = int(h_norm * img.height)
                    color = self.overlay_color or (0, 255, 0)
                    if isinstance(color, str):
                        color = (0, 255, 0) if color.lower() == 'green' else (255, 0, 0)
                    draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
                if self.show_scan_grid and Image:
                    from PIL import ImageDraw
                    draw = ImageDraw.Draw(img)
                    grid_color = (68, 210, 170)
                    for x in range(0, img.width, max(28, img.width // 8)):
                        draw.line((x, 0, x, img.height), fill=grid_color, width=1)
                    for y in range(0, img.height, max(28, img.height // 6)):
                        draw.line((0, y, img.width, y), fill=grid_color, width=1)
                    draw.rectangle((2, 2, img.width - 3, img.height - 3), outline=grid_color, width=2)
            except Exception:
                pass
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=self.size)
            self.label.configure(image=ctk_img, text="")
            self.label.image = ctk_img

        self.parent.after(30, self.update)

    def stop(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.latest_frame = None
        self.focus_frame = None
        self.label.configure(image=None, text=self.fallback_text)
        self.label.image = None

    def set_overlay(self, rect_norm, color='green'):
        """rect_norm: (x_norm, y_norm, w_norm, h_norm) values between 0 and 1"""
        self.overlay_rect = rect_norm
        self.overlay_color = color

    def set_scan_grid(self, enabled):
        self.show_scan_grid = enabled

    def set_focus_frame(self, frame):
        self.focus_frame = frame.copy() if frame is not None else None

    def set_latest_frame(self, frame):
        self.latest_frame = frame.copy() if frame is not None else None


class DashboardPage:
    def __init__(self, parent, controller=None):
        self.controller = controller
        self.parent = parent
        parent.configure(fg_color=PAGE_BG)

        # --- Dédoublonnage & Mémoire des détections récentes ---
        self.recent_detections = {}
        self.deduplication_cooldown = 10  # Secondes avant de ré-alerter pour le même CNI
        self._prompt_active = False  # Évite l'accumulation de fenêtres modales

        # Chargeur Cascade OpenCV pour la détection faciale
        self.face_cascade = None
        if cv2:
            try:
                local_xml = os.path.join(os.path.dirname(__file__), 'haarcascade_frontalface_default.xml')
                if os.path.exists(local_xml):
                    self.face_cascade = cv2.CascadeClassifier(local_xml)
                else:
                    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                    self.face_cascade = cv2.CascadeClassifier(cascade_path)
            except Exception:
                self.face_cascade = None

        # Configuration compacte : caméra, accès, puis carte.
        parent.grid_columnconfigure(0, weight=4)
        parent.grid_columnconfigure(1, weight=4)
        parent.grid_columnconfigure(2, weight=3)
        parent.grid_rowconfigure(0, weight=1)

        # =========================================================
        # 1. BLOC GAUCHE : FLUX CAMÉRA & DÉTECTION / BIENVENUE AUTOMATIQUE
        # =========================================================
        col_left = ctk.CTkFrame(parent, fg_color="transparent")
        col_left.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        col_left.grid_rowconfigure(0, weight=55)
        col_left.grid_rowconfigure(1, weight=45)
        col_left.grid_columnconfigure(0, weight=1)

        # --- Flux Vidéo Intelligent ---
        video_outer_frame = ctk.CTkFrame(col_left, fg_color=PANEL_BG, border_width=1, border_color=FIELD_BORDER)
        video_outer_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        self._create_section_title(video_outer_frame, "DÉTECTION FACIALE INTELLIGENTE",
                                   "FLUX VIDÉO EN DIRECT (ANALYSE ACTIVE)")

        video_display = ctk.CTkFrame(video_outer_frame, fg_color="#10171d", corner_radius=4)
        video_display.pack(fill="both", expand=True, padx=6, pady=6)

        # Initialisation du flux caméra
        self.camera_feed = WebcamPanel(video_display, size=(280, 150), fallback_text="[ Caméra inactive ]")
        self.btn_camera = ctk.CTkButton(
            video_outer_frame, text="LANCER LA CAMÉRA", height=32, font=FONT_BOLD,
            fg_color=TEAL, hover_color=TEAL_HOVER, command=self.start_camera,
        )
        self.btn_camera.pack(fill="x", padx=8, pady=(0, 8))
        self.btn_stop_camera = ctk.CTkButton(
            video_outer_frame, text="ARRÊTER LA CAMÉRA", height=30, font=FONT_BOLD,
            fg_color=DANGER_RED, hover_color="#b91c1c", state="disabled",
            command=self.stop_camera,
        )
        self.btn_stop_camera.pack(fill="x", padx=8, pady=(0, 8))

        # --- Résultats de Détection & Message de Bienvenue ---
        results_outer_frame = ctk.CTkFrame(col_left, fg_color=PANEL_BG, border_width=1, border_color=FIELD_BORDER)
        results_outer_frame.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        self._create_section_title(results_outer_frame, "IDENTIFICATION TEMPS RÉEL", "CAPTURE ET STOCKAGE LOCAL")

        # Zone d'affichage du résultat avec la fiche complète d'information
        self.match_display = ctk.CTkFrame(results_outer_frame, fg_color="transparent")
        self.match_display.pack(fill="both", expand=True, padx=6, pady=4)

        self.lbl_welcome = ctk.CTkLabel(self.match_display, text="<< EN ATTENTE DE DÉTECTION >>",
                                        font=("Times New Roman", 14, "bold"), text_color=WELCOME_GREEN)
        self.lbl_welcome.pack(pady=(2, 4))

        # Carte d'identité / Fiche détaillée
        self.info_card = ctk.CTkFrame(self.match_display, fg_color="#10171d", border_width=1, border_color=FIELD_BORDER, corner_radius=6)
        self.info_card.pack(fill="both", expand=True, padx=4, pady=2)

        self.info_card.grid_columnconfigure(0, weight=0)
        self.info_card.grid_columnconfigure(1, weight=1)
        self.info_card.grid_rowconfigure(0, weight=1)

        # Avatar photo à gauche
        photo_box = ctk.CTkFrame(self.info_card, fg_color="#0b0f14", width=95, height=95, corner_radius=4, border_width=1, border_color="#2a3947")
        photo_box.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")
        photo_box.pack_propagate(False)

        self.lbl_photo_avatar = ctk.CTkLabel(photo_box, text="[ ACCÈS ]\n[ EN ATTENTE ]", font=("Times New Roman", 9, "bold"), text_color=TEXT_MUTED)
        self.lbl_photo_avatar.pack(fill="both", expand=True)

        # Grille d'informations à droite
        details_grid = ctk.CTkFrame(self.info_card, fg_color="transparent")
        details_grid.grid(row=0, column=1, padx=(4, 6), pady=4, sticky="nsew")
        details_grid.grid_columnconfigure(1, weight=1)

        # Lignes d'informations
        # CNI
        ctk.CTkLabel(details_grid, text="CNI / ID :", font=("Times New Roman", 10, "bold"), text_color=TEXT_MUTED, anchor="w").grid(row=0, column=0, sticky="w", pady=1)
        self.lbl_cni_val = ctk.CTkLabel(details_grid, text="----", font=("Times New Roman", 10, "bold"), text_color=TEXT_MAIN, anchor="w")
        self.lbl_cni_val.grid(row=0, column=1, sticky="w", padx=(4, 0), pady=1)

        # NOM & PRÉNOM
        ctk.CTkLabel(details_grid, text="NOM & PRÉNOM :", font=("Times New Roman", 10, "bold"), text_color=TEXT_MUTED, anchor="w").grid(row=1, column=0, sticky="w", pady=1)
        self.lbl_name_val = ctk.CTkLabel(details_grid, text="Aucune personne détectée", font=("Times New Roman", 10, "bold"), text_color="#f1c40f", anchor="w")
        self.lbl_name_val.grid(row=1, column=1, sticky="w", padx=(4, 0), pady=1)

        # POSTE / ZONE
        ctk.CTkLabel(details_grid, text="POSTE :", font=("Times New Roman", 10, "bold"), text_color=TEXT_MUTED, anchor="w").grid(row=2, column=0, sticky="w", pady=1)
        self.lbl_poste_val = ctk.CTkLabel(details_grid, text="----", font=("Times New Roman", 10), text_color=TEXT_MAIN, anchor="w")
        self.lbl_poste_val.grid(row=2, column=1, sticky="w", padx=(4, 0), pady=1)

        # LOCALISATION
        ctk.CTkLabel(details_grid, text="ADRESSE :", font=("Times New Roman", 10, "bold"), text_color=TEXT_MUTED, anchor="w").grid(row=3, column=0, sticky="w", pady=1)
        self.lbl_loc_val = ctk.CTkLabel(details_grid, text="----", font=("Times New Roman", 10), text_color=TEXT_MAIN, anchor="w")
        self.lbl_loc_val.grid(row=3, column=1, sticky="w", padx=(4, 0), pady=1)

        # HEURE DE DÉTECTION
        ctk.CTkLabel(details_grid, text="HEURE SCAN :", font=("Times New Roman", 10, "bold"), text_color=TEXT_MUTED, anchor="w").grid(row=4, column=0, sticky="w", pady=1)
        self.lbl_time_val = ctk.CTkLabel(details_grid, text="----", font=("Times New Roman", 10, "bold"), text_color="#38bdf8", anchor="w")
        self.lbl_time_val.grid(row=4, column=1, sticky="w", padx=(4, 0), pady=1)

        # STATUT D'ACCÈS
        self.lbl_status_val = ctk.CTkLabel(details_grid, text="[ Système en veille active ]", font=("Times New Roman", 10, "bold"), text_color=TEXT_MUTED, anchor="w")
        self.lbl_status_val.grid(row=5, column=0, columnspan=2, sticky="w", pady=(3, 1))

        # Aliases pour compatibilité ascendante
        self.lbl_match_name = self.lbl_name_val
        self.lbl_match_status = self.lbl_status_val

        # =========================================================
        # 2. BLOC CENTRAL : ACCÈS RÉPERTORIÉS
        # =========================================================
        col_mid = ctk.CTkFrame(parent, fg_color=PANEL_BG, border_width=1, border_color=FIELD_BORDER)
        col_mid.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        self._create_section_title(col_mid, "ACCÈS RÉPERTORIÉS", "HISTORIQUE DU CONTRÔLE D'ACCÈS")
        self.access_display = ctk.CTkScrollableFrame(col_mid, fg_color="#0b0f19")
        self.access_display.pack(fill="both", expand=True, padx=6, pady=6)
        self.refresh_accesses()

        # =========================================================
        # 3. BLOC DROIT : GÉOLOCALISATION DYNAMIQUE (tkintermapview)
        # =========================================================
        col_right = ctk.CTkFrame(parent, fg_color=PANEL_BG, border_width=1, border_color=FIELD_BORDER)
        col_right.grid(row=0, column=2, sticky="nsew", padx=8, pady=8)
        self._create_section_title(col_right, "GÉOLOCALISATION DYNAMIQUE & VALIDATION", "MAPPING & STOCKAGE LOCAL")

        right_container = ctk.CTkFrame(col_right, fg_color="transparent")
        right_container.pack(fill="both", expand=True, padx=6, pady=6)

        ctk.CTkLabel(right_container, text="CARTE INTERACTIVE (GOOGLE MAPS)", font=FONT_BOLD,
                     text_color=TEXT_MUTED).pack(anchor="w", pady=(2, 1))

        # Intégration de tkintermapview
        map_box = ctk.CTkFrame(right_container, fg_color="#10171d", height=280, border_width=1,
                               border_color=FIELD_BORDER)
        map_box.pack(fill="x", pady=(0, 10))
        map_box.pack_propagate(False)

        if tkintermapview:
            self.map_widget = tkintermapview.TkinterMapView(map_box, corner_radius=0)
            self.map_widget.pack(fill="both", expand=True)
            self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", max_zoom=22)
            self.map_widget.set_position(3.8480, 11.5021)  # Yaoundé (CHRACERH)
            self.map_widget.set_zoom(13)
        else:
            ctk.CTkLabel(map_box, text="CARTE INDISPONIBLE\n(pip install tkintermapview)", text_color=DANGER_RED,
                         font=FONT_NORMAL).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(right_container, text="COORDONNÉES GPS (Lat/Lon)", font=FONT_BOLD, text_color=TEXT_MUTED).pack(
            anchor="w", pady=(4, 1))
        self.entry_gps = ctk.CTkEntry(right_container, height=28, font=FONT_NORMAL, fg_color=FIELD_BG,
                                      border_color=FIELD_BORDER, text_color=TEXT_MAIN)
        self.entry_gps.insert(0, "3.8480, 11.5021")
        self.entry_gps.pack(fill="x", pady=(0, 15))

        self.lbl_db_status = ctk.CTkLabel(right_container, text="STATUT D'ENREGISTREMENT : PRÊT",
                                          font=FONT_BOLD, text_color="#f1c40f")
        self.lbl_db_status.pack(anchor="w", pady=(4, 2), side="bottom")

        self.face_detection_running = False
        self.running_detection = False
        self.detection_thread = None

        if cv2 is not None:
            self.parent.after(500, self.start_camera)

    def start_camera(self):
        if cv2 is None:
            self.lbl_status_val.configure(text="[ Webcam indisponible : OpenCV non installé ]", text_color=DANGER_RED)
            return
        if self.face_detection_running:
            return
        self.face_detection_running = True
        self.running_detection = True
        self.camera_feed.start()
        if self.camera_feed.cap is None:
            self.face_detection_running = False
            self.running_detection = False
            self.lbl_status_val.configure(text="[ Caméra indisponible ]", text_color=DANGER_RED)
            return
        self.camera_feed.set_scan_grid(True)
        self.btn_camera.configure(text="CAMÉRA ACTIVE", state="disabled")
        self.btn_stop_camera.configure(state="normal")
        self.detection_thread = threading.Thread(target=self.face_detection_loop, daemon=True)
        self.detection_thread.start()

    def stop_camera(self):
        self.face_detection_running = False
        self.running_detection = False
        self.camera_feed.stop()
        self.camera_feed.set_scan_grid(False)
        self.camera_feed.label.configure(image=None, text="[ Caméra arrêtée ]")
        self.camera_feed.label.image = None
        self.btn_camera.configure(text="LANCER LA CAMÉRA", state="normal")
        self.btn_stop_camera.configure(state="disabled")
        self.lbl_status_val.configure(text="[ Système en veille active ]", text_color=TEXT_MUTED)

    def refresh_accesses(self):
        for child in self.access_display.winfo_children():
            child.destroy()
        accesses = db.read_table(TABLE_LOGS)
        if not accesses:
            ctk.CTkLabel(self.access_display, text="Aucun accès répertorié.", font=FONT_BOLD,
                         text_color=TEXT_MUTED).pack(pady=30)
            return
        for access in reversed(accesses):
            status = access.get("statut", "Autorisé")
            color = SUCCESS_GREEN if status.lower() in ("autorisé", "autorise", "enregistré") else DANGER_RED
            card = ctk.CTkFrame(self.access_display, fg_color="#161b22", border_width=1, border_color="#30363d")
            card.pack(fill="x", pady=4)
            ctk.CTkLabel(card, text=f"{access.get('date_heure', '')}  |  {access.get('cni', 'Inconnu')}",
                         font=FONT_BOLD, text_color=TEXT_MAIN).pack(anchor="w", padx=8, pady=(7, 2))
            ctk.CTkLabel(card, text=f"{access.get('piece', 'Zone non précisée')}  •  {status}",
                         font=FONT_NORMAL, text_color=color).pack(anchor="w", padx=8, pady=(0, 7))

    def get_random_person(self):
        rows = db.fetch_all(
            f'SELECT cni, nom, prenom, ville, quartier, photo_path, poste FROM "{TABLE_PERSONNE}" ORDER BY random() LIMIT 1;'
        )
        if rows:
            cni, nom, prenom, ville, quartier, photo_path, poste = rows[0]
            return {
                "cni": cni, "nom": nom, "prenom": prenom, "ville": ville,
                "quartier": quartier, "photo_path": photo_path or "",
                "poste": poste or "Personnel", "registered": True
            }
        return None

    # ---------------------------------------------------------
    # Méthodes de détection automatique et logique de stockage local.
    # ---------------------------------------------------------
    def _create_section_title(self, parent, main_title, sub_title):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=6, pady=(6, 4))
        ctk.CTkLabel(header, text=main_title, font=("Times New Roman", 13, "bold"), text_color=TEXT_MAIN).pack(
            anchor="w")
        ctk.CTkLabel(header, text=sub_title, font=("Times New Roman", 10), text_color=TEXT_MUTED).pack(anchor="w")
        ctk.CTkFrame(parent, fg_color=SEPARATOR_COLOR, height=2).pack(fill="x", padx=6, pady=(0, 4))

    def _display_person_info(self, cni="", nom="", prenom="", poste="", ville="", quartier="", photo_path=None, face_img=None,
                             status_text="Statut inconnu", status_color=TEXT_MUTED,
                             welcome_text="<< DÉTECTION >>", welcome_color=WELCOME_GREEN):
        """Affiche les informations complètes de la personne sous la vidéo."""
        self.lbl_welcome.configure(text=welcome_text, text_color=welcome_color)
        self.lbl_cni_val.configure(text=cni or "----")
        full_name = f"{nom or ''} {prenom or ''}".strip()
        self.lbl_name_val.configure(text=full_name or "Visage non identifié", text_color=TEXT_MAIN if full_name else "#f1c40f")
        self.lbl_poste_val.configure(text=poste or "Zone de Surveillance")
        loc = f"{quartier or ''}, {ville or ''}".strip(', ')
        self.lbl_loc_val.configure(text=loc or "Non précisée")
        self.lbl_time_val.configure(text=datetime.now().strftime("%H:%M:%S (%d/%m/%Y)"))
        self.lbl_status_val.configure(text=status_text, text_color=status_color)

        # Affichage de la photo miniature (avatar)
        loaded_img = None
        if face_img is not None and cv2 and Image:
            try:
                rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                loaded_img = Image.fromarray(rgb).resize((85, 85))
            except Exception:
                loaded_img = None

        if loaded_img is None and photo_path:
            candidate = str(photo_path).replace('\\', '/')
            if not os.path.isabs(candidate):
                root = os.path.dirname(os.path.abspath(__file__))
                candidates = [
                    os.path.abspath(os.path.join(root, candidate)),
                    os.path.abspath(os.path.join(root, 'media', os.path.basename(candidate))),
                    os.path.abspath(os.path.join(root, 'data_photos', os.path.basename(candidate))),
                ]
                for path in candidates:
                    if os.path.isfile(path):
                        candidate = path
                        break
            if os.path.isfile(candidate) and Image:
                try:
                    loaded_img = Image.open(candidate).resize((85, 85))
                except Exception:
                    loaded_img = None

        if loaded_img and ctk:
            try:
                ctk_img = ctk.CTkImage(light_image=loaded_img, dark_image=loaded_img, size=(85, 85))
                self.lbl_photo_avatar.configure(image=ctk_img, text="")
                self.lbl_photo_avatar.image = ctk_img
            except Exception:
                self.lbl_photo_avatar.configure(image=None, text="[ PAS DE\nPHOTO ]")
                self.lbl_photo_avatar.image = None
        else:
            self.lbl_photo_avatar.configure(image=None, text="[ PAS DE\nPHOTO ]")
            self.lbl_photo_avatar.image = None

    def reset_form(self):
        self.lbl_welcome.configure(text="<< EN ATTENTE DE DÉTECTION >>", text_color=WELCOME_GREEN)
        self.lbl_cni_val.configure(text="----")
        self.lbl_name_val.configure(text="Aucune personne détectée", text_color="#f1c40f")
        self.lbl_poste_val.configure(text="----")
        self.lbl_loc_val.configure(text="----")
        self.lbl_time_val.configure(text="----")
        self.lbl_status_val.configure(text="[ Système en veille active ]", text_color=TEXT_MUTED)
        self.lbl_photo_avatar.configure(image=None, text="[ ACCÈS ]\n[ EN ATTENTE ]")
        self.lbl_photo_avatar.image = None

    def simulate_realtime_detection_loop(self):
        """
        Boucle d'alerte / détection automatique de secours si la caméra est inactive.
        """
        simulated_detections = [
            {"nom": "LOMO NTEDE", "prenom": "JULIENNE CHRISTELLE", "cni": "CNI-2026-CH", "ville": "Yaoundé",
             "quartier": "Ngousso", "registered": True},
            {"nom": "DUPONT", "prenom": "JEAN", "cni": "CNI-2025-JD", "ville": "Yaoundé", "quartier": "Bastos",
             "registered": True},
            {"nom": "INCONNU", "prenom": "VISITEUR", "cni": "NEW_001", "ville": "Yaoundé", "quartier": "Centre",
             "registered": False}
        ]

        idx = 0
        while self.running_detection:
            time.sleep(7)
            person = self.get_random_person() or simulated_detections[idx % len(simulated_detections)]
            idx += 1

            name_key = person["nom"]
            now_ts = time.time()
            if name_key in self.recent_detections and now_ts - self.recent_detections[name_key] < self.deduplication_cooldown:
                continue
            self.recent_detections[name_key] = now_ts
            self.parent.after(0, lambda p=person: self.process_automatic_detection(p))

    def face_detection_loop(self):
        """Boucle réelle lisant la webcam, détectant les visages et effectuant la reconnaissance faciale."""
        while self.face_detection_running:
            try:
                cap = getattr(self.camera_feed, 'cap', None)
                if cap is None or not cap.isOpened():
                    time.sleep(0.5)
                    continue

                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.05)
                    continue

                self.camera_feed.set_latest_frame(frame)

                if self.face_cascade is None:
                    time.sleep(0.5)
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

                if len(faces) > 0:
                    # Sélectionner le plus grand visage détecté
                    x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
                    face_img = frame[y:y + h, x:x + w]

                    # Recadrage temporaire centré sur le visage dans le flux affiché.
                    frame_height, frame_width = frame.shape[:2]
                    target_ratio = self.camera_feed.size[0] / self.camera_feed.size[1]
                    crop_height = min(frame_height, max(h * 2, int(w * 2 / target_ratio)))
                    crop_width = min(frame_width, max(w * 2, int(crop_height * target_ratio)))
                    center_x, center_y = x + w // 2, y + h // 2
                    left = max(0, min(frame_width - crop_width, center_x - crop_width // 2))
                    top = max(0, min(frame_height - crop_height, center_y - crop_height // 2))
                    display_frame = frame[top:top + crop_height, left:left + crop_width].copy()

                    # Calcul des coordonnées normalisées pour le rectangle sur la vidéo
                    fh, fw = frame.shape[0], frame.shape[1]
                    x_norm = x / fw
                    y_norm = y / fh
                    w_norm = w / fw
                    h_norm = h / fh

                    # Reconnaissance faciale par comparaison ORB avec les profils locaux.
                    matched = self.match_face(face_img)

                    if matched:
                        # Visage Reconnu
                        frame_color = (0, 255, 0)
                        cni = matched.get('cni', '')
                        now_ts = time.time()
                        should_log = (
                            cni not in self.recent_detections
                            or (now_ts - self.recent_detections[cni]) > self.deduplication_cooldown
                        )
                        if should_log:
                            self.recent_detections[cni] = now_ts
                        person_data = {
                            "cni": matched.get('cni', ''),
                            "nom": matched.get('nom', ''),
                            "prenom": matched.get('prenom', ''),
                            "ville": matched.get('ville', ''),
                            "quartier": matched.get('quartier', ''),
                            "poste": matched.get('poste', 'Personnel'),
                            "photo_path": matched.get('photo_path', ''),
                            "face_img": face_img.copy(),
                            "registered": True
                        }
                        self.parent.after(
                            0,
                            lambda p=person_data, log=should_log: self.process_automatic_detection(p, log)
                        )
                    else:
                        # Visage Inconnu
                        frame_color = (0, 0, 255)
                        now_ts = time.time()
                        unk_key = "UNKNOWN_FACE"

                        if unk_key not in self.recent_detections or (now_ts - self.recent_detections[unk_key]) > self.deduplication_cooldown:
                            self.recent_detections[unk_key] = now_ts
                            self.parent.after(0, lambda f=face_img.copy(): self._handle_unknown_detection(f))

                    relative_x = x - left
                    relative_y = y - top
                    cv2.rectangle(
                        display_frame,
                        (relative_x, relative_y),
                        (relative_x + w, relative_y + h),
                        frame_color,
                        3,
                    )
                    self.camera_feed.set_focus_frame(display_frame)
                    self.camera_feed.set_overlay(None)

                else:
                    self.camera_feed.set_overlay(None)
                    self.camera_feed.set_focus_frame(None)

                time.sleep(0.1)
            except Exception:
                time.sleep(0.5)
                continue

    def _handle_unknown_detection(self, face_img):
        """Affiche l'alerte d'un visage inconnu et propose l'enregistrement."""
        if self._prompt_active:
            return
        self._prompt_active = True

        self._display_person_info(
            cni="INCONNU", nom="VISAGE", prenom="NON IDENTIFIÉ",
            poste="Zone de Surveillance", ville="Inconnue", quartier="Inconnu",
            face_img=face_img,
            status_text="▲ ALERTE : VISAGE NON RECONNU", status_color=DANGER_RED,
            welcome_text="<< ALERTE : INCONNU DÉTECTÉ >>", welcome_color=DANGER_RED
        )

        try:
            ask = messagebox.askyesno('Personne inconnue', 'Un visage non reconnu a été détecté.\nVoulez-vous enregistrer cette personne ?')
            db.execute(
                f'INSERT INTO "{TABLE_INTRUS}" (photo, piece, date_heure, remarque) VALUES (%s, %s, %s, %s);',
                ("", "Zone de surveillance", datetime.now(), "Visage non reconnu"),
            )
            if ask:
                if self.controller and hasattr(self.controller, "switch_tab"):
                    self.controller.switch_tab(1)
        finally:
            self._prompt_active = False

    def process_automatic_detection(self, person, save_log=True):
        """Traite l'affichage dynamique de la détection et remplit la fiche d'information complète."""
        nom = person.get("nom", "")
        prenom = person.get("prenom", "")
        cni = person.get("cni", "")
        poste = person.get("poste", "Accueil / Surveillance")
        ville = person.get("ville", "")
        quartier = person.get("quartier", "")
        photo_path = person.get("photo_path", "")
        face_img = person.get("face_img")
        registered = person.get("registered", False)

        if prenom and ("CHRISTELLE" in prenom.upper() or "LOMO" in nom.upper()):
            welcome_text = "<< BIENVENUE CHRISTELLE >>"
        elif prenom:
            welcome_text = f"<< BIENVENUE {prenom.upper()} >>"
        else:
            welcome_text = "<< BIENVENUE >>"

        if registered:
            status_text = "● ACCÈS AUTORISÉ (Profil local)"
            status_color = SUCCESS_GREEN
        else:
            status_text = "▲ ALERTE : INCONNU NON RECONNU"
            status_color = DANGER_RED

        self._display_person_info(
            cni=cni, nom=nom, prenom=prenom, poste=poste,
            ville=ville, quartier=quartier, photo_path=photo_path, face_img=face_img,
            status_text=status_text, status_color=status_color,
            welcome_text=welcome_text, welcome_color=WELCOME_GREEN if registered else DANGER_RED
        )

        # Mise à jour de la carte interactive Google Maps via tkintermapview
        if tkintermapview and hasattr(self, "map_widget") and (quartier or ville):
            adresse = f"{quartier}, {ville}".strip(', ')
            if adresse:
                try:
                    self.map_widget.set_address(adresse, marker=True)
                    self.map_widget.set_zoom(15)
                except Exception:
                    pass

        # Enregistrement automatique des passages dans le fichier des accès.
        try:
            if save_log:
                db.execute(
                    f'INSERT INTO "{TABLE_LOGS}" (cni, date_heure, piece, statut) VALUES (%s, %s, %s, %s);',
                    (cni, datetime.now(), "Zone de surveillance",
                     "Détecté - Autorisé" if registered else "Détecté - Alerte Inconnu")
                )
            
            # Génération automatique du rapport PDF si la personne est enregistrée en BD
            if registered and save_log:
                try:
                    pdf_path = generate_person_pdf_report(person)
                    if pdf_path:
                        self.lbl_db_status.configure(
                            text=f"STATUT : RAPPORT PDF GÉNÉRÉ ({os.path.basename(pdf_path)})",
                            text_color=SUCCESS_GREEN
                        )
                    else:
                        self.lbl_db_status.configure(text="STATUT D'ENREGISTREMENT : ACCÈS SAUVEGARDÉ EN JSON",
                                                     text_color=SUCCESS_GREEN)
                except Exception:
                    self.lbl_db_status.configure(text="STATUT D'ENREGISTREMENT : ACCÈS SAUVEGARDÉ EN JSON",
                                                 text_color=SUCCESS_GREEN)
            elif save_log:
                self.lbl_db_status.configure(text="STATUT D'ENREGISTREMENT : ACCÈS SAUVEGARDÉ EN JSON",
                                             text_color=SUCCESS_GREEN)
        except Exception:
            self.lbl_db_status.configure(text="STATUT D'ENREGISTREMENT : DÉTECTÉ (LOG NON SYNCHRONISÉ)",
                                         text_color="#f1c40f")

        if save_log and self.controller and hasattr(self.controller, 'activity_log'):
            self.controller.activity_log.append(
                {
                    'source': 'Dashboard',
                    'time': datetime.now(),
                    'message': f"Détection {cni} - {'Autorisé' if registered else 'Inconnu'}"
                }
            )

    def match_face(self, face_img, max_candidates=50, match_threshold=38.0):
        """Essaie de retrouver un visage correspondant parmi les profils enregistrés en base (comparaison matricielle).
        Retourne un dict {cni, nom, prenom, photo_path, ville, quartier, poste, face_id} ou None.
        """
        if cv2 is None or face_img is None:
            return None
        try:
            rows = db.fetch_all(f'SELECT cni, nom, prenom, photo_path, ville, quartier, face_id, poste FROM "{TABLE_PERSONNE}";')
            if not rows:
                return None

            current_face_id = extract_face_id(face_img, None)
            if not current_face_id:
                return None

            best_match = None
            min_distance = float('inf')

            for cni, nom, prenom, photo_path, ville, quartier, face_id, poste in rows:
                # Si le face_id est absent mais qu'une photo existe, essayer d'extraire la matrice
                if not face_id and photo_path:
                    face_id = extract_face_id_from_path(photo_path, self.face_cascade)
                    if face_id:
                        try:
                            db.update_record(TABLE_PERSONNE, cni, {"face_id": face_id}, key="cni")
                        except Exception:
                            pass

                if not face_id:
                    continue

                matched, distance = compare_face_ids(current_face_id, face_id, threshold=match_threshold)
                if matched and distance is not None and distance < min_distance:
                    min_distance = distance
                    best_match = {
                        'cni': cni,
                        'nom': nom,
                        'prenom': prenom,
                        'photo_path': photo_path or '',
                        'ville': ville or '',
                        'quartier': quartier or '',
                        'poste': poste or 'Accueil',
                        'face_id': face_id,
                        'distance': distance
                    }

            return best_match
        except Exception as err:
            print(f"[Match Face Error] {err}")
            return None

    def save_profile(self):
        """Sauvegarde manuelle ou mise à jour dans le fichier des profils."""
        nom = self.entry_nom.get().strip()
        prenom = self.entry_prenom.get().strip()
        cni = self.entry_cni.get().strip()
        ville = self.entry_ville.get().strip()
        quartier = self.entry_quartier.get().strip()
        empreinte = self.entry_empreinte.get().strip()
        poste = self.poste_option.get()

        if not nom or not cni:
            messagebox.showerror("Erreur", "Le Nom et le CNI/ID sont obligatoires !")
            return

        is_dup, err_msg, _ = db.check_duplicate_person(cni=cni, nom=nom, prenom=prenom, exclude_cni=cni)
        if is_dup:
            messagebox.showerror("Doublon Détecté", err_msg)
            return

        try:
            people = db.read_table(TABLE_PERSONNE) or []
            existing = next((p for p in people if str(p.get("cni", "")).upper() == cni.upper()), None)
            if existing:
                existing.update({
                    "nom": nom, "prenom": prenom, "ville": ville,
                    "quartier": quartier, "empreinte_digitale": empreinte, "poste": poste
                })
            else:
                people.append({
                    "cni": cni, "nom": nom, "prenom": prenom, "ville": ville,
                    "quartier": quartier, "empreinte_digitale": empreinte, "poste": poste,
                    "date_enregistrement": datetime.now().isoformat(timespec="seconds"),
                })
            db.write_table(TABLE_PERSONNE, people)
            self.lbl_db_status.configure(text="STATUT D'ENREGISTREMENT : SUCCÈS (JSON)", text_color=SUCCESS_GREEN)
            messagebox.showinfo("Succès", f"Profil de {prenom} {nom} enregistré avec succès dans les fichiers JSON !")
        except Exception as e:
            messagebox.showerror("Erreur JSON", f"Erreur lors de l'enregistrement : {str(e)}")

    def upload_photo(self):
        cni = self.entry_cni.get().strip()
        if not cni:
            messagebox.showerror("Erreur", "Veuillez saisir le CNI/ID avant d'importer une photo.")
            return

        filetypes = [("Images", "*.png *.jpg *.jpeg *.bmp"), ("Tous les fichiers", "*")]
        file_path = filedialog.askopenfilename(title="Sélectionner une photo de référence", filetypes=filetypes)
        if not file_path:
            return

        if not os.path.isfile(file_path):
            messagebox.showerror("Erreur", "Le fichier sélectionné est introuvable.")
            return

        nom = self.entry_nom.get().strip()
        prenom = self.entry_prenom.get().strip()
        ville = self.entry_ville.get().strip()
        quartier = self.entry_quartier.get().strip()
        empreinte = self.entry_empreinte.get().strip()
        poste = self.poste_option.get()

        try:
            face_id = extract_face_id_from_path(file_path, self.face_cascade)
            serializable_face_id = face_id.tolist() if hasattr(face_id, "tolist") else face_id
            is_dup, err_msg, _ = db.check_duplicate_person(cni=cni, nom=nom, prenom=prenom, face_id=serializable_face_id, photo_path=file_path, exclude_cni=cni)
            if is_dup:
                messagebox.showerror("Enregistrement Refusé - Doublon Détecté", err_msg)
                return

            people = db.read_table(TABLE_PERSONNE) or []
            existing = next((p for p in people if str(p.get("cni", "")).upper() == cni.upper()), None)
            if existing:
                existing.update({
                    "nom": nom or existing.get("nom"),
                    "prenom": prenom or existing.get("prenom"),
                    "ville": ville or existing.get("ville"),
                    "quartier": quartier or existing.get("quartier"),
                    "photo_path": file_path,
                    "face_id": serializable_face_id,
                    "empreinte_digitale": empreinte or existing.get("empreinte_digitale"),
                    "poste": poste or existing.get("poste"),
                })
            else:
                people.append({
                    "cni": cni, "nom": nom, "prenom": prenom, "ville": ville,
                    "quartier": quartier, "photo_path": file_path, "face_id": serializable_face_id,
                    "empreinte_digitale": empreinte, "poste": poste,
                    "date_enregistrement": datetime.now().isoformat(timespec="seconds"),
                })
            db.write_table(TABLE_PERSONNE, people)
            self.lbl_db_status.configure(text="STATUT D'ENREGISTREMENT : PHOTO ET MATRICE ENREGISTRÉES", text_color=SUCCESS_GREEN)
            messagebox.showinfo("Succès", "Photo et matrice faciale associées au profil et enregistrées dans les fichiers JSON.")
        except Exception as e:
            messagebox.showerror("Erreur JSON", f"Impossible d'enregistrer la photo : {str(e)}")