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
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from kivy.uix.slider import Slider


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
import random

# important global variables
current_song = None
directory = ''
loop = False
queue = []
queue_index = 0
current_song_info = {}



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

def song_finished(ref):
    global current_song
    global queue
    global queue_index
    global loop

    if loop: # close and open player with the same song
        MediaPlayer.close_player(current_song)
        current_song = MediaPlayer(filepath,
                    ff_opts={"paused": False})
    else:
        if queue_index == len(queue)-1:
            queue_index = 0
        else:
            queue_index += 1
    play_song(queue[queue_index], ref, current_song.get_pause())

def play_song(songname, ref, playing):
    global current_song
    global directory
    MediaPlayer.close_player(current_song)
    filepath = directory + songname
    current_song = MediaPlayer(filepath,
                ff_opts={"paused": playing})
    update_info(directory, queue[queue_index], ref)

def update_info(dir, name, ref):
    global current_song_info
    current_song_info = get_mp3_info(dir + name)
    current_song_info['filepath'] = dir + name
    ref.ids.duration_label.text = time.strftime('%M:%S', time.gmtime(current_song_info['duration']))
    ref.ids.song_title.text = current_song_info['title']
    ref.ids.artist_name.text = current_song_info['artist']
    ref.ids.album_cover.texture = get_album_cover(dir + name).texture
    ref.ids.duration_slider.max = current_song_info['duration']
    ref.pause_by_slider = False
    ref.pause_by_button = False

loop = False
directory = 'resources/Test_Resources/'
songname = 'READY TO FLY.mp3'
filepath = directory + songname
current_song = MediaPlayer(filepath,
                           ff_opts={"paused": False})
queue_index = 0

class CustomSlider(Slider):
    def on_touch_down(self, touch):
        # Check if the touch collision is within the widget
        if self.collide_point(*touch.pos):
            print("Slider clicked/touched!")
            # Consume the event
            App.get_running_app().root.slider_touched()
            return super(CustomSlider, self).on_touch_down(touch)
        # If not, ignore
        return False

class MusicMenu(BoxLayout):

    def __init__(self, **kwargs):
        super(MusicMenu, self).__init__(**kwargs)
        Clock.schedule_interval(self.update, 0.1)
        play_song(queue[0], self, True)

    def update(self, *args):
        global current_song_info
        # check if the song is finished
        if (current_song_info['duration'] - current_song.get_pts()) < 0.1:
            song_finished(self)

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
        if math.fabs(new_pos - current_song.get_pts()) > 0.1:
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
        global loop
        if loop:
            loop = False
            self.ids.loop_btn.text = 'Loop: Off'
        else:
            loop = True
            self.ids.loop_btn.text = 'Loop: On'

    def forward_btn_press(self):
        global queue
        global queue_index
        if queue_index == len(queue) - 1:
            queue_index = 0
        else:
            queue_index += 1

        play_song(queue[queue_index], self, current_song.get_pause())

    def song_back(self):
        global current_song
        global queue
        global queue_index
        global loop

        if queue_index == 0:
            queue_index = len(queue)-1
        else:
            queue_index -= 1
        play_song(queue[queue_index], self, current_song.get_pause())

    def shuffle_queue(self):
        global queue
        random.shuffle(queue)

class MusicPlayerApp(App):
    def build(self):
        global queue
        global queue_index
        Window.set_icon('resources/images/icon.png')
        queue = ['pt1.mp3','pt2.mp3','pt3.mp3','pt4.mp3','pt5.mp3','pt6.mp3']
        queue_index = 0
        return MusicMenu()


if __name__ == '__main__':
    MusicPlayerApp().run()