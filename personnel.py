import os
import urllib.request
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:
    from PIL import Image
except ImportError:
    Image = None

import db
from config import (
    ACCENT_COLOR,
    DANGER_COLOR,
    FONT_BOLD,
    FONT_NORMAL,
    SUCCESS_COLOR,
    TABLE_PERSONNE,
    TABLE_SALLE,
    TEXT_MAIN,
    TEXT_MUTED,
)


def get_cascade_path(cv2):
    """Récupère le chemin du Haar Cascade OpenCV ou le télécharge si absent."""
    filename = "haarcascade_frontalface_default.xml"
    
    cv2_path = os.path.join(cv2.data.haarcascades, filename)
    if os.path.exists(cv2_path):
        return cv2_path

    local_path = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(local_path):
        return local_path

    try:
        url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/" + filename
        urllib.request.urlretrieve(url, local_path)
        return local_path
    except Exception:
        return None


class PersonnelPage:
    def __init__(self, parent, controller=None):
        self.parent = parent
        self.controller = controller
        self.editing_cni = None
        self.form_entries = {}
        parent.configure(fg_color="#070a0e")
        parent.grid_columnconfigure(0, weight=5, uniform="personnel")
        parent.grid_columnconfigure(1, weight=0)
        parent.grid_columnconfigure(2, weight=5, uniform="personnel")
        parent.grid_rowconfigure(0, weight=1)

        list_panel = ctk.CTkFrame(parent, fg_color="#161b22", border_width=1, border_color="#30363d")
        list_panel.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        ctk.CTkLabel(list_panel, text="MEMBRES DU PERSONNEL", font=FONT_BOLD,
                     text_color=ACCENT_COLOR).pack(anchor="w", padx=12, pady=(12, 4))
        self.search_entry = ctk.CTkEntry(list_panel, height=30, placeholder_text="Rechercher un nom ou matricule",
                                         fg_color="#0b0f19", border_color="#30363d")
        self.search_entry.pack(fill="x", padx=10, pady=(0, 6))
        self.search_entry.bind("<KeyRelease>", lambda event: self.refresh_people())
        self.people_list = ctk.CTkScrollableFrame(list_panel, fg_color="#0b0f19", height=190)
        self.people_list.pack(fill="both", expand=False, padx=8, pady=(0, 6))
        ctk.CTkLabel(list_panel, text="SALLES PROTÉGÉES", font=FONT_BOLD,
                     text_color=ACCENT_COLOR).pack(anchor="w", padx=12, pady=(3, 3))
        self.rooms_list = ctk.CTkScrollableFrame(list_panel, fg_color="#0b0f19", height=130)
        self.rooms_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        ctk.CTkFrame(parent, width=2, fg_color="#475569").grid(row=0, column=1, sticky="ns", pady=18)

        form_panel = ctk.CTkFrame(parent, fg_color="#161b22", border_width=1, border_color="#30363d")
        form_panel.grid(row=0, column=2, sticky="nsew", padx=(4, 8), pady=8)
        ctk.CTkLabel(form_panel, text="NOUVEAU MEMBRE / MODIFICATION", font=FONT_BOLD,
                     text_color=ACCENT_COLOR).pack(anchor="w", padx=14, pady=(12, 6))
        form = ctk.CTkScrollableFrame(form_panel, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=4)
        for key, label in (("cni", "MATRICULE"), ("nom", "NOM"), ("prenom", "PRÉNOM"),
                           ("fonction", "FONCTION"), ("service", "SERVICE"),
                           ("telephone", "TÉLÉPHONE")):
            ctk.CTkLabel(form, text=label, font=FONT_NORMAL, text_color=TEXT_MAIN).pack(anchor="w", padx=10, pady=(4, 1))
            entry = ctk.CTkEntry(form, height=29, fg_color="#0b0f19", border_color="#30363d")
            entry.pack(fill="x", padx=10, pady=(0, 4))
            self.form_entries[key] = entry

        ctk.CTkLabel(form, text="POSTE HOSPITALIER", font=FONT_NORMAL, text_color=TEXT_MAIN).pack(anchor="w", padx=10, pady=(4, 1))
        self.poste_option = ctk.CTkOptionMenu(form, values=db.get_postes() or ["Accueil"], height=29,
                                               fg_color="#0b0f19", button_color="#30363d")
        self.poste_option.pack(fill="x", padx=10, pady=(0, 5))
        ctk.CTkLabel(form, text="STATUT", font=FONT_NORMAL, text_color=TEXT_MAIN).pack(anchor="w", padx=10, pady=(4, 1))
        self.status_option = ctk.CTkOptionMenu(form, values=["Actif", "Inactif"], height=29,
                                                fg_color="#0b0f19", button_color="#30363d")
        self.status_option.pack(fill="x", padx=10, pady=(0, 5))
        self.photo_path = ""
        self.face_id = None
        self.photo_status = ctk.CTkLabel(form, text="Aucune photo sélectionnée", font=FONT_NORMAL,
                                         text_color=TEXT_MUTED, anchor="w")
        self.photo_status.pack(fill="x", padx=10, pady=(3, 2))
        ctk.CTkButton(form, text="PHOTO DE PROFIL - OUVRIR LA CAMÉRA", height=29, fg_color="#374151",
                      command=self.open_photo_camera).pack(fill="x", padx=10, pady=(0, 5))
        self.face_status = ctk.CTkLabel(form, text="FaceId non scanné", font=FONT_NORMAL,
                                        text_color=DANGER_COLOR, anchor="w")
        self.face_status.pack(fill="x", padx=10, pady=(3, 2))
        ctk.CTkButton(form, text="SCANNER ET ENREGISTRER LE FACEID", height=29,
                      fg_color=ACCENT_COLOR, hover_color="#2563eb",
                      command=self.open_face_scan).pack(fill="x", padx=10, pady=(0, 5))

        actions = ctk.CTkFrame(form_panel, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(4, 10))
        ctk.CTkButton(actions, text="ENREGISTRER", fg_color=SUCCESS_COLOR, height=32,
                      command=self.save_person).pack(side="left", expand=True, fill="x", padx=(0, 3))
        ctk.CTkButton(actions, text="EFFACER", fg_color="#374151", height=32,
                      command=self.clear_form).pack(side="left", expand=True, fill="x", padx=3)
        ctk.CTkButton(actions, text="SUPPRIMER", fg_color=DANGER_COLOR, height=32,
                      command=self.delete_person).pack(side="left", expand=True, fill="x", padx=(3, 0))
        self.refresh_people()
        self.refresh_rooms()

    def refresh_people(self):
        for child in self.people_list.winfo_children():
            child.destroy()
        query = self.search_entry.get().strip().lower()
        people = db.read_table(TABLE_PERSONNE)
        for person in people:
            haystack = " ".join(str(person.get(key, "")) for key in ("cni", "nom", "prenom", "fonction", "service")).lower()
            if query and query not in haystack:
                continue
            card = ctk.CTkFrame(self.people_list, fg_color="#161b22", border_width=1, border_color="#30363d")
            card.pack(fill="x", pady=4)
            active = person.get("is_active", True)
            ctk.CTkLabel(card, text=f"{person.get('nom', '')} {person.get('prenom', '')}",
                         font=FONT_BOLD, text_color=TEXT_MAIN).pack(anchor="w", padx=8, pady=(6, 0))
            ctk.CTkLabel(card, text=f"{person.get('cni', '')}  •  {person.get('poste', 'Poste non défini')}",
                         font=FONT_NORMAL, text_color=SUCCESS_COLOR if active else DANGER_COLOR).pack(anchor="w", padx=8, pady=(0, 6))
            card.bind("<Button-1>", lambda event, item=person: self.load_person(item))
            for child in card.winfo_children():
                child.bind("<Button-1>", lambda event, item=person: self.load_person(item))

    def refresh_rooms(self):
        for child in self.rooms_list.winfo_children():
            child.destroy()
        personnel = {person.get("cni"): person for person in db.read_table(TABLE_PERSONNE)}
        for room in db.read_table(TABLE_SALLE):
            card = ctk.CTkFrame(self.rooms_list, fg_color="#161b22", border_width=1, border_color="#30363d")
            card.pack(fill="x", pady=3)
            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, padx=8, pady=4)
            ctk.CTkLabel(info, text=f"{room.get('nom_salle', 'Salle')}  •  {room.get('numero', '')}",
                         font=FONT_BOLD, text_color=TEXT_MAIN).pack(anchor="w")
            members = len([cni for cni in room.get("liste_personnel", []) if cni in personnel])
            ctk.CTkLabel(info, text=f"Personnel autorisé : {members}", font=FONT_NORMAL,
                         text_color=TEXT_MUTED).pack(anchor="w")
            ctk.CTkButton(card, text="SUPPRIMER", width=88, height=26, fg_color=DANGER_COLOR,
                          hover_color="#b91c1c",
                          command=lambda item=room: self.confirm_delete_room(item)).pack(
                side="right", padx=8, pady=5)

    def confirm_delete_room(self, room):
        if not messagebox.askyesno("Confirmation", f"Supprimer la salle {room.get('nom_salle', '')} ?"):
            return
        if db.delete_record(TABLE_SALLE, room.get("id"), key="id"):
            db.log_history(
                getattr(self.controller, "current_account", {}).get("username"),
                f"SALLE:{room.get('id')}",
                "Salle supprimée",
            )
            self.refresh_rooms()

    def load_person(self, person):
        self.editing_cni = person.get("cni")
        for key, entry in self.form_entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, person.get(key, "") or "")
        poste = person.get("poste", "Accueil")
        self.poste_option.set(poste if poste in db.get_postes() else "Accueil")
        self.status_option.set("Actif" if person.get("is_active", True) else "Inactif")
        self.photo_path = person.get("photo_path", "") or ""
        self.photo_status.configure(text=os.path.basename(self.photo_path) if self.photo_path else "Aucune photo sélectionnée")
        self.face_id = person.get("face_id")
        self.face_status.configure(
            text="FaceId enregistré" if self.face_id is not None else "FaceId non scanné",
            text_color=SUCCESS_COLOR if self.face_id is not None else DANGER_COLOR,
        )

    def clear_form(self):
        self.editing_cni = None
        self.photo_path = ""
        self.face_id = None
        self.photo_status.configure(text="Aucune photo sélectionnée")
        self.face_status.configure(text="FaceId non scanné", text_color=DANGER_COLOR)
        for entry in self.form_entries.values():
            entry.delete(0, tk.END)
        self.poste_option.set(db.get_postes()[0] if db.get_postes() else "Accueil")
        self.status_option.set("Actif")

    def _init_camera(self, cv2):
        for backend in [getattr(cv2, "CAP_DSHOW", None), cv2.CAP_ANY]:
            cap = cv2.VideoCapture(0, backend) if backend is not None else cv2.VideoCapture(0)
            if cap.isOpened():
                return cap
            cap.release()
        return None

    def open_photo_camera(self):
        try:
            import cv2
        except ImportError:
            messagebox.showerror("Caméra indisponible", "OpenCV n'est pas installé correctement.")
            return

        window = ctk.CTkToplevel(self.parent)
        window.title("Capture de la photo de profil")
        window.geometry("440x360")
        window.resizable(False, False)
        window.attributes("-topmost", True)
        window.lift()
        window.focus_force()
        
        preview = ctk.CTkLabel(window, text="Initialisation de la caméra...", width=400, height=270)
        preview.pack(padx=12, pady=12)

        capture_button = ctk.CTkButton(window, text="CAPTURER", fg_color=SUCCESS_COLOR, state="disabled")
        capture_button.pack(side="left", expand=True, fill="x", padx=(12, 4), pady=(0, 12))

        close_button = ctk.CTkButton(window, text="FERMER", fg_color=DANGER_COLOR)
        close_button.pack(side="right", expand=True, fill="x", padx=(4, 12), pady=(0, 12))

        camera = self._init_camera(cv2)
        state = {"running": True, "frame": None}

        if camera is None:
            preview.configure(text="Caméra indisponible")

        def close():
            state["running"] = False
            if camera and camera.isOpened():
                camera.release()
            window.destroy()

        def update_preview():
            if not state["running"] or camera is None:
                return
            ok, frame = camera.read()
            if ok and frame is not None:
                state["frame"] = frame.copy()
                if Image:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(rgb_frame)
                    ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(400, 270))
                    preview.configure(image=ctk_img, text="")
                    capture_button.configure(state="normal")
            window.after(30, update_preview)

        def capture():
            if state["frame"] is None:
                return
            os.makedirs(os.path.join(os.path.dirname(__file__), "media"), exist_ok=True)
            identifier = self.form_entries["cni"].get().strip() or "personnel"
            filename = f"{identifier}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            path = os.path.join("media", filename)
            if cv2.imwrite(os.path.join(os.path.dirname(__file__), path), state["frame"]):
                self.photo_path = path
                self.photo_status.configure(text=filename)
                close()

        capture_button.configure(command=capture)
        close_button.configure(command=close)
        window.protocol("WM_DELETE_WINDOW", close)
        update_preview()

    def open_face_scan(self):
        try:
            import cv2
            from face_utils import extract_face_id
        except ImportError:
            messagebox.showerror("FaceId indisponible", "Vérifiez l'installation d'OpenCV et la présence de face_utils.py.")
            return

        xml_path = get_cascade_path(cv2)
        if not xml_path or not os.path.exists(xml_path):
            messagebox.showerror("Erreur Modèle", "Impossible de charger le fichier haarcascade_frontalface_default.xml.")
            return

        cascade = cv2.CascadeClassifier(xml_path)
        if cascade.empty():
            messagebox.showerror("Erreur Cascade", "Erreur lors du chargement du fichier de détection faciale.")
            return

        window = ctk.CTkToplevel(self.parent)
        window.title("Scan FaceId")
        window.geometry("460x440")
        window.resizable(False, False)
        
        # Forcer la fenêtre à s'ouvrir et à rester au premier plan
        window.attributes("-topmost", True)
        window.lift()
        window.focus_force()

        preview = ctk.CTkLabel(window, text="Initialisation...", width=420, height=290)
        preview.pack(padx=12, pady=12)

        status = ctk.CTkLabel(window, text="Scan en cours... Temps restant : 20s",
                              font=FONT_BOLD, text_color=TEXT_MUTED)
        status.pack(pady=(0, 8))

        actions = ctk.CTkFrame(window, fg_color="transparent")
        actions.pack(fill="x", padx=12, pady=(0, 12))

        retry_button = ctk.CTkButton(actions, text="RELANCER LE SCAN", state="disabled", fg_color=ACCENT_COLOR)
        retry_button.pack(side="left", expand=True, fill="x", padx=(0, 4))

        close_button = ctk.CTkButton(actions, text="FERMER", fg_color=DANGER_COLOR)
        close_button.pack(side="left", expand=True, fill="x", padx=(4, 0))

        camera = self._init_camera(cv2)
        
        # Configuration avec 20 secondes de scan minimum garanti
        MIN_SCAN_DURATION = 20
        state = {
            "running": True, 
            "started": datetime.now().timestamp(),
            "captured_face_id": None
        }

        if camera is None:
            preview.configure(text="Impossible d'accéder à la caméra")
            status.configure(text="Vérifiez si une autre application utilise la caméra", text_color=DANGER_COLOR)

        def close():
            state["running"] = False
            if camera and camera.isOpened():
                camera.release()
            window.destroy()

        def update():
            if not state["running"] or camera is None or not camera.isOpened():
                return
            
            elapsed = int(datetime.now().timestamp() - state["started"])
            remaining = max(0, MIN_SCAN_DURATION - elapsed)

            ok, frame = camera.read()
            if ok and frame is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))

                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Capture du visage si détecté et pas encore enregistré
                if len(faces) > 0 and state["captured_face_id"] is None:
                    try:
                        face_id = extract_face_id(frame, cascade)
                    except TypeError:
                        face_id = extract_face_id(frame)

                    if face_id is not None:
                        state["captured_face_id"] = face_id

                # Mettre à jour les messages d'état
                if state["captured_face_id"] is not None:
                    if remaining > 0:
                        status.configure(
                            text=f"Visage capturé ! Maintien de la fenêtre ({remaining}s)", 
                            text_color=SUCCESS_COLOR
                        )
                    else:
                        self.face_id = state["captured_face_id"]
                        self.face_status.configure(text="FaceId enregistré", text_color=SUCCESS_COLOR)
                        status.configure(text="Scan terminé avec succès.", text_color=SUCCESS_COLOR)
                        state["running"] = False
                        camera.release()
                        window.after(800, close)
                        return
                else:
                    if remaining > 0:
                        status.configure(
                            text=f"Scan en cours... Positionnez votre visage ({remaining}s)", 
                            text_color=TEXT_MUTED
                        )
                    else:
                        status.configure(
                            text="Scan terminé. Aucun visage valide détecté.", 
                            text_color=DANGER_COLOR
                        )
                        retry_button.configure(state="normal")

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_frame)
                ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(420, 290))
                preview.configure(image=ctk_img, text="")

            window.after(30, update)

        def begin_scan():
            nonlocal camera
            if camera and camera.isOpened():
                camera.release()
            camera = self._init_camera(cv2)
            state["started"] = datetime.now().timestamp()
            state["running"] = True
            state["captured_face_id"] = None
            retry_button.configure(state="disabled")
            update()

        retry_button.configure(command=begin_scan)
        close_button.configure(command=close)
        window.protocol("WM_DELETE_WINDOW", close)

        if camera is not None:
            update()

    def save_person(self):
        values = {key: entry.get().strip() for key, entry in self.form_entries.items()}
        
        if not values["cni"] or not values["nom"]:
            self.show_save_feedback(False, "Matricule et nom obligatoires")
            return
        if self.face_id is None:
            self.show_save_feedback(False, "Scannez le FaceId avant d'enregistrer")
            return

        try:
            serializable_face_id = (
                self.face_id.tolist() if hasattr(self.face_id, "tolist") else self.face_id
            )

            values.update({
                "poste": self.poste_option.get(),
                "is_active": self.status_option.get() == "Actif",
                "photo_path": self.photo_path,
                "face_id": serializable_face_id,
                "date_enregistrement": datetime.now().isoformat(timespec="seconds"),
            })

            people = db.read_table(TABLE_PERSONNE) or []

            if self.editing_cni:
                people = [person for person in people if person.get("cni") != self.editing_cni]
            people = [person for person in people if person.get("cni") != values["cni"]]

            people.append(values)
            db.write_table(TABLE_PERSONNE, people)

            username = getattr(self.controller, "current_account", {}).get("username", "Système")
            db.log_history(username, f"PERSONNEL:{values['cni']}", "Profil enregistré ou modifié")

            self.clear_form()
            self.refresh_people()
            self.show_save_feedback(True, "Membre enregistré avec succès")

        except Exception as error:
            self.show_save_feedback(False, f"Enregistrement impossible : {error}")

    def show_save_feedback(self, success, message):
        popup = ctk.CTkToplevel(self.parent)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(fg_color="#102018" if success else "#261417")
        popup.geometry("310x96+" + str(self.parent.winfo_rootx() + 295) + "+" + str(self.parent.winfo_rooty() + 175))
        icon = "✓" if success else "✕"
        color = "#4ade80" if success else "#f87171"
        ctk.CTkLabel(popup, text=icon, font=("Segoe UI Symbol", 30, "bold"),
                     text_color=color).pack(side="left", padx=(18, 10))
        ctk.CTkLabel(popup, text=message, font=FONT_BOLD, text_color="#f8fafc",
                     wraplength=235, justify="left").pack(side="left", fill="both", expand=True, padx=(0, 12))
        popup.after(4000, popup.destroy)

    def delete_person(self):
        if not self.editing_cni:
            messagebox.showinfo("Suppression", "Sélectionnez d'abord un membre.")
            return
        if db.delete_record(TABLE_PERSONNE, self.editing_cni, key="cni"):
            db.log_history(getattr(self.controller, "current_account", {}).get("username"),
                           f"PERSONNEL:{self.editing_cni}", "Profil supprimé")
            self.clear_form()
            self.refresh_people()