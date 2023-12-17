from socket import *
from .db import DB

# tcp and udp server port initializations
print("Registy started...")
PORT = 15600
PORTUDP = 15500

# db initialization
db = DB()

# gets the ip address of this peer
# first checks to get it for windows devices
# if the device that runs this application is not windows
# it checks to get it for macos devices
HOSTNAME=gethostname()
try:
    host=gethostbyname(HOSTNAME)
except gaierror:
    import netifaces as ni
    host = ni.ifaddresses('en0')[ni.AF_INET][0]['addr']


print("Registry IP address: " + host)
print("Registry port number: " + str(PORT))

# onlinePeers list for online account
onlinePeers = {}
# accounts list for accounts
accounts = {}
# tcpThreads list for online client's thread
tcpThreads = {}

#tcp and udp socket initializations
tcpSocket = socket(AF_INET, SOCK_STREAM)
udpSocket = socket(AF_INET, SOCK_DGRAM)
tcpSocket.bind((host,PORT))
udpSocket.bind((host,PORTUDP))
tcpSocket.listen(5)

# input sockets that are listened
INPUTSOCKETS = [tcpSocket, udpSocket]
