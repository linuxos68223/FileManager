# main.py
from kivy.lang import Builder
from kivy.clock import mainthread
from kivy.core.window import Window
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ListProperty, StringProperty
from kivy.factory import Factory
import os
from app.file_manager import list_files_in_storage
from app.thumbnailer import ensure_thumbnail

KV = open("ui.kv", "r", encoding="utf-8").read()

class FileItem(BoxLayout):
    path = StringProperty()
    name = StringProperty()
    thumb = StringProperty()

class MasterRoot(BoxLayout):
    files = ListProperty([])

    def on_kv_post(self, base_widget):
        # স্টার্টআপে স্টোরেজ লিস্টিং রিকোয়েস্ট
        self.ids.status.text = "Scanning storage..."
        list_files_in_storage(callback=self._on_files_ready)

    @mainthread
    def _on_files_ready(self, paths):
        # শুধু ইমেজ ফাইলগুলোর নমুনা নেবো (গ্যালারি হিসাবে দেখাব)
        image_ext = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')
        images = [p for p in paths if p.lower().endswith(image_ext)]
        self.ids.status.text = f"Found {len(images)} images"
        items = []
        for p in images[:200]:  # safety limit প্রথম 200
            thumb = ensure_thumbnail(p)
            items.append({"path": p, "name": os.path.basename(p), "thumb": thumb})
        self.files = items

class MasterApp(App):
    def build(self):
        self.title = "Master - Prototype"
        return Builder.load_string(KV)

if __name__ == "__main__":
    MasterApp().run()
