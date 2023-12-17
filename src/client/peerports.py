class ClientPorts:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ClientPorts, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self.ports = list(range(15601, 15700))  # predefined range of ports
        self.used_ports = []

    def get_port(self):
        if not self.ports:
            raise Exception("No free ports available")
        port = self.ports.pop(0)  # get and remove the first free port
        self.used_ports.append(port)  # mark the port as used
        return port

    def release_port(self, port):
        if port in self.used_ports:
            self.used_ports.remove(port)  # unmark the port as used
            self.ports.append(port)  # add the port back to the list of free ports