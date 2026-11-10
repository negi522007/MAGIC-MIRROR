"""
LLM local optionnel (llama.cpp via `llama-cpp-python`, modèle GGUF quantisé).

Modèle par défaut : Qwen3.5-2B en Q4_K_M (~1,3 Go de RAM), bon en français et assez
rapide sur 3 cœurs d'un Intel N100. Le chargement se fait en arrière-plan au
démarrage ; tant qu'il n'est pas prêt (ou s'il est absent), l'assistant utilise ses
réponses à base de règles.

Pour les modèles Qwen, le prompt est écrit à la main au format ChatML avec un bloc
de réflexion vide : cela désactive le mode « thinking » et la réponse commence tout
de suite. La génération est interrompue au-delà de `timeout` secondes.
"""

import os
import re
import threading
import time

THINK_BLOCK = re.compile(r"<think>.*?</think>", re.S)
MARKDOWN = re.compile(r"[*_#`>]+")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


class LocalLLM:
    def __init__(self, model_path, n_threads=3, n_ctx=1024, max_tokens=90,
                 temperature=0.6, timeout=12):
        self.model_path = model_path
        self.n_threads = n_threads
        self.n_ctx = n_ctx
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.chatml = "qwen" in os.path.basename(model_path or "").lower()
        self._llm = None
        self._lock = threading.Lock()
        self.status = "absent"

    @property
    def ready(self):
        return self._llm is not None

    def load_async(self):
        if not self.model_path or not os.path.exists(self.model_path):
            print(f"[LLM] Modèle absent ({self.model_path}) — réponses à base de règles. "
                  "Voir `scripts/install.sh --with-llm`.")
            return
        self.status = "loading"
        threading.Thread(target=self._load, name="llm-load", daemon=True).start()

    def _load(self):
        try:
            from llama_cpp import Llama
            start = time.monotonic()
            self._llm = Llama(model_path=self.model_path, n_ctx=self.n_ctx,
                              n_threads=self.n_threads, n_batch=256, verbose=False)
            self.status = "ready"
            print(f"[LLM] ✅ {os.path.basename(self.model_path)} chargé en "
                  f"{time.monotonic() - start:.1f} s")
        except ImportError:
            self.status = "absent"
            print("[LLM] llama-cpp-python non installé — réponses à base de règles.")
        except Exception as e:
            self.status = "error"
            print(f"[LLM] ⚠ Chargement impossible : {e}")

    def generate(self, system, user):
        """Réponse nettoyée (prête à être lue), ou None si indisponible / échec."""
        if not self.ready:
            return None
        with self._lock:
            try:
                return self._clean(self._generate(system, user))
            except Exception as e:
                print(f"[LLM] ⚠ Erreur de génération : {e}")
                return None

    def _generate(self, system, user):
        start = time.monotonic()
        if self.chatml:
            prompt = (f"<|im_start|>system\n{system}<|im_end|>\n"
                      f"<|im_start|>user\n{user}<|im_end|>\n"
                      "<|im_start|>assistant\n<think>\n\n</think>\n\n")
            stream = self._llm.create_completion(
                prompt, max_tokens=self.max_tokens, temperature=self.temperature,
                top_p=0.9, stop=["<|im_end|>", "<|im_start|>"], stream=True)
            pieces = (chunk["choices"][0]["text"] for chunk in stream)
        else:
            stream = self._llm.create_chat_completion(
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                max_tokens=self.max_tokens, temperature=self.temperature, stream=True)
            pieces = (chunk["choices"][0]["delta"].get("content", "") for chunk in stream)

        out = []
        for piece in pieces:
            out.append(piece)
            if time.monotonic() - start > self.timeout:
                print("[LLM] Délai dépassé, réponse tronquée")
                break
        text = "".join(out)
        print(f"[LLM] {len(text)} caractères en {time.monotonic() - start:.1f} s")
        return text

    @staticmethod
    def _clean(text):
        text = THINK_BLOCK.sub("", text or "")
        text = text.split("<think>")[0]
        text = EMOJI.sub("", MARKDOWN.sub("", text))
        text = " ".join(text.split())
        # On ne garde que des phrases complètes (la génération peut être coupée).
        if text and text[-1] not in ".!?…":
            cut = max(text.rfind(c) for c in ".!?…")
            text = text[:cut + 1] if cut > 20 else text
        return text or None
