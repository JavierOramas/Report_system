import math

def round_half_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(int(n)*multiplier + 0.5) / multiplier
