# vim:set ft=dockerfile:
FROM litnimax/alpine-asterisk

ENV maintainer litnimaxster@gmail.com

RUN apk add --no-cache python py2-pip py2-tornado bash supervisor

COPY ./docker-entrypoint.sh /

COPY ./etc/supervisord.conf /etc

# Asterisk conf templates
COPY ./etc/asterisk/*tmpl /etc/asterisk/

# Copy agent
COPY ./agent/ /opt/agent/
RUN cd /opt/agent && pip install -r requirements.txt
