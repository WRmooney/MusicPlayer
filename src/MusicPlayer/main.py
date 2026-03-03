import kivy
kivy.require('2.3.1') # replace with your current kivy version !

# IMPORTANT for audio
import sys
import os
os.environ["KIVY_AUDIO"] = "ffpyplayer"

# Kivy Imports (there's a lot, I know)
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty
from kivy.vector import Vector
from kivy.clock import Clock
from random import randint
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage


# Mutagen Imports (for getting file info like title etc.)
import mutagen
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
from mutagen import File
from mutagen.id3 import ID3

# ffpyplayer
import ffpyplayer
from ffpyplayer.player import MediaPlayer

# other imports
import io
import math
import time
import PIL
from PIL import Image

filepath = 'resources/Test_Resources/Chase.mp3'
song1 = MediaPlayer(filepath,
                    ff_opts={"paused": True})
current_song = song1


# mp3 metadata function
def get_mp3_info(filepath):
    # Use mutagen to get info
    try:
        audio = MP3(filepath)
        metadata = mutagen.mp3.Open(filepath)
        info = {
            "title": str(metadata.get("TIT2")),
            "artist": str(metadata.get("TPE1")),
            "duration": audio.info.length
        }
        return info
    except Exception as e:
        print("Error")
        return None

def get_album_cover(filepath):
    try:
        audio = MP3(filepath, ID3=ID3)
        if not audio:
            print("Can't open audio file!")
            return default_image()
        album_art = audio.tags.getall("APIC")[0].data

        if album_art:
            image = Image.open(io.BytesIO(album_art))
            data = io.BytesIO()
            image.save(data, format='png')
            data.seek(0)
            kivy_core_image = CoreImage(io.BytesIO(data.read()), ext='png')
            return kivy_core_image
        else:
            print("No album art found!")
            return default_image()
    except IndexError:
        print("No album art found! (No APIC tag)")
        return default_image()
    except Exception as e:
        print("Error")
        return default_image()

def default_image():
    image = Image.open('./resources/images/icon.png')
    data = io.BytesIO()
    image.save(data, format='png')
    data.seek(0)
    kivy_core_image = CoreImage(io.BytesIO(data.read()), ext='png')
    return kivy_core_image

current_info = get_mp3_info(filepath)

class MusicMenu(BoxLayout):

    def __init__(self, **kwargs):
        super(MusicMenu, self).__init__(**kwargs)
        Clock.schedule_interval(self.update, 1)
        self.ids.duration_label.text = time.strftime('%M:%S', time.gmtime(current_info['duration']))
        self.ids.song_title.text = current_info['title']
        self.ids.artist_name.text = current_info['artist']
        self.ids.album_cover.texture = get_album_cover(filepath).texture




    def update(self, *args):
        # get song position and update slider
        cur_pos = current_song.get_pts()
        self.ids.duration_slider.value = cur_pos/current_info['duration']*100
        self.ids.time_stamp_label.text = time.strftime('%M:%S', time.gmtime(cur_pos))



    def play_btn_press(self):
        if current_song.get_pause():
            current_song.set_pause(False)
            self.ids.play_btn.text = 'Pause'
        else:
            current_song.set_pause(True)
            self.ids.play_btn.text = 'Play'







class MusicPlayerApp(App):
    def build(self):
        Window.set_icon('resources/images/icon.png')

        return MusicMenu()


if __name__ == '__main__':
    MusicPlayerApp().run()