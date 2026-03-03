import kivy
kivy.require('2.3.1') # replace with your current kivy version !

# IMPORTANT for audio
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


# Mutagen Imports (for getting file info like title etc.)
import mutagen
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

# ffpyplayer
import ffpyplayer
from ffpyplayer.player import MediaPlayer

filepath = 'resources/Test_Resources/Modal Soul.mp3'
song1 = MediaPlayer('resources/Test_Resources/Modal Soul.mp3',
                    ff_opts={"paused": True})
current_song = song1


# mp3 metadata function
def get_mp3_info(filepath):
    # Use mutagen to get info
    try:
        audio = MP3(filepath)
        info = {
            "title": audio.get('title', ['Unknown Title'])[0],
            "artist": audio.get('artist', ['Unknown Artist'])[0],
            "album": audio.get('album', ['Unknown Album'])[0],
            "duration": audio.info.length
        }
        return info
    except Exception as e:
        print("Error")
        return None

current_info = get_mp3_info(filepath)

class MusicMenu(BoxLayout):

    def __init__(self, **kwargs):
        super(MusicMenu, self).__init__(**kwargs)
        Clock.schedule_interval(self.update, 1)
        self.ids.duration_label.text = str(current_info['duration'])



    def update(self, *args):
        # get song position and update slider
        cur_pos = current_song.get_pts()
        self.ids.duration_slider.value = cur_pos/current_info['duration']*100
        print(song1.get_pts())


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