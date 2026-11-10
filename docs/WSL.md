# Tester le miroir sous WSL2 (Windows 11)

WSL2 n'a pas accès directement à la webcam et au micro. Le son passe par le serveur
PulseAudio de WSLg ; la webcam est diffusée par Windows sur le réseau local (ffmpeg),
ou « prêtée » à WSL avec `usbipd-win` (moins fiable).

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

## 2. Webcam — méthode recommandée : flux réseau depuis Windows

La webcam reste branchée à Windows ; ffmpeg (Windows) la diffuse en MJPEG et le miroir
(WSL) lit ce flux. Fonctionne avec toutes les webcams.

Dans PowerShell (normal, pas besoin d'administrateur) :

```powershell
winget install Gyan.FFmpeg                                   # une seule fois, puis rouvrir PowerShell
ffmpeg -list_devices true -f dshow -i dummy                  # nom exact de la webcam, ex. "VGA WebCam"
ffmpeg -f dshow -video_size 640x480 -i video="VGA WebCam" -vf fps=15 -c:v mjpeg -q:v 5 -f mpjpeg -listen 1 http://0.0.0.0:8090
```

Au premier lancement, autoriser ffmpeg dans la fenêtre du pare-feu Windows (réseaux privés).
Laisser cette fenêtre ouverte, puis dans WSL :

```bash
./scripts/run.sh --windowed --camera http://WINDOWS_HOST:8090
```

`WINDOWS_HOST` est remplacé automatiquement par l'adresse de Windows vue depuis WSL (passerelle
par défaut, ex. `172.29.128.1`). `-listen 1` ne sert qu'un client à la fois et s'arrête quand le
miroir se ferme : relancer la commande ffmpeg avant chaque essai. Si le flux est coupé pendant
que le miroir tourne, il se reconnecte tout seul.

## 3. Webcam — autre méthode : USB/IP (`usbipd-win`)

⚠ **Échec constaté le 2026-11-10** avec une « VGA WebCam » qui ne propose que du YUYV brut
(pas de MJPG) : par USB/IP, chaque image arrive tronquée (97 % de l'image verte), et avec
`uvcvideo nodrop=0` aucune image complète n'arrive en 10 s (`vhci_hcd: urb->status -104` dans
`dmesg`). Cette méthode n'a de chances qu'avec une webcam qui propose le MJPG.

PowerShell **administrateur** :

```powershell
winget install --interactive --exact dorssel.usbipd-win
usbipd list                          # repérer la webcam, ex. BUSID 1-7
usbipd bind --busid 1-7              # une seule fois
usbipd attach --wsl --busid 1-7      # après chaque redémarrage ; `usbipd detach --busid 1-7` pour la rendre à Windows
```

WSL :

```bash
sudo apt install v4l-utils
sudo modprobe -r uvcvideo && sudo modprobe uvcvideo nodrop=0 quirks=128
sudo usermod -aG video $USER        # puis `wsl --shutdown` depuis Windows
v4l2-ctl --list-formats-ext -d /dev/video0   # MJPG doit apparaître
./scripts/run.sh --windowed
```

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| « PortAudio library not found » | `libportaudio2` absent | étape 1 |
| Aucun son, pas d'erreur | ALSA ne passe pas par Pulse | `libasound2-plugins`, puis `echo $PULSE_SERVER` (doit valoir `unix:/mnt/wslg/PulseServer`) |
| « Caméra http://… introuvable » | ffmpeg pas lancé, ou bloqué par le pare-feu | relancer la commande ffmpeg ; autoriser ffmpeg dans le pare-feu Windows |
| « Caméra 0 introuvable » | (USB/IP) webcam non attachée ou module absent | `usbipd attach …` puis `sudo modprobe uvcvideo` |
| `/dev/video0` existe mais permission refusée | utilisateur hors du groupe `video` | `usermod -aG video`, puis `wsl --shutdown` |
| Image en grande partie verte / aucune image | (USB/IP) trames YUYV tronquées | utiliser la méthode ffmpeg (section 2) |
| Webcam intégrée du portable absente de `usbipd list` | certaines caméras intégrées ne sont pas USB | utiliser une webcam USB |
