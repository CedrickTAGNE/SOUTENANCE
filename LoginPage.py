# page_login.py
# L'image de fond ("Gemini.png/.jpg") ne contient QUE le décor (écrans, ville,
# lampe...) — la carte vitrée avec le titre, les champs et le bouton n'existe
# pas dans le fichier image lui-même : elle est entièrement recréée ici avec
# PIL (flou gaussien + voile translucide + coins arrondis + textes), puis
# fusionnée dans l'image avant affichage, pour reproduire fidèlement la
# maquette cible (carte "BUILDING SAMAR" centrée).
#
# Seuls les 3 éléments réellement interactifs (champ utilisateur, champ mot
# de passe, bouton LOGIN) restent des vrais widgets CustomTkinter, positionnés
# exactement sur les emplacements dessinés dans la carte.
#
# Si l'alignement n'est pas parfait chez toi, ajuste UNIQUEMENT les
# constantes CARD_* et FIELD_* ci-dessous (en pixels, par rapport au coin
# haut-gauche de la fenêtre 1400x820) — rien d'autre à toucher.

import os
import customtkinter as ctk

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageFont
except ImportError:
    Image = None
    ImageTk = None
    ImageDraw = None
    ImageFilter = None
    ImageFont = None

from config import (
    APP_USERNAME, APP_PASSWORD, LOGIN_BACKGROUND_BASENAME,
    FONT_NORMAL, FONT_BOLD, ACCENT_COLOR,
    APP_TITLE, APP_SUBTITLE, APP_FORGOT_TEXT, APP_LOCK_TEXT,
    CARD_BLUR_RADIUS, CARD_TINT_ALPHA, CARD_BORDER_ALPHA,
)
import db

WINDOW_W, WINDOW_H = 900, 500

# ---- Géométrie de la carte vitrée, centrée horizontalement ----
# Dimensionnée pour englober TOUT le contenu (titre -> champs -> bouton ->
# forgot password -> ligne d'authentification). Si tu agrandis CARD_H sans
# décaler les offsets ci-dessous, le bas de la carte laissera juste plus
# de marge vide ; ça ne cassera rien.
CARD_W = 380
CARD_H = 360
CARD_X = (WINDOW_W - CARD_W) // 2
CARD_Y = 105
CARD_RADIUS = 26

# ---- Ajuste ces valeurs si les champs ne tombent pas exactement
#      sur les zones de la carte (toutes exprimées en offset depuis CARD_Y,
#      donc si tu déplaces CARD_Y, tout le contenu suit automatiquement) ----
FIELD_W = CARD_W - 100
FIELD_X = CARD_X + 50
FIELD_H = 38

FIELD_USER_Y = CARD_Y + 105
FIELD_PASS_Y = CARD_Y + 157
FIELD_BTN_Y = CARD_Y + 209

# ---- Positions des textes secondaires (sous le bouton) ----
FORGOT_Y = CARD_Y + 264
LOCK_LINE_Y = CARD_Y + 305
TOP_TITLE_Y = 8


def _find_background_file():
    here = os.path.dirname(os.path.abspath(__file__))
    for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
        candidate = os.path.join(here, LOGIN_BACKGROUND_BASENAME + ext)
        if os.path.exists(candidate):
            return candidate
    return None


def _load_font(size, bold=False):
    """Cherche Times New Roman (cohérent avec FONT_NORMAL/FONT_BOLD) puis
    retombe sur Liberation/DejaVu si introuvable — ne plante jamais."""
    candidates = (
        ["timesbd.ttf", "Times New Roman Bold.ttf", "LiberationSerif-Bold.ttf"] if bold
        else ["times.ttf", "Times New Roman.ttf", "LiberationSerif-Regular.ttf"]
    )
    search_dirs = (
        "C:/Windows/Fonts",
        "/usr/share/fonts/truetype/msttcorefonts",
        "/usr/share/fonts/truetype/liberation",
        "/usr/share/fonts/truetype/dejavu",
        ".",
    )
    for name in candidates:
        for base in search_dirs:
            path = os.path.join(base, name)
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _centered_text(draw, text, y, font, fill, card_w):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(((card_w - w) / 2, y), text, font=font, fill=fill)


def _hide_background_title(base_img):
    """Masque la zone de titre déjà présente dans l'image de fond pour laisser
    le titre officiel apparaître uniquement dans le login."""
    overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    top_band = Image.new("RGBA", (base_img.width, 88), (8, 22, 38, 170))
    overlay.paste(top_band, (0, 0))
    return Image.alpha_composite(base_img.convert("RGBA"), overlay)


def _build_glass_card(base_img):
    """Découpe la zone de la carte dans base_img, la floute (effet givré),
    pose un voile translucide + un contour arrondi clair, écrit le titre,
    le sous-titre, "Forgot Password?" et la ligne d'authentification, puis
    recolle le résultat dans base_img."""

    # 1) Flouter uniquement la zone de la carte
    region = base_img.crop((CARD_X, CARD_Y, CARD_X + CARD_W, CARD_Y + CARD_H))
    region = region.convert("RGBA").filter(ImageFilter.GaussianBlur(CARD_BLUR_RADIUS))

    # 2) Voile translucide clair par-dessus le flou
    tint = Image.new("RGBA", (CARD_W, CARD_H), (255, 255, 255, CARD_TINT_ALPHA))
    region = Image.alpha_composite(region, tint)

    # 3) Masque à coins arrondis pour la carte
    mask = Image.new("L", (CARD_W, CARD_H), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle((0, 0, CARD_W - 1, CARD_H - 1), radius=CARD_RADIUS, fill=255)

    card_layer = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    card_layer.paste(region, (0, 0), mask)

    draw = ImageDraw.Draw(card_layer)
    draw.rounded_rectangle(
        (0, 0, CARD_W - 1, CARD_H - 1), radius=CARD_RADIUS,
        outline=(255, 255, 255, CARD_BORDER_ALPHA), width=2,
    )

    # 4) Textes statiques de la carte
    # Le titre principal est affiché au-dessus de la carte, pour éviter la répétition de BUILDING SAMAR
    font_sub = _load_font(13)
    font_small = _load_font(11)

    _centered_text(draw, APP_SUBTITLE, 72, font_sub, (210, 220, 232, 230), CARD_W)
    _centered_text(draw, APP_FORGOT_TEXT, FORGOT_Y - CARD_Y, font_small, (222, 230, 240, 220), CARD_W)

    lock_text = f"\U0001F512 {APP_LOCK_TEXT}"
    _centered_text(draw, lock_text, LOCK_LINE_Y - CARD_Y, font_small, (188, 198, 210, 210), CARD_W)

    # 5) Recoller la carte finie dans l'image de fond
    base_img.paste(card_layer, (CARD_X, CARD_Y), card_layer)
    return base_img


class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, on_success):
        super().__init__(parent, fg_color="black")
        self.on_success = on_success
        self.pack(fill="both", expand=True)

        self._build_background()
        self._build_controls()

    def _build_background(self):
        bg_path = _find_background_file()
        if not (Image and bg_path):
            ctk.CTkLabel(
                self,
                text=f"Image introuvable : {LOGIN_BACKGROUND_BASENAME}.png/.jpg/.jpeg\n"
                     f"Place-la au même endroit que main.py, sous ce nom exact.",
                text_color="#f85149", font=FONT_BOLD,
            ).place(relx=0.5, rely=0.5, anchor="center")
            return

        img = Image.open(bg_path).convert("RGBA").resize((WINDOW_W, WINDOW_H))
        img = _hide_background_title(img)
        img = _build_glass_card(img)
        self.bg_photo = ImageTk.PhotoImage(img.convert("RGB"))
        ctk.CTkLabel(self, text="", image=self.bg_photo).place(x=0, y=0, relwidth=1, relheight=1)

    def _build_controls(self):
        self._add_logo()
        ctk.CTkLabel(self, text=APP_TITLE, font=("Times New Roman", 30, "bold"),
                     text_color="#f0f5ff", fg_color="transparent").place(
            relx=0.5, y=TOP_TITLE_Y, anchor="n")

        self.login_card = ctk.CTkFrame(
            self, width=CARD_W, height=CARD_H, corner_radius=22,
            fg_color="#111827", border_width=1, border_color="#91a4c4",
        )
        self.login_card.place(x=CARD_X, y=CARD_Y)
        self.login_card.pack_propagate(False)
        ctk.CTkLabel(self.login_card, text="CONNEXION SÉCURISÉE", font=("Times New Roman", 18, "bold"),
                     text_color="#f8fafc").pack(pady=(24, 2))
        ctk.CTkLabel(self.login_card, text=APP_SUBTITLE, font=FONT_NORMAL,
                     text_color="#a8b5ca").pack(pady=(0, 18))

        field_box = ctk.CTkFrame(self.login_card, fg_color="transparent")
        field_box.pack(fill="x", padx=42)
        ctk.CTkLabel(field_box, text="IDENTIFIANT", font=FONT_BOLD,
                     text_color="#cbd5e1").pack(anchor="w", pady=(0, 4))
        self.entry_user = ctk.CTkEntry(
            field_box, placeholder_text="Votre identifiant", height=38,
            fg_color="#0b1220", border_width=1, border_color="#475569",
            text_color="#ffffff", placeholder_text_color="#7f8da3",
            font=("Times New Roman", 14),
        )
        self.entry_user.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(field_box, text="MOT DE PASSE", font=FONT_BOLD,
                     text_color="#cbd5e1").pack(anchor="w", pady=(0, 4))
        self.entry_pass = ctk.CTkEntry(
            field_box, placeholder_text="Votre mot de passe", height=38,
            fg_color="#0b1220", border_width=1, border_color="#475569",
            text_color="#ffffff", placeholder_text_color="#7f8da3",
            font=("Times New Roman", 14), show="•",
        )
        self.entry_pass.pack(fill="x")
        self.entry_pass.bind("<Return>", lambda e: self._try_login())

        self.lbl_error = ctk.CTkLabel(
            self.login_card, text="", font=FONT_NORMAL, text_color="#fca5a5",
            fg_color="transparent", wraplength=CARD_W - 84,
        )
        self.lbl_error.pack(pady=(8, 2))
        ctk.CTkButton(
            self.login_card, text="OUVRIR LA SESSION", font=FONT_BOLD,
            fg_color="#2f6fe4", hover_color="#1e40af", height=38,
            corner_radius=8, command=self._try_login,
        ).pack(fill="x", padx=42, pady=(4, 8))
        ctk.CTkLabel(self.login_card, text="Accès réservé au personnel autorisé",
                     font=("Times New Roman", 10), text_color="#94a3b8").pack()

    def _add_logo(self):
        path = os.path.join(os.path.dirname(__file__), "chracerh_logo.png")
        if not (Image and ImageTk and os.path.isfile(path)):
            return
        try:
            image = Image.open(path)
            self.login_logo = ImageTk.PhotoImage(image.resize((180, 84)))
            ctk.CTkLabel(self, image=self.login_logo, text="", fg_color="transparent").place(
                relx=0.5, y=58, anchor="center")
        except (OSError, ValueError):
            return

    def _try_login(self):
        user = self.entry_user.get().strip()
        pwd = self.entry_pass.get().strip()
        account = db.authenticate(user, pwd)
        if account or (user == APP_USERNAME and pwd == APP_PASSWORD):
            self.destroy()
            self.on_success(account or {"username": user, "nom": user, "role": "super_user"})
        else:
            self.lbl_error.configure(text="Identifiants incorrects.")