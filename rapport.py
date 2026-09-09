# rapport.py
# Onglet Rapport : 4 sous-carrés, synthèse par onglet et export PDF.

import os
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime

try:
    from PIL import Image
except ImportError:
    Image = None

from config import FONT_NORMAL, FONT_BOLD, ACCENT_COLOR, SUCCESS_COLOR, TABLE_PERSONNE, TABLE_LOGS, TABLE_ZONE, TABLE_SALLE
import db
from dashboard import generate_person_pdf_report

PAGE_BG = "#1a232c"
PANEL_BG = "#151d24"
SEPARATOR_COLOR = "#293744"
TEXT_MAIN = "#ffffff"
TEXT_MUTED = "#8795a1"
CARD_BORDER = "#273145"


def _create_quadrant_frame(parent, title, subtitle):
    frame = ctk.CTkFrame(parent, fg_color=PANEL_BG, border_width=1, border_color=CARD_BORDER)
    frame.grid(sticky="nsew", padx=8, pady=8)
    frame.grid_rowconfigure(1, weight=1)

    ctk.CTkLabel(frame, text=title, font=("Times New Roman", 14, "bold"), text_color=ACCENT_COLOR).pack(
        anchor="w", padx=10, pady=(10, 4))
    ctk.CTkLabel(frame, text=subtitle, font=FONT_NORMAL, text_color=TEXT_MUTED).pack(
        anchor="w", padx=10, pady=(0, 8))

    body = ctk.CTkFrame(frame, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    return frame, body


class RapportPage:
    def __init__(self, parent, controller=None):
        self.controller = controller
        parent.configure(fg_color=PAGE_BG)

        parent.grid_columnconfigure(0, weight=3)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        self.dashboard_summary = None
        self.database_summary = None
        self.alerts_summary = None
        self.parameters_summary = None

        access_panel = ctk.CTkFrame(parent, fg_color=PANEL_BG, border_width=1, border_color=CARD_BORDER)
        access_panel.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        ctk.CTkLabel(access_panel, text="JOURNAL DES ACCÈS ET INTRUSIONS",
                     font=("Times New Roman", 15, "bold"), text_color=ACCENT_COLOR).pack(
            anchor="w", padx=12, pady=(12, 2))
        ctk.CTkLabel(access_panel, text="Accès autorisés et authentifications échouées",
                     font=FONT_NORMAL, text_color=TEXT_MUTED).pack(anchor="w", padx=12, pady=(0, 8))
        self.access_list = ctk.CTkScrollableFrame(access_panel, fg_color="#0b0f19")
        self.access_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        summary_panel = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                                scrollbar_button_color="#475569")
        summary_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        summary_panel.grid_columnconfigure(0, weight=1)
        for row_index in range(4):
            summary_panel.grid_rowconfigure(row_index, weight=1, uniform="summary")
        frame1, body1 = _create_quadrant_frame(summary_panel, "DASHBOARD", "Flux et détections")
        frame1.grid(row=0, column=0, sticky="nsew", padx=0, pady=4)
        self.dashboard_summary = ctk.CTkLabel(body1, text="Chargement...", font=FONT_NORMAL,
                                              text_color=TEXT_MAIN, justify="left", wraplength=250)
        self.dashboard_summary.pack(anchor="nw")
        frame2, body2 = _create_quadrant_frame(summary_panel, "PERSONNEL", "Profils et accès")
        frame2.grid(row=1, column=0, sticky="nsew", padx=0, pady=4)
        self.database_summary = ctk.CTkLabel(body2, text="Chargement...", font=FONT_NORMAL,
                                              text_color=TEXT_MAIN, justify="left", wraplength=250)
        self.database_summary.pack(anchor="nw")
        frame3, body3 = _create_quadrant_frame(summary_panel, "ALERTES", "Intrusions détectées")
        frame3.grid(row=2, column=0, sticky="nsew", padx=0, pady=4)
        self.alerts_summary = ctk.CTkLabel(body3, text="Chargement...", font=FONT_NORMAL,
                                            text_color=TEXT_MAIN, justify="left", wraplength=250)
        self.alerts_summary.pack(anchor="nw")
        frame4, body4 = _create_quadrant_frame(summary_panel, "EXPORT", "Documents de supervision")
        frame4.grid(row=3, column=0, sticky="nsew", padx=0, pady=4)
        self.parameters_summary = ctk.CTkLabel(body4, text="Chargement...", font=FONT_NORMAL,
                                                text_color=TEXT_MAIN, justify="left", wraplength=250)
        self.parameters_summary.pack(anchor="nw")

        self._build_actions(summary_panel)
        self.refresh_access_list()
        self.refresh_report()

    def _build_actions(self, parent):
        action_frame = ctk.CTkFrame(parent, fg_color="transparent")
        action_frame.grid(row=4, column=0, sticky="ew", padx=0, pady=(4, 8))

        ctk.CTkButton(action_frame, text="RAFRAÎCHIR", fg_color=ACCENT_COLOR,
                      hover_color="#2563eb", height=34, font=FONT_BOLD,
                      command=self.refresh_report).pack(side="left", padx=(0, 6))
        ctk.CTkButton(action_frame, text="EXPORTER LES DONNÉES PDF", fg_color=SUCCESS_COLOR,
                      hover_color="#0f766e", height=34, font=FONT_BOLD,
                      command=self.generate_pdf).pack(side="left")
        ctk.CTkButton(action_frame, text="RAPPORT D'UNE SALLE", fg_color="#0f766e",
                      hover_color="#115e59", height=34, font=FONT_BOLD,
                      command=self.show_room_report).pack(side="left", padx=(6, 6))
        ctk.CTkButton(action_frame, text="RAPPORT PAR PERSONNE", fg_color="#2563eb",
                      hover_color="#1d4ed8", height=34, font=FONT_BOLD,
                      command=self.show_person_report).pack(side="left")

    def refresh_access_list(self):
        for child in self.access_list.winfo_children():
            child.destroy()
        personnel = {row.get("cni"): row for row in db.read_table(TABLE_PERSONNE)}
        events = [(row, True) for row in db.read_table(TABLE_LOGS)]
        events += [(row, False) for row in db.read_table("INTRUS")]
        events.sort(key=lambda item: str(item[0].get("date_heure", "")), reverse=True)
        if not events:
            ctk.CTkLabel(self.access_list, text="Aucun événement enregistré.", font=FONT_BOLD,
                         text_color=TEXT_MUTED).pack(pady=30)
            return
        for event, allowed in events:
            card = ctk.CTkFrame(self.access_list, fg_color="#13251b" if allowed else "#291517",
                                border_width=1, border_color="#276749" if allowed else "#991b1b")
            card.pack(fill="x", pady=4)
            if allowed:
                person = personnel.get(event.get("cni"), {})
                label = f"{person.get('nom', 'Personnel')} {person.get('prenom', '')} ({event.get('cni', '')})"
                detail = f"ACCÈS AUTORISÉ  •  {event.get('piece', 'Salle inconnue')}  •  {event.get('date_heure', '')}"
                color = "#86efac"
            else:
                label = f"INTRUSION  •  {event.get('piece', 'Salle inconnue')}"
                detail = f"AUTHENTIFICATION ÉCHOUÉE  •  {event.get('date_heure', '')}  •  {event.get('remarque', '')}"
                color = "#fca5a5"
            ctk.CTkLabel(card, text=label, font=FONT_BOLD, text_color=TEXT_MAIN).pack(anchor="w", padx=10, pady=(8, 2))
            ctk.CTkLabel(card, text=detail, font=FONT_NORMAL, text_color=color,
                         wraplength=560, justify="left").pack(anchor="w", padx=10, pady=(0, 8))

    def show_room_report(self):
        window = ctk.CTkToplevel(self.controller)
        window.title("Rapport d'accès par salle")
        window.geometry("760x540")
        rooms = db.read_table(TABLE_SALLE)
        room_names = [room.get("nom_salle", "") for room in rooms] or ["Aucune salle"]
        selector = ctk.CTkOptionMenu(window, values=room_names)
        selector.pack(fill="x", padx=14, pady=(14, 8))
        output = ctk.CTkTextbox(window, font=FONT_NORMAL)
        output.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        personnel = {row.get("cni"): row for row in db.read_table(TABLE_PERSONNE)}

        def render(*_):
            output.delete("1.0", "end")
            room_name = selector.get()
            accesses = [row for row in db.read_table(TABLE_LOGS) if row.get("piece") == room_name]
            output.insert("end", f"RAPPORT — {room_name}\n\n")
            output.insert("end", f"Nombre de passages : {len(accesses)}\n\n")
            for access in reversed(accesses):
                person = personnel.get(access.get("cni"), {})
                name = f"{person.get('nom', 'Inconnu')} {person.get('prenom', '')}".strip()
                output.insert(
                    "end",
                    f"{access.get('date_heure', '')} | {name} ({access.get('cni', '')}) | "
                    f"{access.get('statut', 'Autorisé')}\n",
                )

        selector.configure(command=render)
        ctk.CTkButton(window, text="ACTUALISER", command=render, fg_color=ACCENT_COLOR).pack(pady=(0, 12))
        render()

    def show_person_report(self):
        window = ctk.CTkToplevel(self.controller)
        window.title("Rapport Individuel par Personne")
        window.geometry("780x560")

        people = db.read_table(TABLE_PERSONNE) or []
        if not people:
            messagebox.showinfo("Aucun membre", "Aucun membre du personnel enregistré dans la base de données.")
            return

        people_dict = {f"{p.get('nom', '')} {p.get('prenom', '')} ({p.get('cni', '')})": p for p in people}
        names = list(people_dict.keys())

        header = ctk.CTkFrame(window, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(14, 6))

        ctk.CTkLabel(header, text="Sélectionner la personne :", font=FONT_BOLD, text_color=TEXT_MAIN).pack(side="left", padx=(0, 10))
        selector = ctk.CTkOptionMenu(header, values=names, width=350, fg_color="#0b0f19", button_color="#30363d")
        selector.pack(side="left")

        card_container = ctk.CTkFrame(window, fg_color="#10171d", border_width=1, border_color="#273145", corner_radius=8)
        card_container.pack(fill="both", expand=True, padx=14, pady=8)

        def render_person(*_):
            for child in card_container.winfo_children():
                child.destroy()

            selected_name = selector.get()
            person = people_dict.get(selected_name, {})
            if not person:
                return

            card_container.grid_columnconfigure(0, weight=0)
            card_container.grid_columnconfigure(1, weight=1)
            card_container.grid_rowconfigure(0, weight=1)

            # 1. Image / Photo sur le côté gauche
            photo_box = ctk.CTkFrame(card_container, fg_color="#0b0f14", width=180, height=210, corner_radius=6, border_width=1, border_color="#2a3947")
            photo_box.grid(row=0, column=0, padx=14, pady=14, sticky="n")
            photo_box.pack_propagate(False)

            photo_path = person.get("photo_path", "")
            if photo_path and not os.path.isabs(photo_path):
                photo_path = os.path.join(os.path.dirname(__file__), photo_path)

            if photo_path and os.path.isfile(photo_path) and Image:
                try:
                    pil_img = Image.open(photo_path)
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(160, 190))
                    lbl_img = ctk.CTkLabel(photo_box, image=ctk_img, text="")
                    lbl_img.image = ctk_img
                    lbl_img.pack(fill="both", expand=True)
                except Exception:
                    ctk.CTkLabel(photo_box, text="[ PAS DE PHOTO ]", text_color=TEXT_MUTED).pack(fill="both", expand=True)
            else:
                ctk.CTkLabel(photo_box, text="[ PAS DE PHOTO ]", text_color=TEXT_MUTED).pack(fill="both", expand=True)

            # 2. Informations personnelles sur le côté droit juste à côté de l'image
            info_frame = ctk.CTkFrame(card_container, fg_color="transparent")
            info_frame.grid(row=0, column=1, padx=(10, 14), pady=14, sticky="nsew")

            ctk.CTkLabel(info_frame, text=f"FICHE IDENTITÉ — {person.get('nom', '')} {person.get('prenom', '')}", font=("Times New Roman", 14, "bold"), text_color=ACCENT_COLOR).pack(anchor="w", pady=(0, 10))

            details = [
                ("Matricule CNI / ID", person.get("cni", "")),
                ("Nom complet", f"{person.get('nom', '')} {person.get('prenom', '')}"),
                ("Poste Hospitalier", person.get("poste", "Accueil")),
                ("Service", person.get("service", "Zone hospitalière")),
                ("Téléphone", person.get("telephone", "Non renseigné")),
                ("Ville & Quartier", f"{person.get('ville', '')} - {person.get('quartier', '')}".strip(" -")),
                ("Statut du Compte", "Actif (Autorisé)" if person.get("is_active", True) else "Inactif"),
                ("Matrice FaceID", "Enregistrée (Valide)" if person.get("face_id") is not None else "Non scannée"),
            ]

            for label, val in details:
                row_f = ctk.CTkFrame(info_frame, fg_color="transparent")
                row_f.pack(fill="x", pady=2)
                ctk.CTkLabel(row_f, text=f"{label} :", font=FONT_BOLD, text_color=TEXT_MUTED, width=140, anchor="w").pack(side="left")
                ctk.CTkLabel(row_f, text=str(val), font=FONT_NORMAL, text_color=TEXT_MAIN, anchor="w").pack(side="left")

            # Bouton d'exportation PDF pour cette personne avec sa photo
            ctk.CTkButton(
                info_frame,
                text="📄 EXPORTER LE RAPPORT PDF DE CETTE PERSONNE (AVEC PHOTO)",
                fg_color=SUCCESS_COLOR,
                hover_color="#15803d",
                height=32,
                font=FONT_BOLD,
                command=lambda p=person: self._export_single_person_pdf(p),
            ).pack(fill="x", pady=(14, 0))

        selector.configure(command=render_person)
        render_person()

    def _export_single_person_pdf(self, person):
        try:
            filepath = generate_person_pdf_report(person)
            if filepath:
                try:
                    os.startfile(filepath)
                except Exception:
                    pass
                messagebox.showinfo("PDF Généré", f"Le rapport PDF avec photo a été généré sous :\n{filepath}")
            else:
                messagebox.showerror("Erreur", "Impossible de générer le rapport PDF (ReportLab indisponible).")
        except Exception as err:
            messagebox.showerror("Erreur PDF", f"Échec de la création du PDF : {err}")

    def refresh_report(self):
        self.refresh_access_list()
        default_text = "Aucune activité enregistrée."
        dashboard_text = default_text
        database_text = default_text
        alerts_text = default_text
        parameters_text = default_text

        if self.controller and hasattr(self.controller, 'activity_log'):
            logs = list(self.controller.activity_log)
            dashboard_items = [item for item in logs if item.get('source') == 'Dashboard']
            database_items = [item for item in logs if item.get('source') in ('Personnel JSON', 'Base de données')]
            alerts_items = [item for item in logs if item.get('source') == 'Alertes']
            parameters_items = [item for item in logs if item.get('source') == 'Paramètres']

            dashboard_text = (
                f"Total : {len(dashboard_items)} événements\n"
                f"Dernier : {dashboard_items[-1]['message'] if dashboard_items else 'Aucun'}\n"
                "Webcam : connectée si Dashboard est actif."
            )
            database_text = (
                f"Total : {len(database_items)} événements\n"
                f"Dernier : {database_items[-1]['message'] if database_items else 'Aucun'}\n"
                "Synthèse des logs disponible."
            )
            alerts_text = (
                f"Total : {len(alerts_items)} événements\n"
                f"Dernier : {alerts_items[-1]['message'] if alerts_items else 'Aucun'}\n"
                "Alertes suivies en temps réel."
            )
            parameters_text = (
                f"Total : {len(parameters_items)} événements\n"
                f"Dernier : {parameters_items[-1]['message'] if parameters_items else 'Aucun'}\n"
                "Export PDF disponible."
            )

        if self.controller and hasattr(self.controller, 'activity_log'):
            person_count = db.fetch_one(f'SELECT COUNT(*) FROM "{TABLE_PERSONNE}";') or (0,)
            log_count = db.fetch_one(f'SELECT COUNT(*) FROM "{TABLE_LOGS}";') or (0,)
            zone_count = db.fetch_one(f'SELECT COUNT(*) FROM "{TABLE_ZONE}";') or (0,)
            dashboard_text += f"\nPersonnes en base : {person_count[0]}\nLogs totaux : {log_count[0]}"
            dashboard_text += f"\nZones définies : {zone_count[0]}"

        self.dashboard_summary.configure(text=dashboard_text)
        self.database_summary.configure(text=database_text)
        self.alerts_summary.configure(text=alerts_text)
        self.parameters_summary.configure(text=parameters_text)

    def generate_pdf(self):
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
        except ImportError:
            messagebox.showerror("Reportlab manquant", "Installez reportlab avec : pip install reportlab")
            return

        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads, exist_ok=True)
        filepath = os.path.join(downloads, f"rapport_application_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

        c = canvas.Canvas(filepath, pagesize=letter)
        c.setFont("Times-Bold", 16)
        c.drawString(50, 750, "Rapport de l'application")
        c.setFont("Times-Roman", 11)
        c.drawString(50, 730, f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        y = 700
        for title, label in [
            ("Dashboard", self.dashboard_summary),
            ("Personnel JSON", self.database_summary),
            ("Alertes", self.alerts_summary),
            ("Paramètres", self.parameters_summary),
        ]:
            c.setFont("Times-Bold", 12)
            c.drawString(50, y, title)
            y -= 18
            c.setFont("Times-Roman", 10)
            for line in label.cget("text").split("\n"):
                c.drawString(60, y, line)
                y -= 14
            y -= 10
            if y < 80:
                c.showPage()
                y = 740

        c.showPage()
        c.setFont("Times-Bold", 16)
        c.drawString(50, 750, "Journal des accès et des intrusions")
        y = 720
        personnel = {row.get("cni"): row for row in db.read_table(TABLE_PERSONNE)}
        events = [(row, "AUTORISÉ") for row in db.read_table(TABLE_LOGS)]
        events += [(row, "REFUSÉ") for row in db.read_table("INTRUS")]
        for event, status in events:
            if y < 60:
                c.showPage()
                y = 750
            if status == "AUTORISÉ":
                person = personnel.get(event.get("cni"), {})
                subject = f"{person.get('nom', 'Inconnu')} {person.get('prenom', '')} ({event.get('cni', '')})"
                room = event.get("piece", "Salle inconnue")
            else:
                subject = "Intrusion / visage non reconnu"
                room = event.get("piece", "Salle inconnue")
            c.setFont("Times-Roman", 9)
            c.drawString(50, y, f"{status} | {event.get('date_heure', '')} | {room} | {subject}")
            y -= 15
        c.save()
        try:
            os.startfile(filepath)
        except Exception:
            pass
        messagebox.showinfo("PDF généré", f"Rapport généré : {filepath}")
