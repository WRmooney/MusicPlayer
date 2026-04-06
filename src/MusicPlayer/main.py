# kivy version requirement
import kivy
from kivy.uix.recycleview.views import RecycleDataViewBehavior

kivy.require('2.3.1') # replace with your current kivy version !

#region
# IMPORTANT for audio
import sys
import os
os.environ["KIVY_AUDIO"] = "ffpyplayer"

# Kivy Imports (there's a lot, I know)
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, StringProperty, DictProperty, ListProperty, NumericProperty
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.uix.gridlayout import GridLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from kivy.uix.slider import Slider
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.audio import SoundLoader



# ffpyplayer
import ffpyplayer
from ffpyplayer.player import MediaPlayer

# other imports
import io
import math
import time
import threading
import PIL
from PIL import Image
import random
import json

# modules
import file_manager as fm
import playback_manager as pm

#endregion

# important global variables
try:
    with open('src/MusicPlayer/songs.json', 'r') as songs_j:
        songs = json.load(songs_j)
    with open('src/MusicPlayer/playlists.json', 'r') as playlists_j:
        playlists = json.load(playlists_j)
    with open('src/MusicPlayer/preferences.json', 'r') as preferences_json:
        preferences = json.load(preferences_json)
except:
    print("Error opening JSON files!")



# add these into preferences.JSON later
queue = []
queue_index = 0
current_song_info = {}
current_song = None

# Initialize Important Components
sm = ScreenManager()
PlaybackController = pm.PlaybackManager()



""" 
*** NOTES ***

Need to make that helper class to manage the playback on its own, buttons simply call the functions
of that class.

Playlist view!!!

Catch if there are NO SONGS!!!

Put pause/play, forward and backword functions into a Song Control Manager class!!!
Also put the below functions in there! 
The flow of song playback should continue regardless of what screen is being viewed!

Should have next and previous song loaded

Instead of MusicMenu updating on its own (including when on other screens),
how about PlaybackManager doing the updates, and also only if its on the MusicMenu screen?
"""









# player control flow functions

def song_finished(ref):
    global current_song
    global queue
    global queue_index
    global loop
    global songs


    if not loop:
        while True:
            if queue_index == len(queue)-1:
                queue_index = 0
            else:
                queue_index += 1
            if queue[queue_index] in songs["songs"]:
                break
    try:
        play_song(queue[queue_index], ref, current_song.get_pause())
    except AttributeError:
        play_song(queue[queue_index], ref, True)

def play_song(song_id, ref, playing):
    global current_song
    global directory
    global songs

    # song_finished, forward_btn, back_btn already catch missing files, this is for the first song in queue
    if queue[queue_index] not in songs["songs"]:
        song_finished(ref)
        return
    MediaPlayer.close_player(current_song)

    current_song = MediaPlayer(songs["songs"][song_id]["filepath"],
                ff_opts={"paused": playing},
                ss=0.0)
    update_info(queue[queue_index], ref)

def update_info(song_id, ref):
    global current_song_info
    current_song_info = fm.fetch_song_info(song_id)
    ref.ids.duration_slider.value = 0
    ref.ids.duration_label.text = time.strftime('%M:%S', time.gmtime(current_song_info['duration']))
    ref.ids.song_title.text = current_song_info['title']
    ref.ids.artist_name.text = current_song_info['artist']
    ref.ids.album_cover.texture = fm.get_album_cover(current_song_info["filepath"]).texture
    ref.ids.duration_slider.max = current_song_info['duration']
    ref.pause_by_slider = False
    ref.pause_by_button = False

# custom slider, important for functionality
class CustomSlider(Slider):
    def on_touch_down(self, touch):
        # Check if the touch collision is within the widget
        if self.collide_point(*touch.pos):
            #print("Slider clicked/touched!")
            # Consume the event
            App.get_running_app().root.slider_touched()
            return super(CustomSlider, self).on_touch_down(touch)
        # If not, ignore
        return False

# class to display song and info in songs/playlists view
class Song_Row(RecycleDataViewBehavior, BoxLayout):
    info = DictProperty({})
    id = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def refresh_view_attrs(self, rv, index, data):
        """
        This method is called every time the widget
        is recycled with new data.
        """
        return super(Song_Row, self).refresh_view_attrs(rv, index, data)

    def on_info(self, instance, value):
        self.ids.sr_title.text = value.get('title', 'Empty')
        self.ids.sr_artist.text = value.get('artist', 'Empty')
        self.ids.sr_duration.text = time.strftime('%M:%S', time.gmtime(value.get('duration', 0)))

# class to display song and info in songs/playlists view
class Playlist_Row(RecycleDataViewBehavior, BoxLayout):
    name = StringProperty('')
    song_list = ListProperty([])
    song_count = NumericProperty()
    total_length = NumericProperty()


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def refresh_view_attrs(self, rv, index, data):
        """
        This method is called every time the widget
        is recycled with new data.
        """
        return super(Playlist_Row, self).refresh_view_attrs(rv, index, data)

    def on_info(self, instance, value):
        print(f"UI update triggered for: {value.get('name')}")

        self.ids.pr_name.text = value.get('name', 'Empty')
        self.ids.pr_count.text = self.song_count
        self.ids.pr_duration.text = time.strftime('%M:%S', time.gmtime(self.total_length))

class PlaybackManager:
    pass

class MusicMenu(Screen):

    def __init__(self, **kwargs):
        super(MusicMenu, self).__init__(**kwargs)
        PlaybackController.funcs_to_call.append(self)

    def update(self, *args):
        # DISABLE BUTTONS IF VARIOUS CONDITIONS
        # 1. PQueue is empty, disable BackBtn
        # 2.

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
        #print("slider_touched")

    def slider_up(self):
        new_pos = self.ids.duration_slider.value
        if math.fabs(new_pos - current_song.get_pts()) > 0.1:
            current_song.seek(new_pos, relative=False)
        if self.pause_by_slider:
            current_song.set_pause(False)
            self.pause_by_slider = False
        #print("slider_up")

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
        while True:
            if queue_index == len(queue) - 1:
                queue_index = 0
            else:
                queue_index += 1
            if queue[queue_index] in songs["songs"]:
                break



        play_song(queue[queue_index], self, current_song.get_pause())

    def song_back(self):
        global current_song
        global queue
        global queue_index
        global loop

        while True:
            if queue_index == 0:
                queue_index = len(queue)-1
            else:
                queue_index -= 1
            if queue[queue_index] in songs["songs"]:
                break
        play_song(queue[queue_index], self, current_song.get_pause())

    def shuffle_queue(self):
        global queue
        random.shuffle(queue)

class MainMenu(Screen):
    def __init__(self, **kwargs):
        super(MainMenu, self).__init__(**kwargs)
        self.update_tab()

    def display_songs(self):
        global songs

        # sort by title in alphabetic order
        key_list = sorted(list(songs["songs"].keys()), key=lambda x: songs["songs"][x]["title"])

        # now we have a sorted list of each song as a dictionary, put it in the recycle view
        self.ids.main_song_list.data = [{'info': songs["songs"][key], 'id': key} for key in key_list]
        print([{'info': songs["songs"][key], 'id': key} for key in key_list])

    def display_playlists(self):
        global playlists

        # sort by playlist title in alphabetic order
        playlists_sorted = sorted(playlists["playlists"], key=lambda playlist: playlist["name"])


        self.ids.main_song_list.data = [{'name': playlists_sorted[i]["name"],
                                         'song_list': playlists_sorted[i]["songs"],
                                         'song_count': playlists_sorted[i]["song_count"],
                                         'total_length': playlists_sorted[i]["total_length"]}
                                        for i in range(len(playlists_sorted))]
        print([{'name': playlists_sorted[i]["name"],
                'song_list': playlists_sorted[i]["songs"],
                'song_count': playlists_sorted[i]["song_count"],
                'total_length': playlists_sorted[i]["total_length"]}
               for i in range(len(playlists_sorted))])

    def update_tab(self):
        if self.ids.main_song_list.viewclass == Song_Row:
            self.display_songs()
        elif self.ids.main_song_list.viewclass == Playlist_Row:
            self.display_playlists()
        else:
            print("Viewclass is NOT Song_Row or Playlist_Row!")
        self.ids.main_song_list.scroll_y = 1

    def songs_tab_btn(self):
        self.ids.main_song_list.viewclass = 'Song_Row'
        self.update_tab()

    def playlists_tab_btn(self):
        self.ids.main_song_list.viewclass = 'Playlist_Row'
        self.update_tab()

class MusicPlayerApp(App):
    def build(self):
        global queue
        global queue_index
        global songs
        global playlists
        global sm
        global PlaybackController

        Window.set_icon('resources/images/icon.png')

        fm.update_song_database('C:/Users/w_mooney/PycharmProjects/MusicPlayer/resources/test1')
        try:
            with open('src/MusicPlayer/songs.json', 'r') as songs_j:
                songs = json.load(songs_j)
            with open('src/MusicPlayer/playlists.json', 'r') as playlists_j:
                playlists = json.load(playlists_j)
        except:
            print("Uh oh! Something went wrong in build()!")

        # Initialize PlaybackController
        PlaybackController.previouslyPlayed = preferences['previous_queue']
        PlaybackController.currentSongId = preferences['current_song_id']
        PlaybackController.priorityQueue = preferences['priority_queue']
        PlaybackController.queue = preferences['queue']
        PlaybackController.fullScope = preferences['queue']
        PlaybackController.shuffle = preferences['shuffle']
        PlaybackController.loop = preferences['loop']

        # After initializing the queues, start playback controller
        PlaybackController.Start()

        # MAKE CURRENT SCREEN LOAD FIRST
        sm.add_widget(MusicMenu(name="MusicMenu"))
        sm.add_widget(MainMenu(name="MainMenu"))
        sm.current = 'MusicMenu'

        return sm

if __name__ == '__main__':
    MusicPlayerApp().run()