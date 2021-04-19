
from abc import abstractmethod, ABC

class BaseGateway(ABC):
    CLS_ID = 'base'
    
    @abstractmethod
    def get_swap_funding_fee_rate_history(self, symbol):
        """
        获取资金费历史费率接口
        :param symbol: 合约ID，例如 BTC-USD-SWAP(okex), DOTUSD_PERP(binance)
        :return 历史费率，其中 symbol 每个交易所不一样，这里被归一化为统一格式，方便统计，
            USDT本位类似 BTC-USDT, 币本位类似 BTC-USD
        [
            {
            'symbol': 'BTC-USD', 
            'funding_time': Timestamp('2021-03-17 00:00:00.011000+0000', tz='UTC'), 
            'rate': 0.00016828
            }
            , ...
        ]
        """
        pass

    @abstractmethod
    def get_swap_symbols(self):
        """
        获取永续合约ID接口
        :return 合约ID 列表
        ['BTCUSD_PERP', 'ETHUSD_PERP', ... 'BTCUSDT', 'ETHUSDT', ...] (binance)
        """
        pass