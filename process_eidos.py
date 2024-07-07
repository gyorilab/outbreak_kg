"""Script to process Eidos outputs."""
import os
import csv
import glob
import json
import tqdm
import itertools
from collections import Counter


def extract_timex_data(timex):
    data = {
        k: v for k, v in timex.items()
        if k not in {'@type', '@id'}
    }
    if 'intervals' in data:
        data['intervals'] = [
            {k: v for k, v in interval.items()
             if k not in {'@type', '@id'}}
            for interval in data['intervals']
        ]
    return data


def extract_geo_data(geo):
    data = {
        k: v for k, v in geo.items()
        if k not in {'@type', '@id'}
    }
    return data


def get_context(jd):
    doc = jd['documents'][0]
    sentences = doc.get('sentences', [])
    all_timexes = []
    all_locs = []
    for sentence in sentences:
        timexes = [extract_timex_data(tx)
                   for tx in sentence.get('timexes', [])]
        locs = [extract_geo_data(gl)
                for gl in sentence.get('geolocs', [])]
        all_timexes += timexes
        all_locs += locs
    return all_locs, all_timexes


if __name__ == '__main__':
    fnames = glob.glob('eidos_output/*.jsonld')
    all_locs = {}
    all_timexes = {}
    for fname in tqdm.tqdm(fnames, desc='Processing Eidos outputs'):
        archive_number = os.path.basename(fname).rstrip('.txt.jsonld')
        with open(fname, 'r') as fh:
            jd = json.load(fh)
            locs, timexes = get_context(jd)
            all_locs[archive_number] = locs
            all_timexes[archive_number] = timexes

    loc_cnt = Counter([(loc['text'], loc.get('geoID'))
                       for loc in itertools.chain.from_iterable(all_locs.values())])
    timex_cnt = Counter([(tx['text'], str([(i['start'], i['end'])
                                        for i in tx.get('intervals', [])])
                          if tx.get('intervals') else '')
                         for tx in itertools.chain.from_iterable(all_timexes.values())])

    # Dump geolocs by alert in a single JSON file
    with open('output/promed_geolocs.json', 'w') as fh:
        json.dump(all_locs, fh, indent=1)

    # Dump timexes by alert in a single JSON file
    with open('output/promed_timexes.json', 'w') as fh:
        json.dump(all_timexes, fh, indent=1)

    # Dump stats into a spreadsheet
    with open('output/promed_geoloc_stats.tsv', 'w') as fh:
        rows = [['text', 'geoid', 'count']]
        # Add a header
        for key, value in sorted(loc_cnt.items(), key=lambda x: x[1], reverse=True):
            rows.append([key[0], key[1], value])
        writer = csv.writer(fh, delimiter='\t')
        writer.writerows(rows)

    with open('output/promed_timex_stats.tsv', 'w') as fh:
        # Add a header
        rows = [['text', 'intervals', 'count']]
        for key, value in sorted(timex_cnt.items(), key=lambda x: x[1], reverse=True):
            rows.append([key[0], key[1], value])
        writer = csv.writer(fh, delimiter='\t')
        writer.writerows(rows)

