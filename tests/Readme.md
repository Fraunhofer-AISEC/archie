# Test environment
For ARCHIE we use pytest as test environment for python.
For C currently no test environment exists.
However the python test environment can be used to detect if the behaviour of the faultplugin is the same.

## Pytest
If you want to use the test environment please install the requirements listed in [requriements.txt](requrements.txt).
It will install black and pytest.
Black is used for formating and checking format compliance.
The requirements contains also pytest plugins.
These are cov, xdist and order:
* Cov can be used to generate a coverage report of the python code.
* xdist can be used to run tests in parrallel
* order allows to specify in which order the tests are run.

All tests must be run from the ARCHIE root directory, aka in the parent folder of this folder.

If you want to test your changes you can run 
```
./test.sh
```
It will call make of the faultplugin, test if your code is black compliant and then run pytest.
If everything passes we welcome you to open a Pull request to merge your changes.

If you only want to run pytest:
```
pytest
```

If you want a coverage report in html format:
```
pytest --cov=. --cov-report html --cov-branch
```
If you dont want html remove it from the command

If you want to run your test in parallel use:
```
pytest -n {Number of Workers here}
```

You can combine these option if you like.

### Trouble shooting
If pytest is throwing errors that it can not import ARCHIE files it is most likely that ARCHIE was not added to the search path correctly.
Please open an issue so that we can troubleshoot the issue. You can temporally circumvent the problem by using:
```
python3 -m pytest
```

