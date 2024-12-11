import os
from collections import defaultdict
from itertools import combinations
import pandas as pd
import numpy as np
import gilda
from scipy.special import logsumexp

HERE = os.path.dirname(__file__)
ALERT_DATA = os.path.join(HERE, 'promed_alert_edges.tsv')
MESH_DATA = os.path.join(HERE, 'mesh_hierarchy_nodes.tsv')


exclude_list = {
    'D003142',
    'D004194',
    'D004196',
    'D005190'
    'D012306',
    'D011634',
    'D012816',
    'D042241',
    'D003141',
    'D003643',
    'D007239',
    'D004630',
    'D002947',
    'D012008',
    'D020478',
    'D006262',
    'D011153',
    'D019090',
    'D009272',
    'D003933'
}


def get_mesh_types():
    df = pd.read_csv(MESH_DATA, sep='\t')
    mesh_types = {}
    for _, row in df.iterrows():
        curie = row['curie:ID']
        mesh_id = curie[5:]
        labels_str = row[':LABEL']
        mesh_type = {label for label in labels_str.split(';')
                     if label != 'entity'}
        if len(mesh_type) != 1:
            raise ValueError(f"Multiple types for {curie}: {mesh_type}")
        mesh_types[mesh_id] = list(mesh_type)[0]
    return mesh_types


# Get co-occurrence scores from KG, i.e., the percentage of alerts in
# which two terms co-occur.
def get_coorcurrence(mesh_types):
    df = pd.read_csv(ALERT_DATA, sep='\t')
    terms_by_alert = defaultdict(set)
    coocurrence_scores = defaultdict(int)
    for _, row in df.iterrows():
        alert_id = row[':START_ID']
        mesh_term = row[':END_ID'][5:]
        terms_by_alert[alert_id].add(mesh_term)

    for alert_terms in terms_by_alert.values():
        for term1, term2 in combinations(alert_terms, 2):
            sorted_terms = tuple(sorted([term1, term2]))
            coocurrence_scores[sorted_terms] += 1

    # Normalize log scores
    num_alerts = len(terms_by_alert)
    for terms, count in coocurrence_scores.items():
        coocurrence_scores[terms] = np.log(count) - np.log(num_alerts)

    return coocurrence_scores


def get_coocurrence_score(mesh_ids):
    scores = {}
    for term1, term2 in combinations(mesh_ids, 2):
        if term1 in exclude_list or term2 in exclude_list:
            continue
        if term1 not in mesh_types or term2 not in mesh_types:
            continue
        sorted_terms = tuple(sorted([term1, term2]))
        scores[sorted_terms] = coocurrence_scores.get(sorted_terms, -np.inf)
    score_sum = logsumexp(list(scores.values()))
    return scores, score_sum


def score_text(text):
    annotations = gilda.annotate(text, namespaces=['MESH'])
    mesh_ids = {a.matches[0].term.id for a in annotations}
    scores, score_sum = \
        get_coocurrence_score(mesh_ids)
    return scores, score_sum


mesh_types = get_mesh_types()
coocurrence_scores = get_coorcurrence(mesh_types)


if __name__ == '__main__':
    mesh_types = get_mesh_types()
    coocurrence_scores = get_coorcurrence(mesh_types)