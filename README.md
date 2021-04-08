# gospl recipes

## Overview

This online documentation provides some examples of *pre-* and *post-* processing techniques used to run different **[gospl](https://gospl.readthedocs.io/en/latest/index.html#module-gospl)** simulations and extract useful information from them. 


**[gospl](https://gospl.readthedocs.io/en/latest/index.html#module-gospl)** (short for `Global Scalable Paleo Landscape Evolution`) is an open source, GPL-licensed library providing a scalable parallelised Python-based numerical model to simulate landscapes and basins reconstruction at global scale.

For an overview of **[gospl](https://gospl.readthedocs.io/en/latest/index.html#module-gospl)** functionalities readers are invited to go through the online documentation:

1. the [technical guide](https://gospl.readthedocs.io/en/latest/tech_guide/index.html#tech-guide) provides in-depth information on the underlying physics,
2. the [getting started](https://gospl.readthedocs.io/en/latest/getting_started/index.html#getting-started) pages shows how to install the code itself, but the following sections will provide additional information on that as well,
3. the complete list of input file parameters is describe in the [user guide](https://gospl.readthedocs.io/en/latest/user_guide/inputfile.html#inputfile) section, 
4. the [API reference](https://gospl.readthedocs.io/en/latest/api_ref/index.html#api-ref) describes how methods work and functions have been declared.


### Citing

To cite `gospl` please use following [software paper](https://doi.org/10.21105/joss.XXXXX)
published in the JOSS.

Salles et al. (2020) `gospl: Global Scalable Paleo Landscape Evolution`, Journal of Open
Source Software, 5(56), p. 2804. doi: 10.21105/joss.02804.


    @article{salles_2020,
        author={Salles, Tristan and Mallard, Claire and Zahirovic, Sabin},
        title={gospl: Global Scalable Paleo Landscape Evolution},
        journal={Journal of Open Source Software},
        year={2020},
        volume={5},
        number={56},
        pages={2804},
        DOI={10.21105/joss.02804}
    }

## How to use these recipies

This documentation is written as an online companion to **[gospl](https://gospl.readthedocs.io/en/latest/index.html#module-gospl)** simulation. The examples and *pre-* and *post-* processing methods are actualised on the go, as we develop them. 

We are trying to write them in such a way that they are quickly understandable and modifiable to fit with your specific simulation. If you are starting to use **[gospl](https://gospl.readthedocs.io/en/latest/index.html#module-gospl)**, we strongly recommend to go through several of these examples to familiarise yourself with the code capabilities and input/output formats.


## Contributing 

Contributions of any kind to `gospl` and this documentation are more than welcome. That does not mean new code only, but also improvements of documentation and user guide, additional tests (ideally filling the gaps in existing suite) or bug report or idea what could be added or done better.

All contributions should go through our GitHub repository. Bug reports, ideas or even questions should be raised by opening an issue on the GitHub tracker. Suggestions for changes in code or documentation should be submitted as a pull request. However, if you are not sure what to do, feel free to open an issue. All discussion will then take place on GitHub to keep the development of `gospl` transparent.

If you decide to contribute to the codebase, ensure that you are using an up-to-date `main` branch. The latest development version will always be there, including the documentation (powered by `sphinx`).

Details are available in the contributing guide.
