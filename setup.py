#!/usr/bin/env python

from setuptools import setup
from setuptools import find_packages

version = "0.1"

setup(
    name="rapidsms",
    version="0.1",
    maintainer="RapidSMS development community",
    maintainer_email="rapidsms@googlegroups.com",
    description="A framework for building messaging applications",
    url="http://rapidsms.org/",
    package_dir={'': 'lib'},
    packages=find_packages('lib'),
    package_data={'rapidsms': [
        'skeleton/project/*.ini',
        'skeleton/project/manage.py']},
    scripts=["rapidsms"],
    install_requires=[
        "setuptools",
        "setuptools-git",
        "pytz",
        "Django",
        ],
    long_description="\n\n".join(
        (open("README.txt").read(), open("CHANGES.txt").read())),
    test_suite="rapidsms.tests",
    )
