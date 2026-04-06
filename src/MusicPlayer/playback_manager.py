from ffpyplayer.player import MediaPlayer
import threading
import time
import file_manager as fm


class PlaybackManager:
    def __init__(self):
        # queue variables
        self.previouslyPlayed: []
        self.currentSongId: ""
        self.priorityQueue: []
        self.queue = []
        self.fullScope = [] # whole list of songs to play, used when queue runs out

        # Players (max 3)
        self.prevSong: None
        self.curSong: None
        self.nextSong: None

        # Important Variables
        self.paused = True
        self.shuffle = False
        self.loop = False

        # Reference to Outside Functions
        self.funcs_to_call = []

        # create self.timer, initialized in Start()
        self.timer = None

    def Start(self):
        # At this point, queues have been initialized (may be empty, still)
        try:
            self.curSong = MediaPlayer(self.get_info()["filepath"],ff_opts={"paused": self.paused},
                ss=0.0)
        except: # No Current Song, so no filepath
            self.curSong = None
        try:
            self.prevSong = MediaPlayer(self.get_info(self.previouslyPlayed[-1])["filepath"],ff_opts={"paused": True},
                ss=0.0)
        except: # No previous songs, index error
            self.prevSong = None
        try:
            if self.priorityQueue != []:
                self.nextSong = MediaPlayer(self.get_info(self.priorityQueue[0])["filepath"], ff_opts={"paused": True},
                ss=0.0)
            else:
                self.nextSong = MediaPlayer(self.get_info(self.queue[0])["filepath"], ff_opts={"paused": True},
                ss=0.0)
        except: # No songs queued
            self.nextSong = None

        # Now, all three players are either None or have been initialized
        # prev, cur, next all exist -> at least 3 songs
        # prev, cur exist -> at least 1 song in previous, both pqueue and queue empty
        # cur, next exist -> at least 1 song queued
        # cur exist -> only 1 song
        # none exist -> 0 songs -> do nothing



        # Call self.update() every 0.1 secs
        self.timer = threading.Timer(0.1, self.update)

    def update(self):
        # Check if song is finished
        if self.curSong is not None: # But only if the current song exists
            if (self.get_info()["duration"] - self.get_time()) < 0.1:
                self.song_finished()

        # call updates on any outside functions that need it (MusicMenu)
        for func in self.funcs_to_call:
            func.update()

    def get_time(self):
        try:
            time = self.curSong.get_pts()
        except: # curSong is None
            time=0
        return time

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

    def song_finished(self):
        if self.loop: # restart current song
            self.curSong.seek(0)
        else: # get next song
            if self.nextSong is not None: # Next song exists
                # Use a thread to close previous song and open next song
                close_song_thread = threading.Thread(target=self.close_song, args=(self.prevSong), daemon=True)
                close_song_thread.start()
                # move prev <- cur and cur <- next
                self.prevSong = self.curSong
                self.curSong = self.nextSong

                # get current song id
                self.previouslyPlayed.append(self.currentSongId)
                if self.priorityQueue != []:
                    self.currentSongId = self.priorityQueue.pop(0)
                else: # priority queue is empty, pull from queue
                    if self.queue != []:
                        self.currentSongId = self.queue.pop(0)
                    else: # regular queue is empty, pull from previous (should never happen)
                        if self.previouslyPlayed != []:
                            self.currentSongId = self.previouslyPlayed[0]

            else: # next song does not exist, replay current
                self.curSong.seek(0)



    def close_song(self, ref):
        # ref is a reference to a MediaPlayer object (ex. self.prevSong)
        ref.close_player()





    """
    Need:
    PlaySong
    LoadSong
    PauseSong
    ForwardSong
    BackSong
    SongFinished
    GetInfo (just call fm.fetch_song_info)
    ToggleLoop
    ToggleShuffle
    SetTime
    Each function should take into consideration a non-existent song
    
    Groupings:
    **AUTOMATIC**
    SongFinished
    LoadSong
    PlaySong
    
    **CALLED OUTSIDE**
    PauseSong
    ForwardSong
    BackSong
    GetInfo
    ToggleLoop
    ToggleShuffle
    SetTime
    """

    """
    Initialized in main
    Starts blank
    Main uses preferences.JSON to continue from previous session (need on exit later)
    Use preferences.JSON to overwrite all queues, shuffle, loop, prev/cur/next song
    
    Have a "start" function called in main?
    app init sets queue and stuff, then calls "start"?
    start will load cur, prev, next?
    """


