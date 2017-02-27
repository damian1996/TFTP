#!/usr/bin/env python3
import struct as st
import socket, sys, hashlib

MAX = 65536
block = 1
opt = "Windowsize"
brakPliku = False
fmt = "!H"
blocks = "16"
lastAccp = 0
czyZgub = False
eof = False

def messageRRQ(opcode, filename, mode):
    fmt = '!H%dsc%dsc%dsc%dsc' % (len(filename), len(mode), len(opt), len(blocks))
    pak = st.pack(fmt, opcode, filename.encode(), b'\0', mode.encode(), b'\0', opt.encode(), b'\0', blocks.encode(), b'\0')
    return pak

def ack(opcode, nrblock):
    format = "!HH"
    pak = st.pack(format, opcode, nrblock)
    return pak

HOST = sys.argv[1]
PORT = 8989
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.2)

packet = messageRRQ(1, sys.argv[2], 'octet')
ackToServ = packet
sock.sendto(packet, (HOST, PORT))
m = hashlib.md5()

while True:
    try:
        msg, addr = sock.recvfrom(4096)
        PORT = addr[1]
        msgOpt = msg[0:2]
        msgUnPack = st.unpack(fmt, msgOpt)
        if msgUnPack[0]==5:
            brakPliku = True
            break
        else:
            x = msg.split(b'\0')
            blocks = x[2]
            confAck = ack(4, 0)
            sock.sendto(confAck, (HOST, PORT))
            while True:
                try:
                    firstData, addr = sock.recvfrom(4096)
                    PORT = addr[1]
                    break
                except:
                    sock.sendto(confAck, (HOST, PORT))
            break
    except:
        sock.sendto(packet, (HOST, PORT))

counter = 0

if brakPliku == False:
    nrPack = firstData[2:4]
    nrUnPack = st.unpack(fmt, nrPack)
    if (block + counter) % MAX == nrUnPack[0]:
        lastAccp = nrUnPack[0]
        czyZgub = False
        cutMessage = firstData[4:]
        m.update(cutMessage)
        counter += 1
        if (block + counter - 1) == (block + int(blocks) - 1):
            counter = 0
            block = (block + int(blocks)) % MAX
            if (block == 0):
                ackWindow = ack(4, 65535)
            else:
                ackWindow = ack(4, block - 1)
            sock.sendto(ackWindow, (HOST, PORT))
        if len(cutMessage) < 512:
            x = m.hexdigest()
            print(x)
            ackEnd = ack(4, nrUnPack[0])
            sock.sendto(ackEnd, (HOST, PORT))
            block = 0
            counter = 0
            eof = True
    else:
        if czyZgub == False:
            czyZgub = True
            block = lastAccp + 1
            counter = 0
            ackEr = ack(4, lastAccp)
            sock.sendto(ackEr, (HOST, PORT))

while True:
    if brakPliku == True:
        print("File not found")
        break
    elif eof == True:
        break
    try:
        msg, addr = sock.recvfrom(4096)
        PORT = addr[1]
        nrPack = msg[2:4]
        nrUnPack = st.unpack(fmt, nrPack)
        if (block+counter)%MAX==nrUnPack[0]:
            lastAccp = nrUnPack[0]
            czyZgub = False
            cutMessage = msg[4:]
            m.update(cutMessage)
            counter += 1
            if (block+counter-1)==(block+int(blocks)-1):
                counter = 0
                block = (block + int(blocks) )%MAX
                if (block == 0):
                    ackWindow = ack(4, 65535)
                else:
                    ackWindow = ack(4, block-1)
                sock.sendto(ackWindow, (HOST, PORT))
            if len(cutMessage) < 512:
                x = m.hexdigest()
                print(x)
                ackEnd = ack(4, nrUnPack[0])
                sock.sendto(ackEnd, (HOST, PORT))
                block = 0
                counter = 0
                break
        else:
            if czyZgub == False:
                czyZgub = True
                block = (lastAccp + 1)%MAX
                counter = 0
                ackEr = ack(4, lastAccp)
                sock.sendto(ackEr, (HOST, PORT))
            continue
    except:
        czyZgub = True
        block = (lastAccp + 1) % MAX
        counter = 0
        ackEr = ack(4, lastAccp)
        sock.sendto(ackEr, (HOST, PORT))
        continue
