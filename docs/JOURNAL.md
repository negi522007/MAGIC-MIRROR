# Journal du projet — TEKBOT Magic Mirror

Ce journal permet à quiconque (membre de l'équipe ou agent) de reprendre le travail :
ce qui a été fait, pourquoi, comment c'est mesuré, et ce qu'il reste à faire.
Le plus récent est en haut.

---

## 2026-11-10 (suite) — Test sous WSL2

- Constat sur le PC de dev : WSLg fournit PulseAudio (`/mnt/wslg/PulseServer`), le noyau WSL
  (`6.18.33.2-microsoft-standard-WSL2`) a `uvcvideo` et `usbip` en modules ; il manque
  `libportaudio2` / `libasound2-plugins` et le partage de la webcam par `usbipd-win`.
- Procédure écrite dans `docs/WSL.md`.
- Ajout de `camera.fourcc` (défaut `MJPG`) : par USB/IP, le flux brut YUYV sature souvent le lien.
  Sur une caméra qui ne gère pas MJPG, OpenCV ignore la demande.
- **Webcam par USB/IP : échec.** « VGA WebCam » (BUSID 1-7, usbipd-win 5.3.0) ne propose que
  YUYV 640x480 / 640x360 à 30 fps, sans MJPG. Images reçues à ~10,5 fps mais tronquées : 94 à 98 %
  de chaque image verte (données YUV nulles), quelle que soit la résolution demandée. `dmesg` :
  nombreux `vhci_hcd: unlink ... urb->status -104`. Avec `modprobe uvcvideo nodrop=0 quirks=128`
  (le pilote jette les trames incomplètes) : 0 image en 10 s. Conclusion : le transfert
  isochrone par USB/IP ne tient pas un flux YUYV brut ; rien à régler côté Linux.
- **Solution retenue** : la webcam reste à Windows, ffmpeg la diffuse en MJPEG
  (`-f mpjpeg -listen 1 http://0.0.0.0:8090`), le miroir lit l'URL. `camera.index` (et l'option
  `--camera`) accepte désormais une URL ; `WINDOWS_HOST` y est remplacé par la passerelle par
  défaut de WSL ; un flux coupé est rouvert automatiquement. Testé avec un serveur MJPEG local
  imitant ffmpeg : 60 images en 4 s (15 fps), visage détecté. Reste à valider avec le vrai ffmpeg
  Windows (pare-feu).
- **Lancement manuel de ffmpeg jugé peu pratique** (retour utilisateur) → nouvelle source
  caméra `windows` (`vision/windows_camera.py`) : le miroir lance `ffmpeg.exe` via
  l'interopérabilité WSL, capture DirectShow, sortie MJPEG sur stdout (`-f image2pipe`), découpage
  des JPEG (marqueurs FFD8/FFD9) en sautant aux images les plus récentes. `camera.index: auto`
  (défaut) : `/dev/video0` s'il existe, sinon cette source sous WSL. ffmpeg 9.0.2 installé sous
  Windows par `winget install Gyan.FFmpeg --scope user`.
- Résultats : 14 images/s, démarrage 8,5 s au premier lancement (antivirus) puis ~1 s. Les premiers
  essais donnaient des images **noires** (max ≈ 10/255, bruit) alors que les droits caméra Windows
  étaient « Allow » ; ni `usbipd unbind` ni les options dshow n'y changeaient rien, puis tout est
  rentré dans l'ordre après ouverture de l'appli Caméra de Windows (cause exacte non établie :
  éclairage, cache, ou webcam « réveillée » par l'appli). Ensuite : luminosité ~140/255, image nette.
- Visage non détecté sur l'image de test (personne allongée, visage à contre-jour, incliné, coupé en
  bas du cadre) : score YuNet 0,33 en pleine résolution, rien à 320 px, CLAHE sans effet. Seuils
  laissés tels quels (0,7) pour éviter les fausses détections ; à revoir si les essais face au
  miroir échouent.
- Dossier local renommé `~/Tekbot/MAGIC-MIRROR` (comme le dépôt) ; dépôt rendu public.

---

## 2026-11-10 — Refonte : corrections, performances, interface, modèles

### Point de départ (audit)

Version de mars 2026 : pipeline complet mais plusieurs défauts bloquants ou silencieux.

| # | Bug | Cause | Correction |
|---|---|---|---|
| 1 | Plantage au démarrage | `config.yaml` pointait vers `models/vosk-model-small-fr`, le dossier s'appelle `vosk-model-small-fr-0.22` | chemin corrigé + test `test_project_config_points_to_existing_vosk_model` |
| 2 | Le conseil couleur n'apparaissait jamais | la vision renvoyait `"#rrggbb"`, le moteur de style attendait `"blue"`… | `name_color()` (HSV → 13 noms) ; test `test_color_rule_fires_with_named_color` |
| 3 | L'analyse mesurait surtout le mur | k-means et contraste sur toute l'image | zone du buste sous le visage (`VisualFeatures.outfit_region`) ; test `test_analysis_uses_outfit_not_background` |
| 4 | Phrase lue moitié en anglais (« Tenue dark, contraste low, dominante #3a5f8c, contexte autumn ») | résumé construit avec les clés internes | libellés français accordés (« à dominante bleue ») |
| 5 | Caméra lue par deux threads (Tk + analyse) | `cv2.VideoCapture.read()` appelé partout | un thread de capture, `get_frame()` renvoie la dernière image |
| 6 | Conflit micro (« device busy ») / pauses fragiles | WakeWord et STT ouvraient chacun un flux sur le même micro | `audio/microphone.py` : un flux unique donné à un consommateur à la fois |
| 7 | Modèle Vosk chargé deux fois (RAM, démarrage) | une instance par module | chargé une fois dans le contrôleur, partagé |
| 8 | `FaceDetector.detect_face` renvoyait `False` si appelé < 0,3 s après le précédent | limitation de cadence mélangée au résultat | cadence gérée par `PresenceMonitor`, le détecteur renvoie toujours la vérité |
| 9 | Date affichée en anglais (« Tuesday 10 November ») | `strftime("%A")` dépend de la locale | `core/french.py` |
| 10 | `state_changed` émis tantôt en texte, tantôt en dict ; double émission | contrôleur et StateManager émettaient tous deux | seul `StateManager` émet, toujours le nom de l'état |
| 11 | Un 2ᵉ « miroir magique » pendant une réponse relançait un cycle | pas de garde | `StateManager.try_begin("idle", "listening")` |
| 12 | Saisons « spring » / « autumn » et « afternoon » / « night » sans aucune règle | règles incomplètes | règles pour toutes les saisons / moments + climat tropical |
| 13 | `requirements.txt` = `pip freeze` de 170 paquets dont CUDA / torch (~5 Go) | gel d'un environnement de dev | 7 dépendances directes ; LLM dans `requirements-llm.txt` |
| 14 | `simpleaudio` (non maintenu, ne compile plus en Python ≥ 3.12) | lecture des WAV | lecture via `sounddevice` (déjà requis) |
| 15 | Tests qui ouvrent caméra / micro au chargement, imports cassés (`from tts import TTS`) | scripts manuels nommés `test_*.py` | déplacés dans `tests/legacy/` ; vrais tests pytest + `scripts/check_*.py` |

### Modèles : ce qui était dépassé

Vérifié le 2026-11-10 (listes officielles Vosk, Hugging Face, PyPI) :

- **Vosk `small-fr-0.22`** : toujours le modèle FR léger non obsolète de la liste officielle
  (`alphacephei.com/vosk/models/model-list.json`). **Gardé.** Le gros modèle `fr-0.22` (1,4 Go) est
  trop lourd pour le N100 en temps réel.
- **Coqui TTS 0.22 → Piper** : Coqui (l'entreprise) a fermé fin 2023, le paquet `TTS` n'est plus
  maintenu ; il tire PyTorch (+ CUDA dans l'ancien requirements). Piper (`piper-tts`, maintenu par
  OHF-Voice) est fait pour les petits CPU (ONNX). Voix `fr_FR-siwis-medium` (63 Mo). Coqui et
  pyttsx3 restent des replis configurables (`tts.backends`).
- **Haar Cascade → YuNet** : Haar (Viola-Jones, 2001) rate les visages inclinés ou mal éclairés.
  YuNet (`face_detection_yunet_2023mar.onnx`, 230 Ko) est intégré à OpenCV ≥ 4.8
  (`cv2.FaceDetectorYN`). Repli automatique sur Haar si le fichier manque.
- **LLM** : le cahier des charges demandait un « petit modèle quantisé 1B–3B » mais il n'y en avait
  aucun (détection par mots-clés uniquement). Choix : **Qwen3.5-2B Q4_K_M** (unsloth, 1,28 Go),
  bon en français, via `llama-cpp-python` (0.3.36, oct. 2026). Écartés : Gemma 4 E2B (3,1 Go en
  Q4_K_M, trop lourd), Qwen3.5-0.8B (possible si la RAM manque : changer `models.llm`).
  Le mode « thinking » de Qwen est désactivé par un bloc `<think></think>` vide dans le prompt
  ChatML (`ai/local_llm.py`), sinon le modèle « réfléchit » de longues secondes avant de répondre.

### Performances (cible Intel N100, 4 cœurs)

- Capture : un thread à 15 fps, `CAP_PROP_BUFFERSIZE=1` (pas de retard d'images).
- Affichage : recadrage avant redimensionnement, `cv2.resize` INTER_LINEAR au lieu de PIL LANCZOS,
  `PhotoImage.paste` au lieu d'une nouvelle image par trame, redessin seulement si nouvelle image,
  20 fps au lieu de 30.
- Veille : sans visage pendant `ui.sleep_after` s, l'image n'est plus dessinée et la détection passe
  à 1 /s.
- Détection : image réduite à 320 px de large ; analyse de tenue sur 48×48 px.
- Audio : blocs de 0,25 s au lieu de 0,5 s (réactivité), grammaire Vosk pour le mot clé, résultat
  partiel pour réagir sans attendre le silence, phrases fréquentes de la voix en cache, synthèse de
  la phrase suivante pendant la lecture de la précédente.
- LLM : chargement en arrière-plan, limité à 90 tokens et 12 s ; au-delà ou s'il est absent, le
  gabarit à base de règles répond.

### Mesures (PC de développement sous WSL2, 8 threads, Python 3.11 ; le N100 sera ~2 à 3× plus lent)

| Mesure | Avant | Après | Comment reproduire |
|---|---|---|---|
| Rendu d'une image caméra en 1920×1080 | 71,3 ms (PIL LANCZOS + nouvelle PhotoImage) — plafonne à ~14 fps, image 4:3 étirée | **10,5 ms** (recadrage + `cv2.resize` + `paste`) | micro-benchmark dans le journal de session ; en 1280×720 dans l'appli : 11–15 ms |
| Détection de visage 640×480 | Haar (non mesuré) | **6–8 ms** YuNet sur image réduite à 320 px | `scripts/check_camera.py` affiche le temps |
| Analyse de la tenue | k-means k=1 sur 307 200 px | **~2 ms** (k=3 sur 48×48) | — |
| Synthèse vocale | Coqui VITS (PyTorch) | **Piper : 0,59 s pour 7,4 s d'audio** (×12 temps réel), chargement 1,8 s, « Oui, je vous écoute. » en cache : 0 ms | `scripts/check_tts.py` |
| Mot clé + question | non testable sans micro | **testé de bout en bout** : Piper prononce « Miroir magique. » puis « Comment est ma tenue ? », injectés dans Vosk → mot clé détecté, question transcrite ; une phrase quelconque ne réveille pas le miroir | `pytest tests/test_audio_pipeline.py` |
| Dépendances Python | ~170 paquets dont torch + CUDA | 7 directes (+ llama-cpp-python en option) | `requirements*.txt` |

#### LLM local (Qwen3.5-2B Q4_K_M, llama-cpp-python 0.3.36)

- Le GGUF déclare l'architecture `qwen35` et un gabarit ChatML dont la sortie par défaut est
  `<|im_start|>assistant\n<think>\n\n</think>\n\n` (mode « thinking » coupé) : c'est exactement le
  prompt écrit par `ai/local_llm.py`. Vérifié en lisant `tokenizer.chat_template` dans le fichier.
- **Piège de compilation** : un premier build avec `CMAKE_ARGS="-DGGML_NATIVE=OFF"` (sans AVX2)
  donnait 5–9 s par réponse. Recompilé en natif (défaut de `pip install llama-cpp-python`) :
  chargement 1,0–1,5 s, **3,4–4,9 s par réponse** (~20–25 mots, 3 ou 6 threads : peu de différence).
  Compilation : 14 min / 37 min CPU sur ce PC → prévoir bien plus sur le N100.
- **Qualité** : correcte pour des conseils simples (« Des chaussures noires ou marron clair
  harmonisent parfaitement avec un pantalon beige. ») mais aléatoire (première série : blague
  absurde, « le beige est le choix parfait pour un pantalon beige »). En reformulant l'analyse de
  style, il produisait une phrase agréable mais **perdait les conseils concrets** (blanc, gris,
  marine) et ajoutait ~9 s.
- **Décision** : les conseils de style restent produits par les règles (instantané, précis) ;
  le LLM sert aux questions libres. Reformulation par le LLM disponible via
  `llm.rephrase_style: true`. À réévaluer avec un modèle plus grand si la machine le permet
  (Qwen3.5-4B, 2,7 Go) ou plus petit si la RAM manque (Qwen3.5-0.8B).

Vérification visuelle de l'interface : lancement réel de l'appli Tk avec une photo à la place de la
webcam (WSLg ne permet pas la capture d'écran X ; le contenu du Canvas a été redessiné avec PIL).
Sur la photo de test de Messi (maillot du Barça) : visage trouvé, fiche « Rouge & bleu », luminosité
équilibrée, contraste modéré. Sur le portrait « Lena » (visage en gros plan), l'analyse répond
correctement que le buste n'est pas visible.

Constat OpenCV 5.0 (installé par défaut par pip en nov. 2026) : `cv2.CascadeClassifier` (Haar) a été
retiré. YuNet est donc nécessaire ; le repli Haar ne fonctionne qu'avec OpenCV 4.x. Sans YuNet ni
Haar, le détecteur annonce « none » et l'analyse de tenue répond qu'elle ne voit personne.

### Interface

Canvas unique : image caméra plein écran recadrée sans déformation ; avatar animé (respiration /
ondes / arc qui tourne / pulsation selon l'état) et libellé d'état en haut à gauche ; horloge, date
en français et salutation en haut à droite ; sous-titres (question en gris italique, réponse avec
effet de frappe puis fondu) ; fiche « Analyse de la tenue » à droite ; coins autour du visage pendant
l'écoute / l'analyse ; ligne d'état discrète (hors ligne, IA, moteur de voix). Raccourcis clavier
pour la démo sans micro (`--no-audio`).

### Où sont les données locales (non versionnées)

- `models/` (ignoré par `.gitignore`) — régénérer avec `./scripts/install.sh [--with-llm]` :
  `vosk-model-small-fr-0.22/`, `face_detection_yunet_2023mar.onnx`,
  `piper/fr_FR-siwis-medium.onnx(.json)`, `llm/Qwen3.5-2B-Q4_K_M.gguf`.
- `.venv/` — environnement Python créé par `install.sh`.

### Risques et questions ouvertes

- Le matériel réel (N100, webcam, micro) n'a pas été testé dans cette session (développé sous WSL
  sans caméra ni micro) : vérifier `scripts/check_*.py` sur la machine cible.
- Seuils de couleur / luminosité / contraste réglés sur images synthétiques : à ajuster avec de
  vraies photos sous l'éclairage du lieu de démonstration.
- Le climat par défaut est `temperate` ; mettre `context.climate: tropical` si le miroir est
  présenté au Bénin.
- `stipple` (transparence de la fiche) n'est pas pris en charge sous Windows (fond opaque).

### Reste à faire

- (fait) Dépôt git créé : `github.com/negi522007/MAGIC-MIRROR` (privé). Les anciens tests de la
  première version sont conservés dans `tests/legacy/` pour l'historique.

- Mesurer fps / CPU / latence mot clé → réponse sur le N100.
- Mode conversation : réécouter quelques secondes après une réponse sans redire le mot clé.
- Lancement automatique au démarrage (service systemd).
