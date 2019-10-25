from os import system
import pathlib
from setuptools import setup, find_packages
import sys


# 'setup.py publish' shortcut.
if sys.argv[-1] == 'publish':
    system('python setup.py sdist bdist_wheel')
    system('twine upload dist/*')
    sys.exit()

if sys.version_info < (3, 6, 0):
    raise RuntimeError("audible requires Python 3.6.0+")

here = pathlib.Path(__file__).parent

about = {}
exec((here / 'src' / 'audible' / '_version.py').read_text('utf-8'), about)

long_description = (here / 'README.md').read_text('utf-8')

requires = (here / 'requirements.txt').read_text('utf-8').split()


setup(
    name=about['__title__'],
    version=about['__version__'],
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    description=about['__description__'],
    url=about['__url__'],
    license=about['__license__'],
    author=about['__author__'],
    author_email=about['__author_email__'],
    classifiers=[
         'Development Status :: 4 - Beta',
         'Intended Audience :: Developers',
         'License :: OSI Approved :: GNU Affero General Public License v3',
         'Programming Language :: Python :: 3.6',
         'Programming Language :: Python :: 3.7',
         'Programming Language :: Python :: 3.8'
    ],
    install_requires=requires,
    python_requires='>=3.6',
    keywords='Audible, API, async',
    long_description=long_description,
    long_description_content_type='text/markdown',
)
