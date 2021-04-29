import pandas as pd
import requests
from util import retry_getter, EXCHANGE_TIMEOUT

from .base import BaseGateway

TIMEOUT_SECONDS = EXCHANGE_TIMEOUT / 1000  # 毫秒->秒


class HoubiGateway(BaseGateway):
    CLS_ID = 'huobi'

    def get_swap_funding_fee_rate_history(self, symbol):
        data = []
        if symbol.endswith('USDT'):  # USDT本位合约接口
            prefix = 'https://api.hbdm.com/linear-swap-api/v1'
        else:  # 币本位合约接口
            prefix = 'https://api.hbdm.com/swap-api/v1'

        # 火币每次可以请求 50 笔历史费率，循环请求最近 100 笔
        for i in range(1, 3):
            url = f"{prefix}/swap_historical_funding_rate?contract_code={symbol}&page_size=50&page_index={i}"
            resp = retry_getter(lambda: requests.get(url, timeout=TIMEOUT_SECONDS), raise_err=True)
            resp_data = resp.json()
            if 'data' in resp_data and 'data' in resp_data['data']:
                data.extend(resp_data['data']['data'])
        data = [
            {
                'symbol': x['contract_code'],  # 火币合约代码本身满足标准，不需要归一化
                'funding_time': pd.to_datetime(x['funding_time'], unit='ms', utc=True),
                'rate': float(x['realized_rate'])
            } for x in data
        ]

        # 获取当期资金费率
        url = f"{prefix}/swap_funding_rate?contract_code={symbol}"
        resp = retry_getter(lambda: requests.get(url, timeout=TIMEOUT_SECONDS), raise_err=True)
        x = resp.json()['data']
        data.append({
            'symbol': x['contract_code'],
            'funding_time': pd.to_datetime(x['funding_time'], unit='ms', utc=True),
            'rate': float(x['funding_rate'])
        })
        return data

    def get_swap_symbols(self):
        # 获取币本位合约 ID
        url = 'https://api.hbdm.com/swap-api/v1/swap_contract_info'
        resp = retry_getter(lambda: requests.get(url, timeout=TIMEOUT_SECONDS), raise_err=True)
        symbols_coin = [x['contract_code'] for x in resp.json()['data']]

        # 获取 USDT 本位合约 ID
        url = 'https://api.hbdm.com/linear-swap-api/v1/swap_contract_info'
        resp = retry_getter(lambda: requests.get(url, timeout=TIMEOUT_SECONDS), raise_err=True)
        symbols_cash = [x['contract_code'] for x in resp.json()['data']]
        return symbols_coin + symbols_cash
