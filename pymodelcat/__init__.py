# pymodelcat package

import pkg_resources

from . import catbuilder

__version__ = pkg_resources.require("pymodelcat")[0].version


def get_package_metadata():
    d = pkg_resources.get_distribution('pymodelcat')
    for i in d._get_metadata(d.PKG_INFO):
        print(i)

