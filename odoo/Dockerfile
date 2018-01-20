FROM debian:jessie
ENV maintainer litnimax

# create the working directory and a place to set the logs (if wanted)
RUN mkdir -p /opt/odoo /var/log/odoo

WORKDIR "/opt/odoo"

COPY ./base_requirements.txt ./

# Install some deps, lessc and less-plugin-clean-css, and wkhtmltopdf
RUN set -x; \
        sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main" > /etc/apt/sources.list.d/pgdg.list' \
        && apt-get update \
        && apt-get install -y --no-install-recommends \
            antiword \
            ca-certificates \
            curl \
            ghostscript \
            graphviz \
            less \
            nano \
            node-clean-css \
            node-less \
            poppler-utils \
            python \
            python-libxslt1 \
            python-pip \
            xfonts-75dpi \
            xfonts-base \
            # build packages to clean after the pip install
            build-essential \
            python-dev \
            libfreetype6-dev \
            libxml2-dev \
            libxslt1-dev \
            libsasl2-dev \
            libldap2-dev \
            libssl-dev \
            libjpeg-dev \
            zlib1g-dev \
            libfreetype6-dev \
            tcl expect \
            vim \
        && curl -s https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
        && apt-get update \
        && apt-get install -y --no-install-recommends \
            postgresql-client \
            libpq-dev \
        && curl -o wkhtmltox.deb -SL http://nightly.odoo.com/extra/wkhtmltox-0.12.1.2_linux-jessie-amd64.deb \
        && echo '40e8b906de658a2221b15e4e8cd82565a47d7ee8 wkhtmltox.deb' | sha1sum -c - \
        && dpkg --force-depends -i wkhtmltox.deb \
        && apt-get -y install -f --no-install-recommends \
        && pip install -U pip && pip install -r base_requirements.txt \
        #&& apt-get remove -y build-essential python-dev libfreetype6-dev libpq-dev libxml2-dev libxslt1-dev \
        #                     libsasl2-dev libldap2-dev libssl-dev libjpeg-dev zlib1g-dev libfreetype6-dev \
        && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false -o APT::AutoRemove::SuggestsImportant=false npm \
        && rm -rf /var/lib/apt/lists/* wkhtmltox.deb

# grab gosu for easy step-down from root
RUN gpg --keyserver pool.sks-keyservers.net --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4 \
        && curl -o /usr/local/bin/gosu -SL "https://github.com/tianon/gosu/releases/download/1.2/gosu-$(dpkg --print-architecture)" \
        && curl -o /usr/local/bin/gosu.asc -SL "https://github.com/tianon/gosu/releases/download/1.2/gosu-$(dpkg --print-architecture).asc" \
        && gpg --verify /usr/local/bin/gosu.asc \
        && rm /usr/local/bin/gosu.asc \
        && chmod +x /usr/local/bin/gosu

# grab dockerize for generation of the configuration file and wait on postgres
RUN curl https://github.com/jwilder/dockerize/releases/download/v0.4.0/dockerize-linux-amd64-v0.4.0.tar.gz -L | tar xz -C /usr/local/bin

COPY ./src_requirements.txt ./
COPY ./bin bin
COPY ./etc etc
COPY ./before-migrate-entrypoint.d before-migrate-entrypoint.d
COPY ./start-entrypoint.d start-entrypoint.d
#COPY ./MANIFEST.in ./

VOLUME ["/data/odoo", "/var/log/odoo"]

# Expose Odoo services
EXPOSE 8069 8072

ENV ODOO_VERSION=10.0 \
    PATH=/opt/odoo/bin:$PATH \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    DB_HOST=db \
    DB_PORT=5432 \
    DB_NAME=barrier \
    DB_USER=odoo \
    DB_PASSWORD=odoo \
    ODOO_BASE_URL=http://localhost:8069 \
    DEMO=False \
    ADDONS_PATH=/opt/odoo/local-src,/opt/odoo/external-src,/opt/odoo/src/addons \
    OPENERP_SERVER=/opt/odoo/etc/odoo.cfg

# set to /opt so we can have the same path outside and inside of the container:
# docker run --rm odoo pytest odoo/external-src/abc/xyz/tests/test.py
WORKDIR "/opt"

COPY ./src/odoo/ /opt/odoo/src/
RUN cd /opt/odoo/src && pip install .

# intermediate images should help speed up builds when only local-src, or only
# external-src changes
COPY ./external-src /opt/odoo/external-src
COPY ./local-src /opt/odoo/local-src
COPY ./data /opt/odoo/data
COPY ./songs /opt/odoo/songs
COPY ./setup.py /opt/odoo/
COPY ./VERSION /opt/odoo/
COPY ./migration.yml /opt/odoo/

# need to be called at the end, because it installs . and src
RUN cd /opt/odoo && pip install -r src_requirements.txt

ENV ADDONS_PATH=/opt/odoo/local-src,/opt/odoo/src/addons

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["odoo"]

# Project's specifics packages
RUN set -x; \
        apt-get update \
        && apt-get install -y --no-install-recommends git mosquitto-clients\
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /opt/odoo/
RUN cd /opt/odoo && pip install -r requirements.txt
