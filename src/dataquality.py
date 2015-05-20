#!/usr/bin/env python

import requests
import numpy as np
import matplotlib.pyplot as plot
import sys
import simplejson as json
import argparse
from scipy.stats import pearsonr
from collections import OrderedDict

def get_data(filename=None):
    if filename is not None:
        with open(filename, 'r') as f:
            return json.load(f)

if __name__ == '__main__':
    DESCRIPTION = '''
    Plots the data quality tr tagging accuracy
    '''
    argsparser = argparse.ArgumentParser(description=DESCRIPTION)
    argsparser.add_argument('--file', type=str,
            help='File where the data is located, if omitted request to the local Django server will be made')
    args = argsparser.parse_args()

    json = get_data(args.file)
    lsvdata = json['LSV']
    ordered_entries = OrderedDict(sorted(lsvdata.items()))
    years = ordered_entries.keys()
    percentages = map(lambda entry: entry[1]*1.0/entry[0] * 100, ordered_entries.values())

    plot.plot(years, percentages)
    plot.ylabel('TR tagging accuracy (in percentages)')
    plot.xlabel('Years')
    plot.ylim((0, 100))
    plot.show()
