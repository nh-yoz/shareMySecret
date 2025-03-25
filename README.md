# shareMySecret
Saves encrypted messages to disc retrievable of you have the key.

## Install
1. Clone this repository
2. Copy the contents of the `html_cgi` folder to `/var/www/secret`
3. Rename `config.py.example` to `config.py` and change it to fit your needs
4. Configure apache webserver: template found in the folder `apache_conf`. **/!\ Configure _https_: this app should never be run without https**
5. Create the folder `/var/www/secret/secret` (folder where the encrypted files are stored)
6. Edit the meta-properties `og:url` and `og:image` in the head of `index.html`
7. Change ownership of the folder `/var/www/secret` and its contents to the apache user (usually _apache_ or _www-data_):
```
chown -R www-data: /var/www/secret
chown root: /var/www/secret/clean.sh
```
8. Change umask of files in `/var/www/secret`:
```
chmod -R a-rwx,u+rwX /var/www/secret/*
chmod u+x /var/www/secret/{*.cgi,*.py}
```
9. Run the file `/var/www/secret/clean.sh` by crontab. This will periodically remove expired messages. 
```
crontab -e
```
Add this line:
```
10 * * * * /bin/bash /var/www/secret/clean.sh
```
