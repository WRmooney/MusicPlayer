# kivy version requirement
import kivy
from urllib3.poolmanager import pool_classes_by_scheme

kivy.require('2.3.1') # replace with your current kivy version !

#region
# IMPORTANT for audio
import sys
import os
os.environ["KIVY_AUDIO"] = "ffpyplayer"

# Kivy Imports (there's a lot, I know)
from kivy.app import App
from kivy.properties import ReferenceListProperty, ObjectProperty, StringProperty, DictProperty, ListProperty, NumericProperty
from kivy.clock import Clock, mainthread
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.uix.slider import Slider
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition, FallOutTransition, RiseInTransition
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.dropdown import DropDown
from kivy.uix.label import Label




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
from functools import partial

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
**TODO**
select multiple songs to add to playlist
add queue view in musicmenu and mainmenu
add current scope name for queue view (ex. Playing from: My Playlist 1)
revamp visuals
"""

""" Custom Kivy Classes """
#region
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
    index = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dropdown = SongDropDown(self)
        self.pvdropdown = SongDropDownPlaylistView(self)
        self.playlist_select = PlaylistSelectDropdown(self)

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

    def play_btn(self):
        # set scope, set current song, set queue, empty pqueue, empty prevplayed
        if sm.current == 'MainMenu':
            PlaybackController.play_from_songs(self.id, songs["songs"])
        elif sm.current == 'PlaylistView':
            sm.get_screen('PlaylistView').play_from_playlist(self.index)

    def options_btn(self):
        if sm.current == 'PlaylistView':
            self.pvdropdown.open(self.ids.dropdown_btn)
        else:
            self.dropdown.open(self.ids.dropdown_btn)

    def add_to_queue(self):
        PlaybackController.add_to_queue(self.id)

    def add_to_playlist(self):
        popup_content = AddToPlaylistForm(self, None)
        popup = Popup(title='Add to Playlist(s)', content=popup_content,
                      size_hint=(None,None),
                      size=(Window.width * 0.7, Window.height * 0.7))
        popup_content.popup_ref = popup
        popup_content.ids.playlist_list.data = [{'name': playlist["name"], 'ref':popup_content} for playlist in playlists["playlists"]]

        popup.open()


    def remove_from_playlist(self, btn):
            for playlist in playlists["playlists"]:
                if playlist["name"] == sm.get_screen('PlaylistView').cur_playlist.name:
                    playlist["songs"].pop(self.index)
                    playlist["song_count"], playlist["total_length"] = fm.get_playlist_length(songs, playlist)
                    break
            sm.get_screen('PlaylistView').cur_playlist.song_list.pop(self.index-1)
            sm.get_screen('PlaylistView').update_songs()

            self.dropdown.dismiss()

class PlaylistSelectDropdown(DropDown):
    def __init__(self, song_ref, **kwargs):
        super().__init__(**kwargs)
        self.song_ref = song_ref
        self.width = 400
        for playlist in playlists["playlists"]:
            btn = ClickableLabel(
                text=playlist["name"],
                size_hint_y=None,
                height="100",
                on_release=self.add_song,
                text_size= self.size,
                shorten= True,
                shorten_from= 'right',
                halign='center',
                valign='center'
            )
            self.add_widget(btn)

    def add_song(self, btn):
        for playlist in playlists["playlists"]:
            if playlist["name"] == btn.text:
                playlist["songs"].append(self.song_ref.id)
                playlist["song_count"], playlist["total_length"] = fm.get_playlist_length(songs, playlist)
                self.dismiss()
                return

    def check_playlists(self):
        children = self.container.children
        playlist_names = [playlist["name"] for playlist in playlists["playlists"] if playlist["name"] not in list(child.text for child in children)]
        for name in playlist_names:
            btn = ClickableLabel(
                text=name,
                size_hint_y=None,
                height="100",
                on_release=self.add_song,
                text_size=self.size,
                shorten=True,
                shorten_from='right',
                halign='center',
                valign='center'
            )
            self.add_widget(btn)


    def open(self, widget, **kwargs):
        super().open(widget)
        self.check_playlists()
        self.x = widget.x - self.width
        self.y = self.y + widget.height
        self.halign = 'center'

class PlaylistSelectButton(Button):
    def __init__(self, name, song_ref, dropdown_ref, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.song_ref = song_ref
        self.dropdown_ref = dropdown_ref

    def add_song(self):
        for playlist in playlists["playlists"]:
            if playlist["name"] == self.name:
                playlist["songs"].append(self.song_ref.id)
                self.dropdown_ref.dismiss()
                return

class SongDropDown(DropDown):
    def __init__(self, song_ref, **kwargs):
        super().__init__(**kwargs)
        self.song_ref = song_ref
        self.width = 400

    def add_to_queue(self):
        self.song_ref.add_to_queue()
        self.dismiss()

    def add_to_playlist(self):
        self.song_ref.add_to_playlist()
        self.dismiss()

    def remove_from_playlist(self):
        self.song_ref.remove_from_playlist()
        self.dismiss()

    def open(self, widget, **kwargs):
        super().open(widget)
        self.x = widget.x - self.width

        self.y = self.y + widget.height
        self.halign = 'center'

class SongDropDownPlaylistView(DropDown):
    def __init__(self, song_ref, **kwargs):
        super().__init__(**kwargs)
        self.song_ref = song_ref
        self.width = 400

    def add_to_queue(self):
        self.song_ref.add_to_queue()
        self.dismiss()

    def add_to_playlist(self):
        self.song_ref.add_to_playlist()
        self.dismiss()

    def remove_from_playlist(self):
        self.song_ref.remove_from_playlist()
        self.dismiss()

    def open(self, widget, **kwargs):
        super().open(widget)
        self.x = widget.x - self.width
        self.y = self.y + widget.height
        self.halign = 'center'

class AddToPlaylistRecycleButton(RecycleDataViewBehavior, ToggleButton):
    name = StringProperty('')
    ref = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_press(self):
        self.ref.check_update(self)



# class to display song and info in songs/playlists view
class Playlist_Row(RecycleDataViewBehavior, BoxLayout):
    name = StringProperty('')
    song_list = ListProperty([])
    song_count = NumericProperty()
    total_length = NumericProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dropdown = PlaylistDropDown(self)

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

    def play_btn(self):
        # call play from songs using current playlist list
        if self.song_list != []:
            PlaybackController.play_from_playlist(self.song_list)
            print("Playing Playlist: " + str(self.name))
        else:
            popup_content = Button(text='OK', size_hint=(0.6, 0.9))
            popup = Popup(title="Playlist is Empty", content=popup_content, auto_dismiss=False,
                          size_hint=(0.3, 0.2))
            popup_content.bind(on_press=popup.dismiss)
            popup.open()

    def view_playlist(self):
        sm.transition = RiseInTransition()
        sm.current = 'PlaylistView'
        sm.get_screen('PlaylistView').update_view(self)
        sm.get_screen('MusicMenu').prev_screen = 'PlaylistView'

    def open_dropdown(self):
        self.dropdown.open(self.ids.dropdown_btn)

# custom dropdown for playlists
class PlaylistDropDown(DropDown):
    def __init__(self, playlist_ref, **kwargs):
        super().__init__(**kwargs)
        self.playlist_ref = playlist_ref
        self.mainmenu_ref = sm.get_screen('MainMenu')
        self.width = 400

    def delete_playlist(self):
        self.mainmenu_ref.delete_playlist(self.playlist_ref.name)
        self.dismiss()

    def open(self, widget, **kwargs):
        super().open(widget)
        self.x = widget.x - self.width
        self.y = self.y + widget.height
        self.halign = 'center'

# Clickable layout for playlist_row
class Clickable_Layout(ButtonBehavior, BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class ClickableLabel(ButtonBehavior, Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

# Custom class for creating a playlist from the popup
class Create_Playlist_Form(BoxLayout):
    def __init__(self, ref_to_mainmenu, popup_ref, **kwargs):
        super().__init__(**kwargs)
        self.ref_to_mainmenu = ref_to_mainmenu
        self.popup_ref = popup_ref

    def create_btn_pressed(self):
        # check for empty field
        if self.ids.playlist_name_input.text == '':
            popup_content = Button(text='OK', size_hint=(0.6, 0.9))
            popup = Popup(title="Playlist Name Cannot Be Empty" ,content=popup_content, auto_dismiss=False,
                          size_hint=(0.3,0.2))
            popup_content.bind(on_press=popup.dismiss)
            popup.open()
            return
        # check for pre-existing playlist name
        elif self.ids.playlist_name_input.text in (playlist['name'] for playlist in playlists["playlists"]):
            popup_content = Button(text='OK', size_hint=(0.6, 0.9))
            popup = Popup(title="Playlist Name Already Exists", content=popup_content, auto_dismiss=False,
                          size_hint=(0.3,0.2))
            popup_content.bind(on_press=popup.dismiss)
            popup.open()
            return
        # playlist name is valid
        else:
            self.ref_to_mainmenu.create_playlist(self.ids.playlist_name_input.text)
            self.popup_ref.dismiss()

class AddToPlaylistForm(BoxLayout):
    def __init__(self, ref_to_song, popup_ref, **kwargs):
        super().__init__(**kwargs)
        self.ref_to_song = ref_to_song # can change to "selected_songs" and make a list, iterate through list when adding to playlist
        self.popup_ref = popup_ref


    def check_update(self, btn):
        selected = self.get_selected()
        if len(selected) > 0:
            self.ids.submit_btn.disabled = False
        else:
            self.ids.submit_btn.disabled = True

    def get_selected(self):
        buttons = self.ids.recyclebox.children
        return [button.text for button in buttons if button.state == 'down']

    def submit_to_playlists(self):
        selected = self.get_selected()
        if len(selected) > 0:
            for playlist in playlists["playlists"]:
                if playlist["name"] in selected:
                    playlist["songs"].append(self.ref_to_song.id)
                    playlist["song_count"], playlist["total_length"] = fm.get_playlist_length(songs, playlist)
            self.popup_ref.dismiss()
            return

#endregion

""" Main Screens """
#region
class MusicMenu(Screen):

    def __init__(self, **kwargs):
        super(MusicMenu, self).__init__(**kwargs)
        self.pause_by_slider = False

        PlaybackController.funcs_to_call.append(self)
        self.update_info()
        self.prev_screen = 'MainMenu'

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
        sm.transition = SlideTransition()
        sm.transition.direction = 'down'
        sm.current = self.prev_screen

class PlaylistView(Screen):
    def __init__(self, **kwargs):
        super(PlaylistView, self).__init__(**kwargs)
        PlaybackController.funcs_to_call.append(self)
        self.update_info()
        self.cur_playlist = None

    def display_songs(self):
        if self.cur_playlist is None:
            return
        song_list = self.cur_playlist.song_list
        self.ids.cur_playlist_name.text = self.cur_playlist.name
        self.ids.cur_playlist_song_count.text = str(self.cur_playlist.song_count) + " songs"

        self.ids.cur_playlist_length.text = PlaybackController.get_length_text(self.cur_playlist.total_length)

        # put songs in recycle view
        self.ids.song_list.data = [{'info': songs["songs"][song_list[i]], 'id': song_list[i], 'index': i} for i in range(len(song_list))]

    def open_music_menu(self):
        sm.transition = SlideTransition()
        sm.transition.direction = 'up'
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

    def update_songs(self):
        for playlist in playlists["playlists"]:
            if playlist["name"] == self.cur_playlist.name:
                self.cur_playlist.song_list = playlist["songs"]
                self.cur_playlist.song_count = playlist["song_count"]
                self.cur_playlist.total_length = playlist["total_length"]
                break
        self.update_view(self.cur_playlist)

    def back_btn_press(self):
        PlaybackController.back()
        PlaybackController.debug_print("PlaylistView back_btn_press")

    def play_btn_press(self):
        PlaybackController.toggle_pause()

    def skip_btn_press(self):
        PlaybackController.skip()
        PlaybackController.debug_print("PlaylistView skip_btn_press")

    def update_view(self, playlistref):
        self.cur_playlist = playlistref
        self.display_songs()

    def play_from_playlist(self, index):
        PlaybackController.play_song_in_playlist(self.cur_playlist.song_list, index)

    def back_screen_btn(self):
        sm.transition = FallOutTransition()
        sm.current = 'MainMenu'
        sm.get_screen('MusicMenu').prev_screen = 'MainMenu'

class MainMenu(Screen):
    def __init__(self, **kwargs):
        super(MainMenu, self).__init__(**kwargs)
        PlaybackController.funcs_to_call.append(self)
        self.update_tab()
        self.update_info()

    def display_songs(self):
        global songs

        # sort depending on current sort filter
        if self.ids.mainmenuspinner.text == 'Sort by: Title':
            key_list = sorted(list(songs["songs"].keys()), key=lambda x: songs["songs"][x]["title"])
        elif self.ids.mainmenuspinner.text == 'Sort by: Artist':
            key_list = sorted(list(songs["songs"].keys()), key=lambda x: songs["songs"][x]["artist"])
        elif self.ids.mainmenuspinner.text == 'Sort by: Duration, Ascending':
            key_list = sorted(list(songs["songs"].keys()), key=lambda x: songs["songs"][x]["duration"])
        elif self.ids.mainmenuspinner.text == 'Sort by: Duration, Descending':
            key_list = list(reversed(sorted(list(songs["songs"].keys()), key=lambda x: songs["songs"][x]["duration"])))
        else: # order by ID as a fallback
            print("FALLBACK")
            key_list = list(songs["songs"].keys())

        # now we have a sorted list of each song as a dictionary, put it in the recycle view
        self.ids.main_song_list.data = [{'info': songs["songs"][key], 'id': key} for key in key_list]

        # remove add playlist button
        self.ids.add_playlist_btn.opacity = 0
        self.ids.add_playlist_btn.disabled = True

        # Swap sort by button
        self.ids.mainmenuplaylistspinner.pos = (-1000, 1000)
        self.ids.mainmenuspinner.pos = (0, 0)

    def display_playlists(self):
        global playlists

        # sort depending on order
        if self.ids.mainmenuplaylistspinner.text == 'Sort by: Created':
            playlists_sorted = playlists["playlists"]
        elif self.ids.mainmenuplaylistspinner.text == 'Sort by: Name':
            playlists_sorted = sorted(playlists["playlists"], key=lambda playlist: playlist["name"])
        elif self.ids.mainmenuplaylistspinner.text == 'Sort by: Song Count, Ascending':
            playlists_sorted = sorted(playlists["playlists"], key=lambda playlist: playlist["song_count"])
        elif self.ids.mainmenuplaylistspinner.text == 'Sort by: Song Count, Descending':
            playlists_sorted = list(reversed(sorted(playlists["playlists"], key=lambda playlist: playlist["song_count"])))
        elif self.ids.mainmenuplaylistspinner.text == 'Sort by: Duration, Ascending':
            playlists_sorted = sorted(playlists["playlists"], key=lambda playlist: playlist["total_length"])
        elif self.ids.mainmenuplaylistspinner.text == 'Sort by: Duration, Descending':
            playlists_sorted = list(reversed(sorted(playlists["playlists"], key=lambda playlist: playlist["total_length"])))
        else: # fallback, sort by order created
            playlists_sorted = playlists["playlists"]

        self.ids.main_song_list.data = [{'name': playlists_sorted[i]["name"],
                                         'song_list': playlists_sorted[i]["songs"],
                                         'song_count': playlists_sorted[i]["song_count"],
                                         'total_length': playlists_sorted[i]["total_length"]}
                                        for i in range(len(playlists_sorted))]

        # create add playlist button
        self.ids.add_playlist_btn.opacity = 1
        self.ids.add_playlist_btn.disabled = False

        # Swap sort by button
        self.ids.mainmenuspinner.pos = (-1000, 1000)
        self.ids.mainmenuplaylistspinner.pos = (0,0)

    def update_sort(self):
        if self.ids.main_song_list.viewclass == Song_Row:
            self.display_songs()
        elif self.ids.main_song_list.viewclass == Playlist_Row:
            self.display_playlists()

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
        sm.transition = SlideTransition()
        sm.transition.direction = 'up'
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

    def create_playlist_popup(self):
        popup_content = Create_Playlist_Form(self, None)
        popup = Popup(title='Create Playlist',content=popup_content,
                      size_hint=(0.5, 0.5))
        popup_content.popup_ref = popup
        popup.open()

    def create_playlist(self, playlist_name):
        playlists["playlists"].append({'name': playlist_name, 'songs': [], 'song_count': 0, 'total_length': 0})
        self.display_playlists()

    def delete_playlist(self, playlist_name):
        for playlist in playlists["playlists"]:
            if playlist["name"] == playlist_name:
                playlists["playlists"].remove(playlist)
                self.display_playlists()
                break

#endregion

""" Main App Classes + Main startup """
#region
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
        PlaybackController.start(songs["songs"], True)

        # MAKE CURRENT SCREEN LOAD FIRST
        sm.add_widget(MusicMenu(name="MusicMenu"))
        sm.add_widget(MainMenu(name="MainMenu"))
        sm.add_widget(PlaylistView(name="PlaylistView"))
        sm.current = 'MusicMenu'

        return sm

    def on_stop(self):
        global preferences
        # Set preferences using current preferences
        PlaybackController.set_preferences(preferences)

        with open('src/MusicPlayer/preferences.json', 'w') as pref_j:
            json.dump(preferences, pref_j, indent=4)
        with open('src/MusicPlayer/playlists.json', 'w') as playlists_j:
            json.dump(playlists, playlists_j, indent=4)

if __name__ == '__main__':
    MusicPlayerApp().run()
#endregion