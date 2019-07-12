from setuptools import setup, find_packages

from marktips.version import version

requirements = [
    'requests',
    'dvidtools'
]

setup(
    name='marktips',
    version=version,
    description="mark skeleton tips for review",
    author="Donald J. Olbris",
    author_email='olbrisd@janelia.hhmi.org',
    url='https://github.com/janelia-flyem/marktips',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'marktips=marktips.marktips:main'
        ]
    },
    install_requires=requirements,
)