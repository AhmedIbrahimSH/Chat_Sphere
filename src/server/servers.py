from .globals import *
from socket import *
import threading
import logging
import pickle
from .db import DB



# This class is used to process the peer messages sent to registry
# for each peer connected to registry, a new client thread is created
class ClientThread(threading.Thread):
    # initializations for client thread
    def __init__(self, ip, port, tcpClientSocket):
        threading.Thread.__init__(self)
        # ip of the connected peer
        self.ip = ip
        # port number of the connected peer
        self.port = port
        # socket of the peer
        self.tcpClientSocket:socket = tcpClientSocket
        # username, online status and udp server initializations
        self.username = None
        self.isOnline = True
        self.udpServer = None
        print("New thread started for " + ip + ":" + str(port))

    # main of the thread
    def run(self):
        # locks for thread which will be used for thread synchronization
        self.lock = threading.Lock()
        print("Connection from: " + self.ip + ":" + str(self.port))
        print("IP Connected: " + self.ip)
        
        while True:
            try:
                # waits for incoming messages from peers
                pickle_message = self.tcpClientSocket.recv(1024)
                message:dict = pickle.loads(pickle_message)
                logging.info("Received from " + self.ip + ":" + str(self.port) + " -> " + " ".join(message["header"]))            
                #   JOIN    #
                if message["header"] == "JOIN":
                    # join-exist is sent to peer,
                    # if an account with this username already exists
                    if db.is_account_exist(message["username"]):
                        response = "join-exist"
                        print("From-> " + self.ip + ":" + str(self.port) + " " + response)
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response)  
                        self.tcpClientSocket.send(response.encode())
                    # join-success is sent to peer,
                    # if an account with this username is not exist, and the account is created
                    else:
                        db.register(message["username"], message["password"])
                        response = "join-success"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                #   LOGIN    #
                elif message["header"] == "LOGIN":
                    # login-account-not-exist is sent to peer,
                    # if an account with the username does not exist
                    if not db.is_account_exist(message["username"]):
                        response = "login-account-not-exist"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                    # login-online is sent to peer,
                    # if an account with the username already online
                    elif db.is_account_online(message["username"]):
                        response = "login-online"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                    # login-success is sent to peer,
                    # if an account with the username exists and not online
                    else:
                        # retrieves the account's password, and checks if the one entered by the user is correct
                        retrievedPass = db.get_password(message["username"])
                        # if password is correct, then peer's thread is added to threads list
                        # peer is added to db with its username, port number, and ip address
                        if retrievedPass == message["password"]:
                            self.username = message["username"]
                            self.lock.acquire()
                            try:
                                tcpThreads[self.username] = self
                            finally:
                                self.lock.release()

                            db.user_login(message['username'], self.ip, message['peerServerPort'], message['udpServerPort'])
                            # login-success is sent to peer,
                            # and a udp server thread is created for this peer, and thread is started
                            # timer thread of the udp server is started
                            response = "login-success"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                            
                            self.udpServer = UDPServer(self.username, self.tcpClientSocket)
                            self.udpServer.start()
                            self.udpServer.timer.start()
                        # if password not matches and then login-wrong-password response is sent
                        else:
                            response = "login-wrong-password"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                #   LOGOUT  #
                elif message["header"] == "LOGOUT":
                    # if user is online,
                    # removes the user from onlinePeers list
                    # and removes the thread for this user from tcpThreads
                    # socket is closed and timer thread of the udp for this

                    # user is cancelled
                    if message['username'] is not None and db.is_account_online(message["username"]):
                        db.user_logout(message['username'])
                        self.lock.acquire()
                        try:
                            if message['username'] in tcpThreads:
                                del tcpThreads[message['username']]
                        finally:
                            self.lock.release()
                        print(self.ip + ":" + str(self.port) + " is logged out")
                        self.tcpClientSocket.close()
                        self.udpServer.timer.cancel()
                        break
                    else:
                        self.tcpClientSocket.close()
                        break
                #   SEARCH  #
                elif message["header"] == "SEARCH":
                    # checks if an account with the username exists
                    if db.is_account_exist(message['username']):
                        # checks if the account is online
                        # and sends the related response to peer
                        if db.is_account_online(message['username']):
                            peer_info = db.get_peer_ip_port(message['username'])
                            response = "search-success " + peer_info[0] + ":" + peer_info[1]
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                        else:
                            response = "search-user-not-online"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                    # enters if username does not exist 
                    else:
                        response = "search-user-not-found"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                #   Create-room  #
                elif message["header"] == "CREATE-ROOM":
                    # checks if a chat room with this name already exists
                    if db.is_chat_room_exist(message['room_name']):
                        response = "create-room-exist"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                    # if chat room does not exist, then a new chat room is created
                    else:
                        db.create_chat_room(message['room_name'], message['owner'])
                        response = "create-room-success"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                #   JOIN-ROOM   #
                elif message["header"] == "JOIN-ROOM":
                    # checks if chat room exists
                    if db.is_chat_room_exist(message['room_name']):
                        # checks if peer is already a member of this chat room
                        if message[2] in db.get_chat_room_members(message['room_name']):
                            response = "join-room-already-member"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                        # if peer is not a member of this chat room,
                        # then peer is added to the chat room
                        else:
                            db.add_chat_room_member(message['room_name'], message['username'])
                            response = "join-room-success"
                            logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                            self.tcpClientSocket.send(response.encode())
                    # if chat room does not exist,
                    # then join-room-not-exist response is sent to peer
                    else:
                        response = "join-room-not-exist"
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response) 
                        self.tcpClientSocket.send(response.encode())
                #   LIST-ROOM   #
                elif message["header"] == "LIST-ROOMS":
                    # retrieves the list of chat rooms
                    chat_rooms = db.get_chat_rooms()
                    response = "list-room-success " + ",".join(chat_rooms)
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + "list-room-success") 
                    self.tcpClientSocket.send(response.encode())
                elif message["header"] == "LIST-MY-ROOMS":
                    # retrieve list of chat rooms that the user is a member of
                    chat_rooms = db.get_chat_rooms()
                    my_chat_rooms = []
                    for room in chat_rooms:
                        if message['username'] in db.get_chat_room_members(room):
                            my_chat_rooms.append(room)
                    response = "list-my-room-success " + ",".join(my_chat_rooms)
                    logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + "list-my-room-success")
                    self.tcpClientSocket.send(response.encode())
                #   List-online-member  #
                elif message["header"] == "LIST-ONLINE-MEMBER":
                    # checks if chat room exists
                    if db.is_chat_room_exist(message['room_name']):
                        # retrieves the list of online members of the chat room
                        members = db.get_online_chat_members(message['room_name'])
                        response = {
                            'header': 'list-online-member-success',
                            'members': members
                        }
                        response = pickle.dumps(response)
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + 'list-online-member-success') 
                        self.tcpClientSocket.send(response)
                    # if chat room does not exist,
                    # then list-online-member-not-exist response is sent to peer
                    else:
                        response = {
                            'header': 'room-not-exist',
                        }
                        response = pickle.dumps(response)
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + 'list-online-member-success') 
                        self.tcpClientSocket.send(response)
                #  SEARCH-ROOM  #
                elif message["header"] == "SEARCH-ROOM":
                    # checks if chat room exists
                    if db.is_chat_room_exist(message['room_name']):
                        # Retrieve room information from the database
                        room_info = db.get_chat_room_info(message['room_name'])
                        room_name = room_info['room_name']
                        owner = room_info['owner']
                        # Get IP and port for each member
                        members = room_info['members']
                        members_with_ip = []
                        for member in members:
                            ip_port = db.get_peer_ip_port(member)
                            members_with_ip.append((member, ip_port))
                        # Format the response
                        response = {
                            'header': 'search-room-success', # 'search-room-not-exist
                            'room_name': room_name,
                            'owner': owner,
                            'members': members_with_ip
                        }
                        # Serialize the response
                        serialized_response = pickle.dumps(response)
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + str(response)) 
                        self.tcpClientSocket.send(serialized_response)             
                    # if chat room does not exist,
                    # then search-room-not-exist response is sent to peer
                    else:
                        response = {
                            'header': 'search-room-not-exist',
                        }
                        serialized_response = pickle.dumps(response)
                        logging.info("Send to " + self.ip + ":" + str(self.port) + " -> " + response['header'])
                        self.tcpClientSocket.send(response)

            except OSError as oErr:
                logging.error("OSError: {0}".format(oErr)) 


    # function for resettin the timeout for the udp timer thread
    def resetTimeout(self):
        self.udpServer.resetTimer()

                            
# implementation of the udp server thread for clients
class UDPServer(threading.Thread):


    # udp server thread initializations
    def __init__(self, username, clientSocket):
        threading.Thread.__init__(self)
        self.username = username
        # timer thread for the udp server is initialized
        self.timer = threading.Timer(3, self.waitHelloMessage)
        self.tcpClientSocket = clientSocket
    

    # if hello message is not received before timeout
    # then peer is disconnected
    def waitHelloMessage(self):
        if self.username is not None:
            db.user_logout(self.username)
            if self.username in tcpThreads:
                del tcpThreads[self.username]
        self.tcpClientSocket.close()
        print("Removed " + self.username + " from online peers")


    # resets the timer for udp server
    def resetTimer(self):
        self.timer.cancel()
        self.timer = threading.Timer(5, self.waitHelloMessage)
        self.timer.start()

