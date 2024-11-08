FROM ubuntu:20.04

# Needed to forego timezone configuration
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /sw

RUN apt-get update -y \
    && apt-get upgrade -y \
    && apt-get -y install build-essential \
        zlib1g-dev \
        libncurses5-dev \
        libgdbm-dev \
        libnss3-dev \
        libssl-dev \
        libreadline-dev \
        libffi-dev \
        libsqlite3-dev \
        libbz2-dev \
        curl \
        wget \
        libpq-dev \
        g++ \
        git \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        liblzma-dev \
        lzma \
        libblas3 \
        liblapack3 \
        liblapack-dev \
        libblas-dev \
        gfortran \
        pkg-config \
        unzip

RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt update -y
RUN apt -y install python3.10 python3.10-dev
RUN apt-get purge -y imagemagick imagemagick-6-common
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10

RUN curl -fsSL https://debian.neo4j.com/neotechnology.gpg.key | apt-key add -
RUN add-apt-repository "deb https://debian.neo4j.com stable 4.4"
RUN apt-get install -y neo4j

# Retrieves jar file needed to install apoc
RUN wget https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases/download/4.4.0.30/apoc-4.4.0.30-all.jar -O /var/lib/neo4j/plugins/apoc-4.4.0.30-all.jar

# Set custom configuration to enable apoc
RUN echo "dbms.security.procedures.unrestricted=apoc.*" >> /etc/neo4j/neo4j.conf

# Fixes ERROR: Cannot uninstall 'blinker'. It is a distutils installed project
# and thus we cannot accurately determine which files belong to it which would lead to only a partial uninstall.
RUN python3.10 -m pip install --ignore-installed blinker
RUN python3.10 -m pip install git+https://github.com/sorgerlab/indra.git
RUN python3.10 -m pip install fastapi \
    uvicorn \
    "neo4j<5" \
    tqdm \
    flask \
    flask_cors \
    bootstrap_flask \
    cython \
    pandas \
    networkx \
    gunicorn

# This is for coocurrence
#COPY nodes.tsv /sw/nodes.tsv
#COPY edges.tsv /sw/edges.tsv
COPY alerts.zip /sw/alerts.zip
RUN cd /sw/ && \
    unzip /sw/alerts.zip
RUN mv /sw/eidos_input /sw/alerts

COPY mesh_hierarchy_edges.tsv /sw/mesh_hierarchy_edges.tsv
COPY mesh_hierarchy_nodes.tsv /sw/mesh_hierarchy_nodes.tsv
COPY promed_alert_nodes.tsv /sw/promed_alert_nodes.tsv
COPY promed_alert_edges.tsv /sw/promed_alert_edges.tsv
COPY disease_phenotype_edges.tsv /sw/disease_phenotype_edges.tsv
COPY pathogen_disease_edges.tsv /sw/pathogen_disease_edges.tsv
COPY promed_alert_outbreak_edges.tsv /sw/promed_alert_outbreak_edges.tsv
COPY promed_outbreak_nodes.tsv /sw/promed_outbreak_nodes.tsv
COPY indicator_dev_nodes.tsv /sw/indicator_dev_nodes.tsv
COPY indicator_dev_edges.tsv /sw/indicator_dev_edges.tsv
COPY indicator_health_nodes.tsv /sw/indicator_health_nodes.tsv
COPY indicator_health_edges.tsv /sw/indicator_health_edges.tsv
COPY geoname_nodes.tsv /sw/geoname_nodes.tsv
COPY geoname_edges.tsv /sw/geoname_edges.tsv

# Ingest graph content into neo4j
RUN sed -i 's/#dbms.default_listen_address/dbms.default_listen_address/' /etc/neo4j/neo4j.conf
RUN sed -i 's/#dbms.security.auth_enabled/dbms.security.auth_enabled/' /etc/neo4j/neo4j.conf
RUN neo4j-admin import --delimiter='TAB' --skip-duplicate-nodes=true --skip-bad-relationships=true \
    --relationships /sw/mesh_hierarchy_edges.tsv \
    --nodes /sw/mesh_hierarchy_nodes.tsv \
    --relationships /sw/promed_alert_edges.tsv \
    --nodes /sw/promed_alert_nodes.tsv \
    --relationships /sw/disease_phenotype_edges.tsv \
    --relationships /sw/pathogen_disease_edges.tsv \
    --nodes /sw/promed_outbreak_nodes.tsv \
    --relationships /sw/promed_alert_outbreak_edges.tsv \
    --nodes /sw/indicator_dev_nodes.tsv \
    --relationships /sw/indicator_dev_edges.tsv \
    --nodes /sw/indicator_health_nodes.tsv \
    --relationships /sw/indicator_health_edges.tsv \
    --nodes /sw/geoname_nodes.tsv \
    --relationships /sw/geoname_edges.tsv

ENV DOCKERIZED="TRUE"
ENV NEO4J_URL="bolt://localhost:7687"

RUN python3.10 -m pip install git+https://github.com/gyorilab/gilda.git
RUN python3.10 -c "import nltk;nltk.download('stopwords');nltk.download('punkt_tab')"
RUN python3.10 -m gilda.resources

COPY static static
COPY templates templates
COPY api.py api.py
COPY startup.sh startup.sh
COPY client.py client.py
ENTRYPOINT ["/bin/bash", "/sw/startup.sh"]
