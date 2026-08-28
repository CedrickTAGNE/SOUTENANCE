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
