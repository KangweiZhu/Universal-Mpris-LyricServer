import dbus
from enum import Enum

DBUS_PROPERTIES_IFACE = 'org.freedesktop.DBus.Properties'
MPRIS_ROOT_IFACE = 'org.mpris.MediaPlayer2'
MPRIS_PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'
MPRIS_OBJECT_PATH = '/org/mpris/MediaPlayer2'


class PlaybackStatus(Enum):
    PLAYING = "Playing"
    PAUSED = "Paused"
    STOPPED = "Stopped"


class MprisPlayer:
    """
    Wraps a single MPRIS2 media player DBus service.
    Implements org.mpris.MediaPlayer2 and org.mpris.MediaPlayer2.Player interfaces.
    """
    def __init__(self, dbus_identifier):
        self.dbus_identifier = dbus_identifier
        self.bus = dbus.SessionBus()
        try:
            self.obj = self.bus.get_object(dbus_identifier, MPRIS_OBJECT_PATH)
            self.props_iface = dbus.Interface(self.obj, DBUS_PROPERTIES_IFACE)
            self.root_iface = dbus.Interface(self.obj, MPRIS_ROOT_IFACE)
            self.player_iface = dbus.Interface(self.obj, MPRIS_PLAYER_IFACE)
        except dbus.exceptions.DBusException as e:
            print(f"Error connecting to {dbus_identifier}: {e}")
            self.obj = None


    def _get_property(self, iface, prop_name):
        if not self.obj: return None
        try:
            return self.props_iface.Get(iface, prop_name)
        except dbus.exceptions.DBusException:
            return None


    def _set_property(self, iface, prop_name, value):
        if not self.obj: return
        try:
            self.props_iface.Set(iface, prop_name, value)
        except dbus.exceptions.DBusException:
            pass


    def raise_player(self):
        """Brings the media player's user interface to the front."""
        if self.can_raise:
            try:
                self.root_iface.Raise()
            except dbus.exceptions.DBusException:
                pass


    def quit(self):
        """Causes the media player to stop running."""
        if self.can_quit:
            try:
                self.root_iface.Quit()
            except dbus.exceptions.DBusException:
                pass


    @property
    def can_quit(self):
        return bool(self._get_property(MPRIS_ROOT_IFACE, 'CanQuit'))


    @property
    def fullscreen(self):
        return bool(self._get_property(MPRIS_ROOT_IFACE, 'Fullscreen'))


    @fullscreen.setter
    def fullscreen(self, value):
        if self.can_set_fullscreen:
            self._set_property(MPRIS_ROOT_IFACE, 'Fullscreen', value)


    @property
    def can_set_fullscreen(self):
        return bool(self._get_property(MPRIS_ROOT_IFACE, 'CanSetFullscreen'))


    @property
    def can_raise(self):
        return bool(self._get_property(MPRIS_ROOT_IFACE, 'CanRaise'))


    @property
    def has_track_list(self):
        return bool(self._get_property(MPRIS_ROOT_IFACE, 'HasTrackList'))


    @property
    def identity(self):
        val = self._get_property(MPRIS_ROOT_IFACE, 'Identity')
        return str(val) if val else "Unknown"


    @property
    def desktop_entry(self):
        val = self._get_property(MPRIS_ROOT_IFACE, 'DesktopEntry')
        return str(val) if val else ""


    @property
    def supported_uri_schemes(self):
        val = self._get_property(MPRIS_ROOT_IFACE, 'SupportedUriSchemes')
        return list(val) if val else []


    @property
    def supported_mime_types(self):
        val = self._get_property(MPRIS_ROOT_IFACE, 'SupportedMimeTypes')
        return list(val) if val else []

    # ==========================================
    # org.mpris.MediaPlayer2.Player (Player Interface)
    # ==========================================

    # --- Methods ---
    def next(self):
        try: self.player_iface.Next()
        except: pass


    def previous(self):
        try: self.player_iface.Previous()
        except: pass


    def pause(self):
        try: self.player_iface.Pause()
        except: pass


    def play_pause(self):
        try: self.player_iface.PlayPause()
        except: pass


    def stop(self):
        try: self.player_iface.Stop()
        except: pass


    def play(self):
        try: self.player_iface.Play()
        except: pass


    # --- Properties ---
    @property
    def playback_status(self):
        # "Playing", "Paused", "Stopped"
        val = self._get_property(MPRIS_PLAYER_IFACE, 'PlaybackStatus')
        return PlaybackStatus(str(val)) if val else PlaybackStatus.STOPPED
    
    
    @property
    def loop_status(self):
        # "None", "Track", "Playlist"
        val = self._get_property(MPRIS_PLAYER_IFACE, 'LoopStatus')
        return str(val) if val else "None"


    @loop_status.setter
    def loop_status(self, value):
        self._set_property(MPRIS_PLAYER_IFACE, 'LoopStatus', value)


    @property
    def rate(self):
        val = self._get_property(MPRIS_PLAYER_IFACE, 'Rate')
        return float(val) if val else 1.0


    @rate.setter
    def rate(self, value):
        self._set_property(MPRIS_PLAYER_IFACE, 'Rate', value)


    @property
    def shuffle(self):
        val = self._get_property(MPRIS_PLAYER_IFACE, 'Shuffle')
        return bool(val)


    @shuffle.setter
    def shuffle(self, value):
        self._set_property(MPRIS_PLAYER_IFACE, 'Shuffle', value)


    @property
    def metadata(self):
        val = self._get_property(MPRIS_PLAYER_IFACE, 'Metadata')
        return dict(val) if val else {}


    @property
    def track_info(self):
        """Extract commonly used track info from metadata."""
        meta = self.metadata
        return {
            'title': meta.get('xesam:title', ''),
            'artist': meta.get('xesam:artist', []),
            'album': meta.get('xesam:album', ''),
            'art_url': meta.get('mpris:artUrl', ''),
            'length': meta.get('mpris:length', 0), # microseconds
            'track_id': meta.get('mpris:trackid', ''),
            'genre': meta.get('xesam:genre', []),
            'composer': meta.get('xesam:composer', []),
            'lyricist': meta.get('xesam:lyricist', []),
            'track_number': meta.get('xesam:trackNumber', 0),
            'disc_number': meta.get('xesam:discNumber', 0),
            'lyrics': meta.get('xesam:asText', ''),
        }


    @property
    def volume(self):
        val = self._get_property(MPRIS_PLAYER_IFACE, 'Volume')
        return float(val) if val is not None else 1.0


    @volume.setter
    def volume(self, value):
        self._set_property(MPRIS_PLAYER_IFACE, 'Volume', value)


    @property
    def position(self):
        # Returns position in microseconds
        val = self._get_property(MPRIS_PLAYER_IFACE, 'Position')
        return int(val) if val is not None else 0


    @property
    def min_rate(self):
        val = self._get_property(MPRIS_PLAYER_IFACE, 'MinimumRate')
        return float(val) if val else 1.0


    @property
    def max_rate(self):
        val = self._get_property(MPRIS_PLAYER_IFACE, 'MaximumRate')
        return float(val) if val else 1.0


    @property
    def can_go_next(self):
        val = self._get_property(MPRIS_PLAYER_IFACE, 'CanGoNext')
        return bool(val)


    @property
    def can_go_previous(self):
        val = self._get_property(MPRIS_PLAYER_IFACE, 'CanGoPrevious')
        return bool(val)


    @property
    def can_play(self):
        val = self._get_property(MPRIS_PLAYER_IFACE, 'CanPlay')
        return bool(val)


    @property
    def can_pause(self):
        val = self._get_property(MPRIS_PLAYER_IFACE, 'CanPause')
        return bool(val)


    @property
    def can_seek(self):
        val = self._get_property(MPRIS_PLAYER_IFACE, 'CanSeek')
        return bool(val)


    @property
    def can_control(self):
        val = self._get_property(MPRIS_PLAYER_IFACE, 'CanControl')
        return bool(val)


    def get_full_info(self):
        """Retrieves all properties from both MPRIS2 interfaces as a standard Python dictionary."""
        data = {}
        if not self.obj: return data
        
        def unwrap(val):
            if isinstance(val, dbus.String): return str(val)
            if isinstance(val, (dbus.Int16, dbus.Int32, dbus.Int64, dbus.UInt16, dbus.UInt32, dbus.UInt64)): return int(val)
            if isinstance(val, dbus.Double): return float(val)
            if isinstance(val, dbus.Boolean): return bool(val)
            if isinstance(val, dbus.Array): return [unwrap(x) for x in val]
            if isinstance(val, dbus.Dictionary): return {unwrap(k): unwrap(v) for k, v in val.items()}
            return val

        try:
            root_props = self.props_iface.GetAll(MPRIS_ROOT_IFACE)
            player_props = self.props_iface.GetAll(MPRIS_PLAYER_IFACE)
            
            data['root'] = unwrap(root_props)
            data['player'] = unwrap(player_props)
        except dbus.exceptions.DBusException as e:
            print(f"Error fetching full state for {self.dbus_identifier}: {e}")
            
        return data
