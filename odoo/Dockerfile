FROM odoo:10

USER root

RUN set -x; \
        apt-get update \
        && apt-get install -y --no-install-recommends git mosquitto-clients\
            vim tcpdump ngrep tcl expect \
            antiword ghostscript node-clean-css poppler-utils \
            build-essential python-dev libpq-dev \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

# create the working directory and a place to set the logs (if wanted)
RUN mkdir -p /opt/odoo /var/log/odoo
WORKDIR /opt/odoo

# grab gosu for easy step-down from root
RUN gpg --keyserver pool.sks-keyservers.net --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4 \
        && curl -o /usr/local/bin/gosu -SL "https://github.com/tianon/gosu/releases/download/1.2/gosu-$(dpkg --print-architecture)" \
        && curl -o /usr/local/bin/gosu.asc -SL "https://github.com/tianon/gosu/releases/download/1.2/gosu-$(dpkg --print-architecture).asc" \
        && gpg --verify /usr/local/bin/gosu.asc \
        && rm /usr/local/bin/gosu.asc \
        && chmod +x /usr/local/bin/gosu

# grab dockerize for generation of the configuration file and wait on postgres
RUN curl https://github.com/jwilder/dockerize/releases/download/v0.4.0/dockerize-linux-amd64-v0.4.0.tar.gz -L | tar xz -C /usr/local/bin

COPY ./base_requirements.txt ./
COPY ./requirements.txt ./

RUN cd /opt/odoo && pip install -r base_requirements.txt && pip install -r requirements.txt

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
    ADDONS_PATH=/opt/odoo/local-src,/opt/odoo/external-src \
    OPENERP_SERVER=/opt/odoo/etc/odoo.cfg ODOO_RC=/opt/odoo/etc/odoo.cfg


COPY ./bin bin
COPY ./etc etc
COPY ./before-migrate-entrypoint.d before-migrate-entrypoint.d
COPY ./start-entrypoint.d start-entrypoint.d
COPY ./external-src /opt/odoo/external-src
COPY ./local-src /opt/odoo/local-src
COPY ./data /opt/odoo/data
COPY ./songs /opt/odoo/songs
COPY ./setup.py /opt/odoo/
COPY ./VERSION /opt/odoo/
COPY ./migration.yml /opt/odoo/

# Install songs from setup.py
RUN pip install -e .

VOLUME ["/data/odoo", "/var/log/odoo"]

# Expose Odoo services
EXPOSE 8069 8072

# Clean Odoo 10 official entrypoint and config
RUN rm /entrypoint.sh && rm -rf /etc/odoo && userdel odoo

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["odoo"]
