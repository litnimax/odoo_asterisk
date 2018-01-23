#!/bin/sh

# dockerize templates
for i in `find /etc -name '*.tmpl'`; do
  dockerize -template "$i":"${i%%.tmpl}" && rm "$i"
done

if [ "$1" = "" ]; then
  # This works if CMD is empty or not specified in Dockerfile
  exec /usr/bin/supervisord -c /etc/supervisord.conf
else
  exec "$@"
fi
