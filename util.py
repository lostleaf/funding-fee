import time

EXCHANGE_TIMEOUT = 3000  #3s
DATABASE_PATH = '../crypto_data/crypto.db'  # sqlite数据库路径

def retry_getter(func, retry_times=3, sleep_seconds=1, default=None, raise_err=True):
    for i in range(retry_times):
        try:
            return func()
        except Exception as e:
            print(f'An error occurred {str(e)}')
            if i == retry_times - 1 and raise_err:
                raise e
            time.sleep(sleep_seconds)
    return default