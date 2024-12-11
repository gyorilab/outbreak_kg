import os
import csv
import json
import tqdm
import pystow
import numpy as np
import pandas as pd
from collections import Counter
from scipy.sparse import coo_matrix
from scipy.sparse import save_npz, load_npz
from scipy.stats import fisher_exact

from util import get_mesh_type
from indra.literature import pubmed_client

mesh_file = pystow.join('indra', 'cogex', 'pubmed', name='mesh_pmids.csv')

print('Loading MeSH-PubMed resource files')
csr = load_npz('mesh_pmid_matrix.npz')
with open('mesh_mapping.json', 'r') as fh:
    mesh_mapping = json.load(fh)
with open('pmid_mapping.json', 'r') as fh:
    pmid_mapping = json.load(fh)
with open('mesh_types.json', 'r') as fh:
    mesh_types = json.load(fh)

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


def build_mesh_csr():
    mesh_counter = 0
    pmid_counter = 0
    mesh_mapping = {}
    pmid_mapping = {}
    mesh_types = {}

    pmid_indices = []
    mesh_indices = []
    values = []

    with open(mesh_file, 'r') as fh:
        reader = csv.reader(fh)
        next(reader)
        for row in tqdm.tqdm(reader, total=339439482):
            mesh_id, major, pmid = row
            if mesh_id not in mesh_types:
                mesh_types[mesh_id] = get_mesh_type('MESH', mesh_id)
            if mesh_id not in mesh_mapping:
                mesh_mapping[mesh_id] = mesh_counter
                mesh_counter += 1
            if pmid not in pmid_mapping:
                pmid_mapping[pmid] = pmid_counter
                pmid_counter += 1
            pmid_indices.append(pmid_mapping[pmid])
            mesh_indices.append(mesh_mapping[mesh_id])
            values.append(int(major) + 1)

    print('Number of unique PMIDs:', len(pmid_mapping))
    print('Number of unique MeSH terms:', len(mesh_mapping))
    # Dump mappings as JSON
    with open('mesh_mapping.json', 'w') as fh:
        json.dump(mesh_mapping, fh, indent=1)

    with open('pmid_mapping.json', 'w') as fh:
        json.dump(pmid_mapping, fh, indent=1)

    with open('mesh_types.json', 'w') as fh:
        json.dump(mesh_types, fh, indent=1)

    print('Creating sparse matrix')
    coo = coo_matrix((values, (pmid_indices, mesh_indices)),
                     shape=(len(pmid_mapping), len(mesh_mapping)))
    print('Converting to CSR')
    csr = coo.tocsr()

    print('Saving matrix')
    save_npz('mesh_pmid_matrix.npz', csr)
    return csr


def get_pvalues(mesh_terms):
    mesh_terms = set(mesh_terms) - exclude_list
    # Get index to PMID mappings
    pmid_reverse = {v: k for k, v in pmid_mapping.items()}
    mesh_reverse = {v: k for k, v in mesh_mapping.items()}
    total_pmids, total_topic_terms = csr.shape
    # Map to indices from MeSH terms
    mesh_indices = [mesh_mapping[mesh_term] for mesh_term in mesh_terms]

    # Now take only part of the matrix that is defined by the
    # MeSH terms of interest
    submatrix = csr[:, mesh_indices]

    # Number of MeSH terms that are present in each PMID
    publication_counts = np.array(submatrix.sum(axis=1)).flatten()
    # Get the indices of PMIDs that have at least one of the MeSH terms
    threshold = len(mesh_terms)-1 if len(mesh_terms) <= 4 else 3
    nonzero_indices = np.where(publication_counts >= threshold)[0]
    # Get the counts of MeSH terms for these PMIDs
    nonzero_counts = publication_counts[nonzero_indices]

    query_set = set(mesh_indices)
    p_values = []
    pmids = []
    all_overlap_mesh_ids = []
    all_overlap_mesh_type_counts = []
    all_relevant_mesh_type_coverages = []
    all_mesh_type_coverages = []
    for pub_cnt, pub_idx in tqdm.tqdm(zip(nonzero_counts, nonzero_indices)):
        pmids.append(pmid_reverse[pub_idx])
        target_set = set(csr[pub_idx].nonzero()[1])
        overlap_set = query_set & target_set
        table = np.array([
            [len(overlap_set),                     # query intersection target
             len(query_set - target_set)],         # query minus target
            [len(target_set - query_set),          # target minus query
             total_topic_terms - len(query_set | target_set)]  # neither query nor target
        ])
        res = fisher_exact(table, alternative='greater')
        p_values.append(res.pvalue)

        overlap_mesh_ids = [mesh_reverse[mesh_idx] for mesh_idx in overlap_set]
        overlap_mesh_types = [mesh_types[mesh_id] for mesh_id in overlap_mesh_ids]
        overlap_mesh_type_counts = Counter(overlap_mesh_types)
        all_relevant_mesh_type_coverages.append(
            len(set(overlap_mesh_type_counts) & {'geoloc', 'disease', 'pathogen'})
        )
        all_mesh_type_coverages.append(len(set(overlap_mesh_type_counts)))
        all_overlap_mesh_type_counts.append(overlap_mesh_type_counts)
        all_overlap_mesh_ids.append(overlap_mesh_ids)
    # Combine results into an array or DataFrame
    results = pd.DataFrame({
        'pmid': pmids,
        'overlap': all_overlap_mesh_ids,
        'overlap_counts': all_overlap_mesh_type_counts,
        'overlap_coverage_relevant': all_relevant_mesh_type_coverages,
        'overlap_coverage': all_mesh_type_coverages,
        'pval': p_values
    })
    # Save or view results
    results.sort_values(['overlap_coverage_relevant',
                         'overlap_coverage', 'pval'],
                        ascending=[False, False, True],
                        inplace=True)
    return results


def get_pubmed_meta(results, limit=10):
    pmids = results.pmid[:limit]
    print('Getting metadata for PMIDs')
    meta = pubmed_client.get_metadata_for_ids(pmids, get_abstracts=True)
    return meta


if __name__ == '__main__':
    if os.path.exists('mesh_pmid_matrix.npz'):
        csr = load_npz('mesh_pmid_matrix.npz')
    else:
        csr = build_mesh_csr()
    with open('mesh_mapping.json', 'r') as fh:
        mesh_mapping = json.load(fh)
    with open('pmid_mapping.json', 'r') as fh:
        pmid_mapping = json.load(fh)
    with open('mesh_types.json', 'r') as fh:
        mesh_types = json.load(fh)

    results = get_pvalues(['D007855', 'D015002'])
