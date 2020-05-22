[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/usgs-biolab/pymodelcat/) [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/usgs-biolab/pymodelcat/master)

# pyModelCat

This python package and its repository are set up as a collaborative tool and info-space for building out the USGS Model Catalog, an experimental extension on other cataloging efforts for data, software, and publications. The model catalog is being built in [ScienceBase](https://www.sciencebase.gov/) as a collection of items describing various kinds of models. Model items in ScienceBase are essentially rallying points around the concept of a model that help to bring together all of the disparate information associated with the modeling activity including publications and web pages, modeling source code, information and references to model inputs, model output datasets (often referred to as "the model" when they are used in analysis), and other artifacts. We are working to build and manage the catalog with code as much as possible as opposed to using user interfaces, and this repo contains packaged software for that purpose along with documentation, examples, and other parts of the system we are bringing together.

# Quick Start

If you are just after the pymodelcat package, you can install the latest master with:

```pip install git+git://github.com/usgs-biolab/pymodelcat.git@master```

Note: You can, and may want to, use the environment.yml to create a separate Python environment for this tool.

# Console Scripts

The following console scripts are available following installation:

* update_modelcat_abstract - Updates the USGS Model Catalog abstract (body) with content from the usgs_model_cat_abstract.md file in this repository. Requires ScienceBase authentication and authorization to update the item. An alternate item identifier can be supplied as an argument along with specifying whether or not to convert markdown to HTML.