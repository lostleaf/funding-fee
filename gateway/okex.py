import ccxt
import pandas as pd
from util import EXCHANGE_TIMEOUT, retry_getter

from .base import BaseGateway


class OkexGateway(BaseGateway):
    CLS_ID = 'okex'

    def __init__(self, apiKey=None, secret=None, password=None):
        self.exg = ccxt.okex({
            'apiKey': apiKey,
            'secret': secret,
            'password': password,
            'timeout': EXCHANGE_TIMEOUT,
        })
        
    def get_swap_funding_fee_rate_history(self, symbol):
        params = {'instrument_id': symbol}  
        sym_norm = normalize_symbol(symbol)  # 对 symbol 归一化

        # 获取最近 100 笔历史资金费率
        data = retry_getter(
          lambda: self.exg.swap_get_instruments_instrument_id_historical_funding_rate(params),
          raise_err=True)
        data = [{
            'symbol': sym_norm,
            'funding_time': pd.to_datetime(x['funding_time'], utc=True),
            'rate': float(x['realized_rate'])
        } for x in data]

        # 获取当期资金费率
        x = retry_getter(
          lambda: self.exg.swap_get_instruments_instrument_id_funding_time(params), 
          raise_err=True)
        data.append({
            'symbol': sym_norm,
            'funding_time': pd.to_datetime(x['funding_time'], utc=True),
            'rate': float(x['funding_rate'])
        })
        return data

    def get_swap_symbols(self):
        data = retry_getter(self.exg.swap_get_instruments, raise_err=True)
        return [x['instrument_id'] for x in data]

def normalize_symbol(symbol):
    #归一化 symbol, 去掉 -SWAP 后缀
    if symbol.endswith('-SWAP'):
        return symbol[:-5]
    return symbol
