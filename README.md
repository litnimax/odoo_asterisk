# Odoo Asterisk Documentation

## Installation

### Dependencies for Asterisk
```
apt install odbc-postgresql unixodbc
```
Copy  deploy/roles/asterisk/templates/odbc.ini into /etc/

### Dependencies for Odoo
* humanize
* pyajam

```sh
pip install humanize
```
or if you system wide odoo installation:
```
apt-get install python-humanize
```

Install PyAjam
```
pip install git+https://github.com/litnimax/PyAjam.git
```

### Asterisk Remote Console
To get a remote Asterisk CLI in Odoo you must configure and run cli_server.py daemon.  It is located in *asterisk* folder.

Clone this repo on your Asterisk server, create python virtual environment, go to *asterisk* folder and run
```
virtualenv env
source env/bin/activate
pip install -r requirements.txt
python cli_server.py
```
After that go to Odoo and set Asterisk CLI URL	in server's settings to (for example):
```
ws://192.168.1.1:8010/websocket
```
*Save*, go to Console tab and click *Edit* to activate Asterisk CLI. Click *Discard* to leave the console.

Watch all these steps in this 1 minute video tutorial:



### PostgreSQL preparations
Before installing Odoo Asterisk Application you have to create PostgreSQL role for Asterisk:

```sql
template1=# create user asterisk with password 'change_me';
CREATE ROLE
template1=#

```
