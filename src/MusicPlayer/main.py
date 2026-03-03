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

def song_finished():
    print("song finished")
    


filepath = 'resources/Test_Resources/READY TO FLY.mp3'
song1 = MediaPlayer(filepath,
                    callback=song_finished(),
                    ff_opts={"paused": True})
current_song = song1
current_info = get_mp3_info(filepath)

class MusicMenu(BoxLayout):

    def __init__(self, **kwargs):
        super(MusicMenu, self).__init__(**kwargs)
        Clock.schedule_interval(self.update, 0.5)
        self.ids.duration_label.text = time.strftime('%M:%S', time.gmtime(current_info['duration']))
        self.ids.song_title.text = current_info['title']
        self.ids.artist_name.text = current_info['artist']
        self.ids.album_cover.texture = get_album_cover(filepath).texture
        self.ids.duration_slider.max = current_info['duration']
        self.pause_by_slider = False
        self.pause_by_button = False

    def update(self, *args):
        # check if the song is finished
        if (current_info['duration'] - current_song.get_pts()) < 0.1:
            song_finished()

        # get song position and update slider
        # if song is paused, keep position the same`
        cur_pos = self.ids.duration_slider.value
        if not current_song.get_pause(): # if song is paused, don't update the slider based on song position
            cur_pos = current_song.get_pts()
        self.ids.duration_slider.value = cur_pos
        self.ids.time_stamp_label.text = time.strftime('%M:%S', time.gmtime(cur_pos))





    def slider_touched(self):
        if not current_song.get_pause():
            if not self.pause_by_slider:
                current_song.set_pause(True)
                self.pause_by_slider = True
        print("slider_touched")

    def slider_up(self):
        new_pos = self.ids.duration_slider.value
        current_song.seek(new_pos, relative=False)
        if self.pause_by_slider:
            current_song.set_pause(False)
            self.pause_by_slider = False
        print("slider_up")



    def play_btn_press(self):
        if current_song.get_pause():
            current_song.set_pause(False)
            self.ids.play_btn.text = 'Pause'
            self.pause_by_button = False
        else:
            current_song.set_pause(True)
            self.ids.play_btn.text = 'Play'
            self.pause_by_button = True

    def toggle_loop(self):
        if current_song.ff_opts != 0:
            current_song.loop = 0
            self.ids.loop_btn.text = 'Loop: On'
        else:
            current_song.loop = 1
            self.ids.loop_btn.text = 'Loop: Off'





class MusicPlayerApp(App):
    def build(self):
        Window.set_icon('resources/images/icon.png')

        return MusicMenu()


if __name__ == '__main__':
    MusicPlayerApp().run()