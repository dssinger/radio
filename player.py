#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Player: the all-singing, all-dancing Raspberry Pi MPD client
    Connects to MPD and provides a simplified interface to it.
    Accepts commands on port 6601, always responds with current player 
       status.

"""


import socket
import select
import time
import sys
from mysocket import *

MYPORT = 6601

# Define the handlers for reads.  

class MPDController:
    """ Information about the current status of the MPD player.
        We don't care about the MPD database, since we're handling
        streaming audio only.
    """

    def __init__(self):
        self.mysock = mysocket(reader=self.handleidleresp)    
        self.inidle = False
        self.mysock.connect(('localhost', 6600))
        self.readline()    # Throw away MPD's welcome message
        self.docommand('repeat 1')   # Ensure we can loop around
        # docommand also gets current status and playlist for free.

    def __repr__(self):
        ret = '{' 
        ret += ',\n'.join(['"%s":%s' % (k, self.status[k]) for k in self.status.keys()])
        ret += ',\n"current":' + self.current
        ret += ',\n' + '"idle":"%s"} ' % repr(self.inidle)
        return ret

    def send(self, string):
        self.mysock.send(string)

    def readline(self):
        ret = self.mysock.readline()
        return ret
         
    def readresp(self):
        """ Reads lines until "OK" or "ACK"  """

        ans = []
        ans.append(self.readline())
        while ans[-1] != '' and ans[-1] != 'OK' \
            and not ans[-1].startswith('ACK '):
            ans.append(self.readline())
        return ans[:-1]

    def noidle(self):
        was = self.inidle
        if self.inidle:
            self.send('noidle\n')
            self.readresp()  # Consume the response to noidle!
            self.inidle = False
        return was

    def idle(self):
        self.send('idle\n')
        self.inidle = True

    def parsepair(self, line):
        (item, value) = line.split(':', 1)
        return (item.strip(), value.strip())

    def getstatus(self):
        was = self.noidle()
        self.send("status\n")
        self.status = {}
        for l in self.readresp():
            (item, value) = self.parsepair(l)
            try:
                float(value)
            except ValueError:
                value = '"' + value + '"'
            self.status[item] = value
        if was:
            self.idle()

    def docommand(self, command, args=[]):
        was = self.noidle()
        self.send((command + ' ' + ' '.join(args)).strip() + '\n')
        self.readresp()
        self.getstatus()
        self.getplaylistinfo()
        if was:
            self.idle()

    def getplaylistinfo(self):
        was = self.noidle()
        self.send("playlistinfo\n")
        # We get back a set of file/title/Pos/ID/Name lines.
        playlist = []
        for line in self.readresp():
            (item, value) = self.parsepair(line)
            if item == 'file':
                playlist.append(Station(value))
            elif item == 'Name':
                playlist[-1].name = value
            elif item == 'Pos':
                playlist[-1].pos = int(value)
            elif item == 'Title':
                playlist[-1].title = value
        self.playlist = playlist
        try:
            self.current = repr(self.playlist[int(self.status['song'])])
        except KeyError:
            self.current = ''  # For example, if we're stopped.
        if was:
            self.idle()

    def update(self):
        self.getstatus()
        self.getplaylistinfo()


    def handleidleresp(self, sock):
        self.inidle = False
        updates = {}
        for line in self.readresp():
            updates[self.parsepair(line)[1]] = True
        if 'player' in updates:
            self.getstatus()
        if 'playlist' in updates:
            self.getstatus()
            self.getplaylistinfo()
        ControlSocket.broadcast()
        self.idle()


class Station:
    stations = {}
    def __init__(self, url):
        self.url = url
        self.name = ''
        self.pos = None
        self.title = ''
        self.stations[url] = self

    def __repr__(self):
        return '{"url":"%s",\n"name":"%s",\n"title":"%s"}' % (self.url, self.name, self.title) 
  
    @classmethod
    def find(self, url):
        if url in self.stations:
            return self.stations[url]
        else:
            return self.__init__(url)

    def setname(self, name):
        self.name = name

    def settitle(self, title):
        self.title = title

class ControlSocket(mysocket):
    allsocks = []
    """ Used for connections to control this program.  It's OK if the socket goes away. """

    @classmethod
    def broadcast(self):
        info = repr(mpdcontroller)
        for s in self.allsocks:
            s.send(info+'\n')

    def __init__(self, socket):
        super(self.__class__, self).__init__(sock=socket, reader=self.handlecommand)
        self.allsocks.append(self)

    def remove(self):
        if self in self.allsocks:
            self.allsocks.remove(self)

    def send(self, str):
        try:
            super(self.__class__, self).send(str)
        except RuntimeError:
            self.finis()

    def readline(self):
        try:
            return super(self.__class__, self).readline()
        except RuntimeError:
            self.finis()
            return ''

    def handlecommand(self, ignore):
        command = self.readline() + ' '
        print "Command: '%s'" % command
        if len(command) == 1:
            self.finis()
            return
        (command, args) = command.split(' ', 1)
        if command in self.cmdtable:
            print 'command found'
            self.cmdtable[command](args)
        info = repr(mpdcontroller)
        self.broadcast()

    # TODO:  Why are these behaving like functions instead of class methods?
    # TODO:  Must be the same reason that I have to put them in the table as "play" rather than self.play, etc.

    def play(args):
        mpdcontroller.docommand('play', args)

    def stop(args):
        mpdcontroller.docommand('stop', args)

    def pause(args):
        mpdcontroller.docommand('pause', args)

    def nextstation(args):
        mpdcontroller.docommand('next', args)

    def prevstation(args):
        mpdcontroller.docommand('previous', args)

    def finis(self):
        delreader(self)
        self.socket.close()
        self.remove()

    cmdtable = {'play': play,
                'stop': stop,
                'pause':pause,
                'next': nextstation,
                'prev': prevstation,
                }



def handle_incoming_connection(s):
    (news, addr) = s.socket.accept()
    mpdcontroller.update()
    mynews = ControlSocket(news)   # Wrap it
    mynews.send(repr(mpdcontroller))
    mynews.send('\n')
    addreader(mynews)   # Should keep it from going away

# Let's create sockets to begin with:
# mpd is the socket we'll use to control mpd
# serv is the socket we'll be pinged on if something exciting happens in the world; we'll create new sockets for it.

mpdcontroller = MPDController()
mpdcontroller.idle()

serv = mysocket(reader=handle_incoming_connection)
serv.bind(('0.0.0.0', MYPORT))
serv.listen(5)

# Wait for something interesting to happen

finders = {}
readlist = []
writelist = []
readers = []  

def addreader(mysock):
    socket = mysock.socket
    if socket not in readlist:
        readlist.append(socket)
        finders[socket] = mysock
        
def delreader(mysock):
    socket = mysock.socket
    if socket in readlist:
        readlist.remove(socket)
        del finders[socket]

addreader(mpdcontroller.mysock)
addreader(serv)


while 1:
    while not readers:
        (readers, writers, oops) = select.select(readlist, writelist, [], 60)
        if not readers:
            print 'tick'
            continue

    for sock in readers:
        # "sock" is the raw socket; we need our spiffied socket.
        mys = finders[sock]
        if mys.reader:
           mys.reader(mys)
        readers.remove(sock)
   
    status = time.asctime() + '\n' + repr(mpdcontroller) + '\n'
    print status
    with open('status.txt', 'w') as outfile:
	outfile.write(status)
    sys.stdout.flush()
        



			
