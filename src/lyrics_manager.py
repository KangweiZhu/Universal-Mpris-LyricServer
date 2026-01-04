import requests
from mpris_prober import find_players, find_playing_players
from mpris_player import MprisPlayer, PlaybackStatus

class LyricsManager:
    """
    Core Controller: Manages player selection, tracking, and lyrics fetching.
    
    Note: ms here == microseconds, not miliseconds.
    """
    def __init__(self):
        self.setup()
    
    
    def setup(self, playername=None, playerobj=None, title=None, artist=None, album=None, lyrics=None, current_lyric=None, 
              playback_status=PlaybackStatus.STOPPED, position_ms=0, mutiplexing=True):
        self.playername = playername
        self.playerobj = playerobj
        self.title = title
        self.artist = artist
        self.album = album
        self.lyrics = lyrics
        self.current_lyric = current_lyric
        self.playback_status = playback_status
        self.position_ms = position_ms
    
    
    def poll_status(self, requested_playername=None):
        """
        Polls for player changes and state updates.
        
        requested_playername == None => Global Mode
                        == 'org.mpris.MediaPlayer2.spotify' => Spotify Mode
                        == 'org.mpris.MediaPlayer2.yesplaymusic' => YesPlayMusic Mode
        
        Args:
            requested_playername (str, optional): The specific DBus name to track (e.g. 'org.mpris.MediaPlayer2.spotify').
                                             If None, defaults to the first available player.
        """
        playernames = find_players()
        # Selection Logic:
            # 1. If there is no avaiable mpris complaint player, return empty State.
            # 2. If a specific target is requested:
                # 2.1 If the requested target exists in the mpris2 dbus interface: pick it.
                # 2.2 Otherwise, return empty state as the requested player is not playing.
            # 3. If no target requested, and then we enter the multiplexing mode. 
                # 3.1 If there is a player with playing status, pick it.
                # 3.2 If there is no player with playing status, fallback to the first player(paused/stopped) exists in mpris dbus.
                    # 3.2.1 If there is no player exists in the mpris dbus, return empty state.
        def set_free():
            self.setup()
            return self._get_empty_state()
        
        if not playernames:
            return set_free()
        current_playername = self.playername
        if requested_playername:
             if requested_playername in playernames:
                 current_playername = requested_playername
             else:
                return self._get_empty_state()
        else:
            playing_playernames = find_playing_players()
            playernames = find_players()
            if not playing_playernames:
                if playernames:
                    current_playername = playernames[0]
                else:
                    return set_free()
            else:
                current_playername = playing_playernames[0]
        current_playerobj = MprisPlayer(current_playername)    
        if not current_playerobj:
            return set_free()
        if self.title != current_playerobj.track_info['title'] \
                or self.artist != current_playerobj.track_info['artist'] \
                or self.album != current_playerobj.track_info['album']:
            self._fetch_lyrics(current_playername, current_playerobj)  
        current_lyric = self._get_current_lyric()
        self.setup(
            playername=current_playername,
            playerobj=current_playerobj,
            title=current_playerobj.track_info['title'],
            artist=current_playerobj.track_info['artist'],
            album=current_playerobj.track_info['album'],
            lyrics=self.lyrics,
            current_lyric=current_lyric,
            playback_status=current_playerobj.playback_status,
            position_ms=current_playerobj.position
        )
        return self.get_state()


    def _fetch_lyrics(self, playername, playerobj):
        title = playerobj.track_info['title']
        artists = playerobj.track_info['artist']
        artist = artists[0] if artists else ''
        album = playerobj.track_info['album']
        length = playerobj.track_info['length']
        if not title or not artists:
            self.lyrics = None
            return
        try:
            if playername == 'org.mpris.MediaPlayer2.yesplaymusic':
                self._fetch_lyrics_ypm(title)
            elif playername == 'org.mpris.MediaPlayer2.lx-music-desktop':
                self._fetch_lyrics_lxmusic()
            else:
                self._fetch_lyrics_lrclib(title, artist, album, length)
        except Exception as e:
            self.lyrics = None


    def _fetch_lyrics_ypm(self, title):
        """Fetch lyrics from YesPlayMusic localhost API"""
        ypm_base_url = "http://localhost:27232"
        response = requests.get(f"{ypm_base_url}/player", timeout=5)
        if response.status_code != 200:
            self.lyrics = None
            return
        data = response.json()
        if not data or not data.get('currentTrack') or data['currentTrack'].get('name') != title:
            self.lyrics = None
            return
        track_id = data['currentTrack']['id']
        response = requests.get(f"{ypm_base_url}/api/lyric?id={track_id}", timeout=5)
        if response.status_code != 200:
            self.lyrics = None
            return
        data = response.json()
        if data and data.get('lrc') and data['lrc'].get('lyric'):
            self.lyrics = self._parse_lrc(data['lrc']['lyric'])
        else:
            self.lyrics = None


    def _fetch_lyrics_lxmusic(self, port=23330):
        """Fetch lyrics from LX Music localhost API"""
        lxmusic_base_url = f"http://localhost:{port}"
        response = requests.get(f"{lxmusic_base_url}/lyric", timeout=5)
        if response.status_code == 200 and response.text:
            self.lyrics = self._parse_lrc(response.text)
        else:
            self.lyrics = None


    def _fetch_lyrics_lrclib(self, title, artist, album, length):
        """Fetch lyrics from lrclib.net (compatible mode)"""
        synced_lyrics = None
        duration_sec = length // 1000000 if length else None
        if duration_sec:
            url = f"https://lrclib.net/api/get?track_name={title}&artist_name={artist}&album_name={album}&duration={duration_sec}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                synced_lyrics = data.get('syncedLyrics')
        if not synced_lyrics:
            url = f"https://lrclib.net/api/search?track_name={title}&artist_name={artist}&album_name={album}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                for result in data:
                    if result.get('syncedLyrics'):
                        synced_lyrics = result['syncedLyrics']
                        break
        if synced_lyrics:
            self.lyrics = self._parse_lrc(synced_lyrics)
        else:
            self.lyrics = None


    def _parse_lrc(self, lrc_text):
        lines = []
        for line in lrc_text.splitlines():
            parts = line.split(']')
            if len(parts) > 1:
                time_str = parts[0].replace('[', '').strip()
                lyric = parts[1].strip()
                try:
                    m, s = time_str.split(':')
                    time_ms = int((float(m) * 60 + float(s)) * 1000000)
                    lines.append({"time_ms": time_ms, "lyric": lyric})
                except:
                    continue
        return lines


    def _get_current_lyric(self):
        if not self.lyrics:
            return None
        lyrics_line_num = len(self.lyrics)
        start = 0
        end = lyrics_line_num - 1
        while start <= end:
            mid = (start + end) >> 1
            if self.position_ms == self.lyrics[mid]['time_ms']:
                return self.lyrics[mid]['lyric']
            if self.position_ms > self.lyrics[mid]['time_ms']:
                start = mid + 1
            else:
                end = mid - 1
        if end < 0:
            return None
        return self.lyrics[end]['lyric']       
        
        
    def get_state(self):
        if not self.playerobj:
            return self._get_empty_state()
        track_info = self.playerobj.track_info
        return {
            "playback_status": self.playback_status.value.lower(),
            "player": {
                "identity": self.playerobj.identity,
                "bus_name": self.playername
            },
            "track": {
                "title": track_info['title'],
                "artist": ", ".join(track_info['artist']) if track_info['artist'] else "",
                "album": track_info['album'],
                "duration": track_info['length']
            },
            "position_ms": self.position_ms,
            "lyrics": {
                'current_lyric': self.current_lyric,
            },
            "available_players": find_players()
        }


    def _get_empty_state(self):
        return {
            "playback_status": PlaybackStatus.STOPPED.value.lower(),
            "player": None,
            "track": None,
            "position_ms": 0,
            "lyrics": None,
            "avaiable_players": None
        }