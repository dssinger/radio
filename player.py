#!/usr/bin/python
# -*- coding: utf-8 -*-

""" Player: the all-singing, all-dancing Raspberry Pi MPD client """

import socket
import select


class mysock:

    """ Wraps a raw socket with convenience buffering functions """

    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(socket.AF_INET,
                    socket.SOCK_STREAM)
        else:
            self.sock = sock

        self.recvbuf = ''

    def connect(self, host, port):
        self.sock.connect((host, port))
        self.sock.setblocking(0)  # So we can wait for idles....

    def send(self, msg):
        print 'sending "%s"' % msg
        totalsent = 0
        msglen = len(msg)
        while totalsent < msglen:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError('socket connection broken')
            totalsent += sent
            print 'sent %d bytes, total %d' % (sent, totalsent)

    def readline(self):
        """ Receives one line at a time """

        while '\n' not in self.recvbuf:
            chunk = self.sock.recv(2048)
            if len(chunk) == 0:
                ret = self.recvbuf
                self.recvbuf = ''
                print 'eot'
                return ret
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


# Let's create two sockets to begin with:
# s is the socket we'll use to control mpd
# serv is the socket we'll be pinged on if something exciting happens in the world

s = mpdsock()
s.connect('localhost', 6600)
s.readline()  # Throw away the initial 'ok'

for item in s.sendcommands(['status', 'playlistinfo']):
    print '\n'.join(item)
    print '======'

s.idle()

serv = mysock()

serv.sock.bind(('localhost', 6601))
serv.sock.listen(5)

# Wait for something interesting to happen

readers = []
writers = []
oops = []
readlist = [s.sock, serv.sock]
writelist = []


def handle_mpd_message(s):
    print 'Incoming from MPD'
    ret = '\n'.join(s.readresp())
    if ret:
        print ret
        s.idle()
    print '--'


while 1:
    while not readers:
        print 'select'
        (readers, writers, oops) = select.select(readlist, writelist,
                [], 20)
        if not readers:
            print 'tick'

    print len(readers), 'available to read'

    if s.sock in readers:
        handle_mpd_message(s)
        readers.remove(s.sock)

    if serv.sock in readers:
        print 'incoming connection'
        readers.remove(serv.sock)
        serv.sock.accept()


			
