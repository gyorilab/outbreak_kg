import csv
import json
import tqdm
from itertools import combinations
from collections import Counter
from indra.databases import mesh_client


def is_geoloc(x_db, x_id):
    if x_db == 'MESH':
        return mesh_client.mesh_isa(x_id, 'D005842')
    return False


def is_pathogen(x_db, x_id):
    if x_db == 'MESH':
        return mesh_client.mesh_isa(x_id, 'D001419') or mesh_client.mesh_isa(x_id, 'D014780')
    return False


def is_disease(x_db, x_id):
    if x_db == 'MESH':
        return mesh_client.is_disease(x_id)
    return False


# Some terms that are very common but too generic to be useful
exclude_list = {'Disease', 'Health', 'Affected', 'control', 'Animals',
                'infection', 'Viruses', 'vaccination', 'Vaccines',
                'Therapeutics', 'Nature', 'event', 'Population',
                'Epidemiology', 'Names', 'submitted', 'Laboratories',
                'Disease Outbreaks', 'Central', 'strain'}

if __name__ == '__main__':
    with open('../output/promed_ner_terms_by_alert.json', 'r') as f:
        jj = json.load(f)

    pairs = []
    interesting_pairs = []
    for alert in tqdm.tqdm(jj):
        for a, b in combinations(alert, 2):
            # Normalize for arbitrary order
            a, b = tuple(sorted([a, b], key=lambda x: x[2]))
            if a[2] in exclude_list or b[2] in exclude_list:
                continue
            for a_, b_ in ((a, b), (b, a)):
                if (is_geoloc(a_[0], a_[1]) and is_pathogen(b_[0], b_[1])) \
                        or (is_disease(a_[0], a_[1]) and is_pathogen(b_[0], b_[1])) \
                        or (is_geoloc(a_[0], a_[1]) and is_disease(b_[0], b_[1])):
                    interesting_pairs.append((tuple(a), tuple(b)))
            pairs.append((tuple(a), tuple(b)))

    node_header = ['curie:ID', 'name:string', ':TYPE']
    edge_header = [':START_ID', ':TYPE', ':END_ID', 'count:int']

    nodes = set()
    for pair in interesting_pairs:
        for x in pair:
            if is_pathogen(x[0], x[1]):
                ntype = 'pathogen'
            elif is_geoloc(x[0], x[1]):
                ntype = 'geoloc'
            else:
                ntype = 'disease'
            nodes.add((x[0] + ':' + x[1], x[2], ntype))

    cnt = Counter(interesting_pairs)
    edges = set()
    for (a, b), count in cnt.items():
        edges.add((a[0] + ':' + a[1], 'occurs_with', b[0] + ':' + b[1], count))
    with open('../kg/edges.tsv', 'w') as fh:
        writer = csv.writer(fh, delimiter='\t')
        writer.writerows([edge_header] + list(edges))
    with open('../kg/nodes.tsv', 'w') as fh:
        writer = csv.writer(fh, delimiter='\t')
        writer.writerows([node_header] + list(nodes))
