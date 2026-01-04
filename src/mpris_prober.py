import dbus
import re
from mpris_player import PlaybackStatus

def find_players():
    """
    Finds all running media players that implement the MPRIS2 interface.
    """
    bus = dbus.SessionBus()
    playernames = []
    for s in bus.list_names():
        if re.match('org.mpris.MediaPlayer2.', s):
            playernames.append(s)
    return playernames

def find_playing_players():
    '''
    Finds all running media players that implement the MPRIS2 interface, and current playing something.
    
    Notice:
    From our implementation, the ordering of players is determined solely by their first appearance in 
    the MPRIS DBus via `find_players()` and remains stable across playback state changes. Therefore, 
    earlier-registered players always take priority whenever they enter the Playing state.  
    '''
    playernames = find_players()
    playing_playernames = []
    for playername in playernames:
        dbusobj = dbus.SessionBus().get_object(playername, '/org/mpris/MediaPlayer2')
        props_iface = dbus.Interface(dbusobj, 'org.freedesktop.DBus.Properties')
        playback_status = props_iface.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus')
        if playback_status.lower() == PlaybackStatus.PLAYING.value.lower():
            playing_playernames.append(playername)
    return playing_playernames

