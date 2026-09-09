# db.py
# Service de stockage local JSON partage par les ecrans de l'application.

import json
import os
import re
from datetime import datetime

from config import (
    JSON_FILES, TABLE_PERSONNE, TABLE_LOGS, TABLE_ZONE, TABLE_INTRUS,
    TABLE_SUPER_USER, TABLE_SALLE, TABLE_HISTORY, TABLE_CAMERAS, HOSPITAL_POSTES,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _path(table):
    return os.path.join(BASE_DIR, JSON_FILES[table])


def _read(table):
    try:
        with open(_path(table), "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _write(table, rows):
    with open(_path(table), "w", encoding="utf-8") as file:
        json.dump(rows, file, ensure_ascii=False, indent=2, default=lambda value: value.isoformat(timespec="seconds") if isinstance(value, datetime) else value)


def initialize_json_store():
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    defaults = {
        TABLE_PERSONNE: [{
            "cni": "AA1634", "nom": "NTEDE", "prenom": "JULIENNE CHRISTELLE",
            "ville": "YAOUNDE", "quartier": "NGOUSSO-HOPITAL GENERAL",
            "date_enregistrement": datetime.now(), "photo_path": "data_photos/AA1634.jpg",
            "contact_phone": "+237 6 00 00 00 00", "empreinte_digitale": "", "poste": "Accueil",
            "face_id": None,
        }],
        TABLE_LOGS: [], TABLE_INTRUS: [],
        TABLE_SUPER_USER: [{"username": "admin", "password": "admin", "nom": "Administrateur", "role": "super_user", "date_de_naissance": "", "telephone": ""}],
        TABLE_SALLE: [{"id": index + 1, "nom_salle": poste, "description": "Zone protegée de l'hopital", "numero": f"S-{index + 1:02d}", "liste_personnel": []} for index, poste in enumerate(HOSPITAL_POSTES)],
        TABLE_HISTORY: [],
        TABLE_ZONE: [{"zone_name": poste, "description": "Poste hospitalier", "lat": None, "lon": None, "created_at": datetime.now()} for poste in HOSPITAL_POSTES],
        TABLE_CAMERAS: [
            {"id": 1, "nom": "Caméra Entrée Principale", "zone": "Accueil", "source": "0", "status": "Actif", "type": "USB / Interne"},
            {"id": 2, "nom": "Caméra Bloc A", "zone": "Bloc opératoire", "source": "rtsp://192.168.1.101:554/stream", "status": "Actif", "type": "RTSP / IP"},
            {"id": 3, "nom": "Caméra Urgences 1", "zone": "Urgences", "source": "rtsp://192.168.1.102:554/stream", "status": "Inactif", "type": "RTSP / IP"},
        ],
    }
    for table, rows in defaults.items():
        if not os.path.exists(_path(table)):
            _write(table, rows)
    personnel = _read(TABLE_PERSONNE)
    changed = False
    for person in personnel:
        if "face_id" not in person:
            person["face_id"] = None
            changed = True
    if changed:
        _write(TABLE_PERSONNE, personnel)
    ensure_face_ids()


def ensure_face_ids():
    try:
        personnel = _read(TABLE_PERSONNE)
        if not personnel:
            return
        changed = False
        from face_utils import extract_face_id_from_path
        for person in personnel:
            if not person.get("face_id") and person.get("photo_path"):
                fid = extract_face_id_from_path(person["photo_path"])
                if fid:
                    person["face_id"] = fid
                    changed = True
        if changed:
            _write(TABLE_PERSONNE, personnel)
    except Exception as e:
        print(f"[JSON] Error auto-populating face_ids: {e}")


def check_duplicate_person(cni, nom="", prenom="", face_id=None, photo_path=None, exclude_cni=None, match_threshold=45.0):
    """
    Vérifie si le CNI, l'identité (Nom + Prénom) ou la photo/matrice faciale existe déjà dans TABLE_PERSONNE.
    Retourne (is_duplicate: bool, error_message: str, existing_person: dict ou None).
    """
    try:
        personnel = read_table(TABLE_PERSONNE) or []
        if not personnel:
            return False, "", None

        cni_clean = str(cni or "").strip().upper()
        nom_clean = str(nom or "").strip().lower()
        prenom_clean = str(prenom or "").strip().lower()

        input_words = set(re.findall(r'\w+', f"{nom_clean} {prenom_clean}"))

        from face_utils import compare_face_ids, extract_face_id_from_path

        if not face_id and photo_path:
            face_id = extract_face_id_from_path(photo_path)

        for person in personnel:
            ex_cni = str(person.get("cni", "")).strip().upper()
            if exclude_cni and str(exclude_cni).strip().upper() == ex_cni:
                continue

            ex_nom = str(person.get("nom", "")).strip().lower()
            ex_prenom = str(person.get("prenom", "")).strip().lower()
            full_ex_name = f"{person.get('nom', '')} {person.get('prenom', '')}".strip()

            # 1. Vérification par CNI / Matricule
            if cni_clean and ex_cni == cni_clean:
                return True, f"Un membre avec le CNI/Matricule '{person.get('cni')}' est déjà enregistré ({full_ex_name}).", person

            # 2. Vérification par Nom et Prénom (insensible à l'ordre)
            if input_words:
                ex_words = set(re.findall(r'\w+', f"{ex_nom} {ex_prenom}"))
                if ex_words and input_words == ex_words:
                    return True, f"Une personne nommée '{full_ex_name}' est déjà enregistrée (CNI: {person.get('cni')}).", person
                common = input_words.intersection(ex_words)
                if len(common) >= 2 and (len(common) == len(input_words) or len(common) == len(ex_words)):
                    return True, f"Une personne similaire '{full_ex_name}' est déjà enregistrée (CNI: {person.get('cni')}).", person

            # 3. Vérification par Matrice Faciale / Photo (Seuil de détection doublon à 45.0)
            if face_id is not None:
                ex_fid = person.get("face_id")
                if not ex_fid and person.get("photo_path"):
                    ex_fid = extract_face_id_from_path(person.get("photo_path"))
                    if ex_fid:
                        person["face_id"] = ex_fid

                if ex_fid is not None:
                    dup_threshold = max(float(match_threshold), 45.0)
                    matched, dist = compare_face_ids(face_id, ex_fid, threshold=dup_threshold)
                    if matched:
                        return True, f"Ce visage est DÉJÀ ENREGISTRÉ pour : {full_ex_name} (CNI: {person.get('cni')}). Doublon refusé.", person

        return False, "", None
    except Exception as error:
        print(f"[Check Duplicate Error] {error}")
        return False, "", None


def fetch_all(query="", params=None):
    """Compatibilité JSON pour fetch_all sur TABLE_PERSONNE."""
    if TABLE_PERSONNE in query.upper():
        rows = read_table(TABLE_PERSONNE)
        return [(r.get("cni"), r.get("nom"), r.get("prenom"), r.get("photo_path"),
                 r.get("ville"), r.get("quartier"), r.get("face_id"), r.get("poste")) for r in rows]
    return []


def execute(query="", params=None):
    """Compatibilité JSON pour execute sur TABLE_LOGS et TABLE_PERSONNE."""
    if TABLE_LOGS in query.upper() and params:
        add_record(TABLE_LOGS, {
            "cni": params[0] if len(params) > 0 else "",
            "date_heure": params[1] if len(params) > 1 else datetime.now(),
            "piece": params[2] if len(params) > 2 else "Zone de surveillance",
            "statut": params[3] if len(params) > 3 else "Détecté"
        })




def get_postes():
    return [row.get("zone_name", "") for row in _read(TABLE_ZONE) if row.get("zone_name")]


def read_table(table):
    initialize_json_store()
    return _read(table)


def write_table(table, rows):
    initialize_json_store()
    _write(table, rows)


def authenticate(username, password):
    return next((account for account in _read(TABLE_SUPER_USER)
                 if account.get("username") == username and account.get("password") == password), None)


def add_record(table, record):
    rows = read_table(table)
    record = dict(record)
    record.setdefault("id", max((row.get("id", 0) for row in rows if isinstance(row.get("id", 0), int)), default=0) + 1)
    rows.append(record)
    write_table(table, rows)
    return record


def update_record(table, identifier, changes, key="id"):
    rows = read_table(table)
    for row in rows:
        if str(row.get(key)) == str(identifier):
            row.update(changes)
            write_table(table, rows)
            return row
    return None


def delete_record(table, identifier, key="id"):
    rows = read_table(table)
    filtered = [row for row in rows if str(row.get(key)) != str(identifier)]
    if len(filtered) == len(rows):
        return False
    write_table(table, filtered)
    return True


def log_history(username, target, description):
    add_record(TABLE_HISTORY, {
        "utilisateur": username or "systeme",
        "cible_modifiee": target,
        "description": description,
        "date_action": datetime.now(),
    })


def check_status():
    initialize_json_store()
    return "STOCKAGE JSON LOCAL", "#10b981"


def storage_status():
    initialize_json_store()
    return "STOCKAGE LOCAL ACTIF", "#10b981"


def _table_from_query(query):
    match = re.search(r'FROM\s+"?([A-Z_]+)"?|INTO\s+"?([A-Z_]+)"?|UPDATE\s+"?([A-Z_]+)', query, re.I)
    return next((value.upper() for value in match.groups() if value), None) if match else None


def fetch_all(query, params=None):
    initialize_json_store()
    table = _table_from_query(query)
    rows = _read(table) if table in JSON_FILES else []
    params = list(params or ())
    where = re.search(r"WHERE\s+([a-z_]+)\s*=\s*%s", query, re.I)
    if where and params:
        rows = [row for row in rows if str(row.get(where.group(1))) == str(params[-1])]
    if "COUNT(*)" in query.upper():
        return [(len(rows),)]
    if "ORDER BY random()" in query.lower():
        rows.reverse()
    elif re.search(r"ORDER BY\s+date_enregistrement", query, re.I):
        rows.sort(key=lambda row: str(row.get("date_enregistrement", "")), reverse="DESC" in query.upper())
    elif re.search(r"ORDER BY\s+date_heure", query, re.I):
        rows.sort(key=lambda row: str(row.get("date_heure", "")), reverse="DESC" in query.upper())
    limit = re.search(r"LIMIT\s+(\d+)", query, re.I)
    if limit:
        rows = rows[:int(limit.group(1))]
    select = re.search(r"SELECT\s+(.*?)\s+FROM", query, re.I | re.S)
    if not select:
        return []
    columns = [column.strip().strip('"') for column in select.group(1).split(",")]
    return [tuple(_decode(row.get(column)) for column in columns) for row in rows]


def fetch_one(query, params=None):
    rows = fetch_all(query, params)
    return rows[0] if rows else None


def _decode(value):
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}T", value):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return value


def execute(query, params=None):
    initialize_json_store()
    table = _table_from_query(query)
    if table not in JSON_FILES:
        return False
    rows = _read(table)
    params = list(params or ())
    try:
        if query.strip().upper().startswith("DELETE"):
            match = re.search(r"WHERE\s+([a-z_]+)\s*=\s*%s", query, re.I)
            rows = [row for row in rows if not match or str(row.get(match.group(1))) != str(params[-1])]
        elif query.strip().upper().startswith("UPDATE"):
            assignments = query.split("WHERE", 1)[0]
            fields = re.findall(r"([a-z_]+)\s*=\s*%s", assignments, re.I)
            where = re.search(r"WHERE\s+([a-z_]+)\s*=\s*%s", query, re.I)
            for row in rows:
                if where and str(row.get(where.group(1))) == str(params[-1]):
                    for field, value in zip(fields, params):
                        row[field] = value.isoformat(timespec="seconds") if isinstance(value, datetime) else value
        elif query.strip().upper().startswith("INSERT"):
            columns = re.search(r"\((.*?)\)\s*VALUES", query, re.I | re.S).group(1).split(",")
            record = {column.strip().strip('"'): (value.isoformat(timespec="seconds") if isinstance(value, datetime) else value) for column, value in zip(columns, params)}
            if "ON CONFLICT" in query.upper() and table == TABLE_PERSONNE:
                rows = [row for row in rows if row.get("cni") != record.get("cni")]
            if table in (TABLE_LOGS, "INTRUS"):
                record.setdefault("id", len(rows) + 1)
            rows.append(record)
        _write(table, rows)
        return True
    except (AttributeError, IndexError, TypeError) as error:
        print(f"[JSON] Erreur écriture : {error}")
        return False


initialize_json_store()
