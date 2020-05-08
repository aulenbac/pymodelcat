from setuptools import setup

setup(
    name='pymodelcat',
    version='0.0.1',
    description='Code used in building and maintaining the experimental USGS Model Catalog',
    url='http://github.com/usgs-biolab/pymodelcat',
    author='R. Sky Bristol',
    author_email='sbristol@usgs.gov',
    license='unlicense',
    packages=['pymodelcat'],
    install_requires=[
        'requests',
        'sciencebasepy',
        'pandas',
        'qgrid'
    ],
    zip_safe=False
)
