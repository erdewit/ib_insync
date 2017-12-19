import os
import sys
import codecs
from setuptools import setup
from warnings import warn

import ib_insync

if sys.version_info < (3, 0, 0):
    raise RuntimeError("ib_insync is for Python 3")

if sys.version_info < (3, 6, 0):
    warn("ib_insync requires Python 3.6 or higher")

here = os.path.abspath(os.path.dirname(__file__))
with codecs.open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='ib_insync',
    version=ib_insync.__version__,
    description='Python sync/async framework for Interactive Brokers API',
    long_description=long_description,
    url='https://github.com/erdewit/ib_insync',
    author='Ewald R. de Wit',
    author_email='ewald.de.wit@gmail.com',
    license='BSD',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Office/Business :: Financial :: Investment',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
    ],
    keywords='ibapi asyncio jupyter interactive brokers async',
    packages=['ib_insync']
)
