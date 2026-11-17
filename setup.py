from setuptools import setup,find_packages
setup(name='amk_tools',
      version='1.1',
      author="Diego Garay-Ruiz",
      description="RxN management for AutoMeKin",
      py_modules=['RXReader','RXVisualizer','amk_assets'],
      # install the command-line tools into the environment's bin/, so 'amk_gen_view.py' works
      # anywhere once the env is active (and takes precedence over older copies on PATH)
      scripts=['scripts/amk_gen_view.py','scripts/amk_rxn_stats.py'],
      python_requires='>=3.10',
      # Aligned with the AutoMeKin-X environment (automekin.yml): Python 3.11, numpy 2.x,
      # networkx 3.x. Bokeh 3.9 is the last series supporting Python 3.10/3.11.
      # The JSmol viewer no longer needs jsmol_to_bokeh (Bokeh 2 only) nor NodeJS.
      install_requires=['networkx>=3.0','bokeh>=3.4,<4','matplotlib>=3.7',
                        'numpy>=1.24','scipy>=1.10']
      )
