FROM ubuntu:22.04

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
        python3.11 \
    && apt-get purge -y imagemagick imagemagick-6-common \
    && curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

RUN curl -fsSL https://debian.neo4j.com/neotechnology.gpg.key | apt-key add -
RUN add-apt-repository "deb https://debian.neo4j.com stable 4.4"
RUN apt-get install -y neo4j

# Fixes ERROR: Cannot uninstall 'blinker'. It is a distutils installed project
# and thus we cannot accurately determine which files belong to it which would lead to only a partial uninstall.
RUN python3.11 -m pip install --ignore-installed blinker

RUN python3.11 -m pip install fastapi \
    uvicorn \
    "neo4j<5" \
    tqdm \
    flask \
    bootstrap_flask \
    cython \
    pandas \
    networkx

# Alternative: COPY all files, using .dockerignore for white/blacklisting

COPY nodes.tsv /sw/nodes.tsv
COPY edges.tsv /sw/edges.tsv


# Ingest graph content into neo4j
RUN sed -i 's/#dbms.default_listen_address/dbms.default_listen_address/' /etc/neo4j/neo4j.conf
RUN sed -i 's/#dbms.security.auth_enabled/dbms.security.auth_enabled/' /etc/neo4j/neo4j.conf
RUN neo4j-admin import --delimiter='TAB' --skip-duplicate-nodes=true --skip-bad-relationships=true \
    --relationships /sw/edges.tsv \
    --nodes=uniprot=/sw/nodes.tsv


ENV DOCKERIZED="TRUE"
ENV NEO4J_URL="bolt://localhost:7687"

COPY startup.sh startup.sh
ENTRYPOINT ["/bin/bash", "/sw/startup.sh"]
