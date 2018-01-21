FROM alpine:edge

ENV maintainer litnialex@gmail.com

RUN apk add --no-cache bash mosquitto mosquitto-clients

EXPOSE 1883

CMD ["/usr/sbin/mosquitto", "-v"]
