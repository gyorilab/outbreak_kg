from indra.databases import mesh_client


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


def get_mesh_type(x_db, x_id):
    if is_disease(x_db, x_id):
        return 'disease'
    elif is_geoloc(x_db, x_id):
        return 'geoloc'
    elif is_pathogen(x_db, x_id):
        return 'pathogen'
    else:
        return 'other'
