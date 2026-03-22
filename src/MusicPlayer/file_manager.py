# functions for managing and storing files and playlists

# imports needed here
import json
import mutagen
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
from mutagen import File
from mutagen.id3 import ID3
import kivy
import io
import os
from PIL import Image
from kivy.core.image import Image as CoreImage

"""
*** PLAN ***

SONG STORAGE:

JSON file holds each songs' info
program should pull from JSON instead of the file itself, saves time
On startup, scan song folder for songs not in the JSON
If a song isn't in the JSON, add the song to it
Also, check for mismatched info, and update accordingly
Each song JSON will have:

id: universal int counter, unique for every song
title: the title, kinda obvious
artist: the artist
duration: duration
filepath: absolute path, ex: songfolder/song1.mp3
filename: name of the file, ex: song1.mp3

when removing a song, also remove from all playlists

PLAYLISTS:

much more difficult...

have a JSON for the playlists
each playlist has:
name: obvious
songs: a list of song IDs
"""

"""
control flow for updating database:

go through each song in database:
check the filepath/filename, if it doesn't exist, remove it (it was deleted)
if removing, remove from all playlists
if it does exist, check all info and update info accordingly

then, go through the files in directory and add any songs not in the database yet

"""
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

def update_song_database(directory):
    # get JSON data
    with open('songs.JSON', 'r+') as songs_j:
        with open('playlists.JSON', 'r+') as playlists_j:
            songs_data = json.load(songs_j)
            playlists_data = json.load(playlists_j)

    # get directory data
    try:
        with os.scandir(directory) as entries:
            song_files = entries
    except FileNotFoundError:
        song_files = []
        print("File not found")
    except PermissionError:
        song_files = []
        print("Permission error")

    # go through JSON entries, update/check
    for item in songs_data["songs"]:
        pass

