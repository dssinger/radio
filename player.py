#!/usr/bin/python
""" Player: the all-singing, all-dancing Raspberry Pi MPD client """

import socket, select

class mysock:
   """ Wraps a raw socket with convenience buffering functions """
   def __init__(self, sock=None):
      if sock is None:
          self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      else:
          self.sock = sock

      self.recvbuf = ''
     
   def connect(self, host, port):
      self.sock.connect((host, port))
      self.sock.setblocking(0)    # So we can wait for idles....

   def send(self, msg):
      totalsent = 0
      msglen = len(msg)
      while totalsent < msglen:
          sent = self.sock.send(msg[totalsent:])
          if sent == 0:
              raise RuntimeError("socket connection broken")
          totalsent += sent
    
   def readline(self):
     """ Receives one line at a time """
     while '\n' not in self.recvbuf:
          chunk = self.sock.recv(2048)
          if len(chunk) == 0:
              ret = self.recvbuf
              self.recvbuf = ''
              return ret
          self.recvbuf += chunk
     # We have at least one line in the buffer.  Return it.
     (ret, self.recvbuf) = self.recvbuf.split('\n', 1)
     return ret
    

   def readresp(self):
      """ Reads lines until "OK" or "ACK"  """
      ans = []
      ans.append(self.readline())
      while (ans[-1] != '') and (ans[-1] != 'OK') and (not ans[-1].startswith('ACK ')):
          ans.append(self.readline())
      return ans      

def sendcommands(s, clist):
   """ Send a list of commands to the server, finishing with 'idle' 
       Return all responses in a list """
   res = []
   for c in clist:
     s.send(c.rstrip() + '\n')
     res.append(s.readresp())
   s.send('idle\n')
   return res

# Let's create two sockets to begin with:
# s is the socket we'll use to control mpd
# serv is the socket we'll be pinged on if something exciting happens in the world
s = mysock()
s.connect("localhost", 6600)
s.readline()   # Throw away the initial 'ok'

for item in sendcommands(s, ['status', 'playlistinfo']):
    print '\n'.join(item)
    print '======'


serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serv.bind(('localhost', 6601))
serv.listen(5)

# Wait for something interesting to happen
readers = []
writers = []
oops = []

while not readers:
    readers, writers, oops = select.select([s.sock, serv], [], [], 20)
    print 'tick'

if s.sock in readers:
   print 'something from mpd'
   print '\n'.join(s.readresp())

if serv in readers:
   print 'a connection'

