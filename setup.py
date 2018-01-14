#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='xmbedinit',
    version='0.1.0',
    description='This tool will help local development of mbed',
    long_description='',
    author='MaskedW',
    author_email='maskedw@gmail.com',
    url='',
    license='MIT License',
    packages=find_packages(exclude=('tests', 'docs')),
    package_data={'xmbedinit': ['templates/*']},
    entry_points={
        'console_scripts': ['xmbedinit= xmbedinit.xmbedinit:main'],
    },
    zip_safe=False,
    install_requires=['pathlib', 'jinja2']
)
