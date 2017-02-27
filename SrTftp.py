#!/usr/bin/env python
import socket, sys, struct as st, threading

MAX = 65536
block = 0
opt = "Windowsize"
blocks = "16"
fmt = "!H"

class ThreadClient(threading.Thread):
    def __init__(self, f, msg, addr, blocks, MAX):
        threading.Thread.__init__(self)
        self.f = f
        self.msg = msg
        self.addr = addr
        self.MAX = MAX
        self.block = 0
        self.Q = []
        self.opt = "Windowsize"
        self.fileEmp = False
        self.fmt = "!H"
        self.first = 0
        self.last = 0
        self.blocks = blocks
        self.serwAddr = (addr[0], 0)
        self.lastPacket = 0
        self.lastAccp = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.serwAddr)

    def data(self, msg, nrBlock):
        format = "!HH%ds" % len(msg)
        pak = st.pack(format, 3, nrBlock, msg)
        return pak

    def oack(self, blocks):
        format = "!H%dsc%dsc" % (len(self.opt), len(blocks))
        pak = st.pack(format, 6, self.opt.encode(), b'\0', blocks.encode(), b'\0')
        return pak

    def run(self):
        x = self.msg.split(b'\0')
        propClient = x[4].decode()
        if int(propClient) > int(self.blocks):
            self.blocks = "64"
        else:
            self.blocks = propClient

        oacknw = self.oack(self.blocks)
        self.sock.sendto(oacknw, self.addr)
        while True:
            try:
                msg, addr = self.sock.recvfrom(4096)
                confAck = msg[0:2]
                confAckNr = st.unpack(fmt, confAck)
                self.addr = addr
                if confAckNr[0]==4:
                    for i in range(int(self.blocks)):
                        dataStr = self.f.read1(512)
                        if not dataStr:
                            self.fileEmp = True
                            self.lastPacket = (self.block+i)
                            break
                        self.last = i
                        packet = self.data(dataStr, self.block+i+1)
                        self.Q.append((packet, self.block+i+1))
                        self.sock.sendto(packet, self.addr)
                    break
            except socket.timeout:
                self.sock.sendto(oacknw, self.addr)

        while True:
            try:
                msg, addr = self.sock.recvfrom(4096)
                self.addr = addr
                strAck = msg[2:4]
                nrAck = st.unpack(self.fmt, strAck)
                if nrAck[0]==(self.Q[self.last][1]):
                    self.last = self.first = 0
                    self.block += int(self.blocks)
                    self.block = self.block % self.MAX
                    self.Q = []
                    self.lastAccp = self.block
                    for i in range(int(self.blocks)):
                        dataStr = self.f.read1(512)
                        if not dataStr:
                            self.fileEmp = True
                            self.lastPacket = (self.block+i)%self.MAX
                            break
                        self.last = i
                        packet = self.data(dataStr, (self.block+i+1)%self.MAX)
                        self.Q.append((packet, (self.block+i+1)%self.MAX))
                        self.sock.sendto(packet, self.addr)
                    if not self.Q:
                        break

                else:
                    if self.fileEmp==True and self.lastPacket==nrAck[0]:
                        self.sock.close()
                        self.sock.settimeout(None)
                        break
                    else:
                        if self.first <= self.last:
                            count = self.last - self.first + 1
                        else:
                            count = self.last + int(blocks) - self.first + 1
                        self.lastAccp = nrAck[0]
                        tempFirst = self.first
                        for i in range(count):
                            if self.Q[tempFirst][1]==nrAck[0]:
                                self.first = (tempFirst+1)%int(self.blocks)
                                break
                            tempFirst = (tempFirst + 1) % int(self.blocks)

                        if self.first <= self.last:
                            count = self.last - self.first + 1
                        else:
                            count = self.last + int(blocks) - self.first + 2
                        tempFirst = self.first
                        for i in range(count):
                            self.sock.sendto(self.Q[tempFirst][0], self.addr)
                            tempFirst = (tempFirst + 1) % int(self.blocks)

                        self.block = (self.block+(int(self.blocks)-count))%self.MAX
                        maxPacket = self.Q[self.last][1]
                        for i in range(int(self.blocks)-count):
                            dataStr = self.f.read1(512)
                            if not dataStr:
                                self.fileEmp = True
                                self.lastPacket = (maxPacket + i)%self.MAX
                                break
                            self.last = (self.last+1)%int(self.blocks)
                            packet = self.data(dataStr, (maxPacket + i + 1)%self.MAX)
                            self.Q[self.last] = (packet, (maxPacket+i+1)%self.MAX)
                            self.sock.sendto(packet, self.addr)
            except socket.timeout as e:
                if self.fileEmp == True and self.lastPacket == self.lastAccp:
                    self.sock.close()
                    self.sock.settimeout(None)
                    break
                else:
                    temp = self.first
                    for i in range(int(self.blocks)):
                        self.sock.sendto(self.Q[temp][0], self.addr)
                        temp = (self.first+1)%int(self.blocks)

def error(opcode, errorCode):
    if int(errorCode)==1:
        errMsg = "File not found"
    format = "!HH%dsc" % len(errMsg)
    pak = st.pack(format, opcode, errorCode, errMsg.encode(), b'\0')
    return pak

HOST = ''
PORT = int(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))

while True:
    ack, addr = sock.recvfrom(4096)
    cutAck = ack[2:]
    arrAck = cutAck.split(b'\0')
    dir = sys.argv[2][1:]
    path = dir + '/' + arrAck[0].decode()

    try:
        f = open(path, 'rb')
    except:
        print("%s not exists" % arrAck[0].decode())
        errPacket = error(5, 1)
        sock.sendto(errPacket, addr)
        continue

    x = ThreadClient(f, ack, addr, blocks, MAX)
    x.start()
    continue
