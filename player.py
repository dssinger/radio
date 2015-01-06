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

class mysocket:

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
        self.socket.setblocking(0)  # So we can wait for idles....

    def bind(self, otherend):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(otherend)
        self.socket.setblocking(0)  # So we can wait for idles....

    def listen(self, count):
        self.socket.listen(count)

    def send(self, msg):
        totalsent = 0
        msglen = len(msg)
        while totalsent < msglen:
            sent = self.socket.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError('socket connection broken')
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
        self.send = self.mysock.send   #  Jam in convenience methods
        self.readline = self.mysock.readline   # Jam in convenience methods
        self.inidle = False
        self.mysock.connect(('localhost', 6600))
        self.readline()    # Throw away MPD's welcome message
        self.getstatus()
        self.getplaylistinfo()
        self.getcurrent()

    def __repr__(self):
        ret = '\n'.join(['%s=%s' % (k, self.status[k]) for k in self.status.keys()])
        ret += '\n' + self.current
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
            # print l
            (item, value) = self.parsepair(l)
            self.status[item] = value
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
        if was:
            self.idle()

    def getcurrent(self):
        ix = int(self.status['song'])
        self.current = repr(self.playlist[ix])


    def handleidleresp(self, sock):
        print 'IDLE ended'
        self.inidle = False
        updates = {}
        for line in self.readresp():
            print line
            updates[self.parsepair(line)[1]] = True
        print updates
        if 'player' in updates:
            print 'getting status'
            self.getstatus()
        if 'playlist' in updates:
            print 'getting playlistinfo'
            self.getplaylistinfo()
        print 'Going IDLE'
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

def handle_incoming_connection(s):
    print 'incoming'
    (news, addr) = s.socket.accept()
    news.send('go away')

# Let's create sockets to begin with:
# mpd is the socket we'll use to control mpd
# serv is the socket we'll be pinged on if something exciting happens in the world; we'll create new sockets for it.

mpdcontroller = MPDController()
mpdcontroller.idle()

serv = mysocket(reader=handle_incoming_connection)
serv.bind(('0.0.0.0', MYPORT))
serv.listen(5)

# Wait for something interesting to happen

readers = []
writers = []
oops = []
finders = {}
myreadlist = []  
myreadlist = [mpdcontroller.mysock, serv]
finders = {}
readlist = []
for x in myreadlist:
    finders[x.socket] = x
    readlist.append(x.socket)

writelist = []


while 1:
    while not readers:
        print 'select'
        (readers, writers, oops) = select.select(readlist, writelist, [], 20)
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
        



			
