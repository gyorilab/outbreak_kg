import csv
import json
import tqdm
from itertools import combinations
from collections import Counter
import pandas as pd
from indra.databases import mesh_client
from indra.ontology.bio import bio_ontology

from constants import WORLD_BANK_MESH_COUNTRY_MAPPING


def is_geoloc(x_db, x_id):
    if x_db == 'MESH':
        return mesh_client.mesh_isa(x_id, 'D005842')
    return False


def is_pathogen(x_db, x_id):
    if x_db == 'MESH':
        return mesh_client.mesh_isa(x_id, 'D001419') or \
            mesh_client.mesh_isa(x_id, 'D014780')
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

outbreak_df = pd.read_csv('../output/promed_updates.csv',
                              dtype={"archiveNumber":str})
outbreak_df["archiveNumber"] = outbreak_df["archiveNumber"].apply(
    lambda archive_number: archive_number.replace("\"", ""))

def assemble_coocurrence():
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


def assemble_mesh_hierarchy():
    edges = set()
    nodes = set()
    # Assemble the subtree of diseases, pathogens and geolocations
    for mesh_id, mesh_name in mesh_client.mesh_id_to_name.items():
        is_dis = is_disease('MESH', mesh_id)
        is_pat = is_pathogen('MESH', mesh_id)
        is_geo = is_geoloc('MESH', mesh_id)
        if not any([is_dis, is_pat, is_geo]):
            continue
        if is_dis:
            node_type = 'disease'
        elif is_pat:
            node_type = 'pathogen'
        else:
            node_type = 'geoloc'
        nodes.add((f'MESH:{mesh_id}', mesh_name, node_type))
        parents_ids = list(bio_ontology.child_rel('MESH', mesh_id, {'isa'}))
        parent_mesh_terms = [':'.join(parent) for parent in parents_ids]
        new_edges = set()
        for parent in parent_mesh_terms:
            if is_dis and not is_disease('MESH', parent):
                continue
            if is_pat and not is_pathogen('MESH', parent):
                continue
            if is_geo and not is_geoloc('MESH', parent):
                continue
            new_edges.add((f'MESH:{mesh_id}', 'isa', parent))
        edges |= new_edges
    # TODO: add relations to root nodes
    node_header = ['curie:ID', 'name:string', ':LABEL']
    edge_header = [':START_ID', ':TYPE', ':END_ID']
    with open('../kg/mesh_hierarchy_edges.tsv', 'w') as fh:
        writer = csv.writer(fh, delimiter='\t')
        writer.writerows([edge_header] + list(edges))
    with open('../kg/mesh_hierarchy_nodes.tsv', 'w') as fh:
        writer = csv.writer(fh, delimiter='\t')
        writer.writerows([node_header] + list(nodes))


def assemble_outbreak_nodes():
    nodes = set()
    edges = set()
    added_outbreak_nodes_index = set()
    for _, row in outbreak_df.iterrows():
        outbreak_id = row["ID"]
        outbreak_name = row["outbreakName"]
        if outbreak_id not in added_outbreak_nodes_index:
            added_outbreak_nodes_index.add(outbreak_id)
            nodes.add((f"outbreak:{outbreak_id}", outbreak_name, 'outbreak'))
        archive_number = row["archiveNumber"]
        edges.add((f'promed:{archive_number}', 'has_outbreak',
                   f"outbreak:{outbreak_id}"))
    node_header = ['curie:ID', 'name:string', ':LABEL']
    edge_header = [':START_ID', ':TYPE', ':END_ID']
    with open('../kg/promed_outbreak_nodes.tsv', 'w') as fh:
        writer = csv.writer(fh, delimiter='\t')
        writer.writerows([node_header] + list(nodes))
    with open('../kg/promed_alert_outbreak_edges.tsv', 'w') as fh:
        writer = csv.writer(fh, delimiter='\t')
        writer.writerows([edge_header] + list(edges))


def assemble_alert_relations():
    with open('../output/promed_ner_terms_by_alert.json', 'r') as f:
        terms_by_alert = json.load(f)
    nodes = set()
    edges = set()
    for archive_number, extractions in terms_by_alert.items():
        matching_alerts_df = outbreak_df[outbreak_df["archiveNumber"] ==
                                         archive_number]
        if matching_alerts_df.shape[0] > 0:
            time_stamp = str(matching_alerts_df.iloc[0]["datePublished"])
        else:
            time_stamp = ""
        nodes.add((f'promed:{archive_number}', archive_number, time_stamp,
                   'alert'))
        for ns, id, entry_name in extractions:
            if entry_name in exclude_list:
                continue
            if ns == 'MESH':
                if is_disease(ns, id) or is_pathogen(ns, id) or is_geoloc(ns, id):
                    edges.add((f'promed:{archive_number}', 'mentions', f'MESH:{id}'))
    node_header = ['curie:ID', 'name:string', 'timestamp:string', ':LABEL']
    edge_header = [':START_ID', ':TYPE', ':END_ID']
    with open('../kg/promed_alert_nodes.tsv', 'w') as fh:
        writer = csv.writer(fh, delimiter='\t')
        writer.writerows([node_header] + list(nodes))
    with open('../kg/promed_alert_edges.tsv', 'w') as fh:
        writer = csv.writer(fh, delimiter='\t')
        writer.writerows([edge_header] + list(edges))


def assemble_pathogen_disease_relations():
    import pyobo
    df = pd.read_csv('pathogen_disease_rels.tsv', sep='\t')
    df = df[~df[':START_ID'].str.startswith('umls')]
    df = df[~df[':END_ID'].str.startswith('umls')]
    edges = set()
    for _, row in df.iterrows():
        source_ns, source_id = row[':START_ID'].split(':')
        if source_ns == 'ncbitaxon':
            mapped_id = mesh_client.ncbitaxon_to_mesh.get(source_id)
        else:
            mapped_id = pyobo.get_xref(source_ns, source_id, 'mesh')
        if not mapped_id:
            continue
        target_ns, target_id = row[':END_ID'].split(':')
        if target_ns == 'ncbitaxon':
            mapped_id = mesh_client.ncbitaxon_to_mesh.get(target_id)
        else:
            mapped_id = pyobo.get_xref(target_ns, target_id, 'mesh')
        if not mapped_id:
            continue
        edges.add((f'MESH:{source_id}', 'has_pathogen', f'MESH:{target_id}'))
    with open('../kg/pathogen_disease_edges.tsv', 'w') as fh:
        writer = csv.writer(fh, delimiter='\t')
        writer.writerows([[':START_ID', ':TYPE', ':END_ID']] + list(edges))


def assemble_disease_symptom_relations():
    df = pd.read_csv('disease_phenotype_rels.tsv', sep='\t')
    df = df[df[':START_ID'].str.startswith('mesh')]
    df = df[df[':END_ID'].str.startswith('mesh')]
    edges = set()
    edge_header = [':START_ID', ':TYPE', ':END_ID']
    for _, row in df.iterrows():
        mesh_disease = row[':START_ID'].upper()
        mesh_pheno = row[':END_ID'].upper()
        edges.add((mesh_disease, 'has_phenotype', mesh_pheno))
    with open('../kg/disease_phenotype_edges.tsv', 'w') as fh:
        writer = csv.writer(fh, delimiter='\t')
        writer.writerows([edge_header] + list(edges))


def assemble_world_indicator_data():
    dev_nodes, dev_edges, health_nodes, health_edges = set(), set(), set(), set()
    mesh_node_df = pd.read_csv("../kg/mesh_hierarchy_nodes.tsv", sep="\t")
    country_dev_indicator_df = pd.read_csv(
        "../kg/world_dev_indicator_data.tsv", sep="\t"
    )
    country_health_indicator_df = pd.read_csv(
        "../kg/world_health_indicator_data.tsv", sep="\t"
    )

    # Removed shared series codes between dev and health indicator data from the
    # health indicator dataframe
    dev_series_codes = set(country_dev_indicator_df["Series Code"])
    health_series_code = set(country_health_indicator_df["Series Code"])
    health_series_code_diff = health_series_code - dev_series_codes
    country_health_indicator_df = country_health_indicator_df[
        country_health_indicator_df["Series Code"].isin(health_series_code_diff)
    ]

    # Ground World Bank country/region terms using Mesh terms
    country_dev_indicator_df["Country Name"] = (
        country_dev_indicator_df["Country Name"]
        .map(WORLD_BANK_MESH_COUNTRY_MAPPING)
        .fillna(country_dev_indicator_df["Country Name"])
    )
    country_health_indicator_df["Country Name"] = (
        country_health_indicator_df["Country Name"]
        .map(WORLD_BANK_MESH_COUNTRY_MAPPING)
        .fillna(country_health_indicator_df["Country Name"])
    )

    node_header = ["curie:ID", "name:string", ":LABEL"]
    edge_header = [":START_ID", "years_data:string", ":TYPE", ":END_ID"]

    # Filter out countries that can't be grounded to Mesh terms
    country_dev_indicator_df = pd.merge(
        country_dev_indicator_df,
        mesh_node_df[mesh_node_df[":LABEL"] == "geoloc"],
        left_on="Country Name",
        right_on="name:string",
        how="inner",
    )[country_dev_indicator_df.columns]

    country_health_indicator_df = pd.merge(
        country_health_indicator_df,
        mesh_node_df[mesh_node_df[":LABEL"] == "geoloc"],
        left_on="Country Name",
        right_on="name:string",
        how="inner",
    )[country_health_indicator_df.columns]

    # Process health indicator data
    for _, row in country_health_indicator_df.iterrows():
        country_name = row["Country Name"]
        series_code = row["Series Code"]
        series_name = row["Series Name"]
        country_mesh_info = mesh_node_df[mesh_node_df["name:string"] == country_name]
        indicator_year_data_dict = {}

        # Process indicator year-data only for each row
        for col, val in row[1:].items():
            try:
                float(val)
            except ValueError:
                continue
            indicator_year_data_dict[col[:4]] = round(float(val), 3)
        indicator_year_data_string = json.dumps(indicator_year_data_dict)
        country_curie = country_mesh_info.values[0][0]
        indicator_curie = f"wdi:{series_code}"
        health_nodes.add((indicator_curie, series_name, "indicator"))
        health_edges.add(
            (
                country_curie,
                indicator_year_data_string,
                "has_indicator",
                indicator_curie,
            )
        )
    with open("../kg/indicator_health_nodes.tsv", "w") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerows([node_header] + list(health_nodes))
    with open("../kg/indicator_health_edges.tsv", "w") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerows([edge_header] + list(health_edges))

    # Process dev indicator data
    for _, row in country_dev_indicator_df.iterrows():
        country_name = row["Country Name"]
        series_code = row["Series Code"]
        series_name = row["Series Name"]
        country_mesh_info = mesh_node_df[mesh_node_df["name:string"] == country_name]
        indicator_year_data_dict = {}

        for col, val in row[1:].items():
            try:
                float(val)
            except ValueError:
                continue
            indicator_year_data_dict[col[:4]] = round(float(val), 3)

        indicator_year_data_string = json.dumps(indicator_year_data_dict)
        country_curie = country_mesh_info.values[0][0]
        indicator_curie = f"wdi:{series_code}"
        dev_nodes.add((indicator_curie, series_name, "indicator"))
        dev_edges.add(
            (
                country_curie,
                indicator_year_data_string,
                "has_indicator",
                indicator_curie,
            )
        )
    with open("../kg/indicator_dev_nodes.tsv", "w") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerows([node_header] + list(dev_nodes))
    with open("../kg/indicator_dev_edges.tsv", "w") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerows([edge_header] + list(dev_edges))


def add_geoname_nodes_edges():
    nodes, edges = set(), set()
    node_header = ['curie:ID', 'name:string', ':LABEL']
    edge_header = [':START_ID', ':TYPE', ':END_ID']
    from mira.dkg.resources.geonames import get_geonames_terms
    from pyobo.struct import part_of
    geoname_terms = get_geonames_terms()
    mesh_node_df = pd.read_csv("../kg/mesh_hierarchy_nodes.tsv", sep="\t")
    for term in geoname_terms:
        # See if the name could be mapped a MESH term
        name = term.name
        if name in WORLD_BANK_MESH_COUNTRY_MAPPING:
            name = WORLD_BANK_MESH_COUNTRY_MAPPING[name]
        # Don't add geoloc terms represented by geonames that are already
        # present as MESH terms
        mesh_term_info = mesh_node_df[(mesh_node_df[":LABEL"] == "geoloc") & (mesh_node_df["name:string"]==name)]
        if not mesh_term_info.empty:
            continue
        nodes.add((term.curie, term.name, "geoloc"))
        for parent in term.get_relationships(part_of):
            parent_name = parent.name
            if parent_name in WORLD_BANK_MESH_COUNTRY_MAPPING:
                parent_name = WORLD_BANK_MESH_COUNTRY_MAPPING[parent_name]
            # We only add a geoname node as a target if the geolocation it
            # represents isn't present as a MESH term
            mesh_parent_info = mesh_node_df[(mesh_node_df["name:string"] == parent_name) & (mesh_node_df[":LABEL"] == "geoloc")]
            if not mesh_parent_info.empty:
                parent_curie = mesh_parent_info.values[0][0]
                edges.add((term.curie,"isa",parent_curie))
            else:
                edges.add((term.curie, "isa", parent.curie))
    with open("../kg/geoname_nodes.tsv", "w") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerows([node_header] + list(nodes))
    with open("../kg/geoname_edges.tsv", "w") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerows([edge_header] + list(edges))

if __name__ == "__main__":
    assemble_outbreak_nodes()
    assemble_alert_relations()
    assemble_mesh_hierarchy()
    assemble_pathogen_disease_relations()
    assemble_disease_symptom_relations()
    assemble_world_indicator_data()
    add_geoname_nodes_edges()
