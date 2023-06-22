import web3
import math
import time
import requests

headers = {
    'content-type': 'application/json',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
    }

class Rpc:
    """
    eth rpc方法
    """
    def __init__(self, api='https://goerli.infura.io/v3/', chainid=5, proxies=None, timeout=30):
        self.api = api
        self.chainid = chainid
        self.proxies = proxies
        self.timeout = timeout

    def get_current_block(self):
        """获取最新区块"""
        data = {"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}
        res = requests.post(self.api, json=data, headers=headers, proxies=self.proxies, timeout=self.timeout)
        return res.json()

    def get_block_detail(self, number):
        """获取区块hash"""
        if isinstance(number, int):
            number = hex(number)
        data = {"jsonrpc":"2.0","method":"eth_getBlockByNumber","params":[number,True],"id":1}
        res = requests.post(self.api, json=data, headers=headers, proxies=self.proxies, timeout=self.timeout)
        return res.json()

    def get_transaction(self, txhash):
        """获取的交易详情"""
        data = {"jsonrpc":"2.0","method":"eth_getTransactionByHash","params":[txhash],"id":1}
        res = requests.post(self.api, json=data, headers=headers, proxies=self.proxies, timeout=self.timeout)
        return res.json()

    def get_gas_price(self):
        """获取gasprice"""
        data = {"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}
        res = requests.post(self.api, json=data, headers=headers, proxies=self.proxies, timeout=self.timeout)
        return res.json()

    def get_max_gas_price(self):
        """(base*2 + Priority) * gasLimit"""
        res = self.get_fee_history()
        base = int(res['result']['baseFeePerGas'][-1], 16)
        res = self.get_max_PriorityFeePerGas()
        priority = int(res['result'], 16)
        return base * 2 + priority

    def get_fee_history(self):
        """获取历史gasfee"""
        data = {"jsonrpc":"2.0","method":"eth_feeHistory","params":["0x1", "latest", []],"id":1}
        res = requests.post(self.api, json=data, headers=headers, proxies=self.proxies, timeout=self.timeout)
        return res.json()

    def get_max_PriorityFeePerGas(self):
        """获取Priority"""
        data = {"jsonrpc":"2.0","method":"eth_maxPriorityFeePerGas","params":[],"id":1}
        res = requests.post(self.api, json=data, headers=headers, proxies=self.proxies, timeout=self.timeout)
        return res.json()

    def get_gas_limit(self, from_, to, data):
        """call计算gaslimit"""
        data = {"jsonrpc":"2.0","method":"eth_estimateGas","params":[{"from": from_, "to": to, "data": data}],"id":1}
        res = requests.post(self.api, json=data, headers=headers, proxies=self.proxies, timeout=self.timeout)
        return res.json()

    def get_transaction_count_by_address(self, address):
        data = {"jsonrpc":"2.0","method":"eth_getTransactionCount","params":[address,'latest'],"id":1}
        res = requests.post(self.api, json=data, headers=headers, proxies=self.proxies, timeout=self.timeout)
        return res.json()

    def call(self, to, data):
        data = {"jsonrpc":"2.0","method":"eth_call","params":[{"to": to, "data": data}, "latest"],"id":1}
        res = requests.post(self.api, json=data, headers=headers, proxies=self.proxies, timeout=self.timeout)
        return res.json()

    def send_raw_transaction(self, hex):
        """广播交易"""
        data = {"jsonrpc":"2.0","method":"eth_sendRawTransaction","params":[hex],"id":1}
        res = requests.post(self.api, json=data, headers=headers,  proxies=self.proxies, timeout=self.timeout)
        return res.json()

    def get_balance(self, address):
        """获取余额"""
        data = {"jsonrpc":"2.0","method":"eth_getBalance","params":[address, 'latest'],"id":1}
        res = requests.post(self.api, json=data, headers=headers, proxies=self.proxies, timeout=self.timeout)
        return res.json()#(int(res.json()['result'], 16)) / math.pow(10,18)

    def transfer(self, account, to, amount, gaslimit, **kw):
        amount = int(amount, 16) if isinstance(amount, str) else int(amount)
        gaslimit = int(gaslimit, 16) if not isinstance(gaslimit, int) else gaslimit
        gasprice = int(self.get_gas_price()['result'], 16)
        nonce = int(self.get_transaction_count_by_address(account.address)['result'], 16)
        tx = {'from': account.address, 'value': None,'to': to, 'gas': gaslimit, 'gasPrice': gasprice, 'nonce': nonce, 'chainId': self.chainid}
        if kw:
            tx.update(**kw)
        signed = account.signTransaction(tx)
        return self.send_raw_transaction(signed.rawTransaction.hex())
    
    def transfer_eip1559(self, account, to, amount, gaslimit=410000, priority_fee=None, max_gas_fee=None, **kw):
        """eip 1559发送tx, 更节省gas"""
        amount = int(amount, 16) if isinstance(amount, str) else int(amount)
        gaslimit = int(gaslimit, 16) if not isinstance(gaslimit, int) else gaslimit
        if not priority_fee:
            priority_fee = self.get_max_PriorityFeePerGas()['result']
        priority_fee = int(priority_fee, 16) if not isinstance(priority_fee, int) else priority_fee
        if not max_gas_fee:
            basefee = int(self.get_fee_history()['result']['baseFeePerGas'][-1], 16)
            max_gas_fee = 2 * basefee + priority_fee
        max_gas_fee = int(max_gas_fee, 16) if not isinstance(max_gas_fee, int) else max_gas_fee
        nonce = int(self.get_transaction_count_by_address(account.address)['result'], 16)
        tx = {'from': account.address, 'value': amount,'to': to, 'gas': gaslimit, 'maxPriorityFeePerGas': priority_fee, 'maxFeePerGas': max_gas_fee, 'nonce': nonce, 'chainId': self.chainid}
        if kw:
            tx.update(**kw)
        signed = account.signTransaction(tx)
        return self.send_raw_transaction(signed.rawTransaction.hex())


import math
import time
from web3 import Web3
from rpc import Rpc
import concurrent.futures

web3 = Web3(Web3.HTTPProvider('https://goerli.infura.io/v3/'))

if __name__ == '__main__':
    COIN_DECIMALS = math.pow(10, 18)  # 主币精度
    rpc = Rpc('https://goerli.infura.io/v3/', chainid=5)

    with open("privkey.txt", "r") as f:
        privkeys = f.readlines()

    with open("addr_4.txt", "r") as f:
        addr_4s = f.readlines()

    with open("addrs.txt", "r") as f:
        addrs = f.readlines()

    def send_transaction(privkey, addr_4):
        try:
            account = web3.eth.account.from_key(privkey.strip())
            amount = int(0.010053162085713949 * COIN_DECIMALS)
            uint_0 = hex(amount)[2:].rjust(64, '0')
            method = '0x8ca3bf68'  # 存款方法hash值
            uint_1 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_2 = '000000000000000000000000000000000000000000000000002386f26fc10000'
            uint_3 = '0000000000000000000000000000000000000000000000000000000000000100'
            uint_4 = '0000000000000000000000000000000000000000000000000000000000000140'
            uint_5 = '0000000000000000000000000000000000000000000000000000000000000180'
            uint_6 = '00000000000000000000000000000000000000000000000000000000000003a0'
            addr_7 = addr_4.strip().rjust(64, '0')
            uint_8 = '0000000000000000000000000000000000000000000000000000000000000001'
            uint_9 = '0000000000000000000000000000000000000000000000000000000000000005'
            uint_10 = '6c696e6561000000000000000000000000000000000000000000000000000000'
            uint_11 = '0000000000000000000000000000000000000000000000000000000000000005'
            uint_12 = '6155534443000000000000000000000000000000000000000000000000000000'
            uint_13 = '0000000000000000000000000000000000000000000000000000000000000001'
            uint_14 = '0000000000000000000000000000000000000000000000000000000000000020'
            uint_15 = '0000000000000000000000000000000000000000000000000000000000000002'
            addr_16 = '00000000000000000000000068b3465833fb72a70ecdf485e0e4c7bd8665fc45'
            uint_17 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_18 = '00000000000000000000000000000000000000000000000000000000000000a0'
            uint_19 = '00000000000000000000000000000000000000000000000000000000000001c0'
            uint_20 = '00000000000000000000000000000000000000000000000000000000000000e4'
            uint_21 = '04e45aaf000000000000000000000000b4fbf271143f4fbf7b91a5ded31805e4'
            uint_22 = '2b2208d6000000000000000000000000254d06f33bdc5b8ee05b2ea472107e30'
            uint_23 = '0226659a00000000000000000000000000000000000000000000000000000000'
            uint_24 = '000027100000000000000000000000009beb991eddf92528e6342ec5f7b0846c'
            uint_25 = '24cbab58000000000000000000000000000000000000000000000000002386f2'
            uint_26 = '6fc1000000000000000000000000000000000000000000000000000000000000'
            uint_27 = '000b699d00000000000000000000000000000000000000000000000000000000'
            uint_28 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_29 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_30 = '0000000000000000000000000000000000000000000000000000000000000007'
            uint_31 = '00000000000000000000000000000000000000000000000000000000000000e0'
            uint_32 = '00000000000000000000000000000000000000000000000000000000000001e0'
            uint_33 = '0000000000000000000000000000000000000000000000000000000000000360'
            uint_34 = '0000000000000000000000000000000000000000000000000000000000000580'
            uint_35 = '0000000000000000000000000000000000000000000000000000000000000700'
            uint_36 = '0000000000000000000000000000000000000000000000000000000000000920'
            uint_37 = '0000000000000000000000000000000000000000000000000000000000000a80'
            uint_38 = '0000000000000000000000000000000000000000000000000000000000000003'
            uint_39 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_40 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_41 = '00000000000000000000000000000000000000000000000000000000000000a0'
            uint_42 = '00000000000000000000000000000000000000000000000000000000000000c0'
            uint_43 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_44 = '0000000000000000000000000000000000000000000000000000000000000020'
            addr_45 = '000000000000000000000000254d06f33bdc5b8ee05b2ea472107e300226659a'
            uint_46 = '0000000000000000000000000000000000000000000000000000000000000001'
            addr_47 = '000000000000000000000000254d06f33bdc5b8ee05b2ea472107e300226659a'
            uint_48 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_49 = '00000000000000000000000000000000000000000000000000000000000000a0'
            uint_50 = '0000000000000000000000000000000000000000000000000000000000000120'
            uint_51 = '0000000000000000000000000000000000000000000000000000000000000044'
            uint_52 = '095ea7b30000000000000000000000006aa397cab00a2a40025dbf839a83f16d'
            uint_53 = '5ec7c1eb00000000000000000000000000000000000000000000000000000000'
            uint_54 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_55 = '0000000000000000000000000000000000000000000000000000000000000040'
            addr_56 = '000000000000000000000000254d06f33bdc5b8ee05b2ea472107e300226659a'
            uint_57 = '0000000000000000000000000000000000000000000000000000000000000001'
            uint_58 = '0000000000000000000000000000000000000000000000000000000000000001'
            addr_59 = '0000000000000000000000006aa397cab00a2a40025dbf839a83f16d5ec7c1eb'
            uint_60 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_61 = '00000000000000000000000000000000000000000000000000000000000000a0'
            uint_62 = '00000000000000000000000000000000000000000000000000000000000001c0'
            uint_63 = '00000000000000000000000000000000000000000000000000000000000000e4'
            uint_64 = '04e45aaf000000000000000000000000254d06f33bdc5b8ee05b2ea472107e30'
            uint_65 = '0226659a000000000000000000000000f56dc6695cf1f5c364edebc7dc7077ac'
            uint_66 = '9b58606800000000000000000000000000000000000000000000000000000000'
            uint_67 = '000001f4000000000000000000000000cc3974741a4506552e6491209bbf84e1'
            uint_68 = '859efe4400000000000000000000000000000000000000000000000000000000'
            uint_69 = '000b7cd400000000000000000000000000000000000000000000000000000000'
            uint_70 = '00169db500000000000000000000000000000000000000000000000000000000'
            uint_71 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_72 = '0000000000000000000000000000000000000000000000000000000000000040'
            addr_73 = '000000000000000000000000254d06f33bdc5b8ee05b2ea472107e300226659a'
            uint_74 = '0000000000000000000000000000000000000000000000000000000000000004'
            uint_75 = '0000000000000000000000000000000000000000000000000000000000000001'
            addr_76 = '000000000000000000000000f56dc6695cf1f5c364edebc7dc7077ac9b586068'
            uint_77 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_78 = '00000000000000000000000000000000000000000000000000000000000000a0'
            uint_79 = '0000000000000000000000000000000000000000000000000000000000000120'
            uint_80 = '0000000000000000000000000000000000000000000000000000000000000044'
            uint_81 = '095ea7b30000000000000000000000006aa397cab00a2a40025dbf839a83f16d'
            uint_82 = '5ec7c1eb00000000000000000000000000000000000000000000000000000000'
            uint_83 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_84 = '0000000000000000000000000000000000000000000000000000000000000040'
            addr_85 = '000000000000000000000000f56dc6695cf1f5c364edebc7dc7077ac9b586068'
            uint_86 = '0000000000000000000000000000000000000000000000000000000000000001'
            uint_87 = '0000000000000000000000000000000000000000000000000000000000000001'
            addr_88 = '0000000000000000000000006aa397cab00a2a40025dbf839a83f16d5ec7c1eb'
            uint_89 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_90 = '00000000000000000000000000000000000000000000000000000000000000a0'
            uint_91 = '00000000000000000000000000000000000000000000000000000000000001c0'
            uint_92 = '00000000000000000000000000000000000000000000000000000000000000e4'
            uint_93 = '04e45aaf000000000000000000000000f56dc6695cf1f5c364edebc7dc7077ac'
            uint_94 = '9b5860680000000000000000000000002c1b868d6596a18e32e61b901e4060c8'
            uint_95 = '72647b6c00000000000000000000000000000000000000000000000000000000'
            uint_96 = '000001f4000000000000000000000000cc3974741a4506552e6491209bbf84e1'
            uint_97 = '859efe4400000000000000000000000000000000000000000000000000000000'
            uint_98 = '0016cf8b00000000000000000000000000000000000000000000000000000065'
            uint_99 = '5ba3e6b400000000000000000000000000000000000000000000000000000000'
            uint_100 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_101 = '0000000000000000000000000000000000000000000000000000000000000040'
            addr_102 = '000000000000000000000000f56dc6695cf1f5c364edebc7dc7077ac9b586068'
            uint_103 = '0000000000000000000000000000000000000000000000000000000000000004'
            uint_104 = '0000000000000000000000000000000000000000000000000000000000000001'
            addr_105 = '0000000000000000000000002c1b868d6596a18e32e61b901e4060c872647b6c'
            uint_106 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_107 = '00000000000000000000000000000000000000000000000000000000000000a0'
            uint_108 = '0000000000000000000000000000000000000000000000000000000000000100'
            uint_109 = '0000000000000000000000000000000000000000000000000000000000000024'
            uint_110 = '2e1a7d4d00000000000000000000000000000000000000000000000000000000'
            uint_111 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_112 = '0000000000000000000000000000000000000000000000000000000000000040'
            addr_113 = '0000000000000000000000002c1b868d6596a18e32e61b901e4060c872647b6c'
            uint_114 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_115 = '0000000000000000000000000000000000000000000000000000000000000002'
            addr_116 = addr_4.strip().rjust(64, '0')
            uint_117 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_118 = '00000000000000000000000000000000000000000000000000000000000000a0'
            uint_119 = '00000000000000000000000000000000000000000000000000000000000000c0'
            uint_120 = '0000000000000000000000000000000000000000000000000000000000000000'
            uint_121 = '0000000000000000000000000000000000000000000000000000000000000000'

            data = method + uint_1 + uint_2 + uint_3 + uint_4 + uint_5 + uint_6 + addr_7 + uint_8 + uint_9 + uin_10 + uint_11 + uint_12 + uint_13 + uint_14 + uint_15 + addr_16 + uint_17 + uint_18 + uint_19 + uint_20 + uint_21 + uint_22 + uint_23 + uint_24 + uint_25 + uint_26 + uint_27 + uint_28 + uint_29 + uint_30 + uint_31 + uint_32 + uint_33 + uint_34 + uint_35 + uint_36 + uint_37 + uint_38 + uint_39 + uint_40 + uint_41 + uint_42 + uint_43 + uint_44 + addr_45 + uint_46 + addr_47 + uint_48 + uint_49 + uint_50 + uint_51 + uint_52 + uint_53 + uint_54 + uint_55 + addr_56 + uint_57 + uint_58 + addr_59 + uint_60 + uint_61 + uint_62 + uint_63 + uint_64 + uint_65 + uint_66 + uint_67 + uint_68 + uint_69 + uint_70 + uint_71 + uint_72 + addr_73 + uint_74 + uint_75 + addr_76 + uint_77 + uint_78 + uint_79 + uint_80 + uint_81 + uint_82 + uint_83 + uint_84 + uint_85 + addr_86 + uint_87 + addr_88 + uint_89 + uint_90 + uint_91 + uint_92 + uint_93 + uint_94 + uint_95 + uint_96 + uint_97 + uint_98 + uint_99 + uint_100 + uint_101 + addr_102 + uint_103 + uint_104 + addr_105 + uint_106 + uint_107 + uint_108 + uint_109 + uint_110 + uint_111 + uint_112 + addr_113 + uint_114 + uint_115 + addr_116 + uint_117 + uint_118 + uint_119 + uint_120 + uint_121


            data = data.lower()
            gaslimit = 410000
            gasPrice = web3.toWei('3', 'gwei')  # 设置gasprice的值，单位为Gwei
            to = '0x9bEb991eDdF92528E6342Ec5f7B0846C24cbaB58'  # linea存款的合约地址
            to = web3.toChecksumAddress(to)
            res = rpc.transfer(account, to, amount, gaslimit, gasPrice=gasPrice, data=data)
            print(res)
        except Exception as e:
                print("An error occurred:", str(e))
    
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(send_transaction, privkeys, addr_4s)

