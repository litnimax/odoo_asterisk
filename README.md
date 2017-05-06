# Odoo Asterisk Documentation

## Installation

### Dependencies
* humanize
*

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

### PostgreSQL preparations
Before installing Odoo Asterisk Application you have to create PostgreSQL role for Asterisk:

```sql
template1=# create user asterisk with password 'change_me';
CREATE ROLE
template1=#

```
