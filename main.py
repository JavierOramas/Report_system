import json
import sys
import os

if __name__ == '__main__':
    config = {}

    with open('config.json', 'r') as file:
        config = json.load(file)

    args = sys.argv

    if len(args) > 1:
        if args[1] == 'install':
            os.system(config['setup'])


