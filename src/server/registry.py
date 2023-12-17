import sys
from socket import *
from .servers import ClientThread, UDPServer
from .globals import *
import select
import logging

# log file initialization
logging.basicConfig(filename="log/registry.log", level=logging.INFO)
def entry():
    logging.info("Registry started...")
    try:
        # as long as at least a socket exists to listen registry runs
        while INPUTSOCKETS:

            print("Listening for incoming connections...")
            # monitors for the incoming connections
            readable, writable, exceptional = select.select(INPUTSOCKETS, [], [])
            for s in readable:
                # if the message received comes to the tcp socket
                # the connection is accepted and a thread is created for it, and that thread is started
                if s is tcpSocket:
                    tcpClientSocket, addr = tcpSocket.accept()
                    newThread = ClientThread(addr[0], addr[1], tcpClientSocket)
                    newThread.start()
                # if the message received comes to the udp socket
                elif s is udpSocket:
                    s:UDPServer = s
                    # received the incoming udp message and parses it
                    message, clientAddress = s.recvfrom(1024)
                    message = message.decode().split()
                    # checks if it is a hello message
                    if message[0] == "HELLO":
                        # checks if the account that this hello message 
                        # is sent from is online
                        if message[1] in tcpThreads:
                            # resets the timeout for that peer since the hello message is received
                            tcpThreads[message[1]].resetTimeout()
                            print("Hello is received from " + message[1])
                            logging.info("Received from " + clientAddress[0] + ":" + str(clientAddress[1]) + " -> " + " ".join(message))

    except:
        logging.error("Registry crashed")
    finally:
        # registry tcp socket is closed
        tcpSocket.close()
