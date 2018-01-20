# vim:set ft=dockerfile:
FROM litnimax/alpine-asterisk

ENV maintainer litnimaxster@gmail.com

RUN apk update && \
    apk add supervisor git python py2-pip py2-tornado py2-setproctitle py2-gevent py2-requests py2-paho-mqtt

#Install optional tools
RUN apk add tcpdump ethtool vlan iftop ngrep bash vim screen tmux mosquitto-clients

RUN mkdir /var/log/supervisor

COPY ./ /

RUN pip install -r /services/requirements.txt
