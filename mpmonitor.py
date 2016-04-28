#!/usr/bin/python
import asyncore
import re
import sys
import urllib
import socket
import time
from mplayer.async import AsyncPlayer
import json

subscribers = []       # Connections which care

class Station:
    stationlist = []
    stationdir = {}
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

    @classmethod
    def select(self, what):
        try:
            pos = int(what)
            if (pos > 0) and (pos < len(self.stationlist)):
                self.stationpos = pos
        except ValueError:
            if what in self.stationdir:
                self.stationpos = self.stationdir[what].pos
        return self.stationlist[self.stationpos]

    @classmethod
    def stations(self):
        ret = []
        for s in self.stationlist:
            ret.append(repr(s))
        return '[%s]' % ','.join(ret)
        

    def __init__(self, label, url):
        self.label = label
        self.url = url
        self.pos = len(self.stationlist)
        self.stationlist.append(self)
        self.stationdir[label] = self

    def __repr__(self):
        return '{"pos":%d,"label":"%s","url":"%s"}' % (self.pos, self.label, self.url)
        
    def json(self):
        ans = {}
        ans['pos'] = self.pos
        ans['label'] = self.label
        ans['url'] = self.url
        return ans


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
                            '-msglevel', 'all=0:identify=6:demuxer=6']
        print self.player.args

        # hook a subscriber to Mplayer's stdout
        self.player.stdout.connect(self.handle_data)

        # Manually spawn the Mplayer process
        self.player.spawn()

        # Monkey patch a handle_error event into the player
        self.player.stdout._dispatcher.handle_error = self.handle_error

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
        print '%s %s' % (time.strftime('%Y-%m-%d %H:%M:%S'), line )
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
                                    print "no = in: ", p
            except Exception, err:
                print "songtitle error: " + str(err)
                self.title = content.split("'")[1]
            print self.icy
            info = {}
            info['icy'] = self.icy
            info['station'] = Station.current().json()
            ans = json.dumps(info)
            print ans
            with open('status.json', 'w') as outfile:
                outfile.write(ans)
            for each in subscribers:
                each.outbuf += ans + '\n'
        elif line.startswith('ID_EXIT') or line.startswith('ds_fill_buffer'):
            print '*** EOF ***'
            print 'Station.current().url)', Station.current().url
            print '*** Reloading ***'
            self.player.loadfile(Station.current().url)
        sys.stdout.flush()


class Controller(asyncore.dispatcher):
    def __init__(self, conn_sock, client_address, player):
        self.client_address = client_address
        self.sock = conn_sock
        self.player = player
        self.pp = player.player
        self.buffer = ''
        self.outbuf = '"playing":%s\n' % repr(Station.current()) 
        print '%s accepted from %s' % (time.strftime('%Y-%m-%d %H:%M:%S'),client_address )
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
                print '%s Command: "%s"' % (time.strftime('%Y-%m-%d %H:%M:%S'),line)
                if line.startswith('quit'):
                    sys.exit()
                elif line.startswith('pause'):
                    self.pp.pause()
                elif line.startswith('stop'):
                    self.pp.stop()
                elif line.startswith('play'):
                    rest = line[5:]
                    self.pp.loadfile(Station.select(rest).url)
                elif line.startswith('next'):
                    self.pp.loadfile(Station.next().url)
                elif line.startswith('prev'):
                    self.pp.loadfile(Station.prev().url)
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
            print 'removed', self
            sys.stdout.flush()


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
        sys.stdout.flush()


    def handle_accept(self):
        channel, addr = self.accept()
        self.handlerClass(channel, addr, self.player)
        player = self.player
        

def do_main_program(stations):
    player = Player(parms)
    server = ControlServer(player)
    if len(stations) > 0:
        for i in xrange(len(stations)):
            Station('%d' % i, stations[i])
    else:
        # Define the stations
        Station('KDFC', 'http://8333.live.streamtheworld.com:80/KDFCFM_SC')
        Station('Venice Classical Radio', 'http://174.36.206.197:8000/stream')
        Station('Radio Swiss Classic', 'http://stream.srg-ssr.ch/m/rsc_de/aacp_96')
        Station('BBC Radio 3', 'http://bbcmedia.ic.llnwd.net/stream/bbcmedia_radio3_mf_p?s=1449788045&e=1449802445&h=30697f7cb4a7a30b994f677063a26493')
        Station('Dutch Radio 4', 'http://icecast.omroep.nl/radio4-bb-mp3')
        Station('Linn Classical', 'http://89.16.185.174:8004/stream')
        Station('WQXR', 'http://stream.wqxr.org/wqxr')
        Station('WGBH', 'http://audio.wgbh.org:8004')

    # play the first station
    print Station.current()
    sys.stdout.flush()
    player.player.loadfile(Station.current().url)
    # run the asyncore event loop
    asyncore.loop()

if __name__ == "__main__":
    import daemon, daemon.pidfile, os
    import sys, pwd
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--nodaemon', dest='daemon', action='store_false')
    parser.add_argument('--daemon', dest='daemon', action='store_true')
    parser.add_argument('--charset', metavar='charset', type=str, default='utf-8')
    parser.add_argument('--user', default='david', type=str)
    parser.add_argument('--pidfile', default='mpmonitor.pid', type=str)
    parser.add_argument('--workdir', default='/home/david/src/radio', type=str)
    parser.add_argument('sources', metavar='stations', type=str, nargs='*',
            help='Sources to play (in order).  Default is internal list.')
    parms = parser.parse_args()
    if parms.user:
        user = pwd.getpwnam(parms.user)
        uid = user.pw_uid
        gid = user.pw_gid
        homedir = user.pw_dir
    else:
        uid = os.getuid()
        gid = os.getgid()
        homedir = '/'
    workdir = os.path.join(homedir, parms.workdir)

    if parms.sources:
        parms.daemon = False
    if parms.daemon:
        sys.stderr.close()
        sys.stderr = open(os.path.join(workdir, 'errlog.txt'), 'a')
        sys.stdout.close()
        sys.stdout = open(os.path.join(workdir, 'log.txt'), 'a')
        if parms.pidfile:
            pidfile = daemon.pidfile.PIDLockFile(os.path.join(workdir, parms.pidfile))
        else:
            pidfile = None
        with daemon.DaemonContext(working_directory=workdir,stdout=sys.stdout,stderr=sys.stderr,pidfile=pidfile,uid=uid,gid=gid,initgroups=False):
            do_main_program(parms.sources)
    else:
        do_main_program(parms.sources)

