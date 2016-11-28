#!/usr/bin/python
import asyncore
import re
import sys
import urllib
import socket
import time
from mplayer.async import AsyncPlayer
import json
from station import Station

subscribers = []       # Connections which care

def log(line):
    print '%s %s' % (time.strftime('%Y-%m-%d %H:%M:%S'), line )
    sys.stdout.flush()

class Player:
    def __init__(self, parms):
        # Set up variables we make visible
        self.title = ''
        self.icy = {}
        # Don't autospawn because we want to setup the args later
        self.player = AsyncPlayer(autospawn=False)

        # Setup additional args
        self.player.args = [
                            '-msgcharset', parms.charset,
                            '-noconsolecontrols',
                            '-msglevel', 'all=0:identify=6:demuxer=6']
        log(self.player.args)

        # hook a subscriber to Mplayer's stdout
        self.player.stdout.connect(self.handle_data)

        # Manually spawn the Mplayer process
        self.player.spawn()

    def load_station(self, station):
        log('%s: %s' % ('list' if station.islist else 'file', station.url))
        if station.islist:
            self.player.loadlist(station.url)
        else:
            self.player.loadfile(station.url)

    def handle_error(self):
        (t, v, db) = sys.exc_info()
        sys.stderr.write(repr(v))
        sys.stderr.write('\n')
        sys.stderr.write(repr(t))
        sys.stderr.write('\n')
        sys.stderr.write(repr(db))
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
        if line.startswith('ICY Info:'):
            try: 
                content = line.replace('ICY Info:','').split("';")
                self.icy = {}
                for c in content:
                    if '=' in c:
                        (name,value) = c.split('=',1)
                        name = name.strip()
                        value = value[1:].rstrip()
                        self.icy[name] = value.decode('utf8')
                        self.icy['hex' + name] = value.encode('hex')
                        self.icy['raw' + name] = value
                        if name.lower() == 'streamtitle':
                            self.title = value
                        if name.lower() == 'streamurl' and '&' in value:
                            (value, rest) = value.split('&', 1)
                            self.icy[name] = value
                            parts = rest.split('&')
                            for p in parts:
                                if '=' in p:
                                    (name, value) = p.split('=',1)
                                    self.icy[name] = urllib.unquote(value)
                                else:
                                    log("no = in: " +  p)
            except Exception, err:
                log("songtitle error: " + str(err))
                self.title = content.split("'")[1]
            log(self.icy)
            info = {}
            info['icy'] = self.icy
            info['station'] = Station.current().json()
            ans = json.dumps(info)
            log(ans)
            with open('status.json', 'w') as outfile:
                outfile.write(ans)
            for each in subscribers:
                each.outbuf += ans + '\n'
        elif line.startswith('ID_EXIT') or line.startswith('ds_fill_buffer'):
            log('*** EOF ***')
            log('Station.current().url: ' + Station.current().url)
            log('islist = ' + repr(Station.current().islist))
            log('*** Reloading ***')
            if not Station.current().islist:
                self.player.loadfile(Station.current().url)
            else:
                self.player.loadlist(Station.current().url)
        elif line.startswith('ID_FILENAME') or not line.startswith('ID_'):
            log(line)
        sys.stdout.flush()


class Controller(asyncore.dispatcher):
    def __init__(self, conn_sock, client_address, player):
        self.client_address = client_address
        self.sock = conn_sock
        self.player = player
        self.pp = player.player
        self.buffer = ''
        self.outbuf = '"playing":%s\n' % repr(Station.current()) 
        log('accepted from %s' % repr(client_address))
        sys.stdout.flush()
        # Hook ourselves into the dispatch loop
        subscribers.append(self)
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
            resp = []
            while '\n' in data:
                (line, data) = data.split('\n', 1)
                log('Command: "%s"' % line)
                if line.startswith('quit'):
                    sys.exit()
                elif line.startswith('pause'):
                    self.pp.pause()
                elif line.startswith('stop'):
                    self.pp.stop()
                elif line.startswith('play'):
                    rest = line[5:]
                    self.player.load_station(Station.select(rest))
                elif line.startswith('next'):
                    self.player.load_station(Station.next())
                elif line.startswith('prev'):
                    self.player.load_station(Station.prev())
                elif line.startswith('stat'):
                    resp.append('"stationlist":%s' % Station.stations())
                else:
                    resp.append('"playing":%s' % repr(Station.current()))
                self.outbuf += '{%s}' % ',\n'.join(resp) + '\n'
                sys.stdout.flush()
        else:
            self.close()
    
    def handle_close(self):
        if self in subscribers:
            subscribers.remove(self)
            log('removed ' + repr(self))
            sys.stdout.flush()


class ControlServer(asyncore.dispatcher):
    def __init__(self, player, port=6601, handlerClass=Controller):
        asyncore.dispatcher.__init__(self)
        self.port = port
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.bind(("", port))
        self.listen(5)
        self.handlerClass = handlerClass
        self.player = player
        log("listening on port %s" % self.port)
        sys.stdout.flush()


    def handle_accept(self):
        channel, addr = self.accept()
        self.handlerClass(channel, addr, self.player)
        player = self.player
        

def do_main_program():
    player = Player(parms)
    server = ControlServer(player)

    # play the first station
    log(Station.current())
    sys.stdout.flush()
    player.load_station(Station.current())
    # run the asyncore event loop
    asyncore.loop()

if __name__ == "__main__":
    import os
    import sys, pwd
    import time
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--charset', metavar='charset', type=str, default='utf-8')
    parser.add_argument('--outfile', type=str, default='')
    parser.add_argument('--delay', type=int, default=0)
    parms = parser.parse_args()
    if parms.delay:
        time.sleep(parms.delay)
    if parms.outfile:
        sys.stdout.close()
        sys.stdout = open(parms.outfile, 'a')
    do_main_program()


