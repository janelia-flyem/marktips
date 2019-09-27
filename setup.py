from setuptools import setup, find_packages

import versioneer
 
requirements = [
    'requests',
    'dvidtools'
]

setup(
    name='marktips',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="mark skeleton tips for review",
    author="Donald J. Olbris",
    author_email='olbrisd@janelia.hhmi.org',
    url='https://github.com/janelia-flyem/marktips',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'marktips=marktips.marktips:main',
            'marktipshistory=marktips.marktipshistory:main',
        ]
    },
    install_requires=requirements,
)