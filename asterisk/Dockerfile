FROM alpine:edge

RUN apk update && apk upgrade && \
    apk add supervisor git python psqlodbc \
    py2-pip py2-tornado py2-setproctitle py2-gevent py2-requests py2-paho-mqtt \
    asterisk asterisk-odbc asterisk-sample-config asterisk-sounds-en asterisk-sounds-moh asterisk-srtp

#Install optional tools
RUN apk add tcpdump ethtool vlan iftop ngrep bash vim screen tmux mosquitto-clients curl

# grab dockerize for generation of the configuration file and wait on postgres
RUN curl https://github.com/jwilder/dockerize/releases/download/v0.6.0/dockerize-alpine-linux-amd64-v0.6.0.tar.gz -L | tar xz -C /usr/local/bin

RUN mkdir /var/log/supervisor

# Asterisk conf templates
COPY ./etc/ /etc/
COPY ./services /services/

RUN pip install -r /services/requirements.txt

COPY ./docker-entrypoint.sh /

EXPOSE 5060/udp 5038 8088 8010

ENTRYPOINT ["/docker-entrypoint.sh"]
