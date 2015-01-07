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
MYPORT = 6601

class mysocket(object):  # Force to be newstyle

    """ Wraps a raw socket with convenience buffering functions """

    def __init__(self, sock=None, reader=None):
        if sock is None:
            self.socket = socket.socket(socket.AF_INET,
                    socket.SOCK_STREAM)
        else:
            self.socket = sock
        self.recvbuf = ''
        self.reader = reader

    def connect(self, otherend):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.connect(otherend)
        #self.socket.setblocking(0)  # So we can wait for idles....

    def bind(self, otherend):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(otherend)
        #self.socket.setblocking(0)  # So we can wait for idles....

    def listen(self, count):
        self.socket.listen(count)

    def send(self, msg):
        totalsent = 0
        msglen = len(msg)
        while totalsent < msglen:
            sent = self.socket.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError('sending socket connection broken')
            totalsent += sent

    def readline(self):
        """ Receives one line at a time """

        while '\n' not in self.recvbuf:
            try:
                chunk = self.socket.recv(2048)
            except socket.error as err:
                print err
                ret = self.recvbuf
                self.recvbuf = ''
                return ret

            if len(chunk) == 0:
                if self.recvbuf:
                    ret = self.recvbuf
                    self.recvbuf = ''
                    return ret
                else:
                    raise RuntimeError('incoming socket broken')
            self.recvbuf += chunk

     # We have at least one line in the buffer.  Return it.

        (ret, self.recvbuf) = self.recvbuf.split('\n', 1)
        return ret


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
        self.getstatus()
        self.getplaylistinfo()

    def __repr__(self):
        ret = '\n'.join(['%s=%s' % (k, self.status[k]) for k in self.status.keys()])
        ret += '\n' + self.current
        ret += '\n' + 'idle: ' + repr(self.inidle)
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
        self.current = repr(self.playlist[int(self.status['song'])])
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
        self.idle()


class Station:
    stations = {}
    def __init__(self, file):
        self.file = file
        self.name = ''
        self.pos = None
        self.title = ''
        self.stations[file] = self

    def __repr__(self):
        return self.file + '\n  ' + self.name + '\n  ' + self.title
  
    @classmethod
    def find(self, file):
        if file in self.stations:
            return self.stations[file]
        else:
            return self.__init__(file)

    def setname(self, name):
        self.name = name

    def settitle(self, title):
        self.title = title

class ControlSocket(mysocket):
    allsocks = []
    cmdtable = {}
    """ Used for connections to control this program.  It's OK if the socket goes away. """
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
        print "Commnd: %s" % command
        if len(command) == 1:
            self.finis()
            return
        (command, args) = command.split(' ', 1)
        if command in self.cmdtable:
            print 'command found'
            self.cmdtable[command](args)
            info = repr(mpdcontroller)
            for s in self.allsocks:
                s.send(info)
                s.send('\n')

    # TODO:  Why are these behaving like functions instead of class methods?

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

    for sock in readers:
        # "sock" is the raw socket; we need our spiffied socket.
        mys = finders[sock]
        if mys.reader:
           mys.reader(mys)
        readers.remove(sock)
   
    print time.asctime()
    print mpdcontroller
        



			
