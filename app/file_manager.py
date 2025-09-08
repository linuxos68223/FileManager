# app/file_manager.py
import os
from threading import Thread
from kivy.utils import platform

def _walk_storage(start_path, callback):
    files = []
    for root, dirs, filenames in os.walk(start_path):
        for f in filenames:
            files.append(os.path.join(root, f))
    callback(files)

def list_files_in_storage(callback):
    """
    ব্যাকগ্রাউন্ডে ফোনের প্রধান স্টোরেজ স্ক্যান করে callback(files) কল করবে।
    -- android হলে sdcard path ব্যবহার করে, অন্যথায় current dir।
    """
    from kivy.clock import mainthread

    def cb_wrapper(files):
        callback(files)

    def worker():
        # Android এ সাধারণত /sdcard বা /storage/emulated/0
        start_paths = []
        try:
            if platform == "android":
                # চেষ্টা করে সাবধানে দুইটি সম্ভাব্য রুট
                start_paths = ["/storage/emulated/0", "/sdcard"]
            else:
                start_paths = [os.path.expanduser("~")]
        except Exception:
            start_paths = [os.path.expanduser("~")]

        all_files = []
        for sp in start_paths:
            if os.path.exists(sp):
                for root, dirs, filenames in os.walk(sp):
                    for f in filenames:
                        full = os.path.join(root, f)
                        all_files.append(full)
        cb_wrapper(all_files)

    Thread(target=worker, daemon=True).start()
