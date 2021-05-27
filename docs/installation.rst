Installation
============

The Andalus Judge server  is the central entity that runs the Andalus Judge web interface and API that 
teams, jury members and the judgehosts connect to.

.. admonition:: Requirements

    System requirements
        The operating system is Linux or another Unix variant. Andalus Judge has mostly been tested with 
        Debian and Ubuntu, but should work on other environments.

        It is probably necessary that you have root access to be able to install the necessary components, 
        but it’s not required for actually running the Andalus Judge.

        A TCP/IP network which connects the Andalus Judge, the judgehosts, and the team workstations. 
        All of these machines only need HTTP(S) access to the Andalus Judge.

    Software requirements
        Python >= 3.6 

        A web server with support for Django >= 2..0.7 

        Postgresql >= 10.16 database. 

    Online Resource
        The library source repository currently lives on GitHub at the following URL

        Team, Jury and admin workstation
            https://github.com/Andalus-ICPC/aoj-backend

        Judge Host
            https://github.com/Andalus-ICPC/aoj-judger
            
            https://github.com/Andalus-ICPC/SandboxCommandRunner

Installation Procedure
----------------------
 
Install python3 
```````````````

version (recommended >=3.6)
 
Creating Python Virtual Environment
```````````````````````````````````
    python3 -m venv /path/venv
 
Install dependencies
````````````````````
 
Right there, you will find the requirements.txt file that has all the great debugging tools, django 
helpers and some other cool stuff. To install them, simply type::

    pip install -r requirements.txt

Initialize the database for Judge
`````````````````````````````````

First set the database engine (Postgresql >= 10.16, MySQL, etc..) in your settings files; 
projectname/settings.py . Of course, remember to install the necessary database driver for your engine. 
Then define your credentials as well. Time to finish it up.

If you have no database engine or driver, use the default database that is sqlite3. 
comment mysql configuration and uncomment sqlite3 in projectname/settings.py::

    python manage.py migrate

create super user it is super admin/database admin, simply type::

    python manage.py createsuperuser

and create admin of the system from the user table by selecting the admin role in the django admin site.
Ready? Go!

Run the following 2 bash commands from aoj-backend/start-and-run-servers
	bash django

	bash redis

Installation Procedure for Judgehost
------------------------------------
 
install Python3 (recommended >=3.6)
 
Creating Python Virtual Environment
 
Install dependencies
````````````````````
 
Right there, you will find the requirements.txt file that has all the great debugging tools, 
flask and celery helpers and some other cool stuff. To install them, simply type::

    pip install -r requirements.txt

Install compilers for the programming languages
Ready? Go!

Run the following 2 bash commands from aoj-backend/start-and-run-servers
	bash celery

	sudo bash flask

