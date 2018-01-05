#!/bin/sh

# etc templates
for i in /etc/*tmpl; do
  dockerize -template "$i":"`echo $i|sed s/.tmpl//`";
done

# Asterisk templates
for i in /etc/asterisk/*tmpl; do
  dockerize -template "$i":"`echo $i|sed s/.tmpl//`";
done

if [ "$1" = "" ]; then
  # This works if CMD is empty or not specified in Dockerfile
  exec /usr/bin/supervisord -c /etc/supervisord.conf
else
  exec "$@"
fi
