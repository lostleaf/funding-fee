import ccxt
import pandas as pd
from util import EXCHANGE_TIMEOUT, retry_getter

from .base import BaseGateway


class BinanceGateway(BaseGateway):
    CLS_ID = 'binance'

    def __init__(self, apiKey=None, secret=None):
        self.exg = ccxt.binance({
            'apiKey': apiKey,
            'secret': secret,
            'timeout': EXCHANGE_TIMEOUT,
        })

    def get_swap_funding_fee_rate_history(self, symbol):
        if symbol.endswith('_PERP'):  # 币本位永续合约最近 100 笔历史费率
            data = retry_getter(
              lambda: self.exg.dapiPublic_get_fundingrate({'symbol': symbol}), 
              raise_err=True)
        else:  # USDT 本位永续合约最近 100 笔历史费率
            data = retry_getter(
              lambda: self.exg.fapiPublic_get_fundingrate({'symbol': symbol}), 
              raise_err=True)
        sym_norm = normalize_symbol(symbol)  # 归一化 symbol
        data = [{
            'symbol': sym_norm,
            'funding_time': pd.to_datetime(x['fundingTime'], unit='ms', utc=True),
            'rate': float(x['fundingRate'])
        } for x in data]
        return data

    def get_swap_recent_fee_rate(self):
        # 获取所有币本位合约当期资金费率
        data = retry_getter(self.exg.dapiPublic_get_premiumindex, raise_err=True)
        drates = [{
            'symbol': normalize_symbol(x['symbol']),
            'funding_time': pd.to_datetime(x['nextFundingTime'], unit='ms', utc=True),
            'rate': float(x['lastFundingRate'])
        } for x in data if x['lastFundingRate'] != '']

        # 获取所有 USDT 本位合约当期资金费率
        data = retry_getter(self.exg.fapiPublic_get_premiumindex, raise_err=True)
        frates = [{
            'symbol': normalize_symbol(x['symbol']),
            'funding_time': pd.to_datetime(x['nextFundingTime'], unit='ms', utc=True),
            'rate': float(x['lastFundingRate'])
        } for x in data if x['lastFundingRate'] != '']
        return drates + frates

    def get_swap_symbols(self):
        # 获取币本位合约代码
        data = retry_getter(self.exg.dapiPublic_get_exchangeinfo, raise_err=True)
        # 由于币安永续和交割合约使用同一套 API，这里只保留永续合约
        coin_symbols = [
          x['symbol'] for x in data['symbols'] if x['contractType'] == 'PERPETUAL'
        ]
        
        # 获取 USDT 本位合约代码
        data = retry_getter(self.exg.fapiPublic_get_exchangeinfo, raise_err=True)
        usdt_symbols = [
          x['symbol'] for x in data['symbols'] if x['contractType'] == 'PERPETUAL'
        ]
        return coin_symbols + usdt_symbols


def normalize_symbol(symbol):
    """
    归一化 symbol
    币本位由 BTCUSD_PERP 变为 BTC-USD
    USDT 本位由 BTCUSDT 变为 BTC-USDT
    """
    if symbol.endswith('_PERP'):
        return symbol[:-8] + '-USD'
    return symbol[:-4] + '-USDT'
