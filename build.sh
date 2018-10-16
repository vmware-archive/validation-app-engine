#!/bin/bash
# debian builder file
set -x
echo "Running debian builder"
rm -f ./debian/dist/*
rm -rf ./debian/opt/*

sudo cp -rf ./axon ./debian/opt/
sudo cp -rf ./etc ./debian/opt/axon/
sudo dpkg-deb --build ./debian ./debian/dist/test_axon.deb
