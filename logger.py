import datetime
import pandas as pd

# log function to recieve mutiple arguments
def log(*args):
    with open('log.txt', 'a') as f:
        f.write(f"[{datetime.datetime.now()}] {args}\n")