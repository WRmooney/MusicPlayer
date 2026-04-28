from ffpyplayer.player import MediaPlayer
import threading
import file_manager as fm
import math
import random


class PlaybackManager:
    def __init__(self, prev_played, cur_id, pq, queue, scope, shuffle, loop):
        # queue variables
        self.previouslyPlayed = prev_played
        self.previousSongId = ""
        self.currentSongId = cur_id
        self.nextSongId = ""
        self.priorityQueue = pq
        self.queue = queue
        self.scope = scope # Whole list of songs to play, used when queue runs out

        # Players (max 3)
        self.prevSong = None
        self.curSong = None
        self.nextSong = None

        # Important Variables
        self.paused = True
        self.shuffle = shuffle
        self.loop = loop

        # Reference to Outside Functions
        self.funcs_to_call = []

        # create self.timer, initialized in Start()
        self.thread = threading.Thread(target=self.timer_loop, daemon=True)
        self.stop_event = threading.Event()

    def start(self, songs, first=False):
        # Check all songs and ensure they exist
        if first:
            self.checkSongIds(songs)

        # Check current Song id
        if self.currentSongId == "":
            # set everything to None, don't do anything, maybe change later?
            self.nextSongId = ""
            self.prevSongId = ""
            self.previouslyPlayed = []
            self.priorityQueue = []
            self.queue = []
            # Call self.update() every 0.1 secs
            self.start_timer()
            return
        else: # initialize current song
            self.curSong = MediaPlayer(self.get_info()["filepath"],
                                       ff_opts={"paused": first},ss=0.0)

        # set next and previous songs
        self.set_next_song()
        self.set_prev_song()

        # Call self.update() every 0.1 secs, only on first call
        if first:
            self.start_timer()

        self.debug_print("Start")

    def start_timer(self):
        self.thread.start()

    def timer_loop(self):
        while not self.stop_event.wait(0.1):
            self.update()

    def checkSongIds(self, songs):
        # check current song id
        if self.currentSongId not in songs:
            self.currentSongId = ""
            print("Current song id not in songs!")

        # check previously played
        for songid in self.previouslyPlayed:

            if songid not in songs:
                self.previouslyPlayed.remove(songid)


        # check priority queue
        for songid in self.priorityQueue:
            if songid not in songs:
                self.priorityQueue.remove(songid)

        # check regular queue
        for songid in self.queue:
            if songid not in songs:
                self.queue.remove(songid)

        # check scope
        for songid in self.scope:
            if songid not in songs:
                self.scope.remove(songid)

    def update(self):
        if self.curSong is not None:
            # Check if song is finished
            if self.curSong is not None and not self.curSong.get_pause(): # But only if the current song exists
                if (self.get_info()["duration"] - self.get_time()) < 0.1:
                    self.song_finished()

            # call updates on any outside functions that need it (MusicMenu)
            for func in self.funcs_to_call:
                func.update()

    def get_time(self):
        try:
            curtime = self.curSong.get_pts()
        except: # curSong is None
            curtime=0
        return curtime

    def get_info(self, song_id=None):
        if song_id is None: # if song_id is not none, its prev or next song
            song_id = self.currentSongId
        try:
            info = fm.fetch_song_info(song_id)
        except:
            info = {
                "title" : "No Info",
                "artist" : "No Info",
                "duration" : 0,
                "filepath" : "No Info",
                "filename" : "No Info"
            }
        return info

    # Only called if current song is unpaused, unless called by skip()
    def song_finished(self, skipped=False):
        # no songs, do nothing
        if self.curSong == None:
            return
        if self.loop and not skipped: # restart current song, unless skip button was used
            self.curSong.set_pause(True)
            self.seek(0.0)
            self.curSong.set_pause(False)
            return
        # at least 1 song, loop is off

        # pause current song and seek to 0
        self.curSong.set_pause(True)
        self.seek(0.0)

        # close prevSong MediaPlayer object with a separate thread
        if self.prevSong is not None:
            threading.Thread(target=self.close_song, args=(self.prevSong,), daemon=True).start()

        # move around references, prev <- cur, cur <- next
        self.prevSong = self.curSong
        self.prevSongId = self.currentSongId
        self.curSong = self.nextSong
        self.currentSongId = self.nextSongId

        # Add prev to previouslyPlayed and pop cur from wherever it came from
        self.previouslyPlayed.append(self.prevSongId)
        if self.priorityQueue != []:
            self.priorityQueue.pop(0)
        else:
            self.queue.pop(0)

        # Set Next Song
        self.set_next_song()

        # Play next song if paused is false
        """
        song_finished() is usually called when self.paused == False
        EXCEPT for skip(), which could pass either true or false
        
        if skip() is called when self.paused == True
        nothing happens, song stays paused
        
        when self.paused == False, the song is unpaused here, 
        regardless of where song_finished was called from
        """
        if not self.paused:
            self.curSong.set_pause(False)

        # update info for other classes
        for func in self.funcs_to_call:
            func.update_info()

    # prints queue info
    def debug_print(self, function_name):
        print("\n")
        print("CALLED FROM: " + function_name)
        print("PREVIOUSLY PLAYED: " + str(self.previouslyPlayed))
        print("CURRENT SONG: " + str(self.curSong))
        print("CURRENT SONG NAME: " + str(self.get_info()["title"]))
        print("PRIORITY QUEUE: " + str(self.priorityQueue))
        print("QUEUE: " + str(self.queue))
        print("SCOPE: " + str(self.scope))

    # get the next song id and set next song id, open next song player using thread
    def set_next_song(self):
        # update id
        self.nextSongId = self.get_next_id()
        # use multithreading to load the song in the background
        threading.Thread(target=self.load_song, args=("next", self.nextSongId), daemon=True).start()

    # get the previous song and open the player with a thread
    def set_prev_song(self):
        # Update id
        self.prevSongId = self.get_prev_id()
        # use multithreading to load the song in the background
        threading.Thread(target=self.load_song, args=("prev", self.prevSongId), daemon=True).start()

    # returns the id of the next song based on queues, extends queue using scope if empty
    def get_next_id(self):
        if self.priorityQueue != []:
            nextSongId = self.priorityQueue[0]
        elif self.priorityQueue == [] and self.queue != []:
            nextSongId = self.queue[0]
        elif self.priorityQueue == [] and self.queue == []:
            self.queue.extend(self.scope)
            if self.shuffle:
                self.shuffle_queue()
            print(self.queue)
            print(self.scope)
            nextSongId = self.queue[0]
        return nextSongId

    def get_prev_id(self):
        if self.previouslyPlayed == []:
            return ""
        else:
            return self.previouslyPlayed[-1]

    def load_song(self, ref_key, song_id):

        if ref_key == "next":
            self.nextSong = MediaPlayer(self.get_info(song_id)["filepath"], ff_opts={"paused": True},
                                   ss=0.0)
        elif ref_key == "prev":
            self.prevSong = MediaPlayer(self.get_info(song_id)["filepath"], ff_opts={"paused": True},
                                        ss=0.0) if song_id != "" else None # return none if no previously played songs

    def close_song(self, ref):
        # ref is a reference to a MediaPlayer object (ex. self.prevSong)
        ref.close_player()

    def shuffle_queue(self):
        random.shuffle(self.queue)
        self.update_next_song()

    def update_next_song(self):
        # nothing changed, do nothing
        if self.get_next_id() == self.nextSongId:
            return
        else:
            self.set_next_song()

    def get_pause(self):
        return self.paused

    def set_pause(self, paused):
        if self.curSong is not None:
            self.paused = paused
            self.curSong.set_pause(paused)

    def toggle_pause(self):
        if self.curSong is not None:
            if self.paused:
                self.paused = False
                self.curSong.set_pause(False)
            else:
                self.paused = True
                self.curSong.set_pause(True)

    def toggle_loop(self):
        if self.loop:
            self.loop = False
        else:
            self.loop = True

    def toggle_shuffle(self):
        # Only shuffle if there are songs to shuffle, don't shuffle priority queue
        if self.curSong is not None and self.queue != []:
            if self.shuffle:
                self.shuffle = False
                # !!! Need to add code to put original order (very tough)
            else:
                self.shuffle = True
                self.shuffle_queue()

    def skip(self):
        # just call song finished
        self.song_finished(True)

    def back(self):
        if self.curSong is None:
            return

        # pause current song and seek to 0
        self.curSong.set_pause(True)
        self.seek(0.0)

        # close prevSong MediaPlayer object with a separate thread
        threading.Thread(target=self.close_song, args=(self.nextSong,), daemon=True).start()

        # move around references, prev -> cur, cur -> next
        self.nextSong = self.curSong
        self.nextSongId = self.currentSongId
        self.curSong = self.prevSong
        self.currentSongId = self.prevSongId


        # Add next to queue or pqueue and pop cur from previouslyPlayed
        self.previouslyPlayed.pop(-1)
        if self.priorityQueue != []:
            self.priorityQueue.insert(0, self.nextSongId)
        else:
            self.queue.insert(0,self.nextSongId)

        # Set Next Song
        self.set_prev_song()

        # Play prev song if paused is false
        if not self.paused:
            self.curSong.set_pause(False)

        # update info for other classes
        for func in self.funcs_to_call:
            func.update_info()

    def seek(self, new_pos):
        self.curSong.seek(new_pos, relative=False)

    def set_preferences(self, pref_ref):
        pref_ref["loop"] = self.loop
        pref_ref["shuffle"] = self.shuffle
        pref_ref["previous_queue"] = self.previouslyPlayed
        pref_ref["current_song_id"] = self.currentSongId
        pref_ref["priority_queue"] = self.priorityQueue
        pref_ref["queue"] = self.queue
        pref_ref["scope"] = self.scope

    # Start playing from all songs (mainmenu)
    def play_from_songs(self, song_id, songs):
        # reset players
        self.reset_players()

        # empty queues
        self.previouslyPlayed = []
        self.currentSongId = song_id
        self.priorityQueue = []

        self.prevSongId = ""
        self.nextSongId = ""
        # get list of all song ids, set scope
        queue = sorted(list(songs.keys()), key=lambda x: songs[x]["title"])
        print("QUEUE IN SONGS START: " + str(queue))
        self.scope = queue


        # check shuffle, adjust queue accordingly
        if self.shuffle:
            # remove current song, shuffle the rest

            queue.remove(song_id)
            random.shuffle(queue)
            self.queue = queue
        else:
            # remove current song and ALL songs before it
            cur_index = queue.index(song_id)
            queue = queue[cur_index+1:]
            self.queue = queue

        self.debug_print("Play from songs")

        self.start(songs)
        self.paused = False

        for func in self.funcs_to_call:
            func.update_info()

    def play_from_playlist(self, songs):
        # reset players
        self.reset_players()

        # empty queues
        self.previouslyPlayed = []
        self.priorityQueue = []
        self.scope = []

        self.prevSongId = ""
        self.nextSongId = ""
        # get list of all song ids, set scope
        queue = []
        queue.extend(songs)
        self.scope.extend(queue)

        # check shuffle, adjust queue accordingly
        if self.shuffle:
            # remove current song, shuffle the rest
            self.currentSongId = queue[random.randint(0, len(queue)-1)]
            queue.remove(self.currentSongId)
            random.shuffle(queue)
            self.queue = queue
        else:
            # set first song to current, pop from queue
            self.currentSongId = queue[0]
            self.queue = queue
            self.queue.pop(0)

        self.debug_print("Play from playlist")
        self.start(songs)
        self.paused = False

        for func in self.funcs_to_call:
            func.update_info()

    def play_song_in_playlist(self, playlist, index):
        # reset players
        self.reset_players()

        # empty queues
        self.previouslyPlayed = []
        self.currentSongId = playlist[index]
        self.priorityQueue = []
        self.scope = []

        self.prevSongId = ""
        self.nextSongId = ""
        # get list of all song ids, set scope
        queue = []
        queue.extend(playlist)
        self.scope.extend(queue)

        # check shuffle, adjust queue accordingly
        if self.shuffle:
            # remove current song, shuffle the rest
            queue.remove_at(index)
            random.shuffle(queue)
            self.queue = queue
        else:
            # remove current song and ALL songs before it
            queue = queue[index + 1:]
            self.queue = queue

        self.debug_print("Play from inside playlistview")

        self.start(playlist)
        self.paused = False

        for func in self.funcs_to_call:
            func.update_info()

    def add_to_queue(self, song_id):
        self.priorityQueue.append(song_id)
        self.update_next_song()
        self.debug_print("Add_to_queue")

    def get_length_text(self, length):
        hours = math.floor(length / 3600)
        minutes = math.floor((length - (hours * 3600)) / 60)
        length_str = ""
        if hours != 0:
            if hours == 1:
                length_str += str(hours) + " Hour "
            else:
                length_str += str(hours) + " Hours "
        length_str += str(minutes) + " Min"

        return length_str

    def reset_players(self):
        # Properly shut down each player if it exists
        for player_attr in ['prevSong', 'curSong', 'nextSong']:
            player = getattr(self, player_attr)
            if player is not None:
                try:
                    print("closing player")
                    player.set_pause(True)
                    self.close_song(player)
                except:
                    print("passing")
                    pass
            setattr(self, player_attr, None)