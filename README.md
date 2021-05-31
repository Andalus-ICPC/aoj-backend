# Andalus Installation Guide

This is a brief guide on how to install the Andalus Online Judge System on your machine.

Before any installation make sure you have the latest version of Python 3 installed on your machine and the path is configured properly, also since we are using a virtual environment make sure you you have virtual environment of your choice.

But if you don't have a virtual environment install it using the following command first.

Mainly the OS on your machine should be a linux based OS. This means all the following commands are not guaranteed to work on Windows machine.

```sh
pip install virtualenv
```

#### Step 1: Create a folder that will contain everything, then go into the folder :file_folder:

#### Step 2: Now pull the necessary files from github :arrow_double_down:

The following clones the backend
```sh
git clone https://github.com/Andalus-ICPC/aoj-backend.git
```

The following clones the judger
```sh
git clone https://github.com/Andalus-ICPC/aoj-judger.git
```

The following clones the sandbox
```sh
git clone https://github.com/Andalus-ICPC/SandboxCommandRunner.git
```

The following clones redis
```sh
git clone https://github.com/redis/redis.git
```

#### Step 3: Now let's get to them one by one

- For the backend

```sh
cd aoj-backend
```

Now create a virtual environment
```sh
python -m virtualenv env
```
But if you are on linux and you are getting an error, try the following command
```sh
python3 -m virtualenv env
```
This will create a vritual environment named `env` inside `aoj-backend`

Activate the virtual environment
For linux
```sh
source /env/bin/activate
```

Then install all the requirements
```sh
pip install -r requirements.txt
```
But if you are on linux and you are getting an error, try the following command
```sh
pip3 install -r requirements.txt
```

- For the judger

```sh
cd aoj-judger
```

Now create a virtual environment
```sh
python -m virtualenv env
```
But if you are on linux and you are getting an error, try the following command
```sh
python3 -m virtualenv env
```
This will create a vritual environment named `env` inside `aoj-backend`

Activate the virtual environment
For linux
```sh
source /env/bin/activate
```

Then install all the requirements
```sh
pip install -r requirements.txt
```
But if you are on linux and you are getting an error, try the following command
```sh
pip3 install -r requirements.txt
```

- For the sandbox

```sh
cd SandboxCommandRunner
```

Here we don't need any virtual environment, we just execute the following commands.

```sh
sudo apt-get install libseccomp-dev
```

```sh
mkdir build && cd build && cmake .. && make && sudo make install && cd ..
```

```sh
sudo python3 bindings/python/setup.py install
```

- For redis

```sh
cd redis
```

```sh
make
```

#### Step 4: We are almost there, just a few configurations left :tired_face:

- Now go to `aoj-backend` and setup where and how to run the scripts

Inside the `start-and-run-servers` folder, you will get 5 files, but we will only need 3 of them, `celery`, `django` and `redis`

- Inside `celery`

You will get this line: `source /home/andalus/Documents/django/Andalus-Judge-Repo/aoj-backend/env/bin/activate && cd /home/andalus/Documents/django/Andalus-Judge-Repo/aoj-backend && celery -A AOJ worker -l INFO --concurrency=10`

**Change** `/home/andalus/Documents/django/Andalus-Judge-Repo/aoj-backend/` to the path where your `aoj-backend` lives on both the places.

- Inside `django`

You will get this line: `source /home/andalus/Documents/django/Andalus-Judge-Repo/aoj-backend/env/bin/activate && python /home/andalus/Documents/django/Andalus-Judge-Repo/aoj-backend/manage.py runserver 0:8000`

**Change** `/home/andalus/Documents/django/Andalus-Judge-Repo/aoj-backend/` to the path where your `aoj-backend` lives.


- Inside `redis`

You will get these lines: 
`source /home/andalus/Documents/django/Andalus-Judge-Repo/aoj-backend/env/bin/activate 
/home/andalus/Documents/django/Andalus-Judge-Repo/redis-6.2.1/src/redis-server`

**Change** `/home/andalus/Documents/django/Andalus-Judge-Repo/aoj-backend/` to the path where your `aoj-backend` lives.

**Change** `/home/andalus/Documents/django/Andalus-Judge-Repo/` to the path where your `redis` lives.

- Now go to `aoj-judger` and setup where and how to run one script

Inside the `start-and-run-flask` folder, you will get 1 file, `flask_run`

```
source /home/andalus/Documents/django/Andalus-Judge-Repo/aoj-judger/env/bin/activate && cd /home/andalus/Documents/django/Andalus-Judge-Repo/aoj-judger && export FLASK_APP=/home/andalus/Documents/django/Andalus-Judge-Repo/aoj-judger/server.py && flask run -h 0 -p 5000

# run as root
```

**Change** `/home/andalus/Documents/django/Andalus-Judge-Repo/aoj-judger/` to the path where your `aoj-judger` lives.

##### Step 5: Last Configuration, configuring the environment variable
First configure your database, our system uses postgres by default, but you can use mysql or any other django supported databases

Go to `aoj-backend`
```sh
cd aoj-backend
```

Then create a `.env` file
```sh
touch .env
```

Then open the `.env` file and change the following variables by your database configurations.

```
SECRET_KEY = "[&%lwmqytwig2o10=6hdvz9s%8whm8ie4yjprs0ne38@sxc6-qx]"
EMAIL_HOST_USER = "email"
EMAIL_HOST_PASSWORD = "password"
DB_NAME = "database_name"
DB_USER = "database_username"
DB_PASSWORD = "database_password"
DB_HOST = "host_address"
DB_PORT = "host_port"
```

##### Step 6: Finally run everything :thumbsup: :rocket:

For the `backend`
```sh
cd aoj-backend/start-and-run-servers
```

```sh
bash celery
```

```sh
bash django
```

```sh
bash redis
```

Then for the `judger`

```sh
cd aoj-judger/start-and-run-flask
```

```sh
sudo su
```

After you enter your credentials

```sh
bash flask_run
```
