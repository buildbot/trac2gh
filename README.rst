=======
trac2gh
=======

tools and sandbox (tools will stay in a separate repo)


Usage
~~~~~

This tools uses the real trac parser, and github3.py
You can download the deps by using pipenv

.. code-block:: bash

    # (sudo pip install pipenv)
    pipenv install
    . ./.venv/bin/activate

You will need to download the full trac working directory, so that trac is happy, and make the config file point to that copy

.. code-block:: bash

    cp config.sample ~/trac2gh-config
    # edit config to match your needs
    trac2gh trac2gh ~/trac2gh-config

In this form, the script can take a long time, and probably is not the best suited, you can also run it in three runs


First script will dump the database to a json file.
This can take a long time especially if your mysql database is not in the same network

.. code-block:: bash

    trac2gh trac2json ~/trac2gh-config dump.json

Second script can be used to make sure the users are correctly mapped to github.
In the end the list of unmapped users is printed, with the number of contributions.
This allows you to manually find out the mapping for relevent contributors only

.. code-block:: bash

    trac2gh build-user-mapping ~/trac2gh-config dump.json

Third script is creating the issues in Github, and marking the tickets as migrated.

.. code-block:: bash

    trac2gh json2gh ~/trac2gh-config dump.json
