# vim:set ft=dockerfile:
FROM litnimax/alpine-asterisk

ENV maintainer litnimaxster@gmail.com

RUN apk add --no-cache supervisor git python py2-pip py2-tornado py2-setproctitle py2-gevent py2-requests
RUN apk add --no-cache tcpdump ethtool vlan iftop ngrep bash vim screen tmux

COPY ./ /

RUN pip install -r /etc/agent/requirements.txt && \
    pip install -r /etc/asterisk/services/requirements.txt
