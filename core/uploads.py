"""Validation et nettoyage des fichiers envoyés par les citoyens."""
import io
import uuid

from django.core.files.base import ContentFile
from PIL import Image, ImageOps
from rest_framework import serializers

Image.MAX_IMAGE_PIXELS = 25_000_000       # refuse les "bombes de décompression"
MAX_SIDE = 1280


def clean_photo(f):
    """Vérifie que c'est vraiment une image, SUPPRIME les métadonnées EXIF (GPS, modèle
    du téléphone, heure…), redimensionne et ré-encode en JPEG léger sous un nom aléatoire."""
    try:
        img = Image.open(f)
        img.verify()
        f.seek(0)
        img = Image.open(f)
        if img.format not in ("JPEG", "PNG", "WEBP"):
            raise ValueError("format")
        img = ImageOps.exif_transpose(img)      # applique l'orientation avant de tout effacer
        img = img.convert("RGB")                 # recrée une image neuve : plus aucune métadonnée
        img.thumbnail((MAX_SIDE, MAX_SIDE))
        out = io.BytesIO()
        img.save(out, "JPEG", quality=70, optimize=True)   # pas de paramètre exif= : rien n'est copié
    except Exception:
        raise serializers.ValidationError("Image invalide (JPEG, PNG ou WEBP uniquement).")
    return ContentFile(out.getvalue(), name=f"{uuid.uuid4().hex}.jpg")


_AUDIO = {   # extension -> test sur les premiers octets (le nom envoyé par le client ne prouve rien)
    ".m4a": lambda h: h[4:8] == b"ftyp",
    ".aac": lambda h: h[:2] in (b"\xff\xf1", b"\xff\xf9"),
    ".mp3": lambda h: h[:3] == b"ID3" or h[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"),
    ".ogg": lambda h: h[:4] == b"OggS",
    ".wav": lambda h: h[:4] == b"RIFF" and h[8:12] == b"WAVE",
    ".webm": lambda h: h[:4] == b"\x1a\x45\xdf\xa3",
}


def clean_audio(f):
    name = (f.name or "").lower()
    ext = next((e for e in _AUDIO if name.endswith(e)), None)
    head = f.read(16)
    f.seek(0)
    if not ext or not _AUDIO[ext](head):
        raise serializers.ValidationError("Audio invalide (m4a, aac, mp3, ogg, wav ou webm).")
    return ContentFile(f.read(), name=f"{uuid.uuid4().hex}{ext}")
