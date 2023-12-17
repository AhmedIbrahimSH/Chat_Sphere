import hashlib


# added by Ahmed Ibrahim and kiro at 17 Dec
# function to hash the password taken by user when creating the account
# the hashing algorithm is sha1
# Create an instance of the HashingUtility class

class HashingUtility:
    def sha1_hash(self, input_string):
        sha1 = hashlib.sha1()
        sha1.update(input_string.encode('utf-8'))
        hashed_string = sha1.hexdigest()
        return hashed_string

