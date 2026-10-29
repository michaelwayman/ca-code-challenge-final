#!/bin/sh
# Runs inside python:3.12-slim (see `make typecheck`): installs the pinned checker and the
# services' own requirements, then type-checks cauth and both services against typecheck/*.ini.
set -eu
cd /work
# cauth comes from a copy of the source, not the index, so the check sees what a service sees:
# the installed package, including its py.typed marker. Its pin is not installable from PyPI.
cat services/auth/requirements.txt services/app/requirements.txt | grep -v '^cauth==' >/tmp/requirements.txt
cp -r libs/cauth /tmp/cauth
pip install -q --no-cache-dir /tmp/cauth -r /tmp/requirements.txt \
  mypy==1.18.2 django-stubs==5.2.7 djangorestframework-stubs==3.16.0

status=0
mypy --config-file typecheck/cauth.ini -p cauth || status=1
for service in app auth; do
  (cd services/$service && mypy --config-file /work/typecheck/$service.ini .) || status=1
done
exit $status
