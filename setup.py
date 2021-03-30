'''
setup.py for accpy-pm 

For reference see
https://packaging.python.org/guides/distributing-packages-using-setuptools/

'''
from pathlib import Path
from setuptools import setup, find_packages

HERE = Path(__file__).parent.absolute()
with (HERE / 'README.md').open('rt') as fh:
    LONG_DESCRIPTION = fh.read().strip()

REQUIREMENTS: dict = {
    'core': ['pyfgc_name',
            'cx_Oracle',
    ],
    'test': [
        'pytest',
    ],
    'dev': [
        # 'requirement-for-development-purposes-only',
    ],
    'doc': [
        'sphinx',
    ],
}

setup(
    name='spare-manager',
    version='1.0.1',

    author='cghabrou',
    author_email='carlos.ghabrous@cern.ch',
    description='Spare system manager',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    url='https://gitlab.cern.ch/ccs/fgc/tree/master/sw/clients/python/spare_manager',

    packages=find_packages(),
    python_requires='>=3.6, <4',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],

    install_requires=REQUIREMENTS['core'],
    extras_require={
        **REQUIREMENTS,
        # The 'dev' extra is the union of 'test' and 'doc', with an option
        # to have explicit development dependencies listed.
        'dev': [req
                for extra in ['dev', 'test', 'doc']
                for req in REQUIREMENTS.get(extra, [])],
        # The 'all' extra is the union of all requirements.
        'all': [req for reqs in REQUIREMENTS.values() for req in reqs],
    },
    data_files=[('spare_manager', ['spare_manager_launcher.sh']), 
                ('lib64/python3.6/site-packages/spare_manager', ['spare_manager/create_config_view.ui', 'spare_manager/activate_config_view.ui'])
                ]
)
