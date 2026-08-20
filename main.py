# main.py
# SEUL fichier à exécuter. Il assemble le login puis les 4 pages de l'application.
# Les autres fichiers (page_*.py, config.py, db.py) ne contiennent aucun bloc
# d'exécution : ce sont uniquement des modules importés ici.

import customtkinter as ctk
import tkinter as tk
import os
from datetime import datetime

try:
    from PIL import Image
except ImportError:
    Image = None

from config import FONT_NORMAL, FONT_BOLD, ACCENT_COLOR
from LoginPage import LoginPage


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Système de Vidéosurveillance et Contrôle d'Accès — CHRACERH")
        self.geometry("900x500")
        self.minsize(900, 500)
        ctk.set_appearance_mode("dark")
        self.activity_log = []
        self.current_account = None

        # Le login s'affiche en premier ; l'interface principale n'est construite
        # qu'après une connexion réussie.
        self.login_frame = LoginPage(self, on_success=self._build_main_ui)

    def _build_main_ui(self, account=None):
        self.current_account = account or {"username": "admin", "nom": "Administrateur", "role": "super_user"}
        self.loaded_pages = {}
        self.loading_page = None
        # ---- Barre de titre ----
        title_bar = ctk.CTkFrame(self, fg_color="#0d1117", height=70)
        title_bar.pack(fill="x", side="top")
        title_bar.pack_propagate(False)
        self._add_logo(title_bar, size=(84, 60), side="left", padx=(10, 4))
        ctk.CTkLabel(title_bar, text="C.H.R.A.C.E.R.H  ACCES CONTROL",
                     font=("Times New Roman", 16, "bold"), text_color=ACCENT_COLOR).pack(
            side="left", padx=20, pady=15)
        self.clock_label = ctk.CTkLabel(
            title_bar,
            text="",
            font=("Times New Roman", 13, "bold"),
            text_color="#10b981",
        )
        self.clock_label.pack(side="right", padx=20)
        self.update_clock()

        # ---- Barre d'onglets ----
        tab_bar = ctk.CTkFrame(self, fg_color="#161b22", height=45)
        tab_bar.pack(fill="x", side="top")
        tab_bar.pack_propagate(False)

        tab_names = [
            ("🖥️  DASHBOARD", 0),
            ("🗄️  PERSONNEL", 1),
            ("🔔  ALERTES", 2),
            ("📊  RAPPORT", 3),
            ("⚙️  PARAMÈTRES", 4),
        ]
        self.tab_buttons = []
        self.tab_frames = []

        for label, idx in tab_names:
            btn = ctk.CTkButton(
                tab_bar, text=label, font=FONT_BOLD,
                fg_color=ACCENT_COLOR if idx == 0 else "transparent",
                hover_color="#1e40af", text_color="white", height=34, width=140,
                corner_radius=0, command=lambda i=idx: self.switch_tab(i),
            )
            btn.pack(side="left", padx=2, pady=4)
            self.tab_buttons.append(btn)

        # ---- Zone de contenu ----
        self.content_area = ctk.CTkFrame(self, fg_color="#070a0e")
        self.content_area.pack(fill="both", expand=True, padx=8, pady=8)

        for _ in tab_names:
            f = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent",
                                       scrollbar_button_color="#475569")
            self.tab_frames.append(f)

        self.switch_tab(0)
        # Let Tk display the shell before loading camera/map/report dependencies.
        self.after(40, lambda: self.load_page(0))

    def _add_logo(self, parent, size=(42, 30), side="left", padx=0):
        path = os.path.join(os.path.dirname(__file__), "chracerh_logo.png")
        if not (Image and os.path.isfile(path)):
            return
        try:
            image = Image.open(path)
            logo = ctk.CTkImage(light_image=image, dark_image=image, size=size)
            label = ctk.CTkLabel(parent, image=logo, text="")
            label.image = logo
            label.pack(side=side, padx=padx, pady=8)
        except (OSError, ValueError):
            return

    def load_page(self, index):
        if index in self.loaded_pages or not self.winfo_exists():
            return
        frame = self.tab_frames[index]
        for child in frame.winfo_children():
            child.destroy()
        loading = ctk.CTkLabel(frame, text="Chargement de la page...", font=FONT_BOLD,
                               text_color="#94a3b8")
        loading.place(relx=0.5, rely=0.5, anchor="center")
        self.loading_page = loading
        self.update_idletasks()

        if index == 0:
            from dashboard import DashboardPage
            page = DashboardPage(frame, self)
        elif index == 1:
            from personnel import PersonnelPage
            page = PersonnelPage(frame, self)
        elif index == 2:
            from alerts import AlertesPage
            page = AlertesPage(frame, self)
        elif index == 3:
            from rapport import RapportPage
            page = RapportPage(frame, self)
            self.report_page = page
        else:
            from parameters import ParametersPage
            page = ParametersPage(frame, self)
        self.loaded_pages[index] = page
        if loading.winfo_exists():
            loading.destroy()
        self.loading_page = None

    def switch_tab(self, index):
        for f in self.tab_frames:
            f.place_forget()
        self.tab_frames[index].place(relx=0, rely=0, relwidth=1, relheight=1)
        if hasattr(self, "loaded_pages") and index not in self.loaded_pages:
            self.after(20, lambda i=index: self.load_page(i))
        for i, btn in enumerate(self.tab_buttons):
            btn.configure(fg_color=ACCENT_COLOR if i == index else "transparent")

        tab_sources = ["Dashboard", "Personnel", "Alertes", "Rapport", "Paramètres"]
        if 0 <= index < len(tab_sources):
            self.activity_log.append({
                'source': tab_sources[index],
                'time': datetime.now(),
                'message': f"Ouverture onglet {tab_sources[index]}"
            })

        if index == 3 and hasattr(self, 'report_page'):
            self.report_page.refresh_report()

    def update_clock(self):
        if hasattr(self, "clock_label") and self.clock_label.winfo_exists():
            self.clock_label.configure(
                text=f"● {self.current_account.get('nom', 'Compte actif')}  |  "
                     f"{datetime.now().strftime('%d/%m/%Y  %H:%M:%S')}"
            )
            self.after(1000, self.update_clock)

    def logout(self):
        for child in self.winfo_children():
            child.destroy()
        self.activity_log.clear()
        self.current_account = None
        self.login_frame = LoginPage(self, on_success=self._build_main_ui)


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
