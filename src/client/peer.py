import pickle
from socket import *
import threading
import select
import logging
from .hashing import HashingUtility
from .peerports import ClientPorts
import getpass

CPorts = ClientPorts()

RESET = "\033[0m"
WHITE = "\033[37m"
RED = "\033[31m"
GREEN = "\033[32m"
PURPLE = "\033[95m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
ORANGE = "\033[38;5;208m"
CYAN = "\033[36m"
BRIGHT_BLACK = "\033[90m"
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"


class UDPReceiver(threading.Thread):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(UDPReceiver, cls).__new__(cls)
        return cls._instance

    def __init__(self, peerServerHostname, udpServerPort):
        if not getattr(self, '_initialized', False):
            threading.Thread.__init__(self)
            self.udpServerSocket = socket(AF_INET, SOCK_DGRAM)
            self.udpServerSocket.bind((peerServerHostname, udpServerPort))
            self.unread_messages = []
            self.in_this_room = False
            self.room_name = None
            self.sender_colors = {}
            self.colors = [RED, GREEN, PURPLE, YELLOW, BLUE, ORANGE, CYAN, WHITE, BRIGHT_BLACK, BRIGHT_RED, BRIGHT_GREEN, BRIGHT_YELLOW, BRIGHT_BLUE, BRIGHT_MAGENTA, BRIGHT_CYAN, BRIGHT_WHITE]
            self._initialized = True
            self.stop_flag = False

    def run(self):
        while True:
            if self.stop_flag:
                break
            ready_to_read, _, _ = select.select([self.udpServerSocket], [], [])
            if self.udpServerSocket in ready_to_read:
                response = self.udpServerSocket.recvfrom(1024)
                response = pickle.loads(response[0])
                # Assign a color to the sender if they don't have one yet
                if response["sender"] not in self.sender_colors:
                    self.sender_colors[response["sender"]] = self.colors[len(self.sender_colors) % len(self.colors)]
                color = self.sender_colors[response["sender"]]

                if self.in_this_room and self.room_name:
                    print(color + response["sender"] + RESET + ": " + response["message"])
                else:
                    print('\033[A' + ' ' * len("Enter your choice:") + '\033[A', end='', flush=True)
                    print()
                    print(f"received message from {color}{response['sender']}{RESET} in room {YELLOW}{response['room_name']}{RESET}")
                    self.unread_messages.append(response)
                    self.unread_messages.append("")
                    print("Enter your choice:")
    def stop(self):
        self.stop_flag = True
        self.join()
    
    def print_unread_messages(self):
        for message in self.unread_messages:
            if message["room_name"] == self.room_name:
                color = self.sender_colors[message["sender"]]
                print(f"{color}{message['sender']}{RESET}: {message['message']}")
                self.unread_messages.remove(message)

# Server side of peer
class PeerServer(threading.Thread):


    # Peer server initialization
    def __init__(self, username, peerServerPort, udpServerPort):
        threading.Thread.__init__(self)
       
        self.udp_receiver = None                                    # udp receiver thread

        self.username = username                                    # this peer username
        self.peerServerPort = peerServerPort                        # this peer's server port number
        self.udpServerPort = udpServerPort                          # this peer's server udp port number
        self.tcpServerSocket = socket(AF_INET, SOCK_STREAM)         # this peer's server TCP socket
        
        self.isOnline = True                                        # this is set to false when the user logs out
        #AF_INET is used for IPv4
        self.connectedPeerSocket    = None                          # connected peer socket
        self.connectedPeerIP        = None                          # connected peer's server ip
        self.connectedPeerPort      = None                          # connected peer's server port
        self.chattingClientName     = None                          # connected peer's username
        self.isChatRequested        = 0                             # 0 means not chatting, 1 means chatting
    

    # main method of the peer server thread
    def run(self):
        '''
            gets the ip address of this peer
            first checks to get it for windows devices
            if the device that runs this application is not windows
            it checks to get it for macos devices
            get hostname of localHost --> ex: hostname: mysystem.local 
            ip address of mysystem.local is the user's ip address
        '''
        print("Peer server started...")
        hostname=gethostname()
        try:
            self.peerServerHostname=gethostbyname(hostname)
        except gaierror:
            import netifaces as ni
            #get the ipv4 address of the device --> ip address of the user.
            self.peerServerHostname = ni.ifaddresses('en0')[ni.AF_INET][0]['addr']

        self.udp_receiver = UDPReceiver(self.peerServerHostname, self.udpServerPort)
        self.udp_receiver.start()
        
        # ip address of this peer
        # self.peerServerHostname = 'localhost'
        # socket initializations for the server of the peer
        
        self.tcpServerSocket.bind((self.peerServerHostname, self.peerServerPort))
        # server listens for maximum queue of 4 connections
        self.tcpServerSocket.listen(4)
        # inputs sockets that should be listened
        inputs = [self.tcpServerSocket]
        # server listens as long as there is a socket to listen in the inputs list and the user is online
        while inputs and self.isOnline:
            # monitors for the incoming connections
            try:
                # select functions watches inputs for readable, writable, exceptional conditions and returns 3 lists
                readable, writable, exceptional = select.select(inputs, [], [])
                # If a server waits to be connected enters here
                for s in readable:
                    # if the socket that is receiving the connection is 
                    # the tcp socket of the peer's server, enters here
                    # monitoring our own socket
                    if s is self.tcpServerSocket:
                        # accepts the connection, and adds its connection socket to the inputs list
                        # so that we can monitor that socket as well
                        # connceted is the socket that is connected to this peer's server -> socketObject
                        # addr is the ip address of the peer that is connected to this peer's server -> tuplr
                        connected, addr = s.accept()
                        # sets the socket to non-blocking
                        connected.setblocking(0)
                        inputs.append(connected)
                        # if the user is not chatting, then the ip and the socket of
                        # this peer is assigned to server variables
                        if self.isChatRequested == 0:     
                            print(self.username + " is connected from " + str(addr))
                            self.connectedPeerSocket = connected
                            self.connectedPeerIP = addr[0]
                    # if the socket that receives the data is the one that
                    # is used to communicate with a connected peer, then enters here
                    else:
                        # message is received from connected peer
                        #set buffer size to 1024 then decode the message
                        messageReceived = s.recv(1024).decode()
                        # logs the received message
                        logging.info("Received from " + str(self.connectedPeerIP) + " -> " + str(messageReceived))
                        # if message is a request message it means that this is the receiver side peer server
                        # so evaluate the chat request
                        if len(messageReceived) > 11 and messageReceived[:12] == "CHAT-REQUEST":
                            # text for proper input choices is printed however OK or REJECT is taken as input in main process of the peer
                            # if the socket that we received the data belongs to the peer that we are chatting with,
                            # enters here
                            if s is self.connectedPeerSocket:
                                # parses the message
                                messageReceived = messageReceived.split()
                                # gets the port of the peer that sends the chat request message
                                self.connectedPeerPort = int(messageReceived[1])
                                # gets the username of the peer sends the chat request message
                                self.chattingClientName = messageReceived[2]
                                # prints prompt for the incoming chat request
                                print("Incoming chat request from " + self.chattingClientName + " >> ")
                                print("Enter OK to accept or REJECT to reject:  ")
                                # makes isChatRequested = 1 which means that peer is chatting with someone
                                self.isChatRequested = 1
                            # if the socket that we received the data does not belong to the peer that we are chatting with
                            # and if the user is already chatting with someone else(isChatRequested = 1), then enters here
                            elif s is not self.connectedPeerSocket and self.isChatRequested == 1:
                                # sends a busy message to the peer that sends a chat request when this peer is 
                                # already chatting with someone else
                                message = "BUSY"
                                s.send(message.encode())
                                # remove the peer from the inputs list so that it will not monitor this socket
                                inputs.remove(s)
                        # if an OK message is received then ischatrequested is made 1 and then next messages will be shown to the peer of this server
                        elif messageReceived == "OK":
                            self.isChatRequested = 1
                        # if an REJECT message is received then ischatrequested is made 0 so that it can receive any other chat requests
                        elif messageReceived == "REJECT":
                            self.isChatRequested = 0
                            inputs.remove(s)
                        # if a message is received, and if this is not a quit message ':q' and 
                        # if it is not an empty message, show this message to the user
                        elif messageReceived[:2] != ":q" and len(messageReceived)!= 0:
                            print(YELLOW + self.chattingClientName + RESET + ": " + messageReceived)
                        # if the message received is a quit message ':q',
                        # makes ischatrequested 0 to receive new incoming request messages
                        # removes the socket of the connected peer from the inputs list
                        elif messageReceived[:2] == ":q":
                            self.isChatRequested = 0
                            inputs.clear()
                            inputs.append(self.tcpServerSocket)
                            # connected peer ended the chat
                            if len(messageReceived) == 2:
                                print("User you're chatting with ended the chat")
                                print("Press enter to quit the chat: ")
                        # if the message is an empty one, then it means that the
                        # connected user suddenly ended the chat(an error occurred)
                        elif len(messageReceived) == 0:
                            self.isChatRequested = 0
                            inputs.clear()
                            inputs.append(self.tcpServerSocket)
                            print("User you're chatting with suddenly ended the chat")
                            print("Press enter to quit the chat: ")
            # handles the exceptions, and logs them
            except OSError as oErr:
                logging.error("OSError: {0}".format(oErr))
            except ValueError as vErr:
                logging.error("ValueError: {0}".format(vErr))

# Client side of peer
class PeerClient(threading.Thread):
    def __init__(self, ipToConnect, portToConnect : int, username : str, peerServer : PeerServer, responseReceived : str|None):
        threading.Thread.__init__(self)
        self.username = username                            # this peer's username
        self.tcpClientSocket = socket(AF_INET, SOCK_STREAM) # this peer's client tcp socket
        self.peerServer : PeerServer = peerServer           # this peer's server
        
        self.ipToConnect = ipToConnect                      # other peer's client ip address will connect
        self.portToConnect = portToConnect                  # other peer's client port no. will connect
        
        # phrase in client creation; 
        # if set: client received request; None for requester's client;
        self.responseReceived = responseReceived 
        self.isEndingChat = False                           # this is set to true when the user ends the chat

    # main method of the peer client thread
    def run(self):
        print("Peer client started...")
        # connects to the server of other peer
        self.tcpClientSocket.connect((self.ipToConnect, self.portToConnect))
        
        # if the server of this peer is not connected by someone else and if this is the requester side peer client then enters here
        if self.peerServer.isChatRequested == 0 and self.responseReceived is None:
            # composes a request message and this is sent to server and then this waits a response message from the server this client connects
            requestMessage = "CHAT-REQUEST " + str(self.peerServer.peerServerPort)+ " " + self.username
            # logs the chat request sent to other peer
            logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + requestMessage)
            # sends the chat request
            self.tcpClientSocket.send(requestMessage.encode())
            print("Request message " + requestMessage + " is sent...")
            # received a response from the peer which the request message is sent to
            self.responseReceived = self.tcpClientSocket.recv(1024).decode()
            # logs the received message
            logging.info("Received from " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + self.responseReceived)
            print("Response is " + self.responseReceived)
            # parses the response for the chat request
            self.responseReceived = self.responseReceived.split()
            # if response is ok then incoming messages will be evaluated as client messages and will be sent to the connected server
            if self.responseReceived[0] == "OK":
                # changes the status of this client's server to chatting
                self.peerServer.isChatRequested = 1
                # sets the server variable with the username of the peer that this one is chatting
                self.peerServer.chattingClientName = self.responseReceived[1]
                # as long as the server status is chatting, this client can send messages
                while self.peerServer.isChatRequested == 1:
                    # message input prompt
                    messageSent = input()
                    print('\033[A' + ' ' * len(messageSent) + '\033[A', end='', flush=True)
                    print()
                    # sends the message to the connected peer, and logs it
                    self.tcpClientSocket.send(messageSent.encode())
                    logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + messageSent)
                    # if the quit message is sent, then the server status is changed to not chatting
                    # and this is the side that is ending the chat
                    if messageSent == ":q":
                        self.peerServer.isChatRequested = 0
                        self.isEndingChat = True
                        break
                    if messageSent:
                        print(PURPLE + self.username + RESET + ": " + messageSent)
                # if peer is not chatting, checks if this is not the ending side
                if self.peerServer.isChatRequested == 0:
                    if not self.isEndingChat:
                        # tries to send a quit message to the connected peer
                        # logs the message and handles the exception
                        try:
                            self.tcpClientSocket.send(":q ending-side".encode())
                            logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> :q")
                        except BrokenPipeError as bpErr:
                            logging.error("BrokenPipeError: {0}".format(bpErr))
                    # closes the socket
                    self.responseReceived = None
                    self.tcpClientSocket.close()
            # if the request is rejected, then changes the server status, sends a reject message to the connected peer's server
            # logs the message and then the socket is closed       
            elif self.responseReceived[0] == "REJECT":
                self.peerServer.isChatRequested = 0
                print("client of requester is closing...")
                self.tcpClientSocket.send("REJECT".encode())
                logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> REJECT")
                self.tcpClientSocket.close()
            # if a busy response is received, closes the socket
            elif self.responseReceived[0] == "BUSY":
                print("Receiver peer is busy")
                self.tcpClientSocket.close()
        # if the client is created with OK message it means that this is the client of receiver side peer
        # so it sends an OK message to the requesting side peer server that it connects and then waits for the user inputs.
        elif self.responseReceived == "OK":
            # server status is changed
            self.peerServer.isChatRequested = 1
            # ok response is sent to the requester side
            okMessage = "OK"
            self.tcpClientSocket.send(okMessage.encode())
            logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + okMessage)
            print("Client with OK message is created... and sending messages")
            # client can send messsages as long as the server status is chatting
            while self.peerServer.isChatRequested == 1:
                # input prompt for user to enter message
                messageSent = input()
                print('\033[A' + ' ' * len(messageSent) + '\033[A', end='', flush=True)
                print()
                self.tcpClientSocket.send(messageSent.encode())
                logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> " + messageSent)
                # if a quit message is sent, server status is changed
                if messageSent == ":q":
                    self.peerServer.isChatRequested = 0
                    self.isEndingChat = True
                    break
                if messageSent:
                    print(PURPLE + self.username + RESET + ": " + messageSent)
            # if server is not chatting, and if this is not the ending side
            # sends a quitting message to the server of the other peer
            # then closes the socket
            if self.peerServer.isChatRequested == 0:
                if not self.isEndingChat:
                    self.tcpClientSocket.send(":q ending-side".encode())
                    logging.info("Send to " + self.ipToConnect + ":" + str(self.portToConnect) + " -> :q")
                self.responseReceived = None
                self.tcpClientSocket.close()
                
class PeerClientRoom(threading.Thread):
    def __init__(self, room_name, owner, members, peerServer : PeerServer, mainThread):
        threading.Thread.__init__(self)
        self.room_name = room_name                          # room name  
        self.owner = owner                                  # room owner
        self.members = members                              # this peer's client ip address will connect
        self.online_members = []                            
        self.members_ips = []                               # list of ips of members
        self.udpClientSocket = socket(AF_INET, SOCK_DGRAM)  # this peer's client udp socket
        self.peerServer : PeerServer = peerServer           # this peer's server
        self.mainThread :peerMain = mainThread                        # main thread of the peer
        self.isEndingChat = False                           # this is set to true when the user ends the chat

    # main method of the peer client room thread
    def run(self):
        print("Peer client room started...")
        self.peerServer.udp_receiver.print_unread_messages()
        while not self.isEndingChat:
            # message input prompt
            message = input()
            print('\033[A' + ' ' * len(message) + '\033[A', end='', flush=True)
            print()
            self.online_members = self.mainThread.get_online_members(self.room_name)
            if message == ":q":
                self.isEndingChat = True
                self.peerServer.udp_receiver.in_this_room = False
                self.peerServer.udp_receiver.room_name = None
                break
            if message:
                print(PURPLE + self.mainThread.loginCredentials[0] + RESET + ": " + message)
                messageSent = {
                    "room_name": self.room_name,
                    "sender": self.mainThread.loginCredentials[0],
                    "message": message
                }
                messageSent = pickle.dumps(messageSent)
                for member in self.online_members:
                    member_ip, member_port = member
                    # print(member_ip, member_port, self.peerServer.udpServerPort)
                    if int(member_port) != self.mainThread.udpServerPort:
                        member_port = int(member_port)
                        # Create a new UDP socket for each member
                        sock = socket(AF_INET, SOCK_DGRAM)
                        sock.sendto(messageSent, (member_ip, member_port))
                        sock.close()

# main process of the peer
class peerMain:

    # peer initializations
    def __init__(self):
        while True:
            try:
                self.registryName = input("Enter IP address of registry: ") # ip address of the registry
                #self.registryName = 'localhost'
                self.registryPort = 15600                                   # port number of the registry
                self.tcpClientSocket = socket(AF_INET, SOCK_STREAM)         # tcp socket connection to registry
                self.tcpClientSocket.connect((self.registryName.strip(),self.registryPort)) 
            except ConnectionRefusedError as crErr:
                print("Registry is not online...")
                continue
            except error as err:
                print("can't connect to registry...")
                continue
            break

        self.udpClientSocket = socket(AF_INET, SOCK_DGRAM)          # initializes udp socket which is used to send hello messages
        self.registryUDPPort = 15500                                # udp port of the registry
        
        self.loginCredentials = (None, None)                        # login info of the peer
        self.isOnline = False                                       # online status of the peer
        
        self.peerServerPort = None                                  # server port number of this peer
        self.udpServerPort = None                                   # udp server port number of this peer
        
        self.peerServer = None                                      # server of this peer
        self.peerClient = None                                      # client of this peer
        self.peerClientRoom = None                                  # client of this peer for chat rooms

        self.timer = None                                           # timer for hello messages
        self.__is_logged_in = False                                 # login flag of the peer
        
        choice = "0"
        # log file initialization
        logging.basicConfig(filename="src/log/peer.log", level=logging.INFO)
        # as long as the user is not logged out, asks to select an option in the menu
        while choice != "3":
            # menu selection prompt
            self.__display_main_menu()
            choice = input("Enter your choice: ")
            # Ceate account
            if choice == "1":
                username = input("username: ")
                password = getpass.getpass("password: ")
                hashing_utility = HashingUtility()
                hashed_password = hashing_utility.sha1_hash(password)
                self.createAccount(username, hashed_password)
            # login
            elif choice == "2" and not self.isOnline:
                username = input("username: ")
                password = getpass.getpass("password: ")
                hashing_utility = HashingUtility()
                hashed_password = hashing_utility.sha1_hash(password)

                # asks for the port number for server's tcp socket
                peerServerPort = int(input("Peer server port number:")) #CPorts.get_port()
                udpServerPort = int(input("udp server port number:")) #CPorts.get_port()
                # print("Peer server port number is " + str(peerServerPort))

                status = self.login(username, hashed_password , peerServerPort, udpServerPort)

                # is user logs in successfully, peer variables are set
                if status == 1:

                    self.isOnline = True
                    self.loginCredentials = (username, password)
                    self.peerServerPort = peerServerPort
                    self.udpServerPort = udpServerPort
                    # creates the server thread for this peer, and runs it
                    self.peerServer = PeerServer(self.loginCredentials[0], self.peerServerPort, self.udpServerPort)
                    self.peerServer.start()
                    # hello message is sent to registry
                    self.sendHelloMessage()
            # logged out if logged in
            # and peer variables are set, and server and client sockets are closed
            elif choice == "3" and self.isOnline:
                self.logout(1)
                self.isOnline = False
                self.loginCredentials = (None, None)
                self.peerServer.isOnline = False
                self.peerServer.tcpServerSocket.close()
                self.peerServer.udp_receiver.stop()
                del self.peerServer.udp_receiver
                if self.peerClient is not None:
                    self.peerClient.tcpClientSocket.close()
                del self.peerServer
                print("Logged out successfully")
            # logout
            elif choice == "3":
                self.logout(2)
            # Search user
            elif choice == "4" and self.isOnline:
                username = input("Username to be searched: ")
                searchStatus = self.searchUser(username)
                # if user is found its ip address is shown to user
                if searchStatus is not None and searchStatus != 0:
                    print("IP address of " + username + " is " + searchStatus)
            # Start Chat
            elif choice == "5" and self.isOnline:
                username = input("Enter the username of user to start chat: ")
                searchStatus = self.searchUser(username)
                # if searched user is found, then its ip address and port number is retrieved
                # and a client thread is created
                # main process waits for the client thread to finish its chat
                if searchStatus is not None and searchStatus != 0:
                    searchStatus = searchStatus.split(":")
                    self.peerClient = PeerClient(searchStatus[0], int(searchStatus[1]) , self.loginCredentials[0], self.peerServer, None)
                    self.peerClient.start() # this peer client thread is started
                    self.peerClient.join()  # main process waits for the client thread to finish its chat
            # Create room
            elif choice == "6" and self.isOnline:
                room_name = input("Enter the name of the chat room: ")
                self.create_room(room_name)
            # List rooms
            elif choice == "7" and self.isOnline:
                self.list_rooms()
            # Join room
            elif choice == "8" and self.isOnline:
                room_name = input("Enter the name of the chat room: ")
                self.join_room(room_name)
            # Search room
            elif choice == "9" and self.isOnline:
                room_name = input("Enter the name of the chat room: ")
                roomSearchStatus = self.search_room(room_name)
                if roomSearchStatus is not None:
                    print("Room name: " + roomSearchStatus[0])
                    print("Owner: " + roomSearchStatus[1])
                    print("Members: ")
                    members = roomSearchStatus[2]
                    for member in members:
                        name = member[0]
                        print("\t" + name)
                elif roomSearchStatus is None:
                    print("Room not found")
            # Open chat room
            elif choice == "10" and self.isOnline:
                room_name = input("Enter the name of the chat room: ")
                roomSearchStatus = self.search_room(room_name)
                if roomSearchStatus is not None:
                    room_name = roomSearchStatus[0]
                    owner = roomSearchStatus[1]
                    members = roomSearchStatus[2]
                    members_names = [member[0] for member in members]
                    if self.loginCredentials[0] in members_names:
                        print("entring room ...")
                        self.peerClientRoom = PeerClientRoom(room_name, owner, members, self.peerServer, self)
                        self.peerServer.udp_receiver.in_this_room = True
                        self.peerServer.udp_receiver.room_name = room_name
                        self.peerClientRoom.start()
                        self.peerClientRoom.join()
                    else:
                        print("You are not a member of this chat room")
                elif roomSearchStatus is None:
                    print("Room not found")
            # if this is the receiver side then it will get the prompt to accept an incoming request during the main loop
            # that's why response is evaluated in main process not the server thread even though the prompt is printed by server
            # if the response is ok then a client is created for this peer with the OK message and that's why it will directly
            # sent an OK message to the requesting side peer server and waits for the user input
            # main process waits for the client thread to finish its chat
            elif choice == "OK" and self.isOnline:
                okMessage = "OK " + self.loginCredentials[0]
                logging.info("Send to " + self.peerServer.connectedPeerIP + " -> " + okMessage)
                self.peerServer.connectedPeerSocket.send(okMessage.encode())
                self.peerClient = PeerClient(self.peerServer.connectedPeerIP, self.peerServer.connectedPeerPort , self.loginCredentials[0], self.peerServer, "OK")
                self.peerClient.start()
                self.peerClient.join()
            # if user rejects the chat request then reject message is sent to the requester side
            elif choice == "REJECT" and self.isOnline:
                self.peerServer.connectedPeerSocket.send("REJECT".encode())
                self.peerServer.isChatRequested = 0
                logging.info("Send to " + self.peerServer.connectedPeerIP + " -> REJECT")
            # if choice is cancel timer for hello message is cancelled
            elif choice == "CANCEL":
                self.peerServer.udp_receiver.stop()
                self.timer.cancel()

                break
        # if main process is not ended with cancel selection
        # socket of the client is closed
        if choice != "CANCEL":
            self.tcpClientSocket.close()

    # account creation function
    def createAccount(self, username, password):
        # join message to create an account is composed and sent to registry
        # if response is success then informs the user for account creation
        # if response is exist then informs the user for account existence
        message = {
            "header" : "JOIN",
            "username" : username,
            "password" : password,
        }
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message["header"])
        pickle_message = pickle.dumps(message)
        self.tcpClientSocket.send(pickle_message)
        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        if response == "join-success":
            print("Account created...")
        elif response == "join-exist":
            print("choose another username or login...")

    # login function
    def login(self, username, password, peerServerPort, udpServerPort):
        # a login message is composed and sent to registry
        # an integer is returned according to each response
        message = {
            "header" : "LOGIN",
            "username" : username,
            "password" : password,
            "peerServerPort" : peerServerPort,
            "udpServerPort" : udpServerPort
        }
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message["header"])
        pickle_message = pickle.dumps(message)
        self.tcpClientSocket.send(pickle_message)

        response = self.tcpClientSocket.recv(1024).decode()
        logging.info("Received from " + self.registryName + " -> " + response)
        
        if response == "login-success":
            print(GREEN + "Logged in successfully..." + RESET)
            self.__is_logged_in = True
            return 1
        elif response == "login-account-not-exist":
            print("Account does not exist...")
            self.__is_logged_in = False
            return 0
        elif response == "login-online":
            print(PURPLE + "Account is already online..." + RESET)
            self.__is_logged_in = True
            return 2
        elif response == "login-wrong-password":
            print(RED + "Wrong password..." + RESET)
            self.__is_logged_in = False
            return 3
    
    # logout function
    def logout(self, option):
        # a logout message is composed and sent to registry
        # timer is stopped
        message = {
            "header" : "LOGOUT",
            "username" : None
        }
        if option == 1:
            message['username'] = self.loginCredentials[0]
            self.timer.cancel()
            self.peerServer.udp_receiver.stop()
        self.__is_logged_in = False
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message["header"])
        pickle_message = pickle.dumps(message)
        self.tcpClientSocket.send(pickle_message)
        
    # function for searching an online user
    def searchUser(self, username):
        # a search message is composed and sent to registry
        # custom value is returned according to each response
        # to this search message
        message = {
            "header" : "SEARCH",
            "username" : username
        }
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message["header"])
        pickle_message = pickle.dumps(message)
        self.tcpClientSocket.send(pickle_message)

        response = self.tcpClientSocket.recv(1024).decode().split()
        logging.info("Received from " + self.registryName + " -> " + " ".join(response))
        if response[0] == "search-success":
            print(username + " is found successfully...")
            return response[1]
        elif response[0] == "search-user-not-online":
            print(username + " is not online...")
            return 0
        elif response[0] == "search-user-not-found":
            print(username + " is not found")
            return None
    
    # function for sending hello message
    # a timer thread is used to send hello messages to udp socket of registry
    def sendHelloMessage(self):
        message = "HELLO " + self.loginCredentials[0]
        logging.info("Send to " + self.registryName + ":" + str(self.registryUDPPort) + " -> " + message)
        self.udpClientSocket.sendto(message.encode(), (self.registryName.strip(), self.registryUDPPort))
        self.timer = threading.Timer(1, self.sendHelloMessage)
        self.timer.start()

    def create_room(self, room_name):
        message = {
            "header": "CREATE-ROOM",
            "owner": self.loginCredentials[0],
            "room_name": room_name
        }
        message = "CREATE-ROOM " + room_name + " " + self.loginCredentials[0]
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message['header'])
        self.tcpClientSocket.send(message.encode())

        # Receive the response from the server
        response = self.tcpClientSocket.recv(1024).decode()

        # Handle the response
        if response == "create-room-exist":
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> Chat room already exists")
        elif response == "create-room-success":
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> Chat room created successfully")
        else:
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> Unknown response: " + response)
        
    def join_room(self, room_name):
        message = {
            "header": "JOIN-ROOM",
            "room_name": room_name,
            "username": self.loginCredentials[0]
        }
        message = "JOIN-ROOM " + room_name + " " + self.loginCredentials[0]
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message['header'])
        self.tcpClientSocket.send(message.encode())

        # Receive the response from the server
        response = self.tcpClientSocket.recv(1024).decode()

        # Handle the response
        if response == "join-room-not-exist":
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> Chat room does not exist")
        elif response == "join-room-already-member":
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> You are already a member of this chat room")
        elif response == "join-room-success":
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> Chat room joined successfully")
        else:
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> Unknown response: " + response)

    def list_rooms(self):
        message = {
            "header": "LIST-ROOMS"
        }
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message["header"])
        pickle_message = pickle.dumps(message)
        self.tcpClientSocket.send(pickle_message)
        # Receive the response from the server
        response = self.tcpClientSocket.recv(1024).decode().split(',')
        # Handle the response
        if response[0] == "list-rooms-empty":
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> There are no chat rooms")
        else:
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> " + response[0])
            print("| "+" | ".join(response[1:]) + " |")

    def list_my_rooms(self):
        message = {
            "header": "LIST-MY-ROOMS",
            "username": self.loginCredentials[0]
        }
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message["header"])
        pickle_message = pickle.dumps(message)
        self.tcpClientSocket.send(pickle_message)
        # Receive the response from the server
        response = self.tcpClientSocket.recv(1024).decode().split(',')
        # Handle the response
        if response[0] == "list-my-rooms-empty":
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> You are not a member of any chat room")
        else:
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> " + response[0])
            print("| "+" | ".join(response[1:]) + " |")

    def search_room(self, room_name):
        # Send the message to the server
        message = {
            "header": "SEARCH-ROOM",
            "room_name": room_name
        }
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message["header"])
        pickle_message = pickle.dumps(message)
        self.tcpClientSocket.send(pickle_message)
        
        # Receive the response from the server
        pickle_response = self.tcpClientSocket.recv(1024)
        room_info = pickle.loads(pickle_response)
        if room_info['header'] == "search-room-not-exist":
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> Chat room does not exist")
            return None
        else:
            room_name = room_info['room_name']
            owner = room_info['owner']
            members = room_info['members']
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> Room Name: " + room_name + ", Owner: " + owner)
            return (room_name, owner, members)

    def open_room(self, room_name):
        # Send the message to the server
        message = {
            "header": "OPEN-ROOM",
            "room_name": room_name
        }
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message["header"])
        pickle_message = pickle.dumps(message)
        self.tcpClientSocket.send(pickle_message)
        
        # Receive the response from the server
        pickle_response = self.tcpClientSocket.recv(1024)
        room_info = pickle.loads(pickle_response)
        if room_info is None:
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> Chat room does not exist")
            return None
        else:
            room_name = room_info['room_name']
            owner = room_info['owner']
            members = room_info['members']
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> Room Name: " + room_name + ", Owner: " + owner)
            return (room_name, owner, members)

    def get_online_members(self, room_name):
        # Send the message to the server
        message = {
            "header": "LIST-ONLINE-MEMBER",
            "room_name": room_name
        }
        logging.info("Send to " + self.registryName + ":" + str(self.registryPort) + " -> " + message["header"])
        pickle_message = pickle.dumps(message)
        self.tcpClientSocket.send(pickle_message)
        # Receive the response from the server
        pickle_response = self.tcpClientSocket.recv(1024)
        response:dict = pickle.loads(response)
        # Handle the response
        if response["header"] == "list-online-member-not-exist":
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> There are no online members")
            return None
        elif response["header"] == "list-online-member-success":
            logging.info("Received from " + self.registryName + ":" + str(self.registryPort) + " -> " + response['header'])
            return response["members"]
        
    # function for displaying the main menu
    def __display_main_menu(self):
        if self.__is_logged_in:
            print("3. Logout")
            print("4. Search user")
            print("5. Start a chat")
            print("6. create room")
            print("7. list rooms")
            print("8. join room")
            print("9. search room")
            print("10. open chat room")
            print("")
        else:
            print("1. Create account")
            print("2. Login")

# peer is started
main = peerMain()