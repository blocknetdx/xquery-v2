#!/usr/bin/env python3

from web3 import Web3
from web3.middleware import geth_poa_middleware

import asyncio
from datetime import datetime
import sys
import json
import argparse
import zmq
import multiprocessing as mp
from multiprocessing import Pipe, Process, Event, Pool

import random
import pickle5 as pickle
import hashlib
import base64
import time
import os

import allRC20

from tqdm.notebook import tqdm
nprocs = mp.cpu_count()
print(f"Number of CPU cores: {nprocs}")

class GlobalVars:
    def __init__(self):
        self.queue = False
        self.running = True
        self.backblock_progress = None
        self.forwardblock_progress = None
        self.token_data_cache = dict()
        self.coin_data_cache = dict()
        self.functions_cache = dict()
        self.contracts_cache = dict()
        self.events_cache = list()

    def return_key(self, key):
        if key == 'queue':
            return self.queue
        elif key == 'running':
            return self.running
        elif key == 'backblock_progress':
            return self.backblock_progress
        elif key == 'forwardblock_progress':
            return self.forwardblock_progress
        elif key == 'token_data_cache':
            return self.token_data_cache
        elif key == 'coin_data_cache':
            return self.coin_data_cache
        elif key == 'functions_cache':
            return self.functions_cache
        elif key == 'contracts_cache':
            return self.contracts_cache
        elif key == 'events_cache':
            return self.events_cache

    def update_key(self, key, value):
        if key == 'queue':
            self.queue = value
        elif key == 'running':
            self.running = value
        elif key == 'backblock_progress':
            self.backblock_progress = value
        elif key == 'forwardblock_progress':
            self.forwardblock_progress = value

    def add_key(self, key, value, value1):
        if key == 'token_data_cache':
            self.token_data_cache[value] = value1
        elif key == 'coin_data_cache':
            self.coin_data_cache[value] = value1
        elif key == 'functions_cache':
            self.functions_cache[value] = value1
        elif key == 'contracts_cache':
            self.contracts_cache[value] = value1
        elif key == 'events_cache':
            self.events_cache.insert(0, value)

    def remove_key(self, key):
        if key == 'token_data_cache' and len(self.token_data_cache.keys())>=100:
            self.token_data_cache.pop(random.choice(self.token_data_cache.keys()))
        elif key == 'coin_data_cache' and len(self.coin_data_cache.keys())>=100:
            self.coin_data_cache.pop(random.choice(self.coin_data_cache.keys()))
        elif key == 'functions_cache' and len(self.functions_cache.keys())>=100:
            self.functions_cache.pop(random.choice(self.functions_cache.keys()))
        elif key == 'contracts_cache' and len(self.contracts_cache.keys())>=100:
            self.contracts_cache.pop(random.choice(self.contracts_cache.keys()))
        elif key == 'events_cache' and len(self.events_cache)>=100:
            self.events_cache.pop()

cwd = os.getcwd()

def load_abi():
    abi_path = os.getcwd()+'/'+os.environ.get('ABI_FILE','RC20.json')
    with open(abi_path) as file:
        abi = json.load(file)
        return abi

def get_topic(name,inputs_type):
    string = f'{name}({",".join(inputs_type)})'
    topic = Web3.keccak(text=string).hex()
    return topic



def get_combo(abi):
    name = abi['name']
    inputs = [x['type'] for x in abi['inputs']]
    return [name, inputs]


def get_dict(abi):
    d = {
    "function":[],
    "event":[]
    }
    for i in abi:
        if 'inputs' in list(i):
            if len(i['inputs'])>0 and i['type'].lower() in ['function','event']:
                name, inputs = get_combo(i)
                topic = get_topic(name, inputs)
                # print(f'{name} {topic}')
                d[i['type']].append({"name":name,"topic":topic})
    for i in list(d):
        if not len(d[i]):
            del d[i]
    return d



##
def split(iter, n):
   k, m = divmod(len(iter), n)
   split_data = [iter[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n)]
   split_data_order_number = [[i, v] for i, v in enumerate(split_data)]
   return split_data_order_number

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

#def event_processor(eventtopics, eventlist, routerAddress, routerABI, ERC20ABI, w3):
def event_processor(eventtopics, eventlist, routerAddress, routerABI, ERC20ABI):
    global_vars = GlobalVars()
    infura_url = 'http://192.168.222.241:8545'
    w3 = Web3(Web3.HTTPProvider(infura_url))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    def timeit(func):
        """
        Decorator for measuring function's running time.
        """
        def measure_time(*args, **kw):
            start_time = time.time()
            result = func(*args, **kw)
            print("Processing time of %s(): %.2f seconds."
                  % (func.__qualname__, time.time() - start_time))
            return result

        return measure_time
#def event_processor(eventtopics, eventlist,routerABI, pangolinabi, erc20abi, RC20ABI):
    # get token details from address
    ##@timeit
    def get_token_data(address, abi):
        if address in global_vars.return_key('coin_data_cache'):
            #print('found in cache')
            return json.loads(pickle.loads(global_vars.return_key('coin_data_cache')[address]))
        else:
            contract = w3.eth.contract(address=Web3.toChecksumAddress(address), abi=abi)
            name = None
            symbol = None
            decimals = None
            try:
                name = contract.functions.name().call()
            except Exception as e:
                pass
            try:
                symbol = contract.functions.symbol().call()
            except Exception as e:
                pass
            try:
                decimals = contract.functions.decimals().call()
            except Exception as e:
                pass
            data = {
                "name": str(name) if name else None,
                "symbol": str(symbol) if symbol else None,
                "decimals": int(decimals) if decimals else None
            }
            global_vars.remove_key('coin_data_cache')
            global_vars.add_key('coin_data_cache', address, pickle.dumps(pickle.PickleBuffer(json.dumps(data,sort_keys=True,ensure_ascii=True).encode('UTF-8')), protocol=5))
            return data

    # get pair details from contract address
    ##@timeit
    def get_tokens_from_caddress(contract_address, abi):
        if contract_address in global_vars.return_key('token_data_cache'):
            #print('found in cache')
            return json.loads(pickle.loads(global_vars.return_key('token_data_cache')[contract_address]))
        else:
            contract = w3.eth.contract(address=Web3.toChecksumAddress(contract_address), abi=abi)
            token0_address = contract.functions.token0().call()
            token1_address = contract.functions.token1().call()
            token0 = self.get_token_data(w3, token0_address, abi)
            token1 = self.get_token_data(w3, token1_address, abi)
            data = {
                'token0': token0,
                'token1': token1
            }
            global_vars.remove_key('token_data_cache')
            global_vars.add_key('token_data_cache', contract_address, pickle.dumps(pickle.PickleBuffer(json.dumps(data,sort_keys=True,ensure_ascii=True).encode('UTF-8')), protocol=5))
            return data

    ##@timeit
    def get_function(event_name, tx, contract_address, abi):
        function = {}
        transaction = w3.eth.get_transaction(tx)
        try:
            pb = contract_address.encode('UTF-8') + json.dumps(abi,sort_keys=True,ensure_ascii=True).encode('UTF-8')
            if pb in global_vars.return_key('functions_cache'):
                contract_router = global_vars.return_key('functions_cache')[pb]
            else:    
                contract_router = w3.eth.contract(address=Web3.toChecksumAddress(contract_address), abi=abi)
                global_vars.remove_key('functions_cache')
                global_vars.add_key('functions_cache',pb,contract_router)

            decoded_input = contract_router.decode_function_input(transaction.input)
            func = decoded_input[0]
            func_data = decoded_input[1]
            function["fn_name"] = func.__dict__['fn_name']
            for k, v in func_data.items():
                if not isinstance(v, list):
                    function[k] = str(v)
                else:
                    function[k] = ','.join(v)
        except Exception as e:
            pass
        return function

    ##@timeit
    def process_event(event, event_name, event_type, contract_address, abi):
        xquery_event = {}
        try:
            pb = contract_address.encode('UTF-8') + json.dumps(abi,sort_keys=True,ensure_ascii=True).encode('UTF-8')
            if pb in global_vars.return_key('contracts_cache'):
                contract = global_vars.return_key('contracts_cache')[pb]
            else:
                contract = w3.eth.contract(address=Web3.toChecksumAddress(contract_address), abi=abi)
                global_vars.remove_key('contracts_cache')
                global_vars.add_key('contracts_cache', pb, contract)

            contract_call = getattr(contract, f'{event_type.lower()}s')
            action_call = getattr(contract_call, event_name.lower().capitalize())
            xquery_event = action_call().processLog(event)
            xquery_event = json.loads(Web3.toJSON(xquery_event))
        except Exception as e:
            pass
        return xquery_event

    ##@timeit
    def process_event_args(xquery_name, xquery_event, contract_address, abi):
        args = {}
        try:
            for arg in list(xquery_event['args']):
                args[arg] = xquery_event['args'][arg]
            del args['args']
        except Exception as e:
            pass
        try:
            if xquery_name == 'Swap':
                tokens = get_tokens_from_caddress(w3, xquery_event['address'], ERC20ABI)
                for key, item in tokens.items():
                    for key1, item1 in item.items():
                        args[f'{key}_{key1}'] = item1
                # check side
                if args['amount0Out'] == 0:
                    args['side'] = 'sell'
                elif args['amount1Out'] == 0:
                    args['side'] = 'buy'
            else:
                token_data = get_token_data(contract_address, ERC20ABI)
                args['token0_name'] = token_data['name']
                args['token0_symbol'] = token_data['symbol']
                args['token0_decimals'] = token_data['decimals']
        except Exception as e:
            pass
        return args



    try:
        #print(len(eventlist))
        print('processor')
        print('process it len : {} {}'.format(len(eventlist),datetime.now()))

        n = 0
        # DICT FOR BLOCKNUMBER AND TIMESTAMP
        blockTime = {}
        for event in eventlist:
        #for event_index, event in enumerate(eventlist):
            #print('LOGINDEX: {} tx_hash: {}'.format(event['logIndex'], event['transactionHash']))
            event_hash = hashlib.sha256(json.dumps(Web3.toJSON(event), sort_keys=True, ensure_ascii=True).encode('UTF-8')).hexdigest()
            if event_hash not in global_vars.return_key('events_cache'):
                global_vars.remove_key('events_cache')
                global_vars.add_key('events_cache', event_hash, None)
                xquery_name = None
                xquery_type = 'Event'
                if 0 == 0:
                    n += 1
                    eventtopic = Web3.toJSON(event['topics'][0])
                    eventtopic = eventtopic.strip('"')
                    topic_time_start = datetime.now()
                    for x in eventtopics:
                        # printtime(x['topic'])
                        if x['topic'] == eventtopic:
                            #print('found: {}'.format(x['name']))
                            # SAVE EVENT NAME
                            xquery_name = x['name']
                    topic_time_stop = datetime.now()
                if xquery_name:
                    address = event['address']
                    blockNumber = event['blockNumber']
                    tx = event.transactionHash.hex()
                    #print(f'{address} {blockNumber} {tx}')

                    # GET AND SAVE TIMESTAMP OF BLOCKNUMBER
                    retries = 0
                    """
                    while blockNumber not in blockTime:
                        try:
                            timestamp = w3.eth.getBlock(blockNumber)
                            if 'timestamp' in timestamp:
                                blockTime[blockNumber] = timestamp['timestamp']
                        except Exception as e:
                            print(e)

                        if retries > 10:
                            break
                        retries += 1
                        time.sleep(0.01)
                    if retries > 10:
                        continue
                    timestamp = blockTime[blockNumber]
                    """
                    timestamp = ""

                    try:
                        # process event
                        #print(f'process event for {tx}')
                        xquery_event = process_event(event, xquery_name, xquery_type, address, ERC20ABI)

                        xquery_event['query_name'] = xquery_name
                        xquery_event['tx_hash'] = tx
                        xquery_event['timestamp'] = timestamp
                        xquery_event['blocknumber'] = int(blockNumber)

                        # process args
                        #print(f'process event args for {tx}')
                        args = process_event_args(xquery_name, xquery_event, address, ERC20ABI)
                        for k, v in args.items():
                            xquery_event[f'{k}'] = v

                        # get function
                        #print(f'process event function for {tx}')
                        function = get_function(xquery_name, tx, address, routerABI)
                        if len(list(function)) == 0:
                            function = get_function(xquery_name, tx, address, ERC20ABI)
                            if len(list(function)) == 0:
                                function = get_function(xquery_name, tx, routerAddress, routerABI)
                        for k, v in function.items():
                            xquery_event[f'{k}'] = v

                        # DONE
                        if 'args' in xquery_event.keys():
                           del xquery_event['args']
                        #print(xquery_event)
                        #print(f'process for {tx} DONE')
                        #print(datetime.now())
                    except Exception as e:
                        print('ERROR: {}'.format(e))

        return xquery_event

    except Exception as e:
        print('ERROR: {}'.format(e))


def splitlist(list_a, chunk_size):

  for i in range(0, len(list_a), chunk_size):
    yield list_a[i:i + chunk_size]

# add your blockchain connection information
infura_url = 'http://192.168.222.241:8545'
try:
    web3 = Web3(Web3.HTTPProvider(infura_url))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
except Exception as e:
    print(e)
    sys.exit(1)


event_filter = web3.eth.filter({'toBlock':'latest'})
#w3 = web3
#abi = load_abi()['abi']
#data = get_dict(abi)

# abi = load_abi()['abi']
pangolinabi = allRC20.pangolinABI['abi']
uniswapabi = allRC20.uniswapv2ABI['abi']
erc20abi = allRC20.ERC20ABI['abi']
# = allRC20.ERC20ABI 
routeraddresspangolin = allRC20.pangolinABI['contractAddress']
routeraddressuniswap = allRC20.uniswapv2ABI['contractAddress']
# data = get_dict(abi)
data = get_dict(erc20abi)
eventtopics = data['event']

print(data['event'])
#print(json.dumps(abi,indent=4))
print('###################')
#print(json.dumps(data, indent=4))
#sys.exit(1)
while True:
    #print('waiting for event')
    eventlist = []
    start_time = datetime.now()
    try:
        for event in event_filter.get_new_entries():
            #print('loading event')
            #print(event['logIndex'], event['transactionHash'])
            #print(json.dumps(Web3.toJSON(event),indent=2))
            eventlist.append(event)
    except Exception as e:
        print(e)
        eventlist = []
    if eventlist:
        #print(eventlist)
        print('event process list_len: {} {}'.format(len(eventlist),datetime.now()))
        print(datetime.now())
        start_time = datetime.now()
        runcpu = int(nprocs) - 2
        runcpu = 28 # testing
        jobs = []
        chunk_list = []
        sub_list = []
        # split value
        splitvalue = int((len(eventlist))/runcpu)

        sub_list = splitlist(eventlist,splitvalue)
        print(splitvalue)
        #chunk_list = chunks(eventlist, runcpu)
        #for chunk in chunk_list:
        #    print(len(chunk))
        """
        for sub in sub_list:
            print('sublist: {}'.format(sub))
            #print(sub)
            j = Process(target=event_processor, args=(sub, ))
            jobs.append(j)
        routeraddresspangolin, pangolinabi, erc20abi, web3,))


        j = Process(target=event_processor, args=(eventtopics, eventlist,routeraddresspangolin, pangolinabi, erc20abi, ))
        jobs.append(j)

        for j in jobs:
            j.start()
            j.join()
        """
        njob = 1
        for sub in sub_list:
            print('running job: {} sub_len: {}'.format(njob, len(sub)))
            njob += 1
            j = Process(target=event_processor, args=(eventtopics, eventlist,routeraddresspangolin, pangolinabi, erc20abi, ))
            jobs.append(j)

        for j in jobs:
            j.start()
            #j.join()
    print('starttime: {}'.format(start_time))
    print('endtime: {}'.format(datetime.now()))
    print('sleeping...')
    time.sleep(0.33)

