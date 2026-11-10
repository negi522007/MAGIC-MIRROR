# 🪞 TEKBOT Magic Mirror

Miroir intelligent **100 % offline** : assistant vocal en français, analyse de la tenue
et conseils de style, interface plein écran pensée pour un mini PC **Intel N100**.

> Projet TEKBOT – EPITECH 2026. Cahier des charges d'origine : [`INITIAL_README.md`](INITIAL_README.md).
> Journal de développement (décisions, mesures, bugs corrigés) : [`docs/JOURNAL.md`](docs/JOURNAL.md).

---

## ✨ Fonctionnalités

| | |
|---|---|
| 🎤 **Mot clé** | « miroir magique » — Vosk restreint à la phrase clé (grammaire) : fiable et léger |
| 🗣️ **Reconnaissance vocale** | Vosk FR small 0.22, transcription affichée en direct |
| 🔊 **Synthèse vocale** | **Piper** (voix `fr_FR-siwis-medium`), temps réel sur CPU ; repli Coqui / pyttsx3 |
| 👤 **Détection de visage** | **YuNet** (OpenCV, ONNX) ; repli Haar Cascade (OpenCV 4 uniquement) |
| 👕 **Analyse de la tenue** | zone du buste sous le visage : couleur dominante + secondaire nommées, luminosité, contraste, éclairage |
| 💡 **Conseils de style** | règles couleur / contraste / saison / heure (climat tempéré ou tropical) |
| 🤖 **IA locale (optionnelle)** | **Qwen3.5-2B** quantisé (llama.cpp) pour les questions libres (~4 s par réponse sur PC récent) ; les conseils de style restent produits par les règles |
| 🖥️ **Interface** | avatar animé selon l'état, horloge et date en français, sous-titres, fiche d'analyse, mise en veille sans visage |

---

## 🚀 Installation

Prérequis : Linux (Ubuntu / Debian / Raspberry Pi OS…), Python ≥ 3.10, webcam, micro, haut-parleur.

```bash
git clone git@github.com:negi522007/MAGIC-MIRROR.git && cd MAGIC-MIRROR
./scripts/install.sh              # dépendances + modèles (Vosk, YuNet, voix Piper) ≈ 110 Mo
./scripts/install.sh --with-llm   # + IA locale (llama-cpp-python + Qwen3.5-2B ≈ 1,3 Go)
```

> `--with-llm` compile llama.cpp pour le processeur de la machine (gcc + cmake) : comptez 15 min
> sur un PC récent, nettement plus sur le N100. Ne pas forcer `GGML_NATIVE=OFF` : sans AVX2, le
> LLM est deux fois plus lent.

Le script crée `.venv/`, installe `requirements.txt` et télécharge les modèles dans `models/`
(non versionné). Sans `--with-llm`, le miroir fonctionne entièrement avec ses réponses à base de règles.

<details>
<summary>Installation manuelle</summary>

```bash
sudo apt install python3-venv python3-tk libportaudio2
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# puis télécharger les modèles listés en tête de scripts/install.sh dans models/
```
</details>

---

> 💻 **Sous WSL2 (Windows)** : son via WSLg et webcam Windows diffusée par ffmpeg (`--camera http://WINDOWS_HOST:8090`), voir [`docs/WSL.md`](docs/WSL.md).

---

## ▶️ Lancement

```bash
./scripts/run.sh                    # plein écran
./scripts/run.sh --windowed         # fenêtre 1280x720 (développement)
./scripts/run.sh --no-audio         # sans micro ni voix (démo au clavier)
./scripts/run.sh --no-llm           # sans IA locale
```

### Utilisation

1. Le miroir est en veille : l'avatar « respire », l'état indique *Dites « miroir magique »*.
2. Dites **« miroir magique »** → *« Oui, je vous écoute. »* (l'avatar émet des ondes bleues).
3. Posez votre question : *« comment est ma tenue ? »*, *« quelle heure est-il ? »*,
   *« quel jour sommes-nous ? »*, *« bonjour »*, *« que sais-tu faire ? »*…
4. La réponse est affichée en sous-titre et lue à voix haute ; pour une analyse de tenue,
   une fiche (pastille de couleur, luminosité, contraste, saison) s'affiche à droite.
5. Sans personne devant le miroir pendant 60 s, l'image caméra est masquée (veille).

### Raccourcis clavier

| Touche | Action |
|---|---|
| `Espace` | simule le mot clé |
| `S` / `H` / `D` / `B` / `A` | tenue / heure / date / bonjour / aide |
| `F11` | plein écran on/off |
| `Échap` | quitter |

---

## ⚙️ Configuration

`config.yaml` ne contient que ce qui diffère des valeurs par défaut de [`config.py`](config.py)
(toutes les options y sont commentées). Les plus utiles :

```yaml
audio:
  device_id: null        # ID du micro : python scripts/find_micro.py
context:
  climate: "temperate"   # "tropical" : harmattan / saison sèche / saison des pluies
llm:
  n_threads: 3           # cœurs donnés au LLM (le N100 en a 4)
ui:
  sleep_after: 60        # s sans visage avant la veille (0 = jamais)
```

---

## 🧪 Tests

```bash
.venv/bin/python -m pytest              # tests unitaires (sans matériel)
.venv/bin/python scripts/check_tts.py   # voix + vitesse de synthèse
.venv/bin/python scripts/check_micro.py # micro + reconnaissance
.venv/bin/python scripts/check_camera.py  # caméra + visage + zone analysée (opencv-python avec GUI)
```

---

## 🧱 Architecture

```
main.py, config.py, config.yaml
core/          app_controller (orchestration), event_bus (pub/sub), state_manager,
               colors (vocabulaire des couleurs), french (dates en français)
audio/         microphone (flux unique partagé), wake_word, speech_to_text, tts, audio_state
vision/        camera (thread de capture), face_detector, presence_monitor, visual_features
intelligence/  context_engine, style_engine, recommendation_engine
ai/            llm_interface (intentions + réponses), local_llm (llama.cpp)
ui/            mirror_window, avatar, assistant_overlay, style_card, theme
scripts/       install.sh, run.sh, find_micro.py, list_audio_devices.py, check_*.py
tests/         tests pytest (tests/legacy : anciens scripts, non exécutés)
```

Cycle d'une interaction (machine à états `idle → listening → processing → speaking → idle`) :

```
WakeWord ──wake_word_detected──► AppController : « Oui, je vous écoute. », STT.listen()
STT ──stt_partial / speech_transcribed──► LLMInterface.process (intention)
   ├─ heure, date, salutations… ──────────────────────────────► llm_response
   └─ tenue : style_request ─► PresenceMonitor + VisualFeatures + RecommendationEngine
                ─► recommendation_ready ─► LLMInterface (LLM local ou gabarit) ─► llm_response
llm_response ─► AssistantOverlay (sous-titre) + TTS ─► idle, WakeWord reprend
```

Un seul flux micro est ouvert ; il est donné soit au mot clé, soit à la transcription, et coupé
pendant que le miroir parle (anti-larsen). Un seul thread lit la caméra ; l'interface et l'analyse
lisent la dernière image. Diagramme par module : [`DIAGRAM.md`](DIAGRAM.md).

---

## 📦 Modèles

| Rôle | Modèle | Taille | Remplace |
|---|---|---|---|
| Mot clé + transcription | Vosk `vosk-model-small-fr-0.22` | 41 Mo | (inchangé, toujours le modèle FR léger à jour) |
| Synthèse vocale | Piper `fr_FR-siwis-medium` | 63 Mo | Coqui `TTS` 0.22 (projet arrêté, PyTorch ~2 Go) |
| Visage | YuNet `face_detection_yunet_2023mar` | 0,2 Mo | Haar Cascade (2001) |
| IA locale | Qwen3.5-2B `Q4_K_M` (GGUF) | 1,3 Go | règles fixes uniquement |

---

## 👥 Auteurs

Exaucé AGBODJALOU (intelligence, IA) · Marcellin (vision) · Conrad (audio)

## 📄 Licence

Projet académique — TEKBOT-EPITECH 2026
