FROM alpine:edge

ENV maintainer litnialex@gmail.com

RUN apk add --no-cache bash mosquitto

EXPOSE 1883

CMD ["/usr/sbin/mosquitto", "-v"]

