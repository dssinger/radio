#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Player: the all-singing, all-dancing Raspberry Pi MPD client """

import socket
import select


class mysock:

    """ Wraps a raw socket with convenience buffering functions """

    def __init__(self, sock=None, reader=None):
        if sock is None:
            self.sock = socket.socket(socket.AF_INET,
                    socket.SOCK_STREAM)
        else:
            self.sock = sock
        self.recvbuf = ''
        self.reader = reader

   

    def connect(self, otherend):
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.connect(otherend)
        self.sock.setblocking(0)  # So we can wait for idles....

    def bind(self, otherend):
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(otherend)
        self.sock.setblocking(0)  # So we can wait for idles....

    def listen(self, count):
        self.sock.listen(count)

    def send(self, msg):
        totalsent = 0
        msglen = len(msg)
        while totalsent < msglen:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError('socket connection broken')
            totalsent += sent

    def readline(self):
        """ Receives one line at a time """

        while '\n' not in self.recvbuf:
            chunk = self.sock.recv(2048)
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


class mpdsock(mysock):

    def readresp(self):
        """ Reads lines until "OK" or "ACK"  """

        ans = []
        ans.append(self.readline())
        while ans[-1] != '' and ans[-1] != 'OK' \
            and not ans[-1].startswith('ACK '):
            ans.append(self.readline())
        return ans

    def sendcommands(self, clist):
        """ Send a list of commands to the server
          Return all responses in a list """

        res = []
        for c in clist:
            self.send(c.rstrip() + '\n')
            res.append(self.readresp())
        return res

    def idle(self):
        self.send('idle\n')

# Define the handlers for reads.  

def handle_mpd_message(s):
    print 'Incoming from MPD'
    ret = '\n'.join(s.readresp())
    if ret:
        print ret
        s.idle()
    print '--'

def handle_x10_message(s):
    print 'x10: ', s.readline()

def handle_incoming_connection(s):
    print 'incoming'
    s.sock.accept()

# Let's create sockets to begin with:
# mpd is the socket we'll use to control mpd
# serv is the socket we'll be pinged on if something exciting happens in the world; we'll create new sockets for it.
# x10 is the socket to use with mochad

mpd = mpdsock(reader=handle_mpd_message)
mpd.connect(('localhost', 6600))
mpd.readline()  # Throw away the initial 'ok'

for item in mpd.sendcommands(['status', 'playlistinfo']):
    print '\n'.join(item)
    print '======'

mpd.idle()

serv = mysock(reader=handle_incoming_connection)
serv.bind(('localhost', 6601))
serv.listen(5)

x10 = mysock(reader=handle_x10_message)
x10.connect(('localhost', 1099))


# Wait for something interesting to happen

readers = []
writers = []
oops = []
myreadlist = [mpd, serv, x10]
finders = {}
readlist = []
for x in myreadlist:
    finders[x.sock] = x
    readlist.append(x.sock)

writelist = []


while 1:
    while not readers:
        print 'select'
        (readers, writers, oops) = select.select(readlist, writelist,
                [], 20)
        if not readers:
            print 'tick'

    for sock in readers:
        mys = finders[sock]
        if mys.reader:
           mys.reader(mys)
        readers.remove(sock)
        



			
