# Miroir Magique Intelligent — Cahier global

## 1️⃣ Objectif final du projet

Le projet consiste à créer un **miroir intelligent offline**, capable de :

1. Afficher le flux vidéo de la webcam en mode miroir.
2. Afficher un assistant IA (avatar + texte) dans un coin de l’écran.
3. Se réveiller lorsqu’on prononce une **phrase magique**.
4. Analyser la personne devant le miroir :
   - Présence d’un visage
   - Tenue (outfit) : couleurs dominantes, contraste, style
   - Proposer des **recommandations stylistiques personnalisées**, basées sur contexte (heure, saison, température approximative)
5. Parler via synthèse vocale locale (TTS).
6. Respecter la **confidentialité totale** (100% offline).
7. Être optimisé pour un **mini PC faible puissance** (Intel N100) :
   - Résolution caméra limitée (640x480)
   - Analyses espacées (300–500ms)
   - Modules désactivés en veille
   - LLM petit modèle quantisé (1B–3B)
   - Minimum de threads et CPU-friendly

---

## 2️⃣ Règles et contraintes

- **100% offline** : aucune requête externe (API, cloud) n’est autorisée.
- **Optimisation CPU / mémoire** : toutes les fonctions doivent être légères, travailler sur basse résolution et limiter les traitements fréquents.
- **Modularité** : chaque module doit être indépendant et respecter un contrat clair (entrée/sortie définie).
- **Découplage** : communication via **Event Bus** et non par appels directs.
- **Testabilité** : chaque module doit pouvoir être testé isolément.
- **Extensibilité** : futur remplacement de modules par des versions plus avancées sans toucher aux autres.

---

## 3️⃣ Architecture générale

Le projet suit une architecture **modulaire et scalable** :
TEKBOT-MAGIC-MIRROR-2026/
│
├── main.py # point d’entrée, lance le contrôleur
├── config.py # paramètres globaux
│
├── core/ # logique centrale et orchestration
│ ├── app_controller.py # orchestration modules
│ ├── event_bus.py # communication interne
│ └── state_manager.py # états du miroir (idle, listening, etc.)
│
├── ui/ # interface utilisateur
│ ├── mirror_window.py # fenêtre principale
│ └── assistant_overlay.py # avatar et texte IA
│
├── vision/ # caméra et analyse
│ ├── camera.py
│ ├── face_detector.py
│ └── visual_features.py
│
├── intelligence/ # moteur stylistique et contexte
│ ├── style_engine.py
│ ├── context_engine.py
│ └── recommendation_engine.py
│
├── audio/ # micro et synthèse vocale
│ ├── wake_word.py
│ ├── speech_to_text.py
│ └── tts.py
│
├── ai/ # interface LLM local
│ └── llm_interface.py
│
├── scripts/ # installation et lancement
└── assets/ # avatars, images, sons, icônes


### Points clés pour l’équipe

- **Event Bus** → tous les modules doivent communiquer via bus (pas d’appels directs).
- **State Manager** → gère les états : `IDLE`, `LISTENING`, `PROCESSING`, `SPEAKING`.
- **Modules indépendants** → chaque membre travaille sur sa branche (`feature/vision`, `feature/audio`, etc.).
- **Contrats clairs** → entrée / sortie de chaque module définie pour intégration future.

---

## 4️⃣ Résultat attendu à la fin du projet

1. Le miroir démarre automatiquement et reste en veille (`IDLE`) jusqu’au wake word.
2. Wake word détecté → caméra activée + analyse visage et tenue.
3. Recommandations stylisées calculées selon règles + contexte offline.
4. Assistant IA reformule les recommandations via LLM local.
5. Synthèse vocale locale prononce le message.
6. Tout fonctionne **fluidement** sur un mini PC Intel N100.
7. Le système reste **entièrement offline**, modulaire et extensible.