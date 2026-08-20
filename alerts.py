# page_alertes.py
# Onglet Alertes : Reproduction exacte du design (4 quadrants : Journal, Monitoring/Analyse, Carte Géo, Paramètres/Seuils)

import customtkinter as ctk
from tkinter import messagebox
import time
import threading
from datetime import datetime

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

# Configuration et styles cohérents avec le projet
from config import FONT_NORMAL, FONT_BOLD, ACCENT_COLOR, TABLE_PERSONNE, TABLE_LOGS, TABLE_ZONE, TABLE_INTRUS
from dashboard import WebcamPanel
import db

# --- Palette de couleurs (Thème Sombre / SOC) ---
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
DANGER_RED = "#c0392b"
ALERT_ORANGE = "#d35400"


class AlertesPage:
    def __init__(self, parent, controller=None):
        self.controller = controller
        parent.configure(fg_color=PAGE_BG)

        # Configuration de la grille principale en 2x2 (4 quadrants)
        parent.grid_columnconfigure(0, weight=50)
        parent.grid_columnconfigure(1, weight=50)
        parent.grid_rowconfigure(0, weight=50)
        parent.grid_rowconfigure(1, weight=50)

        # =========================================================
        # QUADRANT 1 (HAUT-GAUCHE) : LOG ET PRIORISATION DES ALERTES
        # =========================================================
        q1_frame = ctk.CTkFrame(parent, fg_color=PANEL_BG, border_width=1, border_color=FIELD_BORDER)
        q1_frame.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self._create_section_title(q1_frame, "LOG ET PRIORISATION DES ALERTES",
                                   "JOURNAL D'ALERTES PRIORISÉES (TEMPS RÉEL)")

        # Contenu Tableau des Alertes
        table_container = ctk.CTkFrame(q1_frame, fg_color="#10171d", border_width=1, border_color=FIELD_BORDER)
        table_container.pack(fill="both", expand=True, padx=8, pady=(2, 6))

        # En-têtes du tableau
        headers_frame = ctk.CTkFrame(table_container, fg_color=SEPARATOR_COLOR, height=28)
        headers_frame.pack(fill="x", padx=2, pady=2)
        headers_frame.pack_propagate(False)

        cols = [("ID", 45), ("PRIORITÉ", 85), ("NATURE DE L'ALERTE", 210), ("HEURE", 65), ("ACTIONS", 110)]
        for col_name, width in cols:
            ctk.CTkLabel(headers_frame, text=col_name, font=("Times New Roman", 10, "bold"), text_color=TEXT_MAIN,
                         width=width).pack(side="left", padx=2)

        # Liste scrollable des alertes
        self.alerts_scroll = ctk.CTkScrollableFrame(table_container, fg_color="transparent")
        self.alerts_scroll.pack(fill="both", expand=True, padx=2, pady=2)

        # Remplissage des fausses alertes temps réel inspirées de l'image
        self.selected_alert_sound = "Bip standard"
        self.populate_initial_alerts()
        if self.controller and hasattr(self.controller, 'activity_log'):
            self.controller.activity_log.append(
                {'source': 'Alertes', 'time': datetime.now(),
                 'message': 'Onglet Alertes ouvert et initialisé'}
            )

        # Boutons d'actions globales en bas du Quadrant 1
        actions_bar = ctk.CTkFrame(q1_frame, fg_color="transparent")
        actions_bar.pack(fill="x", padx=8, pady=(0, 6))

        ctk.CTkButton(actions_bar, text="ACKNOWLEDGE ALL", fg_color=DANGER_RED, hover_color="#a93226", height=28,
                      font=("Times New Roman", 9, "bold"), width=110).pack(side="left", padx=2)
        ctk.CTkButton(actions_bar, text="MOBILIZE UNIT", fg_color=ALERT_ORANGE, hover_color="#b9770e", height=28,
                      font=("Times New Roman", 9, "bold"), width=110).pack(side="left", padx=2)
        ctk.CTkButton(actions_bar, text="CONTACT RESP", fg_color=TEAL, hover_color=TEAL_HOVER, height=28,
                      font=("Times New Roman", 9, "bold"), width=110).pack(side="left", padx=2)
        ctk.CTkButton(actions_bar, text="VOIR LES INTRUSIONS", fg_color=ACCENT_COLOR, hover_color="#2563eb", height=28,
                  font=("Times New Roman", 9, "bold"), width=130, command=self.show_intrusions).pack(side="right", padx=2)

        # =========================================================
        # QUADRANT 2 (HAUT-DROIT) : MONITORING VISUEL & ANALYSE DE FLUX
        # =========================================================
        q2_frame = ctk.CTkFrame(parent, fg_color=PANEL_BG, border_width=1, border_color=FIELD_BORDER)
        q2_frame.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        self._create_section_title(q2_frame, "MONITORING VISUEL & ANALYSE DE FLUX",
                                   "CAMÉRAS ACTIVES & RECONNAISSANCE FACIALE (SOC)")

        q2_content = ctk.CTkFrame(q2_frame, fg_color="transparent")
        q2_content.pack(fill="both", expand=True, padx=8, pady=6)

        # Mini flux caméras (Simulés avec encadrés rouges comme sur l'image)
        cams_top = ctk.CTkFrame(q2_content, fg_color="transparent")
        cams_top.pack(fill="x", pady=(0, 6))

        cam3_box = ctk.CTkFrame(cams_top, fg_color="#10171d", border_width=1, border_color=FIELD_BORDER, height=110)
        cam3_box.pack(side="left", fill="both", expand=True, padx=(0, 4))
        cam3_box.pack_propagate(False)
        ctk.CTkLabel(cam3_box, text="Cam 3 [Lobby - Entrée Principale]", font=("Times New Roman", 9, "bold"),
                     text_color=TEXT_MUTED).pack(anchor="nw", padx=4, pady=2)
        ctk.CTkLabel(cam3_box, text="🔴 [LIVE STREAM - SOC ACTIVE]", font=("Times New Roman", 11, "bold"),
                     text_color=DANGER_RED).pack(expand=True)

        cam2_box = ctk.CTkFrame(cams_top, fg_color="#10171d", border_width=1, border_color=FIELD_BORDER, height=110)
        cam2_box.pack(side="right", fill="both", expand=True, padx=(4, 0))
        cam2_box.pack_propagate(False)
        ctk.CTkLabel(cam2_box, text="Cam 2 [Couloir Zone Sensible]", font=("Times New Roman", 9, "bold"),
                     text_color=TEXT_MUTED).pack(anchor="nw", padx=4, pady=2)
        ctk.CTkLabel(cam2_box, text="🔴 [LIVE STREAM - SOC ACTIVE]", font=("Times New Roman", 11, "bold"),
                     text_color=DANGER_RED).pack(expand=True)

        live_cam_box = ctk.CTkFrame(q2_content, fg_color="#10171d", border_width=1, border_color=FIELD_BORDER, height=180)
        live_cam_box.pack(fill="x", pady=(6, 0))
        live_cam_box.pack_propagate(False)
        ctk.CTkLabel(live_cam_box, text="Caméra Inactive - PC Webcam", font=("Times New Roman", 10, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="nw", padx=6, pady=4)

        self.alerts_webcam = WebcamPanel(live_cam_box, size=(620, 150), fallback_text="[ Caméra indisponible ou non accessible ]")
        self.alerts_capture = self.alerts_webcam.cap
        camera_actions = ctk.CTkFrame(q2_content, fg_color="transparent")
        camera_actions.pack(fill="x", pady=(4, 4))
        self.camera_start_button = ctk.CTkButton(
            camera_actions, text="LANCER LA CAMÉRA", height=28, fg_color=TEAL,
            hover_color=TEAL_HOVER, command=self.start_alert_camera,
        )
        self.camera_start_button.pack(side="left", expand=True, fill="x", padx=(0, 3))
        self.camera_stop_button = ctk.CTkButton(
            camera_actions, text="ARRÊTER LA CAMÉRA", height=28, fg_color=DANGER_RED,
            hover_color="#a93226", state="disabled", command=self.stop_alert_camera,
        )
        self.camera_stop_button.pack(side="left", expand=True, fill="x", padx=(3, 0))

        # Cadre Analyse Faciale & Identification (Bas du Quadrant 2)
        face_analysis_frame = ctk.CTkFrame(q2_content, fg_color="#10171d", border_width=1, border_color=FIELD_BORDER)
        face_analysis_frame.pack(fill="both", expand=True, pady=(2, 0))

        ctk.CTkLabel(face_analysis_frame, text="ANALYSE FACIALE & IDENTIFICATION (PROFILS LOCAUX)",
                     font=("Times New Roman", 10, "bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=6, pady=4)

        fa_inner = ctk.CTkFrame(face_analysis_frame, fg_color="transparent")
        fa_inner.pack(fill="both", expand=True, padx=6, pady=4)

        # Boîte de détection simulant l'image
        detection_info = ctk.CTkFrame(fa_inner, fg_color=FIELD_BG, border_width=1, border_color=FIELD_BORDER)
        detection_info.pack(side="left", fill="both", expand=True, padx=(0, 4))
        ctk.CTkLabel(detection_info, text="VISAGE DÉTECTÉ :\nNON IDENTIFIÉ (Confiance: 95.2%)",
                     font=("Times New Roman", 10, "bold"), text_color=ALERT_ORANGE).pack(expand=True, padx=4, pady=4)

        db_ref_box = ctk.CTkFrame(fa_inner, fg_color=FIELD_BG, border_width=1, border_color=FIELD_BORDER, width=150)
        db_ref_box.pack(side="right", fill="y", padx=(4, 0))
        db_ref_box.pack_propagate(False)
        ctk.CTkLabel(db_ref_box, text="RÉFÉRENCE JSON\n[ Match : Inconnu ]", font=("Times New Roman", 9),
                     text_color=TEXT_MUTED).pack(expand=True, padx=4, pady=4)

        # =========================================================
        # QUADRANT 3 (BAS-GAUCHE) : ALERTES GÉO-LOCALISÉES & SUIVI
        # =========================================================
        q3_frame = ctk.CTkFrame(parent, fg_color=PANEL_BG, border_width=1, border_color=FIELD_BORDER)
        q3_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        self._create_section_title(q3_frame, "ALERTES GÉO-LOCALISÉES & SUIVI CARTOGRAPHIQUE",
                                   "CARTOGRAPHIE DES INCIDENTS (CHRATCERH / YAOUNDÉ)")

        q3_content = ctk.CTkFrame(q3_frame, fg_color="transparent")
        q3_content.pack(fill="both", expand=True, padx=8, pady=6)

        # Intégration Carte
        map_box = ctk.CTkFrame(q3_content, fg_color="#10171d", height=140, border_width=1, border_color=FIELD_BORDER)
        map_box.pack(fill="x", pady=(0, 4))
        map_box.pack_propagate(False)

        if tkintermapview:
            self.map_widget = tkintermapview.TkinterMapView(map_box, corner_radius=0)
            self.map_widget.pack(fill="both", expand=True)
            self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", max_zoom=22)
            self.map_widget.set_position(3.8480, 11.5021)  # Yaoundé
            self.map_widget.set_zoom(14)
            # Chargement dynamique des zones depuis la table TABLE_ZONE
            try:
                rows = db.fetch_all(f'SELECT zone_name, description, lat, lon FROM "{TABLE_ZONE}";')
                if rows:
                    for zone_name, description, lat, lon in rows:
                        try:
                            if lat is not None and lon is not None:
                                self.map_widget.set_marker(lat, lon, text=f"{zone_name} ({description or ''})")
                        except Exception:
                            pass
                else:
                    # fallback: marqueurs simulés
                    self.map_widget.set_marker(3.8490, 11.5030, text="Alerte #001 (Lobby)")
                    self.map_widget.set_marker(3.8470, 11.5010, text="Alerte #002 (Zone Restreinte)")
            except Exception:
                # si erreur DB, utiliser des marqueurs simulés
                self.map_widget.set_marker(3.8490, 11.5030, text="Alerte #001 (Lobby)")
                self.map_widget.set_marker(3.8470, 11.5010, text="Alerte #002 (Zone Restreinte)")
        else:
            ctk.CTkLabel(map_box, text="CARTE INTERACTIVE INDISPONIBLE", text_color=DANGER_RED, font=FONT_NORMAL).place(
                relx=0.5, rely=0.5, anchor="center")

        # Historique des positions bas de carte
        history_box = ctk.CTkFrame(q3_content, fg_color="#10171d", border_width=1, border_color=FIELD_BORDER)
        history_box.pack(fill="both", expand=True)
        ctk.CTkLabel(history_box, text="HISTORIQUE DES POSITIONS GÉO-LOGS", font=("Times New Roman", 9, "bold"),
                     text_color=TEXT_MUTED).pack(anchor="w", padx=6, pady=2)
        ctk.CTkLabel(history_box,
                     text="• GPS: 3.8490N, 11.5030E | 14:40:12 → Alerte Critique Lobby\n• GPS: 3.8470N, 11.5010E | 14:38:05 → Mouvement Suspect Zone Sécurisée",
                     font=("Times New Roman", 9), text_color=TEXT_MAIN).pack(anchor="w", padx=6, pady=2)

        # =========================================================
        # QUADRANT 4 (BAS-DROIT) : PARAMÈTRES SYSTÈME & SEUILS CRITIQUES
        # =========================================================
        q4_frame = ctk.CTkFrame(parent, fg_color=PANEL_BG, border_width=1, border_color=FIELD_BORDER)
        q4_frame.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)
        self._create_section_title(q4_frame, "PARAMÈTRES SYSTÈME D'ALERTE ET SEUILS CRITIQUES",
                                   "CONFIGURATION DES RÈGLES DE SÉCURITÉ & LOGS")

        q4_content = ctk.CTkFrame(q4_frame, fg_color="transparent")
        q4_content.pack(fill="both", expand=True, padx=8, pady=6)

        # 3 Blocs internes comme sur l'image
        b1 = ctk.CTkFrame(q4_content, fg_color="#10171d", border_width=1, border_color=FIELD_BORDER)
        b1.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(b1, text="1. SEUILS CRITIQUES DÉFINIS (SÉCURITÉ)", font=("Times New Roman", 10, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=6, pady=2)

        slider_frame = ctk.CTkFrame(b1, fg_color="transparent")
        slider_frame.pack(fill="x", padx=6, pady=2)
        ctk.CTkLabel(slider_frame, text="Confidence Threshold:", font=("Times New Roman", 9),
                     text_color=TEXT_MUTED).pack(side="left")

        self.slider_val = ctk.CTkLabel(slider_frame, text="90%", font=("Times New Roman", 10, "bold"),
                                       text_color=SUCCESS_GREEN)
        self.slider_val.pack(side="right")

        self.thresh_slider = ctk.CTkSlider(b1, from_=50, to=99, number_of_steps=49, progress_color=TEAL,
                                           button_color=TEAL_HOVER, height=14)
        self.thresh_slider.set(90)
        self.thresh_slider.pack(fill="x", padx=6, pady=(0, 4))

        b2 = ctk.CTkFrame(q4_content, fg_color="#10171d", border_width=1, border_color=FIELD_BORDER)
        b2.pack(fill="both", expand=True)
        ctk.CTkLabel(b2, text="2. JOURNAUX TECHNIQUES & MISES À JOUR JSON", font=("Times New Roman", 10, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=6, pady=2)

        ctk.CTkLabel(b2, text="Son d'alerte par défaut", font=("Times New Roman", 9), text_color=TEXT_MUTED).pack(
            anchor="w", padx=6, pady=(6, 2)
        )
        self.alert_sound_option = ctk.CTkOptionMenu(b2,
                                                    values=["Bip standard", "Sirène courte", "Tonalité discrète"],
                                                    command=self._on_alert_sound_change,
                                                    fg_color=FIELD_BG, button_color=SEPARATOR_COLOR,
                                                    height=28, font=FONT_NORMAL)
        self.alert_sound_option.set("Bip standard")
        self.alert_sound_option.pack(fill="x", padx=6, pady=(0, 8))

        logs_txt = ctk.CTkTextbox(b2, height=65, fg_color=FIELD_BG, text_color=TEXT_MUTED, font=("Times New Roman", 9),
                                  border_width=1, border_color=FIELD_BORDER)
        logs_txt.pack(fill="both", expand=True, padx=6, pady=4)
        logs_txt.insert("1.0",
                        "[INFO] Matching face -> No match found (ID: 104)\n[INFO] Matching face -> JSON Match: LOMO NTEDE Julienne (98.4%)\n[INFO] Capteur de Mouvement Actif - Cam 3\n[SUCCESS] Fichiers JSON synchronisés")
        logs_txt.configure(state="disabled")

    def _on_alert_sound_change(self, value):
        self.selected_alert_sound = value
        if self.controller and hasattr(self.controller, 'activity_log'):
            self.controller.activity_log.append(
                {'source': 'Alertes', 'time': datetime.now(), 'message': f"Son d'alerte sélectionné : {value}"}
            )

    def start_alert_camera(self):
        self.alerts_webcam.start()
        self.alerts_capture = self.alerts_webcam.cap
        self.camera_start_button.configure(state="disabled", text="CAMÉRA ACTIVE")
        self.camera_stop_button.configure(state="normal")

    def stop_alert_camera(self):
        self.alerts_webcam.stop()
        self.alerts_capture = None
        self.camera_start_button.configure(state="normal", text="LANCER LA CAMÉRA")
        self.camera_stop_button.configure(state="disabled")

    def show_intrusions(self):
        window = ctk.CTkToplevel(self.parent)
        window.title("Tentatives d'accès refusées")
        window.geometry("820x560")
        container = ctk.CTkScrollableFrame(window, fg_color="#0b0f19")
        container.pack(fill="both", expand=True, padx=12, pady=12)
        rows = db.read_table(TABLE_INTRUS)
        if not rows:
            ctk.CTkLabel(container, text="Aucune tentative refusée enregistrée.", font=FONT_BOLD,
                         text_color=TEXT_MUTED).pack(pady=30)
            return
        for incident in reversed(rows):
            card = ctk.CTkFrame(container, fg_color="#251515", border_width=1, border_color=DANGER_RED)
            card.pack(fill="x", pady=6)
            ctk.CTkLabel(card, text=f"{incident.get('piece', 'Zone inconnue')}  •  {incident.get('date_heure', '')}",
                         font=FONT_BOLD, text_color="#fecaca").pack(anchor="w", padx=12, pady=(10, 2))
            ctk.CTkLabel(card, text=f"Photo : {incident.get('photo', 'non disponible')}\n{incident.get('remarque', 'Aucune remarque')}",
                         font=FONT_NORMAL, text_color=TEXT_MAIN, justify="left", wraplength=760).pack(anchor="w", padx=12, pady=(0, 10))

    def _update_alerts_cam(self, container):
        if not self.alerts_capture:
            return
        ret, frame = self.alerts_capture.read()
        if ret and frame is not None:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                width = max(container.winfo_width() - 20, 200)
                frame = Image.fromarray(frame).resize((width, 140))
            except Exception:
                frame = Image.fromarray(frame).resize((360, 140))
            ctk_img = ctk.CTkImage(light_image=frame, dark_image=frame, size=(frame.size[0], frame.size[1]))
            self.alerts_cam_label.configure(image=ctk_img, text="")
            self.alerts_cam_label.image = ctk_img
        self.parent.after(100, lambda: self._update_alerts_cam(container))

    def _create_section_title(self, parent, main_title, sub_title):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=6, pady=(6, 2))
        ctk.CTkLabel(header, text=main_title, font=("Times New Roman", 11, "bold"), text_color=TEXT_MAIN).pack(
            anchor="w")
        ctk.CTkLabel(header, text=sub_title, font=("Times New Roman", 9), text_color=TEXT_MUTED).pack(anchor="w")
        ctk.CTkFrame(parent, fg_color=SEPARATOR_COLOR, height=2).pack(fill="x", padx=6, pady=(2, 4))

    def populate_initial_alerts(self):
        """Remplit le tableau des alertes avec des données de sécurité réalistes."""
        alerts_data = [
            ("#001", "🔴 CRITIQUE", "ALERTE SÉCURITÉ (Zone Lobby)", "14:40", "CONTACT RESP."),
            ("#002", "⚠️ ATTENTION", "PERSONNE NON-IDENTIFIÉE (Cam 3)", "14:38", "MOBILIZE UNIT"),
            ("#003", "⚠️ ATTENTION", "DÉVIATION DE VALEUR (Zone Sécurisée)", "14:35", "ACKNOWLEDGE"),
            ("#004", "⚠️ ATTENTION", "DÉVIATION DE VALEUR (Taux Intrusion)", "14:35", "ACKNOWLEDGE"),
            ("#005", "⚠️ ATTENTION", "INTTRUSION DÉTECTÉE (Bloc Opératoire)", "14:33", "MOBILIZE UNIT"),
            ("#006", "ℹ️ INFO", "ACCÈS PERSONNEL (LOMO Julienne)", "14:32", "FILTRAGE"),
            ("#007", "ℹ️ INFO", "ACCÈS PERSONNEL (Dr. Dupont)", "14:32", "FILTRAGE"),
            ("#008", "ℹ️ INFO", "MAINTENANCE SYSTÈME (Cam 2)", "14:30", "ARCHIVÉ"),
        ]

        for aid, prio, desc, time_str, action in alerts_data:
            row_frame = ctk.CTkFrame(self.alerts_scroll, fg_color="#11171d", height=26, corner_radius=2)
            row_frame.pack(fill="x", pady=2)
            row_frame.pack_propagate(False)

            prio_color = DANGER_RED if "CRITIQUE" in prio else (ALERT_ORANGE if "ATTENTION" in prio else TEXT_MUTED)

            ctk.CTkLabel(row_frame, text=aid, font=("Times New Roman", 9, "bold"), text_color=TEXT_MAIN, width=45).pack(
                side="left", padx=2)
            ctk.CTkLabel(row_frame, text=prio, font=("Times New Roman", 9, "bold"), text_color=prio_color,
                         width=85).pack(side="left", padx=2)
            ctk.CTkLabel(row_frame, text=desc, font=("Times New Roman", 9), text_color=TEXT_MAIN, width=210,
                         anchor="w").pack(side="left", padx=2)
            ctk.CTkLabel(row_frame, text=time_str, font=("Times New Roman", 9), text_color=TEXT_MUTED, width=65).pack(
                side="left", padx=2)

            btn = ctk.CTkButton(row_frame, text=action, fg_color=TEAL, hover_color=TEAL_HOVER, height=20, width=100,
                                font=("Times New Roman", 8, "bold"))
            btn.pack(side="right", padx=2)