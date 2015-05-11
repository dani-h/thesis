#!/usr/bin/env python

import __init__
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
    subplot.scatter(x.data, y.data, s=100)
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
    d['defect_density'] = DataEntry('defect_density')
    d['defect_density_abc'] = DataEntry('defect_density_abc')

    for entry in dataset:
        for key in keys:
            d[key].data.append(entry[key])

        defects_abc = entry['defects_a'] + entry['defects_b'] + entry['defects_c']
        defect_density = 0 if entry['nloc'] == 0 else entry['defects'] * 1.0 / entry['nloc']
        defect_density_abc = 0 if entry['nloc'] == 0 else defects_abc * 1.0 / entry['nloc']
        d['defects_abc'].data.append(defects_abc)
        d['defect_density'].data.append(defect_density)
        d['defect_density_abc'].data.append(defect_density_abc)

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
                pearson_dict['value'] = pearsonr(entry_x.data, entry_y.data)[0]
                pearson_dict['label'] = "x: {0:30s} y: {1:30s} Pearson correlation: {2:.2f}".format(
                        entry_x.label, entry_y.label, pearson_dict['value'])
                correlations.append(pearson_dict)

            finished.append(as_set)
    return correlations

if __name__ == '__main__':
    DESCRIPTION = '''
    Script that correlates and plots various contributor and defects data.
    The data is fetched from a local file or from a Django server that serves the data from
        `localhost:8000/contributors_defects_data/`
    It displays plots using matplotlib and calculates the perason correlation using scipy.
    '''

    argsparser = argparse.ArgumentParser(description=DESCRIPTION)
    argsparser.add_argument('--file', type=str,
            help='File where the data is located, if omitted request to the local Django server will be made')
    argsparser.add_argument('--c', type=bool,
            help='Prints the pearson correlation values for all metrics')
    argsparser.add_argument('--p', type=bool,
            help='Plots scatter charts for some of the metrics')

    args = argsparser.parse_args()
    json = get_data(args.file)

    jsonarr_srcfiles = filter(lambda entry: entry['file'].endswith((".cc", ".cpp", ".c", ".sbs")), json)
    jsonarr_handwritten = filter(lambda entry: entry['file'].endswith((".cc", ".cpp", ".c")), json)
    jsonarr_sbs = filter(lambda entry: entry['file'].endswith(".sbs"), json)

    db_metrics = ['contributors_tr', 'contributors_cm', 'defects', 'defects_a', 'defects_b', 'defects_c',
            'defects_improvement', 'nloc', 'cyclomatic_complexity']

    dict_arr_all = create_data_entries(json, db_metrics)
    dict_arr_srcfiles = create_data_entries(jsonarr_srcfiles, db_metrics)
    dict_arr_handwritten = create_data_entries(jsonarr_handwritten, db_metrics)
    dict_arr_sbs = create_data_entries(jsonarr_sbs, db_metrics)

    if args.correlate:
        correlations = correlate_all(dict_arr_srcfiles)
        sorted_correlations = sorted(correlations, key=lambda entry: entry['value'])
        for correlation in sorted_correlations:
            print correlation['label']

    if args.plot:
        plot_new_window(dict_arr_handwritten['nloc'], dict_arr_handwritten['defect_density_abc'])
        plot_new_window(dict_arr_handwritten['contributors_tr'], dict_arr_handwritten['defect_density_abc'])
        plot_new_window(dict_arr_handwritten['contributors_cm'], dict_arr_handwritten['defect_density_abc'])
        plot_new_window(dict_arr_handwritten['nloc'], dict_arr_handwritten['defect_density'])
        plot.show()

