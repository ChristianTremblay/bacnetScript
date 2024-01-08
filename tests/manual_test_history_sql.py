import time

import BAC0

bacnet = BAC0.Async()

pcv = BAC0.ADevice("303:12", 5012, bacnet)
for _ in range(4):
    pcv["SUPHTG1-C"] = True
    time.sleep(1)

pcv.backup_histories_df()
