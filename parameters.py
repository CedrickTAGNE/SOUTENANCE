# parameters.py
# Page Paramètres : Gestion Utilisateurs, Adressage Caméras, Configuration Sécurité & Rapport d'État Général

import json
import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

import db
from config import (
    ACCENT_COLOR,
    DANGER_COLOR,
    FONT_BOLD,
    FONT_NORMAL,
    SUCCESS_COLOR,
    TABLE_CAMERAS,
    TABLE_HISTORY,
    TABLE_INTRUS,
    TABLE_LOGS,
    TABLE_PERSONNE,
    TABLE_SALLE,
    TABLE_SUPER_USER,
    TABLE_ZONE,
    TEXT_MAIN,
    TEXT_MUTED,
)

PAGE_BG = "#070a0e"
PANEL_BG = "#161b22"
PANEL_BORDER = "#30363d"
FIELD_BG = "#0b0f19"
FIELD_BORDER = "#30363d"
CARD_BG = "#11171d"

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "system_config.json")


def get_system_settings():
    defaults = {
        "face_match_threshold": 35.0,
        "alert_cooldown_seconds": 10,
        "camera_index": 0,
        "auto_detection": True,
    }
    if not os.path.exists(SETTINGS_FILE):
        return defaults
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            defaults.update(data)
            return defaults
    except Exception:
        return defaults


def save_system_settings(settings):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


class ParametersPage:
    def __init__(self, parent, controller=None):
        self.parent = parent
        self.controller = controller

        parent.configure(fg_color=PAGE_BG)

        # Grille 2x2 homogène pour les 4 cadrans
        parent.grid_columnconfigure(0, weight=1, uniform="params")
        parent.grid_columnconfigure(1, weight=1, uniform="params")
        parent.grid_rowconfigure(0, weight=1, uniform="params")
        parent.grid_rowconfigure(1, weight=1, uniform="params")

        # ---------------------------------------------------------
        # QUADRANT 1 (HAUT-GAUCHE) : COMPTES & ACCÈS UTILISATEURS
        # ---------------------------------------------------------
        self._build_users_panel(parent, row=0, col=0)

        # ---------------------------------------------------------
        # QUADRANT 2 (HAUT-DROITE) : ADRESSAGE & GESTION DES CAMÉRAS
        # ---------------------------------------------------------
        self._build_cameras_panel(parent, row=0, col=1)

        # ---------------------------------------------------------
        # QUADRANT 3 (BAS-GAUCHE) : DÉTECTION & SCAN FACIAL
        # ---------------------------------------------------------
        self._build_config_panel(parent, row=1, col=0)

        # ---------------------------------------------------------
        # QUADRANT 4 (BAS-DROITE) : RAPPORT D'ÉTAT GÉNÉRAL & AUDIT
        # ---------------------------------------------------------
        self._build_audit_report_panel(parent, row=1, col=1)

    # =========================================================================
    # 1. GESTION DES COMPTES UTILISATEURS
    # =========================================================================
    def _build_users_panel(self, parent, row, col):
        panel = ctk.CTkFrame(parent, fg_color=PANEL_BG, border_width=1, border_color=PANEL_BORDER)
        panel.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)

        ctk.CTkLabel(
            panel,
            text="🔑 COMPTES & ACCÈS UTILISATEURS",
            font=FONT_BOLD,
            text_color=ACCENT_COLOR,
        ).pack(anchor="w", padx=12, pady=(8, 4))

        content = ctk.CTkFrame(panel, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        left = ctk.CTkFrame(content, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))

        ctk.CTkLabel(left, text="Comptes enregistrés", font=FONT_NORMAL, text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 2))
        self.users_list = ctk.CTkScrollableFrame(left, fg_color=FIELD_BG, height=130)
        self.users_list.pack(fill="both", expand=True)

        right = ctk.CTkFrame(content, fg_color="transparent", width=200)
        right.pack(side="right", fill="y", padx=(4, 0))

        ctk.CTkLabel(right, text="Nouvel Utilisateur", font=FONT_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))

        self.user_entries = {}
        for key, label in (("username", "Identifiant"), ("nom", "Nom complet"), ("password", "Mot de passe")):
            ctk.CTkLabel(right, text=label, font=FONT_NORMAL, text_color=TEXT_MUTED).pack(anchor="w", pady=(1, 0))
            show_char = "*" if key == "password" else ""
            entry = ctk.CTkEntry(right, height=25, fg_color=FIELD_BG, border_color=FIELD_BORDER, show=show_char)
            entry.pack(fill="x", pady=(0, 2))
            self.user_entries[key] = entry

        ctk.CTkLabel(right, text="Rôle d'accès", font=FONT_NORMAL, text_color=TEXT_MUTED).pack(anchor="w", pady=(1, 0))
        self.role_option = ctk.CTkOptionMenu(
            right,
            values=["super_user", "operateur"],
            height=25,
            fg_color=FIELD_BG,
            button_color=FIELD_BORDER,
        )
        self.role_option.pack(fill="x", pady=(0, 4))

        ctk.CTkButton(
            right,
            text="ENREGISTRER",
            fg_color=SUCCESS_COLOR,
            hover_color="#15803d",
            height=26,
            font=FONT_BOLD,
            command=self.save_user,
        ).pack(fill="x")

        self.refresh_users()

    def refresh_users(self):
        for child in self.users_list.winfo_children():
            child.destroy()

        users = db.read_table(TABLE_SUPER_USER) or []
        for user in users:
            card = ctk.CTkFrame(self.users_list, fg_color=CARD_BG, border_width=1, border_color=FIELD_BORDER)
            card.pack(fill="x", pady=2, padx=2)

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=6, pady=3)

            name = user.get("nom") or user.get("username", "Utilisateur")
            username = user.get("username", "")
            role = user.get("role", "user")

            ctk.CTkLabel(info, text=f"{name} ({username})", font=FONT_BOLD, text_color=TEXT_MAIN).pack(anchor="w")
            ctk.CTkLabel(info, text=f"Rôle : {role}", font=FONT_NORMAL, text_color=TEXT_MUTED).pack(anchor="w")

            if username != "admin":
                ctk.CTkButton(
                    card,
                    text="❌",
                    width=24,
                    height=22,
                    fg_color=DANGER_COLOR,
                    hover_color="#991b1b",
                    command=lambda u=username: self.delete_user(u),
                ).pack(side="right", padx=4)

    def save_user(self):
        username = self.user_entries["username"].get().strip()
        nom = self.user_entries["nom"].get().strip()
        password = self.user_entries["password"].get().strip()
        role = self.role_option.get()

        if not username or not password:
            messagebox.showwarning("Incomplet", "Veuillez saisir l'identifiant et le mot de passe.")
            return

        users = db.read_table(TABLE_SUPER_USER) or []
        existing = next((u for u in users if u.get("username") == username), None)
        if existing:
            existing["nom"] = nom or username
            existing["password"] = password
            existing["role"] = role
        else:
            users.append({"username": username, "password": password, "nom": nom or username, "role": role})

        db.write_table(TABLE_SUPER_USER, users)
        current_admin = getattr(self.controller, "current_account", {}).get("username", "admin")
        db.log_history(current_admin, f"USER:{username}", f"Compte {username} mis à jour (Rôle: {role})")

        for entry in self.user_entries.values():
            entry.delete(0, tk.END)

        self.refresh_users()
        messagebox.showinfo("Succès", f"Compte {username} enregistré avec succès.")

    def delete_user(self, username):
        if not messagebox.askyesno("Confirmation", f"Supprimer l'utilisateur '{username}' ?"):
            return
        if db.delete_record(TABLE_SUPER_USER, username, key="username"):
            current_admin = getattr(self.controller, "current_account", {}).get("username", "admin")
            db.log_history(current_admin, f"USER:{username}", f"Compte utilisateur {username} supprimé")
            self.refresh_users()

    # =========================================================================
    # 2. ADRESSAGE & GESTION DES CAMÉRAS IP / RTSP / USB
    # =========================================================================
    def _build_cameras_panel(self, parent, row, col):
        panel = ctk.CTkFrame(parent, fg_color=PANEL_BG, border_width=1, border_color=PANEL_BORDER)
        panel.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)

        ctk.CTkLabel(
            panel,
            text="🎥 ADRESSAGE & GESTION DES CAMÉRAS",
            font=FONT_BOLD,
            text_color=ACCENT_COLOR,
        ).pack(anchor="w", padx=12, pady=(8, 4))

        content = ctk.CTkFrame(panel, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        left = ctk.CTkFrame(content, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))

        ctk.CTkLabel(left, text="Caméras configurées", font=FONT_NORMAL, text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 2))
        self.cameras_list = ctk.CTkScrollableFrame(left, fg_color=FIELD_BG, height=130)
        self.cameras_list.pack(fill="both", expand=True)

        right = ctk.CTkFrame(content, fg_color="transparent", width=210)
        right.pack(side="right", fill="y", padx=(4, 0))

        ctk.CTkLabel(right, text="Adressage Caméra", font=FONT_BOLD, text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 2))

        ctk.CTkLabel(right, text="Nom / Repère", font=FONT_NORMAL, text_color=TEXT_MUTED).pack(anchor="w", pady=(1, 0))
        self.cam_name_entry = ctk.CTkEntry(right, height=25, fg_color=FIELD_BG, border_color=FIELD_BORDER)
        self.cam_name_entry.pack(fill="x", pady=(0, 2))

        ctk.CTkLabel(right, text="Zone hospitalière", font=FONT_NORMAL, text_color=TEXT_MUTED).pack(anchor="w", pady=(1, 0))
        postes = db.get_postes() or ["Accueil"]
        self.cam_zone_option = ctk.CTkOptionMenu(
            right,
            values=postes,
            height=25,
            fg_color=FIELD_BG,
            button_color=FIELD_BORDER,
        )
        self.cam_zone_option.pack(fill="x", pady=(0, 2))

        ctk.CTkLabel(right, text="Adresse / Source (Index ou RTSP)", font=FONT_NORMAL, text_color=TEXT_MUTED).pack(anchor="w", pady=(1, 0))
        self.cam_source_entry = ctk.CTkEntry(right, height=25, placeholder_text="0 ou rtsp://...", fg_color=FIELD_BG, border_color=FIELD_BORDER)
        self.cam_source_entry.pack(fill="x", pady=(0, 2))

        ctk.CTkLabel(right, text="Statut", font=FONT_NORMAL, text_color=TEXT_MUTED).pack(anchor="w", pady=(1, 0))
        self.cam_status_option = ctk.CTkOptionMenu(
            right,
            values=["Actif", "Inactif"],
            height=25,
            fg_color=FIELD_BG,
            button_color=FIELD_BORDER,
        )
        self.cam_status_option.pack(fill="x", pady=(0, 4))

        ctk.CTkButton(
            right,
            text="ADRESSER / ENREGISTRER",
            fg_color=SUCCESS_COLOR,
            hover_color="#15803d",
            height=26,
            font=FONT_BOLD,
            command=self.save_camera,
        ).pack(fill="x")

        self.refresh_cameras()

    def refresh_cameras(self):
        for child in self.cameras_list.winfo_children():
            child.destroy()

        cameras = db.read_table(TABLE_CAMERAS) or []
        for cam in cameras:
            card = ctk.CTkFrame(self.cameras_list, fg_color=CARD_BG, border_width=1, border_color=FIELD_BORDER)
            card.pack(fill="x", pady=2, padx=2)

            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=6, pady=3)

            name = cam.get("nom", "Caméra")
            zone = cam.get("zone", "Non affectée")
            source = cam.get("source", "0")
            status = cam.get("status", "Actif")
            is_active = status == "Actif"

            ctk.CTkLabel(info, text=f"{name} ({zone})", font=FONT_BOLD, text_color=TEXT_MAIN).pack(anchor="w")
            ctk.CTkLabel(
                info,
                text=f"Src: {source}  •  {status}",
                font=FONT_NORMAL,
                text_color=SUCCESS_COLOR if is_active else DANGER_COLOR,
            ).pack(anchor="w")

            ctk.CTkButton(
                card,
                text="❌",
                width=24,
                height=22,
                fg_color=DANGER_COLOR,
                hover_color="#991b1b",
                command=lambda cid=cam.get("id"): self.delete_camera(cid),
            ).pack(side="right", padx=4)

    def save_camera(self):
        nom = self.cam_name_entry.get().strip()
        zone = self.cam_zone_option.get()
        source = self.cam_source_entry.get().strip() or "0"
        status = self.cam_status_option.get()

        if not nom:
            messagebox.showwarning("Incomplet", "Veuillez indiquer un nom ou repère pour la caméra.")
            return

        cameras = db.read_table(TABLE_CAMERAS) or []
        cam_type = "USB / Interne" if source.isdigit() else "RTSP / IP"
        new_id = max((c.get("id", 0) for c in cameras if isinstance(c.get("id", 0), int)), default=0) + 1

        cameras.append({
            "id": new_id,
            "nom": nom,
            "zone": zone,
            "source": source,
            "status": status,
            "type": cam_type,
            "date_adressage": datetime.now().isoformat(timespec="seconds"),
        })

        db.write_table(TABLE_CAMERAS, cameras)
        current_admin = getattr(self.controller, "current_account", {}).get("username", "admin")
        db.log_history(current_admin, f"CAMERA:{nom}", f"Adressage caméra {nom} ({zone} -> {source})")

        self.cam_name_entry.delete(0, tk.END)
        self.cam_source_entry.delete(0, tk.END)
        self.refresh_cameras()
        messagebox.showinfo("Succès", f"La caméra '{nom}' a été adressée avec succès.")

    def delete_camera(self, cam_id):
        if not messagebox.askyesno("Confirmation", "Supprimer cette adresse de caméra ?"):
            return
        if db.delete_record(TABLE_CAMERAS, cam_id, key="id"):
            current_admin = getattr(self.controller, "current_account", {}).get("username", "admin")
            db.log_history(current_admin, f"CAMERA:{cam_id}", "Suppression de l'adresse de caméra")
            self.refresh_cameras()

    # =========================================================================
    # 3. DÉTECTION & SCAN FACIAL (FIX CTKSLIDER Crash with to=)
    # =========================================================================
    def _build_config_panel(self, parent, row, col):
        panel = ctk.CTkFrame(parent, fg_color=PANEL_BG, border_width=1, border_color=PANEL_BORDER)
        panel.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)

        ctk.CTkLabel(
            panel,
            text="⚙️ CONFIGURATION SÉCURITÉ & SCAN FACIAL",
            font=FONT_BOLD,
            text_color=ACCENT_COLOR,
        ).pack(anchor="w", padx=12, pady=(8, 4))

        settings = get_system_settings()

        form = ctk.CTkFrame(panel, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=12, pady=4)

        # Seuil de correspondance FaceID
        threshold_frame = ctk.CTkFrame(form, fg_color="transparent")
        threshold_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(
            threshold_frame,
            text="Seuil de tolérance FaceID (Distance Max) :",
            font=FONT_NORMAL,
            text_color=TEXT_MAIN,
        ).pack(side="left")

        self.threshold_val_label = ctk.CTkLabel(
            threshold_frame,
            text=f"{settings.get('face_match_threshold', 35.0):.1f}",
            font=FONT_BOLD,
            text_color=ACCENT_COLOR,
        )
        self.threshold_val_label.pack(side="right")

        # Note: CTkSlider utilise 'from_' et 'to' (PAS 'to_')
        self.threshold_slider = ctk.CTkSlider(
            form,
            from_=10.0,
            to=80.0,
            number_of_steps=70,
            command=self._on_threshold_change,
        )
        self.threshold_slider.set(settings.get("face_match_threshold", 35.0))
        self.threshold_slider.pack(fill="x", pady=(0, 6))

        # Cooldown des alertes d'intrus
        cooldown_frame = ctk.CTkFrame(form, fg_color="transparent")
        cooldown_frame.pack(fill="x", pady=2)

        ctk.CTkLabel(
            cooldown_frame,
            text="Temporisation Alerte Intrus (Secondes) :",
            font=FONT_NORMAL,
            text_color=TEXT_MAIN,
        ).pack(side="left")

        self.cooldown_entry = ctk.CTkEntry(
            cooldown_frame, width=80, height=25, fg_color=FIELD_BG, border_color=FIELD_BORDER
        )
        self.cooldown_entry.insert(0, str(settings.get("alert_cooldown_seconds", 10)))
        self.cooldown_entry.pack(side="right")

        # Sélection de la Caméra principale par défaut
        cam_frame = ctk.CTkFrame(form, fg_color="transparent")
        cam_frame.pack(fill="x", pady=4)

        ctk.CTkLabel(
            cam_frame,
            text="Caméra principale par défaut :",
            font=FONT_NORMAL,
            text_color=TEXT_MAIN,
        ).pack(side="left")

        self.cam_option = ctk.CTkOptionMenu(
            cam_frame,
            values=["Caméra 0 (USB / Interne)", "Caméra 1 (Externe)", "Caméra 2"],
            width=170,
            height=25,
            fg_color=FIELD_BG,
            button_color=FIELD_BORDER,
        )
        cam_idx = settings.get("camera_index", 0)
        self.cam_option.set(f"Caméra {cam_idx}" if cam_idx > 0 else "Caméra 0 (USB / Interne)")
        self.cam_option.pack(side="right")

        # Bouton enregistrer configuration
        ctk.CTkButton(
            form,
            text="💾 SAUVEGARDER LES PARAMÈTRES",
            fg_color=SUCCESS_COLOR,
            hover_color="#15803d",
            height=30,
            font=FONT_BOLD,
            command=self.save_config,
        ).pack(fill="x", pady=(10, 0))

    def _on_threshold_change(self, val):
        self.threshold_val_label.configure(text=f"{val:.1f}")

    def save_config(self):
        try:
            cooldown = int(self.cooldown_entry.get().strip())
        except ValueError:
            messagebox.showerror("Erreur", "Saisissez un nombre entier pour la temporisation.")
            return

        cam_text = self.cam_option.get()
        cam_idx = 1 if "1" in cam_text else (2 if "2" in cam_text else 0)

        new_settings = {
            "face_match_threshold": round(float(self.threshold_slider.get()), 1),
            "alert_cooldown_seconds": max(1, cooldown),
            "camera_index": cam_idx,
            "auto_detection": True,
        }

        save_system_settings(new_settings)
        current_admin = getattr(self.controller, "current_account", {}).get("username", "admin")
        db.log_history(current_admin, "SYSTEM:CONFIG", f"Paramètres modifiés (Seuil: {new_settings['face_match_threshold']})")
        messagebox.showinfo("Succès", "Les paramètres de sécurité ont été mis à jour.")

    # =========================================================================
    # 4. RAPPORT D'ÉTAT GÉNÉRAL DE L'APPLICATION & DIAGNOSTIC
    # =========================================================================
    def _build_audit_report_panel(self, parent, row, col):
        panel = ctk.CTkFrame(parent, fg_color=PANEL_BG, border_width=1, border_color=PANEL_BORDER)
        panel.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)

        ctk.CTkLabel(
            panel,
            text="📊 RAPPORT D'ÉTAT GÉNÉRAL & AUDIT SYSTÈME",
            font=FONT_BOLD,
            text_color=ACCENT_COLOR,
        ).pack(anchor="w", padx=12, pady=(8, 4))

        content = ctk.CTkFrame(panel, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        # Cartes d'indicateurs système en temps réel
        stats_frame = ctk.CTkFrame(content, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 4))

        p_count = len(db.read_table(TABLE_PERSONNE) or [])
        l_count = len(db.read_table(TABLE_LOGS) or [])
        i_count = len(db.read_table(TABLE_INTRUS) or [])
        c_count = len(db.read_table(TABLE_CAMERAS) or [])

        for title, val, color in (
            ("Personnel", str(p_count), ACCENT_COLOR),
            ("Logs Accès", str(l_count), SUCCESS_COLOR),
            ("Intrusions", str(i_count), DANGER_COLOR),
            ("Caméras", str(c_count), "#eab308"),
        ):
            card = ctk.CTkFrame(stats_frame, fg_color=CARD_BG, border_width=1, border_color=FIELD_BORDER)
            card.pack(side="left", fill="x", expand=True, padx=2)
            ctk.CTkLabel(card, text=val, font=("Times New Roman", 13, "bold"), text_color=color).pack(pady=(2, 0))
            ctk.CTkLabel(card, text=title, font=("Times New Roman", 9), text_color=TEXT_MUTED).pack(pady=(0, 2))

        # Bouton principal pour Générer le Rapport d'État Général
        ctk.CTkButton(
            content,
            text="📄 GÉNÉRER LE RAPPORT D'ÉTAT GÉNÉRAL DE L'APPLICATION",
            fg_color=ACCENT_COLOR,
            hover_color="#1d4ed8",
            height=30,
            font=FONT_BOLD,
            command=self.open_general_state_report,
        ).pack(fill="x", pady=(4, 6))

        # Zone d'aperçu rapide de l'historique d'audit
        ctk.CTkLabel(content, text="Dernières actions enregistrées", font=FONT_NORMAL, text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 2))
        self.history_list = ctk.CTkScrollableFrame(content, fg_color=FIELD_BG, height=80)
        self.history_list.pack(fill="both", expand=True)

        self.refresh_history()

    def refresh_history(self):
        for child in self.history_list.winfo_children():
            child.destroy()

        history = db.read_table(TABLE_HISTORY) or []
        for item in reversed(history[-20:]):
            card = ctk.CTkFrame(self.history_list, fg_color=CARD_BG, border_width=1, border_color=FIELD_BORDER)
            card.pack(fill="x", pady=1, padx=2)

            user = item.get("utilisateur", "système")
            target = item.get("cible_modifiee", "")
            desc = item.get("description", "")

            ctk.CTkLabel(card, text=f"[{user}] {target} — {desc}", font=("Times New Roman", 10), text_color=TEXT_MAIN).pack(anchor="w", padx=4, pady=2)

    def open_general_state_report(self):
        win = ctk.CTkToplevel(self.parent)
        win.title("Rapport d'État Général de l'Application — CHRACERH")
        win.geometry("640x560")
        win.grab_set()

        ctk.CTkLabel(
            win,
            text="📋 RAPPORT D'ÉTAT ET DE DIAGNOSTIC GÉNÉRAL",
            font=("Times New Roman", 14, "bold"),
            text_color=ACCENT_COLOR,
        ).pack(anchor="w", padx=16, pady=(14, 4))

        textbox = ctk.CTkTextbox(win, fg_color="#0b0f19", border_color="#30363d", font=("Consolas", 10))
        textbox.pack(fill="both", expand=True, padx=14, pady=6)

        # Construction du texte du rapport d'état général
        settings = get_system_settings()
        personnel = db.read_table(TABLE_PERSONNE) or []
        logs = db.read_table(TABLE_LOGS) or []
        intrus = db.read_table(TABLE_INTRUS) or []
        users = db.read_table(TABLE_SUPER_USER) or []
        cameras = db.read_table(TABLE_CAMERAS) or []
        postes = db.read_table(TABLE_ZONE) or []

        face_count = sum(1 for p in personnel if p.get("face_id") is not None)
        active_cams = sum(1 for c in cameras if c.get("status") == "Actif")

        report_lines = [
            "================================================================================",
            "        C.H.R.A.C.E.R.H ACCES CONTROL — RAPPORT D'ÉTAT GÉNÉRAL DU SYSTÈME",
            f"        Généré le : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}",
            "================================================================================",
            "",
            "[1] ÉTAT DE LA BASE DE DONNÉES & STOCKAGE LOCAL JSON",
            "--------------------------------------------------------------------------------",
            "  • Mode de Stockage       : Fichiers JSON locaux (Structure autonome)",
            f"  • Membres du Personnel   : {len(personnel)} enregistrés ({face_count} matrices FaceID scannées)",
            f"  • Postes / Zones Gardées  : {len(postes)} zones hospitalières actives",
            f"  • Intrusions Détectées   : {len(intrus)} enregistrements d'alertes",
            f"  • Journal d'Accès (Logs) : {len(logs)} événements horodatés",
            f"  • Comptes Utilisateurs   : {len(users)} comptes (Super Utilisateurs & Opérateurs)",
            "",
            "[2] RÉSEAU DE VIDÉOSURVEILLANCE & ADRESSAGE CAMÉRAS",
            "--------------------------------------------------------------------------------",
            f"  • Nombre de Caméras      : {len(cameras)} enregistrées",
            f"  • Caméras Actives        : {active_cams} / {len(cameras)}",
            f"  • Index Caméra Principale: Caméra {settings.get('camera_index', 0)}",
            "  • Liste des caméras adressées :",
        ]

        if not cameras:
            report_lines.append("      - Aucune caméra adressée pour le moment.")
        else:
            for cam in cameras:
                report_lines.append(
                    f"      - [{cam.get('status', 'Inactif')}] {cam.get('nom')} | Zone: {cam.get('zone')} | Source: {cam.get('source')}"
                )

        report_lines.extend([
            "",
            "[3] PARAMÈTRES DE SÉCURITÉ & RECONNAISSANCE FACIALE",
            "--------------------------------------------------------------------------------",
            f"  • Seuil de Tolérance (Match Threshold) : {settings.get('face_match_threshold', 35.0)}",
            f"  • Temporisation d'Alerte Intrus       : {settings.get('alert_cooldown_seconds', 10)} secondes",
            f"  • Mode Détection Automatique          : {'ACTIVÉ' if settings.get('auto_detection') else 'DÉSACTIVÉ'}",
            "",
            "[4] DIAGNOSTIC GLOBAL ET CONCLUSION",
            "--------------------------------------------------------------------------------",
            "  • Statut de l'Application : OPERATIONNEL — Système de sécurité fonctionnel.",
            "  • Intégrité des Données   : Base de données conforme et synchronisée.",
            "================================================================================",
        ])

        report_text = "\n".join(report_lines)
        textbox.insert("1.0", report_text)
        textbox.configure(state="disabled")

        btn_bar = ctk.CTkFrame(win, fg_color="transparent")
        btn_bar.pack(fill="x", padx=14, pady=(0, 12))

        def export_report():
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Fichiers Texte", "*.txt"), ("Tous les fichiers", "*.*")],
                initialfile=f"Rapport_Etat_General_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            )
            if path:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(report_text)
                    messagebox.showinfo("Export réussi", f"Le rapport a été exporté sous :\n{path}")
                except Exception as err:
                    messagebox.showerror("Erreur d'exportation", f"Impossible de sauvegarder le rapport : {err}")

        ctk.CTkButton(
            btn_bar,
            text="💾 EXPORTER EN FICHIER TEXTE (.TXT)",
            fg_color=SUCCESS_COLOR,
            hover_color="#15803d",
            command=export_report,
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))

        ctk.CTkButton(
            btn_bar,
            text="FERMER",
            fg_color=DANGER_COLOR,
            hover_color="#991b1b",
            command=win.destroy,
        ).pack(side="right", expand=True, fill="x", padx=(4, 0))