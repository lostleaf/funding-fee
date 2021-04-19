import sqlite3

import fire
import pandas as pd

from gateway import BinanceGateway, HoubiGateway, OkexGateway
from util import DATABASE_PATH


class FundingFeeTask:
    def save_history(self):
        """
        保存三大交易所历史和当期费率
        """
        fees = []
        for gw_cls in [BinanceGateway, HoubiGateway, OkexGateway]:
            gw = gw_cls()
            df = fetch_funding_fee_history(gw)  # 获取历史资金费
            if gw.CLS_ID == 'binance':  # 对币安特殊处理，获取当期资金费
                df = pd.concat([df, pd.DataFrame(gw.get_swap_recent_fee_rate())])
            df['exchange'] = gw.CLS_ID  # 添加一列，交易所名称
            df.sort_values(
                ['exchange', 'symbol', 'funding_time'], 
                inplace=True, 
                ignore_index=True)
            fees.append(df)
        df_rate = pd.concat(fees)  # 合并所有交易所资金费为一个大表
        df_stat = calc_stat(df_rate)  # 计算统计数据，例如年化， 3日平均， 3日年化等

        # 将时间戳转化为 ISO 字符串，不然 grafana 无法识别
        df_rate['funding_time'] = df_rate['funding_time'].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        df_stat['funding_time'] = df_stat['funding_time'].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # 写入 sqlite，覆盖掉老数据
        with sqlite3.connect(DATABASE_PATH) as conn:
            df_stat.to_sql('funding_fee_stat', conn, index=False, if_exists='replace')
            df_rate.to_sql('funding_fee_rate', conn, index=False, if_exists='replace')

    def update_binance(self):
        """
        更新币安实时费率
        """
        gw = BinanceGateway()

        # 获取实时费率，保存为 DataFrame
        df_recent = pd.DataFrame(gw.get_swap_recent_fee_rate())
        df_recent['exchange'] = gw.CLS_ID

        # 从数据库中获取之前保存的费率
        with sqlite3.connect(DATABASE_PATH) as conn:
            df_rate = pd.read_sql('SELECT * FROM funding_fee_rate', conn)

        # 将时间戳字符串转为 pandas Timestamp 类型
        df_rate['funding_time'] = pd.to_datetime(df_rate['funding_time'], utc=True)

        # 用新费率替换旧费率
        df_rate = pd.concat([df_rate, df_recent])
        df_rate.drop_duplicates(
            ['exchange', 'symbol', 'funding_time'], 
            keep='last', 
            inplace=True)
        df_rate.sort_values(
            ['exchange', 'symbol', 'funding_time'], 
            inplace=True, 
            ignore_index=True)

        # 重新计算统计量
        df_stat = calc_stat(df_rate)

        # 将时间戳转化为 ISO 字符串，不然 grafana 无法识别
        df_rate['funding_time'] = df_rate['funding_time'].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        df_stat['funding_time'] = df_stat['funding_time'].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # 写入 sqlite，覆盖掉老数据
        with sqlite3.connect(DATABASE_PATH) as conn:
            df_stat.to_sql('funding_fee_stat', conn, index=False, if_exists='replace')
            df_rate.to_sql('funding_fee_rate', conn, index=False, if_exists='replace')


def fetch_funding_fee_history(gw):
    """
    对给定交易所，获取历史和当期资金费
    """
    symbols = gw.get_swap_symbols()  # 获取交易所永续合约ID
    data = []
    for symbol in symbols:  # 遍历合约，保存资金费率为 DataFrame
        data.append(pd.DataFrame(gw.get_swap_funding_fee_rate_history(symbol)))
    return pd.concat(data)  # 合成为一个大 DataFrame 表


def calc_stat(df):
    df_stat = df.groupby(['exchange', 'symbol']).agg({
        'funding_time': 'last', 
        'rate': 'last'
    })

    # 计算年化费率的 lambda 函数, 8 小时付息一次，则一年付息 365 * 3 次
    ann_rate = lambda x: (1 + x)**(365 * 3) - 1

    # 计算平均 n 天收益率的 lambda 函数，x 为费率 Series
    avg_rate = lambda n: lambda x: (1 + x.tail(3 * n)).prod()**(1 / 3 / n) - 1

    df_stat['annual'] = ann_rate(df_stat['rate'])  # 当期年化

    # 3日平均与年化
    df_stat['avg_3d'] = df.groupby(['exchange', 'symbol'])['rate'].apply(avg_rate(3))  
    df_stat['annual_3d'] = ann_rate(df_stat['avg_3d'])

    # 7日平均与年化
    df_stat['avg_7d'] = df.groupby(['exchange', 'symbol'])['rate'].apply(avg_rate(7))  
    df_stat['annual_7d'] = ann_rate(df_stat['avg_7d'])

    df_stat.reset_index(inplace=True)

    # symbol 为 -USDT 后缀的为 USDT 本位合约，为 -USD 后缀的为币本位合约
    df_stat['type'] = df_stat['symbol'].str.split('-').str[1]
    df_stat.loc[df_stat['type'] == 'USD', 'type'] = 'Coin'
    return df_stat


if __name__ == '__main__':
    fire.Fire(FundingFeeTask)
