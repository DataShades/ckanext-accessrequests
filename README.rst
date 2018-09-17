------------------------------------------------------------------------------------------
ckanext-accessrequests
------------------------------------------------------------------------------------------

A user who has an Admin role in the top-level organisation has able to access the list of requests and approve/reject requests (he can approve/reject users)

------------
Requirements
------------

For example, you might want to mention here which versions of CKAN this
extension works with.


------------
Installation
------------

.. Add any additional install steps to the list below.
   For example installing any non-Python dependencies or adding any required
   config settings.

To install ckanext-accessrequests:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-accessrequests Python package into your virtual environment::

     pip install ckanext-accessrequests

3. Add ``accessrequests`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload


Configuration
=============

Set configuration options in ini file::

  ckan.plugins = accessrequests

  # admin email for receiving info about new users requests
  ckanext.accessrequests.approver_email = email@example.com

  # list of roles that are not available during access request process
  ckanext.accessrequests.restricted_roles = creator admin
------------------------
Development Installation
------------------------

To install ckanext-accessrequests for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/DataShades/ckanext-accessrequests.git
    cd ckanext-accessrequests
    python setup.py develop
    pip install -r dev-requirements.txt


-----------------
Running the Tests
-----------------

To run the tests, do::

    nosetests --nologcapture --with-pylons=test.ini

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run::

    nosetests --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.accessrequests --cover-inclusive --cover-erase --cover-tests


------------------------------------------------------------------------------------------
Registering ckanext-accessrequests on PyPI
------------------------------------------------------------------------------------------

ckanext-accessrequests should be availabe on PyPI as
https://pypi.python.org/pypi/ckanext-accessrequests. If that link doesn't work, then
you can register the project on PyPI for the first time by following these
steps:

1. Create a source distribution of the project::

     python setup.py sdist

2. Register the project::

     python setup.py register

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the first release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.1 then do::

       git tag 0.0.1
       git push --tags


------------------------------------------------------------------------------------------
Releasing a New Version of ckanext-accessrequests
------------------------------------------------------------------------------------------

ckanext-accessrequests is availabe on PyPI as https://pypi.python.org/pypi/ckanext-accessrequests.
To publish a new version to PyPI follow these steps:

1. Update the version number in the ``setup.py`` file.
   See `PEP 440 <http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers>`_
   for how to choose version numbers.

2. Create a source distribution of the new version::

     python setup.py sdist

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the new release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.2 then do::

       git tag 0.0.2
       git push --tags
