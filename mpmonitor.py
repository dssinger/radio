#!/usr/bin/python
import asyncore
import re
import sys
import urllib
import socket
import time
from mplayer.async import AsyncPlayer

class Station:
    stationlist = []
    stationpos = 0

    @classmethod
    def next(self):
        self.stationpos += 1
        if self.stationpos >= len(self.stationlist):
            self.stationpos = 0
        return self.stationlist[self.stationpos]

    @classmethod
    def prev(self):
        self.stationpos -= 1
        if self.stationpos < 0:
            self.stationpos = len(self.stationlist) - 1
        return self.stationlist[self.stationpos]

    @classmethod
    def current(self):
        return self.stationlist[self.stationpos]

    def __init__(self, label, url):
        self.label = label
        self.url = url
        self.pos = len(self.stationlist)
        self.stationlist.append(self)

    def __repr__(self):
        return '%d: %s\n   %s' % (self.pos, self.label, self.url)
        

class Player:
    def __init__(self):
        # Set up variables we make visible
        self.title = ''
        self.icy = {}
        # Don't autospawn because we want to setup the args later
        self.player = AsyncPlayer(autospawn=False)

        # Setup additional args
        self.player.args = ['-quiet', '-msglevel', 'all=0:identify=6:demuxer=6']

        # hook a subscriber to Mplayer's stdout
        self.player.stdout.connect(self.handle_data)

        # Manually spawn the Mplayer process
        self.player.spawn()

        # Monkey patch a handle_error event into the player
        self.player.stdout._dispatcher.handle_error = self.handle_error

    def handle_error(self):
        (t, v, db) = sys.exc_info()
        sys.stderr.write(v)
        sys.stderr.write('\n')
        return

    def __repr__(self):
        ret = []
        ret.append('"title":"%s"' % self.title)
        ret.append('"icyinfo":"%s"' % repr(self.icy))
        ret.append('"metadata":"%s"' % self.player.metadata)
        ret.append('"paused":"%s"' % self.player.paused)
        return '{' + ',\n'.join(ret) + '}'


    def handle_data(self, line):
        # Called one line at a time by mplayer.py
        print '%s %s' % (time.strftime('%Y-%m-%d %H:%M:%S'), line )
        if line.startswith('ICY Info:'):
            try: 
                content = line.replace('ICY Info:','').split("';")
                self.icy = {}
                for c in content:
                    if '=' in c:
                        (name,value) = c.split('=',1)
                        value = value[1:].rstrip()
                        self.icy[name] = value
                        if name.lower() == 'streamtitle':
                            self.title = value
                        if name.lower() == 'streamurl' and '&' in value:
                            (value, rest) = value.split('&', 1)
                            self.icy[name] = value
                            parts = rest.split('&')
                            for p in parts:
                                if '=' in p:
                                    (name, value) = p.split('=',1)
                                    self.icy[name] = urllib.unquote(value).decode('utf8')
                                else:
                                    print "no = in: ", p
            except Exception, err:
                print "songtitle error: " + str(err)
                self.title = content.split("'")[1]
            print self.icy
        elif line.startswith('ID_EXIT') or line.startswith('ds_fill_buffer'):
            self.player.loadfile(Station.current().url)


class Controller(asyncore.dispatcher):
    def __init__(self, conn_sock, client_address, player):
        self.client_address = client_address
        self.sock = conn_sock
        self.player = player
        self.pp = player.player
        self.buffer = ''
        self.outbuf = ''
        print("accepted from", client_address)
        # Hook ourselves into the dispatch loop
        asyncore.dispatcher.__init__(self, self.sock)

    def readable(self):
        return True     # Always willing to read

    def writeable(self):
        return len(self.outbuf) > 0

    def handle_write(self):
        sent = self.send(self.outbuf)
        self.outbuf = self.outbuf[sent:]
    
    def handle_read(self):
        data = self.recv(1024)
        if data:
            self.buffer += data
            while '\n' in data:
                (line, data) = data.split('\n', 1)
                print 'Command: "%s"' % line
                if line.startswith('quit'):
                    sys.exit()
                elif line.startswith('pause'):
                    self.pp.pause()
                elif line.startswith('stop'):
                    self.pp.stop()
                elif line.startswith('play'):
                    self.pp.loadfile(Station.current().url)
                elif line.startswith('next'):
                    self.pp.loadfile(Station.next().url)
                elif line.startswith('prev'):
                    self.pp.loadfile(Station.prev().url)
                self.outbuf += repr(Station.current()) + '\n' + repr(self.player) + '\n'
    


class ControlServer(asyncore.dispatcher):
    def __init__(self, player, port=6601, handlerClass=Controller):
        asyncore.dispatcher.__init__(self)
        self.port = port
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(("", port))
        self.listen(5)
        self.handlerClass = handlerClass
        self.player = player
        print "listening on port", self.port


    def handle_accept(self):
        channel, addr = self.accept()
        self.handlerClass(channel, addr, self.player)
        player = self.player
        

def do_main_program(stations):
    player = Player()
    server = ControlServer(player)
    if len(stations) > 0:
        for i in xrange(len(stations)):
            Station('%d' % i, stations[i])
    else:
        # Define the stations
        Station('KDFC', 'http://8343.live.streamtheworld.com/KDFCFMAAC_SC')
        Station('Venice Classical Radio', 'http://174.36.206.197:8000/stream')
        Station('Radio Swiss Classic', 'http://stream.srg-ssr.ch/m/rsc_de/aacp_96')
        Station('BBC Radio 3', 'http://bbcmedia.ic.llnwd.net/stream/bbcmedia_radio3_mf_p?s=1449788045&e=1449802445&h=30697f7cb4a7a30b994f677063a26493')
        Station('Dutch Radio 4', 'http://icecast.omroep.nl/radio4-bb-mp3')
        Station('WQXR', 'http://stream.wqxr.org/wqxr')
        Station('WGBH', 'http://audio.wgbh.org:8004')

    # play the first station
    print Station.current()
    player.player.loadfile(Station.current().url)
    # run the asyncore event loop
    asyncore.loop()

if __name__ == "__main__":
    import daemon
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--nodaemon', dest='daemon', action='store_false')
    parser.add_argument('--daemon', dest='daemon', action='store_true')
    parser.add_argument('sources', metavar='stations', type=str, nargs='*',
            help='Sources to play (in order).  Default is internal list.')
    parms = parser.parse_args()

    if parms.daemon:
        sys.stderr.close()
        sys.stderr = open('/home/david/src/radio/errlog.txt', 'a')
        sys.stdout.close()
        sys.stdout = open('/home/david/src/radio/log.txt', 'a')
        with daemon.DaemonContext(working_directory="/home/david/src/radio",initgroups=False):
            do_main_program(parms.sources)
    else:
        do_main_program(parms.sources)

