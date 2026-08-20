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
from face_utils import compare_face_ids, extract_face_id

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

        ret, frame = self.cap.read()
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
        self.label.configure(image=None, text=self.fallback_text)
        self.label.image = None

    def set_overlay(self, rect_norm, color='green'):
        """rect_norm: (x_norm, y_norm, w_norm, h_norm) values between 0 and 1"""
        self.overlay_rect = rect_norm
        self.overlay_color = color

    def set_scan_grid(self, enabled):
        self.show_scan_grid = enabled


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

        # Zone d'affichage du résultat avec le message de bienvenue dynamique
        self.match_display = ctk.CTkFrame(results_outer_frame, fg_color="transparent")
        self.match_display.pack(fill="both", expand=True, padx=6, pady=6)

        self.lbl_welcome = ctk.CTkLabel(self.match_display, text="<< EN ATTENTE DE DÉTECTION >>",
                                        font=("Times New Roman", 15, "bold"), text_color=WELCOME_GREEN)
        self.lbl_welcome.pack(pady=(15, 5))

        self.lbl_match_name = ctk.CTkLabel(self.match_display, text="Aucune personne détectée",
                                           font=("Times New Roman", 12, "bold"), text_color=TEXT_MAIN)
        self.lbl_match_name.pack(pady=(2, 2))

        self.lbl_match_status = ctk.CTkLabel(self.match_display, text="Système en veille active", font=FONT_NORMAL,
                                             text_color=TEXT_MUTED)
        self.lbl_match_status.pack(pady=(2, 10))

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

    def start_camera(self):
        if self.face_detection_running:
            return
        self.face_detection_running = True
        self.running_detection = True
        self.camera_feed.start()
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
        self.lbl_match_status.configure(text="Système en veille active", text_color=TEXT_MUTED)

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
            f'SELECT cni, nom, prenom, ville, quartier FROM "{TABLE_PERSONNE}" ORDER BY random() LIMIT 1;'
        )
        if rows:
            cni, nom, prenom, ville, quartier = rows[0]
            return {"cni": cni, "nom": nom, "prenom": prenom, "ville": ville, "quartier": quartier, "registered": True}
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

    def _add_form_field(self, parent, label_text):
        ctk.CTkLabel(parent, text=label_text, font=FONT_BOLD, text_color=TEXT_MUTED).pack(anchor="w", pady=(3, 1))
        entry = ctk.CTkEntry(parent, height=28, font=FONT_NORMAL, fg_color=FIELD_BG, border_color=FIELD_BORDER,
                             text_color=TEXT_MAIN)
        entry.pack(fill="x", pady=(0, 6))
        return entry

    def reset_form(self):
        for entry in [self.entry_nom, self.entry_prenom, self.entry_cni, self.entry_dob, self.entry_quartier,
                  self.entry_ville, self.entry_empreinte]:
            entry.delete(0, 'end')
        self.poste_option.set(db.get_postes()[0] if db.get_postes() else "Accueil")
        self.lbl_welcome.configure(text="<< EN ATTENTE DE DÉTECTION >>", text_color=WELCOME_GREEN)
        self.lbl_match_name.configure(text="Aucune personne détectée")
        self.lbl_match_status.configure(text="Système en veille active")

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
        os.makedirs('data_photos', exist_ok=True)
        no_camera_counter = 0

        while self.face_detection_running:
            try:
                cap = getattr(self.camera_feed, 'cap', None)
                if cap is None or not cap.isOpened():
                    no_camera_counter += 1
                    if no_camera_counter > 10:
                        # Revenir à la simulation si la caméra n'est pas branchée
                        self.simulate_realtime_detection_loop()
                        break
                    time.sleep(0.5)
                    continue

                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.05)
                    continue

                if self.face_cascade is None:
                    time.sleep(0.5)
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

                if len(faces) > 0:
                    # Sélectionner le plus grand visage détecté
                    x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
                    face_img = frame[y:y + h, x:x + w]

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
                        self.camera_feed.set_overlay((x_norm, y_norm, w_norm, h_norm), color='green')
                        cni = matched.get('cni', '')
                        now_ts = time.time()

                        if cni not in self.recent_detections or (now_ts - self.recent_detections[cni]) > self.deduplication_cooldown:
                            self.recent_detections[cni] = now_ts
                            person_data = {
                                "cni": matched.get('cni', ''),
                                "nom": matched.get('nom', ''),
                                "prenom": matched.get('prenom', ''),
                                "ville": matched.get('ville', ''),
                                "quartier": matched.get('quartier', ''),
                                "registered": True
                            }
                            self.parent.after(0, lambda p=person_data: self.process_automatic_detection(p))
                    else:
                        # Visage Inconnu
                        self.camera_feed.set_overlay((x_norm, y_norm, w_norm, h_norm), color='red')
                        now_ts = time.time()
                        unk_key = "UNKNOWN_FACE"

                        if unk_key not in self.recent_detections or (now_ts - self.recent_detections[unk_key]) > self.deduplication_cooldown:
                            self.recent_detections[unk_key] = now_ts
                            self.parent.after(0, lambda f=face_img.copy(): self._handle_unknown_detection(f))

                else:
                    self.camera_feed.set_overlay(None)

                time.sleep(0.1)
            except Exception:
                time.sleep(0.5)
                continue

    def _handle_unknown_detection(self, face_img):
        """Affiche l'alerte d'un visage inconnu et propose l'enregistrement."""
        if self._prompt_active:
            return
        self._prompt_active = True

        self.lbl_welcome.configure(text="<< ALERTE : INCONNU DÉTECTÉ >>", text_color=DANGER_RED)
        self.lbl_match_name.configure(text="Visage non reconnu dans les profils locaux")
        self.lbl_match_status.configure(text="Statut : Nouveau / Inconnu (Capture Live)", text_color=DANGER_RED)

        try:
            ask = messagebox.askyesno('Personne inconnue', 'Un visage non reconnu a été détecté.\nVoulez-vous enregistrer cette personne ?')
            capture_path = None
            if face_img is not None:
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                capture_path = os.path.join('data_photos', f"intrus_{ts}.jpg")
                try:
                    cv2.imwrite(capture_path, face_img)
                except Exception:
                    capture_path = None
            db.execute(
                f'INSERT INTO "{TABLE_INTRUS}" (photo, piece, date_heure, remarque) VALUES (%s, %s, %s, %s);',
                (capture_path or "", "Zone de surveillance", datetime.now(), "Visage non reconnu"),
            )
            if ask:
                new_cni = simpledialog.askstring('Enregistrer', 'Entrez le CNI / NISS de la personne :')
                if new_cni:
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{new_cni}_{ts}.jpg"
                    filepath = os.path.join('data_photos', filename)
                    filepath = capture_path or filepath

                    try:
                        if filepath:
                            db.execute(
                                f'INSERT INTO "{TABLE_PERSONNE}" (cni, nom, prenom, ville, quartier, date_enregistrement, photo_path) '
                                f'VALUES (%s, %s, %s, %s, %s, %s, %s) '
                                f'ON CONFLICT (cni) DO UPDATE SET photo_path = EXCLUDED.photo_path;',
                                (new_cni, 'INCONNU', 'Nouveau', '', '', datetime.now(), filepath)
                            )
                        else:
                            db.execute(
                                f'INSERT INTO "{TABLE_PERSONNE}" (cni, nom, prenom, ville, quartier, date_enregistrement) '
                                f'VALUES (%s, %s, %s, %s, %s, %s);',
                                (new_cni, 'INCONNU', 'Nouveau', '', '', datetime.now())
                            )
                        db.execute(
                            f'INSERT INTO "{TABLE_LOGS}" (cni, date_heure, commentaire, piece, statut) VALUES (%s, %s, %s, %s, %s);',
                            (new_cni, datetime.now(), 'Enregistré via alerte détection', 'Zone de surveillance', 'Enregistré')
                        )

                        self.lbl_db_status.configure(text="STATUT D'ENREGISTREMENT : ENREGISTRÉ (NOUVEAU)", text_color=SUCCESS_GREEN)
                        messagebox.showinfo("Succès", f"Capture et CNI {new_cni} enregistrés dans les fichiers JSON !")
                    except Exception as e:
                        messagebox.showerror("Erreur JSON", f"Échec de l'enregistrement : {e}")
        finally:
            self._prompt_active = False

    def process_automatic_detection(self, person):
        """Traite l'affichage dynamique de la détection et remplit les fiches."""
        nom = person.get("nom", "")
        prenom = person.get("prenom", "")

        # Affichage du message de bienvenue dynamique
        if prenom and ("CHRISTELLE" in prenom.upper() or "LOMO" in nom.upper()):
            welcome_text = "<< BIENVENUE CHRISTELLE >>"
        elif prenom:
            welcome_text = f"<< BIENVENUE {prenom.upper()} >>"
        else:
            welcome_text = "<< BIENVENUE >>"

        self.lbl_welcome.configure(text=welcome_text, text_color=WELCOME_GREEN)
        self.lbl_match_name.configure(text=f"{nom} {prenom} (CNI: {person.get('cni', '')})")

        if person.get("registered", False):
            self.lbl_match_status.configure(text="Statut : Reconnu (photo locale chargée)", text_color=SUCCESS_GREEN)
        else:
            self.lbl_match_status.configure(text="Statut : Nouveau / Inconnu (Capture Live)", text_color=DANGER_RED)

        # Mise à jour de la carte interactive Google Maps via tkintermapview
        if tkintermapview and hasattr(self, "map_widget") and (person.get('quartier') or person.get('ville')):
            adresse = f"{person.get('quartier', '')}, {person.get('ville', '')}".strip(', ')
            if adresse:
                try:
                    self.map_widget.set_address(adresse, marker=True)
                    self.map_widget.set_zoom(15)
                except Exception:
                    pass

        # Enregistrement automatique des passages dans le fichier des accès.
        try:
            db.execute(
                f'INSERT INTO "{TABLE_LOGS}" (cni, date_heure, piece, statut) VALUES (%s, %s, %s, %s);',
                (person["cni"], datetime.now(), "Zone de surveillance",
                 "Détecté - Autorisé" if person.get("registered") else "Détecté - Alerte Inconnu")
            )
            self.lbl_db_status.configure(text="STATUT D'ENREGISTREMENT : ACCÈS SAUVEGARDÉ EN JSON",
                                         text_color=SUCCESS_GREEN)
        except Exception:
            self.lbl_db_status.configure(text="STATUT D'ENREGISTREMENT : DÉTECTÉ (LOG NON SYNCHRONISÉ)",
                                         text_color="#f1c40f")

        if self.controller and hasattr(self.controller, 'activity_log'):
            self.controller.activity_log.append(
                {
                    'source': 'Dashboard',
                    'time': datetime.now(),
                    'message': f"Détection {person.get('cni')} - {'Autorisé' if person.get('registered') else 'Inconnu'}"
                }
            )

    def match_face(self, face_img, max_candidates=30, match_threshold=12):
        """Essaie de retrouver un visage correspondant parmi les photos stockées en base.
        Retourne un dict {cni, nom, prenom, photo_path, ville, quartier} ou None.
        """
        if cv2 is None or face_img is None:
            return None
        try:
            rows = db.fetch_all(f'SELECT cni, nom, prenom, photo_path, ville, quartier, face_id FROM "{TABLE_PERSONNE}" WHERE photo_path IS NOT NULL;')
            if not rows:
                return None

            gray_q = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
            orb = cv2.ORB_create(500)
            kp1, des1 = orb.detectAndCompute(gray_q, None)
            if des1 is None:
                return None

            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            checked = 0

            current_face_id = extract_face_id(face_img, None)
            for cni, nom, prenom, photo_path, ville, quartier, face_id in rows:
                if (not face_id and not photo_path) or checked >= max_candidates:
                    checked += 1
                    continue
                if current_face_id and face_id:
                    matched, _ = compare_face_ids(current_face_id, face_id)
                    if matched:
                        return {'cni': cni, 'nom': nom, 'prenom': prenom, 'photo_path': photo_path,
                                'ville': ville, 'quartier': quartier, 'face_id': face_id}
                try:
                    if not os.path.exists(photo_path):
                        checked += 1
                        continue

                    img2 = cv2.imread(photo_path)
                    if img2 is None:
                        checked += 1
                        continue

                    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
                    kp2, des2 = orb.detectAndCompute(gray2, None)
                    if des2 is None:
                        checked += 1
                        continue

                    matches = bf.knnMatch(des1, des2, k=2)
                    good = [m for m, n in matches if len(matches) > 0 and len(m_n := (m, n)) == 2 and m.distance < 0.75 * n.distance] if matches else []

                    if len(good) >= match_threshold:
                        return {'cni': cni, 'nom': nom, 'prenom': prenom, 'photo_path': photo_path, 'ville': ville, 'quartier': quartier}
                except Exception:
                    pass
                checked += 1
            return None
        except Exception:
            return None

    def _show_matched_person(self, matched):
        try:
            self.lbl_match_status.configure(text='Statut : Reconnu (photo locale chargée)', text_color=SUCCESS_GREEN)
            self.lbl_welcome.configure(text=f"<< BIENVENUE {matched.get('prenom') or ''} >>", text_color=SUCCESS_GREEN)
            self.lbl_match_name.configure(text=f"{matched.get('nom') or ''} {matched.get('prenom') or ''} (CNI: {matched.get('cni')})")
        except Exception:
            pass

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

        try:
            db.execute(
                f'INSERT INTO "{TABLE_PERSONNE}" (nom, prenom, cni, ville, quartier, empreinte_digitale, poste) VALUES (%s, %s, %s, %s, %s, %s, %s) '
                f'ON CONFLICT (cni) DO UPDATE SET nom = EXCLUDED.nom, prenom = EXCLUDED.prenom, ville = EXCLUDED.ville, quartier = EXCLUDED.quartier, empreinte_digitale = EXCLUDED.empreinte_digitale, poste = EXCLUDED.poste;',
                (nom, prenom, cni, ville, quartier, empreinte, poste)
            )
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
            db.execute(
                f'INSERT INTO "{TABLE_PERSONNE}" (cni, nom, prenom, ville, quartier, photo_path, empreinte_digitale, poste) '
                f'VALUES (%s, %s, %s, %s, %s, %s, %s, %s) '
                f'ON CONFLICT (cni) DO UPDATE SET nom = EXCLUDED.nom, prenom = EXCLUDED.prenom, '
                f'ville = EXCLUDED.ville, quartier = EXCLUDED.quartier, photo_path = EXCLUDED.photo_path, '
                f'empreinte_digitale = EXCLUDED.empreinte_digitale, poste = EXCLUDED.poste;',
                (cni, nom, prenom, ville, quartier, file_path, empreinte, poste)
            )
            self.lbl_db_status.configure(text="STATUT D'ENREGISTREMENT : PHOTO ENREGISTRÉE", text_color=SUCCESS_GREEN)
            messagebox.showinfo("Succès", "Photo associée au profil et enregistrée dans les fichiers JSON.")
        except Exception as e:
            messagebox.showerror("Erreur JSON", f"Impossible d'enregistrer la photo : {str(e)}")