#!/usr/bin/python
import asyncore
import re
import sys
import urllib
import socket
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
        # Don't autospawn because we want to setup the args later
        self.player = AsyncPlayer(autospawn=False)

        # Setup additional args
        self.player.args = ['-quiet', '-msglevel', 'all=0:identify=6:demuxer=6']

        # hook a subscriber to Mplayer's stdout
        self.player.stdout.connect(self.handle_data)

        # Manually spawn the Mplayer process
        self.player.spawn()

    def __repr__(self):
        ret = []
        ret.append('"title":"%s"' % self.title)
        ret.append('"icyinfo":"%s"' % repr(self.icy))
        ret.append('"paused":"%s"' % self.player.paused)
        ret.append('"metadata":"%s"' % self.player.metadata)
        return '{' + ',\n'.join(ret) + '}'

    def handle_data(self, data):
        if not data.startswith('EOF code'):
            print('log: %s' % (data, ))
            if data.startswith('ICY Info:'):
                    
                start = "StreamTitle='"
                end = "';"

                try: 
                    content = data.replace('ICY Info:','').split("';")
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
        else:
            self.player.quit()


class Controller(asyncore.dispatcher):
    def __init__(self, conn_sock, client_address, player):
        self.client_address = client_address
        self.sock = conn_sock
        self.player = player
        self.pp = player.player
        self.buffer = ''
        print("accepted from", client_address)
        # Hook ourselves into the dispatch loop
        asyncore.dispatcher.__init__(self, self.sock)

    def handle_read(self):
        data = self.recv(1024)
        if data:
            self.buffer += data
            while '\n' in data:
                (line, data) = data.split('\n', 1)
                print 'Command: "%s"' % line
                print 'paused = ', self.pp.paused
                if line[0] == 'q':
                    sys.exit()
                elif line.startswith('stop') and not self.pp.paused:
                    self.pp.pause()
                    print 'paused => ', self.pp.paused
                elif line.startswith('play') and self.pp.paused:
                    self.pp.pause()
                    print 'paused => ', self.pp.paused
                elif line.startswith('next'):
                    self.pp.loadfile(Station.next().url)
                    if self.pp.paused:
                        self.pp.pause()
                elif line.startswith('prev'):
                    self.pp.loadfile(Station.prev().url)
                    if self.pp.paused:
                        self.pp.pause()
                self.send(repr(Station.current()) + '\n')            
                print repr(self.player) 
    


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

def do_main_program():
    player = Player()
    server = ControlServer(player)
    # Define the stations
    Station('KDFC', 'http://8343.live.streamtheworld.com/KDFCFMAAC_SC')
    Station('Venice Classical Radio', 'http://174.36.206.197:8000/stream')
    Station('Radio Swiss Classic', 'http://stream.srg-ssr.ch/m/rsc_de/aacp_96')
    Station('WQXR', 'http://stream.wqxr.org/wqxr')
    Station('BBC Radio 3', 'http://bbcmedia.ic.llnwd.net/stream/bbcmedia_radio3_mf_p?s=1449788045&e=1449802445&h=30697f7cb4a7a30b994f677063a26493')
    Station('Dutch Radio 4', 'http://icecast.omroep.nl/radio4-bb-mp3')
    Station('WGBH', 'http://audio.wgbh.org:8004')

    # play a stream
    if len(sys.argv) > 1:
        player.player.loadfile(sys.argv[1])
    else:
        player.player.loadfile(Station.current().url)
    # run the asyncore event loop
    asyncore.loop()

if __name__ == "__main__":
    do_main_program()
    
