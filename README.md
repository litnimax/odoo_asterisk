# Odoo Asterisk Documentation

## Installation

### Dependencies
* humanize
*

```sh
pip install humanize
```

### PostgreSQL preparations
Before installing Odoo Asterisk Application you have to create PostgreSQL role for Asterisk:

```sql
template1=# create user asterisk with password 'change_me';
CREATE ROLE
template1=#

```
