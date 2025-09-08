# app/thumbnailer.py
import os
from PIL import Image
from hashlib import md5

THUMB_DIR = os.path.join(os.path.abspath("."), ".thumbs")
os.makedirs(THUMB_DIR, exist_ok=True)

def _thumb_path_for(file_path):
    key = md5(file_path.encode("utf-8")).hexdigest()
    return os.path.join(THUMB_DIR, f"{key}.jpg")

def ensure_thumbnail(file_path, size=(300,300)):
    """
    যদি থাম্ব না থাকে তৈরি করবে, তারপর থাম্বের পাথ রিটার্ন করবে।
    """
    try:
        tpath = _thumb_path_for(file_path)
        if os.path.exists(tpath):
            return tpath
        im = Image.open(file_path)
        im.thumbnail(size)
        im.convert("RGB").save(tpath, "JPEG", quality=75)
        return tpath
    except Exception:
        # যদি thumbnail তৈরি না হয় তাহলে None রিটার্ন
        return ""
