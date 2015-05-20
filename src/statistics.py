#!/usr/bin/env python

import requests
import numpy as np
import matplotlib.pyplot as plot
import sys
import simplejson as json
import argparse
from scipy.stats import pearsonr
from collections import defaultdict


class DataEntry():
    def __init__(self, key):
        self.label = key[0].upper() + key[1:len(key)].replace('_', ' ')
        self.data = []


def normalize_json(json_arr):
    keys = json_arr[0]
    values = json_arr[1:len(json_arr)]
    json = []
    for val in values:
        entry = {}
        for idx in range(0, len(keys)):
            entry[keys[idx]] = val[idx]
        json.append(entry)
    return json


def plot_new_window(x, y, suptitle='', title=''):
    '''
    :type x: DataEntry
    :type y: DataEntry
    '''
    fig = plot.figure()
    fig.suptitle(suptitle)

    subplot = fig.add_subplot(111)
    subplot.scatter(x.data, y.data, s=30)
    subplot.set_xlim(xmin=0)
    subplot.set_ylim(ymin=0)

    subplot.set_title(title)
    subplot.set_xlabel(x.label)
    subplot.set_ylabel(y.label)


def create_data_entries(dataset, keys):
    d = {}
    for key in keys:
        d[key] = DataEntry(key)
    # Additional data we aggregate
    d['defects_abc'] = DataEntry('defects_abc')
    d['defect_density_nloc'] = DataEntry('defect_density_nloc')
    d['defect_density_nloc_abc'] = DataEntry('defect_density_nloc_abc')
    d['defect_density_complexity_abc'] = DataEntry('defect_density_complexity_abc')

    for entry in dataset:
        for key in keys:
            d[key].data.append(entry[key])

        defects_abc = entry['defects_a'] + entry['defects_b'] + entry['defects_c']
        defect_density = 0 if entry['nloc'] == 0 else entry['defects'] * 1.0 / entry['nloc']
        defect_density_abc = 0 if entry['nloc'] == 0 else defects_abc * 1.0 / entry['nloc']
        defect_density_complexity_abc = 0 if entry['cyclomatic_complexity'] == 0 else defects_abc * 1.0 / entry['cyclomatic_complexity']

        d['defects_abc'].data.append(defects_abc)
        d['defect_density_nloc'].data.append(defect_density)
        d['defect_density_nloc_abc'].data.append(defect_density_abc)
        d['defect_density_complexity_abc'].data.append(defect_density_complexity_abc)

    return d

def get_data(filename=None):
    if filename:
        with open(filename, 'r') as f:
            return normalize_json(json.load(f))
    else:
        try:
            url = "http://localhost:8000/contributors_defects_data"
            req = requests.get(url)
            return normalize_json(req.json())
        except:
            print 'Failed to make a request to the local at %s' % (url)
            sys.exit(1)

def correlate_all(data_entries):
    '''
    Returns correlations of all the data entries.
    Filters the correlations so that no duplicates or self correlations exist

    :type data_entries: Dict[str, str]
    '''
    for qq in data_entries:
        pass
    finished = []
    correlations = []
    for entry_y in data_entries.values():
        for entry_x in data_entries.values():
            as_set = {entry_x.label, entry_y.label}
            if as_set not in finished and entry_x != entry_y:
                pearson_dict = {}
                pearson_dict['value'] = pearsonr(entry_x.data, entry_y.data)
                pearson_dict['label'] = "x: {0:30s} y: {1:30s} Pearson correlation: {2:.2f} P value: {3}".format(
                        entry_x.label, entry_y.label, pearson_dict['value'][0], pearson_dict['value'][1])
                correlations.append(pearson_dict)

            finished.append(as_set)
    return correlations

if __name__ == '__main__':
    DESCRIPTION = '''
    Script that correlates and plots various contributor and defects data.
    The data is fetched from a local file or from a Django server that serves the data from
        `localhost:8000/contributors_defects_data/`
    It displays plots using matplotlib and calculates the perason correlation using scipy.

    Tips:
    If trying to quickly find a single corrleation between two metrics pipe the output to grep.
    Example: ./statistics.py --file data.json -c | egrep -i "contributors cm.*defects abc".
    This will case insensitive grep for the line containing both `contributors cm` and `defects abc`.
    '''

    argsparser = argparse.ArgumentParser(description=DESCRIPTION)
    argsparser.add_argument('--file', type=str,
            help='File where the data is located, if omitted request to the local Django server will be made')
    argsparser.add_argument('--filter', nargs="+", type=str,
            help='Filter the files to these file endings. Usage: --filter .a .b .c. Recommended: .c, .cc, cpp, .cxx, .sbs.')
    argsparser.add_argument('-c', action='store_true',
            help='Prints the pearson correlation values for all metrics')
    argsparser.add_argument('-p', action='store_true',
            help='Plots scatter charts for some of the metrics')

    args = argsparser.parse_args()
    json = get_data(args.file)

    if args.filter:
        print "-" * 40
        print "Only using these filetypes", args.filter
        print "-" * 40
        jsonarr = filter(lambda entry: entry['file'].endswith(tuple(args.filter)), json)
    else:
        jsonarr = json

    db_metrics = ['contributors_tr', 'contributors_cm', 'defects', 'defects_a', 'defects_b', 'defects_c',
            'defects_improvement', 'nloc', 'cyclomatic_complexity', 'effective_complexity']

    # Dict of arrays containing values, incl aggregated values not found in the source data
    dict_arr = create_data_entries(jsonarr, db_metrics)

    if args.c:
        correlations = correlate_all(dict_arr)
        sorted_correlations = sorted(correlations, key=lambda entry: entry['value'])
        for correlation in sorted_correlations:
            print correlation['label']

    if args.p:
        plot_new_window(dict_arr['contributors_tr'], dict_arr['defects_abc'],
                suptitle="Contributors TR and defects a,b,c for all files")
        plot.show()

