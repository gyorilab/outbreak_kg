"""Process ProMed alerts and run named entity recognition."""
import glob
import json
import os
import re
import datetime
from collections import Counter

import tqdm

import gilda
from indra.sources.eidos.cli import extract_from_directory


GILDA_NS = ['MESH', 'EFO', 'HP', 'DOID', 'GO']
EXCLUDE = {'J', 'one', 'news', 'large', 'go', 'cut', 'white', 'Kelly'}


def parse_contents_from_body(body):
    lines = body.split('\n')
    start_alert = False
    contents = []
    try:
        for idx, line in enumerate(lines):
            if line.strip().startswith('---'):
                start_alert = True
                title = lines[idx-1]
                content = []
            elif line.strip() == '--':
                start_alert = False
                contents.append({'title': title,
                                 'content': ' '.join(content)})
            elif start_alert:
                content.append(line.strip())
    except Exception:
        return contents
    return contents


def annotate(txt):
    return gilda.annotate(txt, namespaces=GILDA_NS)


def run_eidos(input_folder, output_folder):
    extract_from_directory(input_folder, output_folder)


def parse_header(header):
    assert len(header) == 1
    header = header[0]
    # Example: Published Date: 2016-04-28 16:59:45 EDT\nSubject: PRO/AH/EDR>
    # Lumpy skin disease - Bulgaria (06): bovine, spread, vaccination\nArchive Number: 20160428.4189378
    # We need to parse out the date, subject and archive number
    date = re.search(r'Published Date: (.+)\n', header)
    subject = re.search(r'Subject:(.+?)\n', header)
    archive = re.search(r'Archive Number: (\d{8}\.\d+)?', header)
    # Now parse the date into a datetime object
    date = date.group(1)
    subject = parse_subject(subject.group(1)) if subject else None
    archive_number = archive.group(1) if archive else None
    # Parse this into a datetime object: 2016-04-28 16:59:45 EDT
    dt_obj = datetime.datetime.strptime(date[:-4], '%Y-%m-%d %H:%M:%S')
    data = {'date': dt_obj,
            'subject': subject,
            'archive_number': archive_number}

    return data


def parse_subject(subject):
    # Example: PRO/AH/EDR> Lumpy skin disease - Bulgaria (06): bovine, spread, vaccination
    # We need to parse out the disease, location, and other details
    # The format is: DISEASE - LOCATION (ID): DETAILS
    # FIXME: this pattern is not reliably preserved so this would need more work
    #parts = re.search(r'(.+) - (.+) \((.+)\)(: (.+))?', subject)
    #data = {'code': parts.group(1),
    #        'location': parts.group(2),
    #        'id': parts.group(3),
    #        'details': parts.group(4)}
    data = {'subject': subject.strip()}
    return data


def dump_alert_for_eidos(alert, fname):
    subj = alert['header']['subject']['subject'] if alert['header']['subject'] else ''
    arch = alert['header']['archive_number'] if alert['header']['archive_number'] else ''
    content_str = str(arch) + '\n\n'
    content_str += subj + '\n\n'
    for content in alert['body']:
        content_str += content['title'] + '\n\n' + content['content'] + '\n\n'

    with open(fname, 'w') as fh:
        fh.write(content_str)


if __name__ == '__main__':
    input_path = '../CHAIN/Data/ProMED/'

    # Process original JSON files into alert text files
    fnames = glob.glob(input_path + '*.json')

    alerts = []
    for fname in tqdm.tqdm(fnames):
        with open(fname, 'r') as fh:
            content = json.load(fh)
        for entry in content:
            if entry['header'] == ['']:
                continue
            header = parse_header(entry['header'])
            if len(entry['body']) > 1:
                assert False
            assert len(entry['body']) == 1
            contents = parse_contents_from_body(entry['body'][0])
            alerts.append({'header': header,
                           'body': contents})

    # Dump alerts for Eidos
    for idx, alert in enumerate(alerts):
        dump_alert_for_eidos(alert, f'eidos_input/alert_{idx}.txt')

    # Run NER on alerts
    annotations = []
    for alert in tqdm.tqdm(alerts, desc='Annotating alerts'):
        for content in alert['body']:
            annotations.append(
                    {'header': annotate(content['title']),
                     'content': annotate(content['content'])}
                )

    # Gather NER statistics
    terms_by_alert = []
    text_stats = []
    for annotation in annotations:
        terms = set()
        for key in ['header', 'content']:
            for match in annotation[key]:
                terms.add((match[1].term.db, match[1].term.id,
                           match[1].term.entry_name))
                text_stats.append((match[0], match[1].term.db,
                                   match[1].term.id, match[1].term.entry_name))
        terms_by_alert.append(sorted(terms))

    # Dump terms by alert into a JSON file
    with open('output/promed_ner_terms_by_alert.json', 'w') as fh:
        json.dump(terms_by_alert, fh, indent=2)

    # Dump stats into a spreadsheet
    text_stats_cnt = Counter(text_stats)
    with open('output/promed_ner_stats.tsv', 'w') as fh:
        # Add a header
        fh.write('text\tterm_db\tterm_id\tterm_name\tcount\n')
        for key, value in sorted(text_stats_cnt.items(), key=lambda x: x[1], reverse=True):
            fh.write(f'{key[0]}\t{key[1]}\t{key[2]}\t{key[3]}\t{value}\n')
