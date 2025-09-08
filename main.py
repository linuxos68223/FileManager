# Master - single-file Kivy Android app (main.py)
# Package: org.master.net
# Note: This is a large, practical starting implementation. Some advanced features
# (malware scanning, deep converters, reverse-image web search, AI assistant) are
# provided as placeholders or lightweight implementations because they require
# server-side services or platform-specific native libraries.

"""
Requirements (for Buildozer / python-for-android):
- kivy
- plyer
- pillow
- python-magic (optional, for file type)
- mutagen (optional, for audio metadata)
- ffmpeg (for advanced conversion; not packaged by default)

Buildozer spec highlights (add to buildozer.spec):

requirements = kivy,plyer,pillow,mutagen,python-magic
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,INTERNET
package.name = Master
package.domain = org.master.net
package.version = 0.1

Run:
- Install buildozer and dependencies on Linux (Ubuntu recommended)
- buildozer android debug

This single-file app demonstrates the main UI structure and implements many
features in a lightweight, cross-platform way. On Android some functionality
(e.g., sharing files via Intents) uses plyer and Android APIs.

"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.recycleview import RecycleView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.filechooser import FileChooserIconView
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.utils import platform
from kivy.lang import Builder

import os
import threading
import traceback
from functools import partial
from datetime import datetime

# Optional third-party libs
try:
    from plyer import filechooser, email, share
except Exception:
    filechooser = None
    share = None

try:
    from PIL import Image as PILImage
except Exception:
    PILImage = None

# ----------------------------- Utility functions ----------------------------

def human_size(num, suffix='B'):
    for unit in ['','K','M','G','T','P']:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Y{suffix}"


def list_files(root, exts=None):
    """Return list of files under root. exts is a set of lower-case extensions."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fname in filenames:
            try:
                if exts:
                    if os.path.splitext(fname)[1].lower() in exts:
                        out.append(os.path.join(dirpath, fname))
                else:
                    out.append(os.path.join(dirpath, fname))
            except Exception:
                continue
    return out


# ----------------------------- UI Widgets ----------------------------------

KV = '''
<MainUI>:
    orientation: 'vertical'
    BoxLayout:
        size_hint_y: None
        height: '52dp'
        padding: '6dp'
        spacing: '6dp'
        Button:
            text: 'Files'
            on_press: root.switch_tab('files')
        Button:
            text: 'Gallery'
            on_press: root.switch_tab('gallery')
        Button:
            text: 'Audio'
            on_press: root.switch_tab('audio')
        Button:
            text: 'Docs'
            on_press: root.switch_tab('docs')
        Button:
            text: 'Apps'
            on_press: root.switch_tab('apps')
    BoxLayout:
        id: content_area

'''

Builder.load_string(KV)


class FileListView(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grid = GridLayout(cols=1, size_hint_y=None, spacing=6, padding=6)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.add_widget(self.grid)

    def set_files(self, files):
        self.grid.clear_widgets()
        for f in files:
            b = Button(text=f"{os.path.basename(f)}\n{human_size(os.path.getsize(f))}", size_hint_y=None, height='64dp')
            b.bind(on_press=partial(self.open_file, f))
            self.grid.add_widget(b)

    def open_file(self, path, *args):
        popup = Popup(title=os.path.basename(path), size_hint=(.9, .9))
        box = BoxLayout(orientation='vertical')
        box.add_widget(Label(text=path))
        h = BoxLayout(size_hint_y=None, height='48dp')
        open_btn = Button(text='Open')
        share_btn = Button(text='Share')
        h.add_widget(open_btn)
        h.add_widget(share_btn)
        box.add_widget(h)
        popup.content = box
        open_btn.bind(on_press=lambda *a: self._open(path))
        share_btn.bind(on_press=lambda *a: self._share(path))
        popup.open()

    def _open(self, path):
        try:
            if platform == 'android':
                # Use Intent to open external file
                from jnius import autoclass, cast
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Uri = autoclass('android.net.Uri')
                Intent = autoclass('android.content.Intent')
                File = autoclass('java.io.File')
                java_file = File(path)
                uri = Uri.fromFile(java_file)
                intent = Intent()
                intent.setAction(Intent.ACTION_VIEW)
                # try to set mime
                intent.setDataAndType(uri, '*/*')
                currentActivity = PythonActivity.mActivity
                currentActivity.startActivity(intent)
            else:
                os.startfile(path)
        except Exception as e:
            print('open error', e)

    def _share(self, path):
        if share:
            try:
                share.share(path)
            except Exception as e:
                print('share error', e)
        else:
            print('share not available')


class GalleryView(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grid = GridLayout(cols=3, size_hint_y=None, spacing=6, padding=6)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.add_widget(self.grid)

    def set_images(self, images):
        self.grid.clear_widgets()
        for img_path in images:
            try:
                img = Image(source=img_path, size_hint=(1, None), height='120dp')
                self.grid.add_widget(img)
            except Exception:
                continue


class AudioView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.listview = FileListView()
        self.add_widget(self.listview)
        self.current_sound = None

    def set_audio_files(self, files):
        self.listview.set_files(files)


class AppsView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.grid = GridLayout(cols=1, size_hint_y=None)
        self.scroll = ScrollView()
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.scroll.add_widget(self.grid)
        self.add_widget(self.scroll)

    def set_apps(self, apps):
        self.grid.clear_widgets()
        for a in apps:
            b = Button(text=a, size_hint_y=None, height='48dp')
            self.grid.add_widget(b)


# ----------------------------- Main UI -------------------------------------

class MainUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.content_area = None

        self.tabs = {}
        self.current_tab = None
        # create default tab views
        self.file_view = FileListView()
        self.gallery_view = GalleryView()
        self.audio_view = AudioView()
        self.docs_view = FileListView()
        self.apps_view = AppsView()
        # start with files
        Clock.schedule_once(lambda dt: self.switch_tab('files'), 0.1)

    def switch_tab(self, name):
        # clear content_area and add view
        root = self.children[0] if self.children else None
        # because content_area defined in KV; fetch by id
        content = self.ids.get('content_area')
        if not content:
            # kv id not found; attempt to find by attribute
            # fallback: use self.add_widget
            pass
        # Remove previous
        content.clear_widgets()
        if name == 'files':
            content.add_widget(self.file_view)
            Clock.schedule_once(lambda dt: self.load_files(), 0.2)
        elif name == 'gallery':
            content.add_widget(self.gallery_view)
            Clock.schedule_once(lambda dt: self.load_gallery(), 0.2)
        elif name == 'audio':
            content.add_widget(self.audio_view)
            Clock.schedule_once(lambda dt: self.load_audio(), 0.2)
        elif name == 'docs':
            content.add_widget(self.docs_view)
            Clock.schedule_once(lambda dt: self.load_docs(), 0.2)
        elif name == 'apps':
            content.add_widget(self.apps_view)
            Clock.schedule_once(lambda dt: self.load_apps(), 0.2)
        self.current_tab = name

    # The loading functions perform filesystem scans - run in thread to avoid UI hang
    def load_files(self):
        def _scan():
            try:
                root = '/'
                if platform == 'android':
                    # typical storage path
                    root = '/storage/emulated/0'
                files = list_files(root)
                Clock.schedule_once(lambda dt: self.file_view.set_files(sorted(files, key=os.path.getmtime, reverse=True)[:500]))
            except Exception as e:
                print('load_files error', e)
        threading.Thread(target=_scan, daemon=True).start()

    def load_gallery(self):
        def _scan():
            try:
                root = '/'
                if platform == 'android':
                    root = '/storage/emulated/0'
                exts = {'.jpg','.jpeg','.png','.webp','.bmp','.gif','.mp4','.mkv','.mov'}
                files = list_files(root, exts=exts)
                images = [f for f in files if os.path.splitext(f)[1].lower() in {'.jpg','.jpeg','.png','.webp','.bmp','.gif'}]
                images = sorted(images, key=os.path.getmtime, reverse=True)[:500]
                Clock.schedule_once(lambda dt: self.gallery_view.set_images(images))
            except Exception as e:
                print('load_gallery error', e)
        threading.Thread(target=_scan, daemon=True).start()

    def load_audio(self):
        def _scan():
            try:
                root = '/'
                if platform == 'android':
                    root = '/storage/emulated/0'
                exts = {'.mp3','.wav','.m4a','.flac','.ogg'}
                files = list_files(root, exts=exts)
                Clock.schedule_once(lambda dt: self.audio_view.set_audio_files(sorted(files, key=os.path.getmtime, reverse=True)))
            except Exception as e:
                print('load_audio error', e)
        threading.Thread(target=_scan, daemon=True).start()

    def load_docs(self):
        def _scan():
            try:
                root = '/'
                if platform == 'android':
                    root = '/storage/emulated/0'
                exts = {'.pdf','.doc','.docx','.xls','.xlsx','.ppt','.pptx','.txt','.csv'}
                files = list_files(root, exts=exts)
                Clock.schedule_once(lambda dt: self.docs_view.set_files(sorted(files, key=os.path.getmtime, reverse=True)))
            except Exception as e:
                print('load_docs error', e)
        threading.Thread(target=_scan, daemon=True).start()

    def load_apps(self):
        def _scan():
            try:
                apps = []
                if platform == 'android':
                    # use jnius to list installed packages
                    try:
                        from jnius import autoclass
                        PythonActivity = autoclass('org.kivy.android.PythonActivity')
                        pm = PythonActivity.mActivity.getPackageManager()
                        packages = pm.getInstalledApplications(0)
                        for i in range(packages.size()):
                            app = packages.get(i)
                            apps.append(str(pm.getApplicationLabel(app)))
                    except Exception as e:
                        print('apps jnius error', e)
                else:
                    apps = ['ExampleApp1', 'ExampleApp2']
                Clock.schedule_once(lambda dt: self.apps_view.set_apps(sorted(apps)))
            except Exception as e:
                print('load_apps error', e)
        threading.Thread(target=_scan, daemon=True).start()


class MasterApp(App):
    def build(self):
        self.title = 'Master'
        root = MainUI()
        return root

    # Simple helper: show a quick popup message
    def toast(self, text):
        popup = Popup(title='Info', content=Label(text=text), size_hint=(.6,.2))
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 1.6)


# ----------------------------- Extra Placeholder Features ------------------

# File converter (very simple image -> webp/pdf and text->pdf using PIL where possible)

def convert_image_to_webp(src, dest):
    if PILImage is None:
        raise RuntimeError('Pillow not available')
    im = PILImage.open(src)
    im.save(dest, 'WEBP')
    return dest


def find_similar_images_by_hash(target, directory, max_results=10):
    """A very naive image-similarity using average hash (aHash)."""
    if PILImage is None:
        return []
    import hashlib
    def ahash(img, size=8):
        img = img.resize((size, size)).convert('L')
        pixels = list(img.getdata())
        avg = sum(pixels)/len(pixels)
        bits = ''.join('1' if p>avg else '0' for p in pixels)
        return int(bits, 2)
    try:
        timg = PILImage.open(target)
        t_hash = ahash(timg)
    except Exception:
        return []
    results = []
    for dirpath, dirnames, filenames in os.walk(directory):
        for fname in filenames:
            p = os.path.join(dirpath, fname)
            try:
                if os.path.splitext(p)[1].lower() in {'.jpg','.jpeg','.png','.webp'}:
                    h = ahash(PILImage.open(p))
                    # hamming distance
                    d = bin(t_hash ^ h).count('1')
                    results.append((d, p))
            except Exception:
                continue
    results.sort()
    return [p for d,p in results[:max_results]]


# Basic phone scan: look for suspicious filenames/extensions - NOT a real antivirus.

def quick_phone_scan(root=None):
    if root is None:
        root = '/storage/emulated/0' if platform == 'android' else '/'
    suspicious_exts = {'.exe', '.scr', '.bat', '.cmd', '.sh'}
    suspicious_names = ['wallet', 'trojan', 'keylogger', 'crack']
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fname in filenames:
            lfname = fname.lower()
            ext = os.path.splitext(lfname)[1]
            if ext in suspicious_exts or any(x in lfname for x in suspicious_names):
                findings.append(os.path.join(dirpath, fname))
            if len(findings) > 500:
                return findings
    return findings


# Lightweight AI assistant - local rule-based suggestions

def ai_suggest(action, context=None):
    if action == 'clean':
        return 'Consider removing files in Download/ or large unused videos. Use the "Files" tab to inspect large files sorted by date.'
    if action == 'backup':
        return 'Backup important documents to cloud or external SD. Use the Share function to send via email.'
    return 'Sorry, AI module is offline in this build. Consider integrating with an online API for richer responses.'


# ----------------------------- Entry Point --------------------------------

if __name__ == '__main__':
    try:
        MasterApp().run()
    except Exception:
        traceback.print_exc()

