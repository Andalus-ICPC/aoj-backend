Overview
========

Andalus Judge is a system for running programming contests, like the ICPC regional and world finals 
programming contests.
This usually means that teams are on-site and have a fixed time period (mostly 5 hours) and one computer 
to solve a number of problems (mostly 8-12). Problems are solved by writing a program in one of the allowed
programming languages(Python, C/C++, Java), that reads input according to the problem input specification 
and writes the correct, corresponding output.
The judging is done by submitting the source code of the solution to the jury. 
There the jury system automatically compiles and runs the program and compares the program output with 
the expected output.
This software can handle the submission and judging during such contests. It also handles feedback to the 
teams(clarification from jury) and helps on communication between teams and jury on problems 
(clarification requests). It has web interfaces for the jury, the teams (their submissions and 
clarification requests) and the public (scoreboard).

.. admonition:: Features

    A global overview of the features that Andalus Judge provides
        Automatic judging with distributed (scalable) judge hosts

        Web interface for portability and simplicity
        
        Modular system for plugging in languages/compilers and validators
        
        Detailed jury information (submissions, judgings, diffs) and options (rejudge, clarifications)
        
        Designed with security in mind

.. admonition:: Requirements and contest planning

    Andalus requires the following to be available to run. 
        At least one machine to act as the Andalus Judge server. The machine needs to be running 
        Linux (or possibly a Unix variant) and a web server with Django 2.0.7 or newer. 
        A Postgresql >= 10.16 database is also needed.

        A number of machines to act as judgehosts (at least one). They need to run Linux with (sudo) 
        root access. Required software is Flask and compilers for the languages you want to support.

        Team workstations, one for each team. They require only a modern web browser to interface with 
        Andalus Judge, but of course need a local development environment for teams to develop and test 
        solutions. Optionally these have the Andalus Judge submit client installed.

        Jury / admin workstations. The jury members (persons) that want to configure and monitor the 
        contest need just any workstation with a web browser to access the web interface. No Andalus 
        Judge software runs on these machines.
 
One (virtual) machine is required to run the Andalus Judge Server. The minimum amount of judgehosts 
is also one, but preferably more: depending on configured time limits, and the amount of test cases 
per problem, judging one solution can tie up a judgehost for several minutes, and if there’s a problem 
with one judgehost it can be resolved while judging continues on the others.

As a rule of thumb, we recommend one judgehost per 20 teams.
However, overprovisioning does not hurt: Andalus Judge scales easily in the number of judgehosts, 
so if hardware is available, by all means use it. But running a contest with fewer machines will equally 
work well, only the waiting time for teams to receive an answer may increase.

Each judgehost should be a dedicated (virtual) machine that performs no other tasks. For example, although 
running a judgehost on the same machine as the judgeserver is possible, it’s not recommended except for 
testing purposes. Judgehosts should also not double as local workstations for jury members. Having all 
judgehosts be of uniform hardware configuration helps in creating a fair, reproducible setup; in the ideal 
case they are run on the same type of machines that the teams use.

Copyright and Licensing
-----------------------

Andalus Judge is developed by ``Mukerem Ali``, ``Mustefa Kamil`` and ``Amir Kheiru``. Many other people 
have contributed: ``Abdi Adem``, ``Elias Amha``, ``Temkin Mengistu``, ``Mebatsion Sahle``. 

 Andalus Judge is Copyright (c) |2018 - 2021| by the Andalus Judge developers and contributors.

