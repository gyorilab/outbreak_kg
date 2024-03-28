"""Script to process Eidos outputs."""
import csv
import glob
import json
import tqdm
from collections import Counter


def get_context(jd):
    doc = jd['documents'][0]
    sentences = doc.get('sentences', [])
    all_timexes = []
    all_locs = []
    for sentence in sentences:
        timexes = sentence.get('timexes', [])
        locs = sentence.get('geolocs', [])
        all_timexes += timexes
        all_locs += locs
    return all_locs, all_timexes


if __name__ == '__main__':
    fnames = glob.glob('eidos_output/*.jsonld')
    all_locs = []
    all_timexes = []
    for fname in tqdm.tqdm(fnames):
        with open(fname, 'r') as fh:
            jd = json.load(fh)
            locs, timexes = get_context(jd)
            all_locs += locs
            all_timexes += timexes

    loc_cnt = Counter([(loc['text'], loc['geoID']) for loc in all_locs])
    timex_cnt = Counter([(tx['text'], *[(i['start'], i['end'])
                                        for i in tx.get('intervals', [])])
                         for tx in all_timexes])

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
        for key, value in sorted(loc_cnt.items(), key=lambda x: x[1], reverse=True):
            rows.append([key[0], key[1], value])
        writer = csv.writer(fh, delimiter='\t')
        writer.writerows(rows)

