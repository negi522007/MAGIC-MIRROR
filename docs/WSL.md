# Tester le miroir sous WSL2 (Windows 11)

WSL2 n'a pas accès directement à la webcam et au micro. Le son passe par le serveur
PulseAudio de WSLg ; la webcam USB doit être « prêtée » à WSL avec `usbipd-win`.

Vérifié sur : Ubuntu 26.04 sous WSL2, noyau `6.18.33.2-microsoft-standard-WSL2`
(modules `uvcvideo` et `usbip` présents), WSLg actif (`/mnt/wslg/PulseServer`).

## 1. Son (micro + haut-parleurs) — côté WSL

```bash
sudo apt install libportaudio2 libasound2-plugins pulseaudio-utils
```

- `libportaudio2` : requis par `sounddevice` (sinon « PortAudio library not found »).
- `libasound2-plugins` : fait passer ALSA par PulseAudio, donc par WSLg vers Windows.

Vérification :

```bash
pactl info | grep "Server Name"                     # doit répondre (WSLg)
.venv/bin/python scripts/list_audio_devices.py       # doit lister « pulse » / « default »
.venv/bin/python scripts/check_tts.py                # la voix sort sur les haut-parleurs Windows
.venv/bin/python scripts/check_micro.py              # parlez : le texte s'affiche
```

Laisser `audio.device_id: null` dans `config.yaml` (périphérique par défaut = PulseAudio).
Si le micro reste muet : Windows → Paramètres → Confidentialité → Microphone → autoriser
les applications de bureau.

## 2. Webcam — côté Windows (PowerShell **administrateur**)

```powershell
winget install --interactive --exact dorssel.usbipd-win   # une seule fois
usbipd list                                              # repérer la webcam, ex. BUSID 2-3
usbipd bind --busid 2-3                                  # une seule fois par webcam
usbipd attach --wsl --busid 2-3                          # à refaire après chaque redémarrage
```

Tant qu'elle est attachée à WSL, la webcam n'est plus utilisable par Windows
(`usbipd detach --busid 2-3` pour la rendre).

## 3. Webcam — côté WSL

```bash
sudo apt install v4l-utils
sudo modprobe uvcvideo
sudo usermod -aG video $USER        # puis fermer et rouvrir WSL : wsl --shutdown depuis Windows
ls /dev/video*                      # doit afficher /dev/video0 (et souvent /dev/video1)
v4l2-ctl --list-formats-ext -d /dev/video0   # vérifier que MJPG est proposé
```

Le miroir demande le format MJPG (`camera.fourcc` dans `config.yaml`) : par USB/IP, le
format brut YUYV sature souvent le lien et donne une image figée ou noire.

## 4. Lancer

```bash
./scripts/run.sh --windowed
```

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| « PortAudio library not found » | `libportaudio2` absent | étape 1 |
| Aucun son, pas d'erreur | ALSA ne passe pas par Pulse | `libasound2-plugins`, puis `echo $PULSE_SERVER` (doit valoir `unix:/mnt/wslg/PulseServer`) |
| « Caméra 0 introuvable » | webcam non attachée ou module absent | `usbipd attach …` puis `sudo modprobe uvcvideo` |
| `/dev/video0` existe mais permission refusée | utilisateur hors du groupe `video` | `usermod -aG video`, puis `wsl --shutdown` |
| Image figée / noire | format YUYV trop lourd pour USB/IP | `camera.fourcc: "MJPG"` (défaut), ou `camera.width: 320` / `height: 240` |
| Webcam intégrée du portable absente de `usbipd list` | certaines caméras intégrées ne sont pas USB | utiliser une webcam USB |
