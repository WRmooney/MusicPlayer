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
from kivy.clock import Clock, mainthread
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

# Initialize Important Components
sm = ScreenManager()
PlaybackController = None

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





# custom slider, important for functionality
class CustomSlider(Slider):
    def on_touch_down(self, touch):
        # Check if the touch collision is within the widget
        if self.collide_point(*touch.pos):
            #print("Slider clicked/touched!")
            # Consume the event
            sm.get_screen('MusicMenu').slider_touched()
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

class MusicMenu(Screen):

    def __init__(self, **kwargs):
        super(MusicMenu, self).__init__(**kwargs)
        self.pause_by_slider = False

        PlaybackController.funcs_to_call.append(self)
        self.update_info()

    def update(self, *args):
        # DISABLE BUTTONS ON VARIOUS CONDITIONS
        # Update Labels as well

        # back button
        if PlaybackController.prevSong is None or PlaybackController.curSong is None:
            if self.ids.reverse_btn.disabled != True:
                self.ids.reverse_btn.disabled = True
        else:
            if self.ids.reverse_btn.disabled != False:
                self.ids.reverse_btn.disabled = False

        # pause button
        if PlaybackController.curSong is None:
            if self.ids.play_btn.disabled != True:
                self.ids.play_btn.disabled = True
        else:
            if self.ids.play_btn.disabled != False:
                self.ids.play_btn.disabled = False
        if PlaybackController.get_pause() and self.ids.play_btn.text != 'Play' and not self.pause_by_slider:
            self.ids.play_btn.text = 'Play'
        elif not PlaybackController.get_pause() and self.ids.play_btn.text != 'Pause':
            self.ids.play_btn.text = 'Pause'

        # Shuffle Button
        if PlaybackController.shuffle and self.ids.shuffle_btn.text != 'Shuffle: On':
            self.ids.shuffle_btn.text = 'Shuffle: On'
        elif not PlaybackController.shuffle and self.ids.shuffle_btn.text != 'Shuffle: Off':
            self.ids.shuffle_btn.text = 'Shuffle: Off'

        # Loop Button
        if PlaybackController.loop and self.ids.loop_btn.text != 'Loop: On':
            self.ids.loop_btn.text = 'Loop: On'
        elif not PlaybackController.loop and self.ids.loop_btn.text != 'Loop: Off':
            self.ids.loop_btn.text = 'Loop: Off'

        # get song position and update slider
        # if song is paused, keep position the same`
        cur_pos = self.ids.duration_slider.value
        if not PlaybackController.get_pause(): # if song is paused, don't update the slider based on song position
            cur_pos = PlaybackController.get_time()
        self.ids.duration_slider.value = cur_pos
        self.ids.time_stamp_label.text = time.strftime('%M:%S', time.gmtime(cur_pos))

    def slider_touched(self):
        if not PlaybackController.get_pause():
            if not self.pause_by_slider:
                PlaybackController.set_pause(True)
                self.pause_by_slider = True

    @mainthread
    def update_info(self):
        # update info
        current_song_info = PlaybackController.get_info()
        self.ids.duration_slider.value = 0
        self.ids.duration_label.text = time.strftime('%M:%S', time.gmtime(current_song_info['duration']))
        self.ids.song_title.text = current_song_info['title']
        self.ids.artist_name.text = current_song_info['artist']
        self.ids.album_cover.texture = fm.get_album_cover(current_song_info["filepath"]).texture
        self.ids.duration_slider.max = current_song_info['duration']
        self.pause_by_slider = False



    def slider_up(self):
        new_pos = self.ids.duration_slider.value
        if math.fabs(new_pos - PlaybackController.get_time()) > 0.1:
            PlaybackController.seek(new_pos)
        if self.pause_by_slider:
            PlaybackController.set_pause(False)
            self.pause_by_slider = False

    def play_btn_press(self):
        PlaybackController.toggle_pause()


    def toggle_loop(self):
        PlaybackController.toggle_loop()
        PlaybackController.debug_print("toggle_loop")

    def forward_btn_press(self):
        PlaybackController.skip()
        PlaybackController.debug_print("forward_btn_press")

    def back_btn_press(self):
        PlaybackController.back()
        PlaybackController.debug_print("back_btn_press")

    def shuffle_queue(self):
        PlaybackController.toggle_shuffle()
        PlaybackController.debug_print("shuffle_queue")

    def back_screen_btn(self):
        sm.current = 'MainMenu'

class MainMenu(Screen):
    def __init__(self, **kwargs):
        super(MainMenu, self).__init__(**kwargs)
        PlaybackController.funcs_to_call.append(self)
        self.update_tab()
        self.update_info()

    def display_songs(self):
        global songs

        # sort by title in alphabetic order
        key_list = sorted(list(songs["songs"].keys()), key=lambda x: songs["songs"][x]["title"])

        # now we have a sorted list of each song as a dictionary, put it in the recycle view
        self.ids.main_song_list.data = [{'info': songs["songs"][key], 'id': key} for key in key_list]

    def display_playlists(self):
        global playlists

        # sort by playlist title in alphabetic order
        playlists_sorted = sorted(playlists["playlists"], key=lambda playlist: playlist["name"])


        self.ids.main_song_list.data = [{'name': playlists_sorted[i]["name"],
                                         'song_list': playlists_sorted[i]["songs"],
                                         'song_count': playlists_sorted[i]["song_count"],
                                         'total_length': playlists_sorted[i]["total_length"]}
                                        for i in range(len(playlists_sorted))]

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

    def open_music_menu(self):
        sm.current = 'MusicMenu'

    @mainthread
    def update_info(self):
        self.ids.cur_title_label.text = PlaybackController.get_info()["title"]
        self.ids.cur_artist_label.text = PlaybackController.get_info()["artist"]

    def update(self):
        if PlaybackController.curSong is not None:
            self.ids.cur_duration_label.text = (str(time.strftime('%M:%S', time.gmtime(PlaybackController.get_time()))) + " / "
                                                + str(time.strftime('%M:%S', time.gmtime(PlaybackController.get_info()["duration"]))))
        # back button
        if PlaybackController.prevSong is None or PlaybackController.curSong is None:
            if self.ids.main_back_btn.disabled != True:
                self.ids.main_back_btn.disabled = True
        else:
            if self.ids.main_back_btn.disabled != False:
                self.ids.main_back_btn.disabled = False

        # pause button
        if PlaybackController.curSong is None:
            if self.ids.main_play_btn.disabled != True:
                self.ids.main_play_btn.disabled = True
        else:
            if self.ids.main_play_btn.disabled != False:
                self.ids.main_play_btn.disabled = False
        if PlaybackController.get_pause() and self.ids.main_play_btn.text != 'Play':
            self.ids.main_play_btn.text = 'Play'
        elif not PlaybackController.get_pause() and self.ids.main_play_btn.text != 'Pause':
            self.ids.main_play_btn.text = 'Pause'

    def back_btn_press(self):
        PlaybackController.back()
        PlaybackController.debug_print("MainMenu back_btn_press")

    def play_btn_press(self):
        PlaybackController.toggle_pause()

    def skip_btn_press(self):
        PlaybackController.skip()
        PlaybackController.debug_print("MainMenu skip_btn_press")

class MusicPlayerApp(App):
    def build(self):
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
        PlaybackController = pm.PlaybackManager(
            preferences['previous_queue'],
            preferences['current_song_id'],
            preferences['priority_queue'],
            preferences['queue'],
            preferences['scope'],
            preferences['shuffle'],
            preferences['loop']
        )

        # After initializing the queues, start playback controller
        PlaybackController.start(songs["songs"])

        # MAKE CURRENT SCREEN LOAD FIRST
        sm.add_widget(MusicMenu(name="MusicMenu"))
        sm.add_widget(MainMenu(name="MainMenu"))
        sm.current = 'MusicMenu'

        return sm

if __name__ == '__main__':
    MusicPlayerApp().run()