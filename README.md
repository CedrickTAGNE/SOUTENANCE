# Vidéosurveillance Intelligente au CHRACERH

## À propos du projet

Ce projet a été réalisé dans le cadre d'un stage académique au Centre Hospitalier 
de Recherche et d'Application en Chirurgie Endoscopique et Reproduction Humaine 
(CHRACERH), à Yaoundé. Avant ce projet, l'établissement ne disposait d'aucun 
système de vidéosurveillance : la sécurité reposait uniquement sur la vigilance 
d'agents humains.

L'application développée répond à ce besoin en proposant une solution de 
vidéosurveillance intelligente capable de détecter automatiquement les mouvements 
suspects, de générer des alertes horodatées, et d'offrir une supervision 
centralisée des zones sensibles de l'établissement, en temps réel comme à distance.

## Contexte institutionnel

- **Établissement** : CHRACERH, centre de référence médicale à Yaoundé
- **Formation** : Licence Professionnelle, Réseaux, Systèmes et Cybersécurité — 
  Institut Supérieur AZIMUT
- **Durée du stage** : avril à août 2026
- **Problématique** : absence de système de vidéosurveillance et de traçabilité 
  des incidents de sécurité au sein d'un environnement hospitalier sensible

## Fonctionnalités principales

- 🎥 **Détection de mouvement en temps réel** via OpenCV (niveaux de gris, flou 
  gaussien, soustraction de fond, détection de contours)
- 🚨 **Gestion et enregistrement automatique des alertes** avec horodatage précis
- 📊 **Tableau de bord de supervision** centralisant l'état des caméras et des 
  alertes en cours
- 🗄️ **Base de données des personnes et des logs de reconnaissance**, consultable 
  depuis l'interface
- ⚙️ **Page de paramètres** pour la configuration des caméras et du système
- 🔐 **Authentification** avant tout accès à l'interface

## Architecture technique

Le système repose sur une architecture matérielle et logicielle en trois couches :

**Côté matériel** : caméras → enregistreur (DVR/NVR) → commutateur PoE → routeur 
(accès distant) → moniteur (supervision locale)

**Côté logiciel** (architecture 3-tiers) :
- **Présentation** : interface graphique développée avec CustomTkinter
- **Métier** : module caméra basé sur OpenCV, exécuté dans un thread séparé pour 
  ne jamais bloquer l'interface
- **Données** : accès centralisé à PostgreSQL via `db.py`

## Stack technique

| Composant       | Technologie          |
|-----------------|-----------------------|
| Langage          | Python                |
| Interface        | CustomTkinter          |
| Traitement vidéo  | OpenCV                 |
| Base de données   | PostgreSQL (psycopg2)   |
| Environnement      | Anaconda                |

## Structure du projet
main.py # Orchestration et navigation entre les pages
config.py # Configuration (connexion DB, constantes)
db.py # Accès aux données (execute, fetch_all, fetch_one)
page_login.py # Authentification
page_dashboard.py # Supervision en temps réel
page_database.py # Consultation des personnes / logs
page_alertes.py # Gestion des alertes
page_parameters.py # Paramètres de configuration

## Base de données

Le système s'appuie sur PostgreSQL avec les tables suivantes :
- `TB_PERSONNE` — informations sur les personnes enregistrées
- `LOGS_RECONNAISSANCE` — historique des détections/reconnaissances
- `ALERTE` — alertes générées avec horodatage
- `TB_CAMERA` — informations et statut des caméras

## Installation

1. Cloner le dépôt
2. Créer un environnement Python (Anaconda recommandé)
3. Installer les dépendances : `pip install customtkinter opencv-python psycopg2`
4. Configurer la connexion PostgreSQL dans `config.py`
5. Créer les tables nécessaires dans la base de données
6. Lancer l'application : `python main.py`

## Utilisation

Après connexion, la navigation se fait via les onglets :
**Dashboard → Base de Données → Alertes → Paramètres**

## Auteure

**Lomo Ntede Julienne Christelle**  
Licence Professionnelle — Réseaux, Systèmes et Cybersécurité  
Institut Supérieur AZIMUT, Yaoundé  
Stage réalisé au CHRACERH (avril–août 2026)
