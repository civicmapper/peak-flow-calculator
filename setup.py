from setuptools import setup, find_packages

setup(
    name='ccem',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'numpy',
        'petl',
        'pint'
    ],
    entry_points='''
        [console_scripts]
        peakflow_lite=core.peakflow_cli:lite
        peakflow_full=core.peakflow_cli:full
        cn_prep=core.peakflow_cli:prepare_cn_raster
    '''
)