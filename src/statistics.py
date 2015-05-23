#!/usr/bin/env python

import requests
import numpy as np
import matplotlib
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


def normalize_json(json_arr, aggregate_func=None):
    keys = json_arr[0]
    values = json_arr[1:len(json_arr)]
    json = []
    for val in values:
        entry = {}
        for idx in range(0, len(keys)):
            entry[keys[idx]] = val[idx]

        if aggregate_func: aggregate_func(entry)
        json.append(entry)
    return json


def aggregate_values(entry):
    entry['defect_density'] = 0
    entry['defect_density_complexity'] = 0
    defects_abc = entry['defects_a'] + entry['defects_b'] + entry['defects_c']
    entry['defects_abc'] = defects_abc

    if entry['nloc'] > 0:
        entry['defect_density'] = (defects_abc * 1.0) / entry['nloc']

    if entry['cyclomatic_complexity'] > 0:
        entry['defect_density_complexity'] = (defects_abc * 1.0) / entry['cyclomatic_complexity']


def plot_new_window(x, y, xlabel='', ylabel='', suptitle='', title=''):
    fig = plot.figure()
    fig.suptitle(suptitle)

    subplot = fig.add_subplot(111)
    subplot.scatter(x, y, s=30)
    subplot.set_xlim(xmin=0)
    subplot.set_ylim(ymin=0)

    subplot.set_title(title)
    subplot.set_xlabel(xlabel)
    subplot.set_ylabel(ylabel)


def create_data_entries(dataset, excluded_keys=None):
    d = {}
    if excluded_keys is None:
        keys = dataset[0].keys()
    else:
        keys = set(dataset[0].keys()) - set(excluded_keys)

    for key in keys:
        d[key] = DataEntry(key)

    for entry in dataset:
        for key in keys:
            d[key].data.append(entry[key])

    return d


def get_data(filename=None):
    if filename:
        with open(filename, 'r') as f:
            return json.load(f)
    else:
        try:
            url = "http://localhost:8000/contributors_defects_data"
            req = requests.get(url)
            return req.json()
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


def pearson_metadata(jsonarr):
    '''
    @Todo: Refactor, written in a hurry

    Correlate:
        x axis nloc
        y axis pearsonnr defects/contributors

    :type jsonarr: []
    '''
    INCR = 10
    sizes = 0
    max_nloc = max(map(lambda entry: entry['nloc'], jsonarr))
    xvals = []
    yvals = []
    while sizes < max_nloc:
        filtered = filter(lambda entry: entry['nloc'] > sizes, jsonarr)
        contributors_arr = map(lambda entry: entry['contributors_tr'], filtered)
        defect_density_arr = map(lambda entry: entry['defect_density'], filtered)
        pearson_val = pearsonr(contributors_arr, defect_density_arr)
        xvals.append(sizes)
        yvals.append(pearson_val[0])
        sizes += INCR

    fig = plot.figure(facecolor='white')
    subplot = fig.add_subplot(111)
    subplot.plot(xvals, yvals)
    subplot.set_title('Pearson metadata')
    subplot.set_xlabel('LOC')
    subplot.set_ylabel('Peason correlation coefficient for defect density/contributors')
    subplot.set_xlim(xmin=0, xmax=15000)
    subplot.set_ylim(ymin=0, ymax=1)
    font = {'size': 22}
    matplotlib.rc('font', **font)
    plot.show()



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
            help='Filter the files to these file extensions. Usage: .c, .cc, cpp, .cxx, .sbs.')
    argsparser.add_argument('-c', action='store_true',
            help='Prints the pearson correlation values for all metrics')
    argsparser.add_argument('-p', action='store_true',
            help='Plots scatter charts for some of the metrics')
    argsparser.add_argument('-metadata', action='store_true',
            help='Plots a chart with pearson metadata')

    args = argsparser.parse_args()
    jsondata_nonformatted = get_data(args.file)
    json = normalize_json(jsondata_nonformatted, aggregate_values)

    if args.filter:
        print "-" * 40
        print "Only using these filetypes", args.filter
        print "-" * 40
        jsonarr = filter(lambda entry: entry['file'].endswith(tuple(args.filter)), json)
    else:
        jsonarr = json

    excluded_keys = ['id', 'file', 'subsystem_id', 'subsystem']
    dict_arr = create_data_entries(jsonarr, excluded_keys)

    if args.c:
        correlations = correlate_all(dict_arr)
        sorted_correlations = sorted(correlations, key=lambda entry: entry['value'])
        for correlation in sorted_correlations:
            print correlation['label']

    if args.p:
        plot_new_window(dict_arr['contributors_cm'].data, dict_arr['defects_abc'].data,
                suptitle="Contributors cm and defects a,b,c")
        plot.show()

    if args.metadata:
        pearson_metadata(jsonarr)

