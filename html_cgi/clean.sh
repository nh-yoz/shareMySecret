#!/bin/bash
for i in $(grep -l ', "expires": "' /var/www/misc/sharesecret/secret/*)
do [[ $(sed -rn 's/^.*, "expires": "([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]{8})\.[0-9]{6}".*$/\1/p' "${i}") < $(date +"%Y-%m-%dT%H:%M:%S") ]] && rm -f "${i}"
done
