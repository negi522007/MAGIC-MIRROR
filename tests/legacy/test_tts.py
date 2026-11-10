"""Test TTS en isolation pour voir l'erreur exacte"""

try:
    print("Import TTS...")
    from TTS.api import TTS

    print("Chargement du modèle tts_models/fr/mai/tacotron2-DDC...")
    tts = TTS(model_name="tts_models/fr/mai/tacotron2-DDC")

    print("Génération audio...")
    tts.tts_to_file(text="Bonjour, je suis votre miroir magique.", file_path="/tmp/test_tts.wav")

    print("✅ Fichier généré : /tmp/test_tts.wav")

except Exception as e:
    print(f"❌ Erreur : {type(e).__name__}: {e}")

    import traceback
    traceback.print_exc()