#!/bin/bash
# debian builder file
set -x

echo "Delete old directories and associated packages."
rm -f ./debian/dist/*
rm -rf ./debian/opt/*
rm -rf ./dist
echo "Deletion successful."


echo "Running debian builder"
sudo cp -rf ./axon ./debian/opt/
sudo cp -rf ./etc ./debian/opt/axon/
sudo dpkg-deb --build ./debian ./debian/dist/axon_service.deb
echo "Debian is created successfully."

echo "Creating axon sdist package."
python setup.py sdist
sdist_package=`ls -t ./dist | head -n1`
echo "Axon sdist package creation is successful."

echo "copy distribution packages to packages archive"
mkdir -p /var/lib/automation/packages/
cp -f ./dist/$sdist_package /var/lib/automation/packages/axon_service.tar.gz
cp -f ./debian/dist/axon_service.deb /var/lib/automation/packages/
cp -f ./requirements.txt /var/lib/automation/packages/axon_requirements.txt

