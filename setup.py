from setuptools import setup, find_namespace_packages

setup(
    name='pymodelcat',
    version='0.0.2',
    description='Code used in building and maintaining the experimental USGS Model Catalog',
    url='http://github.com/usgs-biolab/pymodelcat',
    author='R. Sky Bristol',
    author_email='sbristol@usgs.gov',
    license='unlicense',
    packages=find_namespace_packages(),
    scripts=[
        'bin/update_modelcat_abstract'
    ],
    install_requires=[
        'requests',
        'sciencebasepy',
        'pandas',
        'qgrid',
        'markdown'
    ],
    zip_safe=False
)
