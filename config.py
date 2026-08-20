import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FONT_NORMAL = ("Times New Roman", 11)
FONT_BOLD = ("Times New Roman", 11, "bold")
ACCENT_COLOR = "#2f6fe4"
SUCCESS_COLOR = "#16a34a"
DANGER_COLOR = "#dc2626"
TEXT_MAIN = "#ffffff"
TEXT_MUTED = "#9ca3af"

TABLE_PERSONNE = "PERSONNEL"
TABLE_LOGS = "ACCES_CONTROL"
TABLE_ZONE = "POSTES"
TABLE_INTRUS = "INTRUS"
TABLE_SUPER_USER = "SUPER_USER"
TABLE_SALLE = "SALLES"
TABLE_HISTORY = "HISTORIQUE_MODIFICATION"

JSON_FILES = {
    TABLE_PERSONNE: os.path.join("data", "personnel.json"),
    TABLE_LOGS: os.path.join("data", "acces_control.json"),
    TABLE_INTRUS: os.path.join("data", "intrus.json"),
    TABLE_SUPER_USER: os.path.join("data", "super_user.json"),
    TABLE_SALLE: os.path.join("data", "salles.json"),
    TABLE_HISTORY: os.path.join("data", "historique_modification.json"),
    TABLE_ZONE: os.path.join("data", "postes.json"),
}

APP_USERNAME = "admin"
APP_PASSWORD = "admin"
LOGIN_BACKGROUND_BASENAME = "Gemini"
APP_TITLE = "BUILDING SAMAR"
APP_SUBTITLE = "Système de supervision et contrôle d'accès"
APP_FORGOT_TEXT = "Mot de passe oublié ?"
APP_LOCK_TEXT = "AUTHENTIFICATION REQUISE"
CARD_BLUR_RADIUS = 8
CARD_TINT_ALPHA = 80
CARD_BORDER_ALPHA = 150

HOSPITAL_POSTES = [
    "Administration",
    "Accueil",
    "Bloc opératoire",
    "Direction",
    "Laboratoire",
    "Pharmacie",
    "Radiologie",
    "Réanimation",
    "Urgences",
]
