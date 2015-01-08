import socket

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


