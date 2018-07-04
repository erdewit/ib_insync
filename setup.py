import os
import sys
import codecs
import ast
from setuptools import setup
from warnings import warn

if sys.version_info < (3, 0, 0):
    raise RuntimeError("ib_insync is for Python 3")

if sys.version_info < (3, 6, 0):
    warn("ib_insync requires Python 3.6 or higher")

here = os.path.abspath(os.path.dirname(__file__))
with codecs.open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# find __init__ assignments due to runtime ibapi checks preventing import
with codecs.open(os.path.join(here, 'ib_insync', '__init__.py')) as f:
    # extract top level assignment statements
    nodes = ast.parse(f.read())
    assigns = [ n for n in nodes.body if isinstance(n, ast.Assign) ]
    # execute just assignment statments from __init__ into ib_insync
    ib_insync = {}
    exec(compile(ast.Module(assigns), '<setup>', 'exec'), ib_insync)



setup(
    name='ib_insync',
    version=ib_insync['__version__'],
    description='Python sync/async framework for Interactive Brokers API',
    long_description=long_description,
    url='https://github.com/erdewit/ib_insync',
    author=ib_insync['__author__'],
    author_email=ib_insync['__email__'],
    license=ib_insync['__license__'],
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
