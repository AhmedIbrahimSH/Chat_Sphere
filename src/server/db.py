import logging
from pymongo import MongoClient


logging.basicConfig(filename='src/log/db.log', level=logging.INFO)
class DB:
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        # self.client['p2p-chat'].command("dropDatabase") # cleaning database
        # self.client['rooms'].command("dropDatabase")    # cleaning database
        self.client['p2p-chat'].online_peers.drop()     # cleaning collection
         
        self.db = self.client['p2p-chat']               # users database
        self.chat_rooms = self.client['rooms']          # chat rooms database

        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    ############################
    ##### Users functions ######
    ############################
    def is_account_exist(self, username):
        self.logger.info(f"Checking if account {username} exists")
        return self.db.accounts.count_documents({'username': username}) > 0

    def register(self, username, password):
        self.logger.info(f"Registering account {username}")
        account = {
            "username": username,
            "password": password
        }
        self.db.accounts.insert_one(account)

    def get_password(self, username):
        self.logger.info(f"Getting password for account {username}")
        user_data = self.db.accounts.find_one({"username": username})
        return user_data["password"] if user_data else None

    def is_account_online(self, username):
        self.logger.info(f"Checking if account {username} is online")
        return self.db.online_peers.count_documents({"username": username}) > 0

    def user_login(self, username, ip, TCPport, UDPport):
        self.logger.info(f"Logging in user {username}")
        online_peer = {
            "username": username,
            "ip": ip,
            "port": TCPport,
            "udp_port": UDPport
        }
        self.db.online_peers.insert_one(online_peer)

    def user_logout(self, username):
        self.logger.info(f"Logging out user {username}")
        self.db.online_peers.delete_one({"username": username})

    def get_peer_ip_port(self, username):
        self.logger.info(f"Getting IP and port for peer {username}")
        res = self.db.online_peers.find_one({"username": username})
        return (res["ip"], res["port"]) if res else (None, None)
    
    def get_peer_udp_port(self, username):
        self.logger.info(f"Getting UDP port for peer {username}")
        res = self.db.online_peers.find_one({"username": username})
        return (res['ip'], res["udp_port"]) if res else None
    
    ############################
    ### Chat rooms functions ###
    ############################
    def create_chat_room(self, room_name, owner):
        self.logger.info(f"Creating chat room {room_name}")
        chat_room = {
            "room_name": room_name,
            "owner": owner,
            "members": [owner],
            "messages": []
        }
        self.chat_rooms.chat_rooms.insert_one(chat_room)

    def is_chat_room_exist(self, room_name):
        self.logger.info(f"Checking if chat room {room_name} exists")
        return self.chat_rooms.chat_rooms.count_documents({'room_name': room_name}) > 0
    
    def get_chat_room_owner(self, room_name):
        self.logger.info(f"Getting owner of chat room {room_name}")
        room_data = self.chat_rooms.chat_rooms.find_one({"room_name": room_name})
        return room_data["owner"] if room_data else None

    def get_chat_rooms(self):
        self.logger.info(f"Getting all chat rooms")
        chat_rooms_list = list(self.chat_rooms.chat_rooms.find({}, {"_id": 0, "messages": 0}))
        chat_rooms_names = [room["room_name"] for room in chat_rooms_list]
        return chat_rooms_names

    def get_chat_room_members(self, room_name):
        self.logger.info(f"Getting members of chat room {room_name}")
        room_data = self.chat_rooms.chat_rooms.find_one({"room_name": room_name})
        return room_data["members"] if room_data else None
    
    def get_chat_room_info(self, room_name):
        self.logger.info(f"Getting info of chat room {room_name}")
        room_data = self.chat_rooms.chat_rooms.find_one({"room_name": room_name})
        return room_data if room_data else None

    def get_online_chat_members(self, room_name):
        self.logger.info(f"Getting online members of chat room {room_name}")
        online_members = []
        room_members = self.get_chat_room_members(room_name)
        for member in room_members:
            if self.is_account_online(member):
                online_members.append(self.get_peer_udp_port(member))
        return online_members
    
    def add_chat_room_member(self, room_name, username):
        self.logger.info(f"Adding member {username} to chat room {room_name}")
        self.chat_rooms.chat_rooms.update_one(
            {"room_name": room_name},
            {"$push": {"members": username}}
            )

    def remove_chat_room_member(self, room_name, username):
        self.logger.info(f"Removing member {username} from chat room {room_name}")
        self.chat_rooms.chat_rooms.update_one(
            {"room_name": room_name},
            {"$pull": {"members": username}}
            )

    def add_message_to_chat_room(self, room_name, message):
        self.logger.info(f"Adding message to chat room {room_name}")
        self.chat_rooms.chat_rooms.update_one(
            {"room_name": room_name}, 
            {"$push": {"messages": message}}
            )
    