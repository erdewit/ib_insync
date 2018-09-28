#!/bin/bash
pushd docs
make html
popd
rm -Rf dist/*
python3 setup.py sdist bdist_wheel
python3 -m twine upload dist/*
