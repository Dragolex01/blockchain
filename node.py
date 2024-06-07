from flask import Flask, request
from json import loads, dumps, JSONDecodeError
from uuid import uuid4
from loguru import logger
from time import time
import requests
from hashlib import sha256
from _thread import start_new_thread
from sys import argv
import blockchain

VERSION = '0.0.1'
ID = str(uuid4())

if len(argv) > 1:
    CONFIG_FILE = argv[1]
else:
    CONFIG_FILE = 'nodeconfig.json'

with open(CONFIG_FILE, 'r') as f:
    CONFIG = loads(f.read())
    f.close()

def saveConfig():
    with open(CONFIG_FILE, 'w') as f:
        f.write(dumps(CONFIG))
        f.close()

IP = 'http://' + CONFIG['host'] + ':' + str(CONFIG['port'])

# message query

class Message:
    def __init__(self, code, data = {}):
        self.id = ID
        self.sender = IP
        self.code = code
        self.data = data
        self.timestamp = int(time())
        self.bounce = 4
    
    def to_json(self):
        return dumps(self.__dict__)
    
    def add_data(self, key, value):
        self.data[key] = value
    
    def get_data(self, key):
        return self.data[key]
    
    @staticmethod
    def from_json(json):
        try:
            m = Message(0)
            m.__dict__ = loads(json)
            return m
        except JSONDecodeError:
            return -1
    
    def hash(self):
        d = self.__dict__
        d['bounce'] = 0
        return sha256(str(d).encode()).hexdigest()
    
    def __eq__(self, other: object) -> bool:
        return self.hash() == other.hash()

class MessageQuery:
    def __init__(self):
        self.query = []
    
    def messages(self):
        while True:
            if len(self.query) == 0:
                yield None
            else:
                yield self.query.pop(0)
    
    def add(self, message: Message):
        if ( 
            (not (message in self.query)) and
            (message.id != ID)
         ):
            self.query.append(message)

# flask server (receive)

msgQuery = MessageQuery()

app = Flask(__name__)

@app.route('/')
@app.route('/index')
def index():
    return 'Blockchain v' + VERSION

@app.route('/message', methods=['POST'])
def message():
    msgQuery.add(Message.from_json(request.data))
    return 'ack'

logger.debug('Starting Flask server...')
start_new_thread(lambda: app.run(CONFIG['host'], CONFIG['port']), ())
logger.debug('Flask server started - ' + 'http://' + str(CONFIG['host']) + ':' + str(CONFIG['port']))

# requests client (send)

def send(ip, message: Message):
    try: 
        requests.post(ip + '/message', json=message.__dict__, timeout=0.5)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        if ip in CONFIG['nodes']:
            logger.error('Node ' + ip + 'timed out. Removing it from list of nodes.')
            CONFIG['nodes'].remove(ip)

def broadcast(message: Message):
    for n in CONFIG['nodes']:
        send(n, message)

# BLOCKCHAIN
bc = blockchain.BlockChain(dbfilename=CONFIG['blockchain_file'])

# initial hello
broadcast(Message('HELLO?'))

# processing messages
def process(message: Message):
    logger.info('Received message: ' + message.code)
    
    # ? = request for something
    # ! = response back, ACK, result

    if message.code == 'HELLO?':
        if message.sender not in CONFIG['nodes']:
            CONFIG['nodes'].append(message.sender)
            logger.info('New node ' + message.sender + 'added.')
            send(message.sender, Message('HELLO!'))
    if message.code == 'HELLO!':
        if message.sender not in CONFIG['nodes']:
            CONFIG['nodes'].append(message.sender)
            logger.info('New node ' + message.sender + 'added.')
    
    if message.code == 'HEIGHT?':
        send(message.sender, Message('HEIGHT', {'height': bc.length()}))
    if message.code == 'HEIGHT':
        pass

    if message.code == 'NEW_TRANSACTION':
        pass

    if message.bounce > 0:
        message.bounce -= 1
        broadcast(message)

for m in msgQuery.messages():
    if m:
        process(m)