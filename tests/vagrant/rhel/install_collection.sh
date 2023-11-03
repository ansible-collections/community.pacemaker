#!/bin/bash -eu

echo "Building community.pacemaker collection";
WD=$(pwd);
cd ../../../;
rm -f community-pacemaker-*.tar.gz;
ansible-galaxy collection build;
ansible-galaxy collection install --force community-pacemaker-*.tar.gz;
rm -f community-pacemaker-*.tar.gz;
cd "$WD" || exit 1;