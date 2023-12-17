import logging
from pymongo import MongoClient


logging.basicConfig(filename='src/log/db.log', level=logging.INFO)
class DB:
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.client['p2p-chat'].command("dropDatabase")  # replace with your database name 
        
        self.db = self.client['p2p-chat']
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

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

    def user_login(self, username, ip, port):
        self.logger.info(f"Logging in user {username}")
        online_peer = {
            "username": username,
            "ip": ip,
            "port": port
        }
        self.db.online_peers.insert_one(online_peer)

    def user_logout(self, username):
        self.logger.info(f"Logging out user {username}")
        self.db.online_peers.delete_one({"username": username})

    def get_peer_ip_port(self, username):
        self.logger.info(f"Getting IP and port for peer {username}")
        res = self.db.online_peers.find_one({"username": username})
        return (res["ip"], res["port"]) if res else (None, None)