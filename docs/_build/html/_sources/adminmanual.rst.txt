Admin Manual
============

Configuring the system
----------------------

Configuration of the judge system is done by logging in as administrator to the web interface.

Setting up users and teams
--------------------------

Under Users from the homepage you can add user accounts for the people accessing your system. 
There are several roles possible:

    Administrative User:
        can configure and change everything in Andalus Judge.
    Jury User:
        can view submissions ,clarification requests, users, problem, contest and leaderboard.
    Team User:
        can view its own team interface and submit solutions, send clarification requests.

So add users accordingly. For users registration there are two ways using csv format and manual 
adding users. 

The formats are as shown below:
    Figure 1 CSV format

    Figure 2 manual format

Resetting the password for a user

Adding a Problem
----------------
When registration is done, you can upload the intended problems that teams need to solve under Problems. 

.. figure:: img/add-problem.png
   :width: 80%

.. figure:: img/add-testcase.png
   :width: 80%

Andalus Judge supports uploading problems as a zip file or configuring each problem manually 
via the interface. You can add a problem to a contest by editing the contest from the Contests page later.

Time Limit is the maximum number of seconds a submission for this problem is allowed to run before a 
‘TIME LIMIT’ response is given (``to be multiplied possibly by a language factor``).

Error is  the maximum absolute difference between the test case output and user output for 
precision problems.

Adding a Contest
----------------

.. figure:: img/add-contest.png
   :width: 80%

You configure a new contest by adding it under the Contests link from the main page. Besides the name 
the most important configuration about a contest are the various time milestones.

A contest can be selected for viewing after its activation time, but the scoreboard will only become 
visible to the public and teams once the contest starts. Thus no data such as problems and teams is 
revealed before then.

When the contest ends, the scores will remain displayed until the deactivation time passes.

Andalus Judge has the option to ‘freeze’ the public and team scoreboards at some point during the contest. 
This means that scores are no longer updated and remain to be displayed as they were at the time of the 
freeze. This is often done to keep the last hour interesting for all. The scoreboard freeze time can be 
set with the frozentime milestone.

The scoreboard freezing works by looking at the time a submission is made. Therefore it’s possible that 
submissions from (just) before the frozen time but judged after it can still cause updates to the public 
scoreboard. A rejudging during the freeze may also cause such updates. The jury and admin interface will 
however always show the actual scoreboard.

Once the contest is over, the scores are not directly ‘unfrozen’. You can release the final scores to the 
team and public interfaces when the time is right. You can do this either by setting a predefined 
unfrozentime in the contest table.

All events happen at the first moment of the defined time. That is: for a contest with start time 
“12:00:00” and end time “17:00:00”, the first submission will be accepted at 12:00:00 and the last one 
at 16:59:59.

Clarification Requests
----------------------

Communication between teams and admin happens through Clarification Requests. Everything related to that 
is handled under the Clarifications menu item.

.. figure:: img/admin-clarification.png
   :width: 80%

   teams can use their web interface to send a clarification request to the admin. The admin can send a 
   response to that team specifically, or send it to all teams. The latter is done to ensure that all 
   teams have the same information about the problem set. The admin can also send a clarification that 
   does not correspond to a specific request. These will be termed general clarification.

Handling clarification requests
```````````````````````````````

Under Clarifications, three lists are shown: requested clarification list, new clarifications and 
answered clarifications.

.. figure:: img/admin-clarification-handle.png
   :width: 80%

Every incoming clarification request will initially be marked as unanswered. A request will be marked 
as answered when a response has been sent. Additionally it’s possible to mark a clarification request 
as answered with the button that can be found when viewing the request. 

An answer to a clarification request is made by putting the text in the input box under the request text. 
You can choose to either send it to the team that requested the clarification, or to all teams.

Judging topics
--------------

Flow of a submission
````````````````````

The flow of an incoming submission is as follows.
    1. Team submits solution.

    2. The first available judgehost compiles, runs and checks the submission. The outcome and outputs 
    are stored as a judging of this submission. 

    3. The result is automatically recorded and the team can view the result and the scoreboard is 
    updated (unless after the scoreboard freezes).

.. figure:: img/admin-submit.png
   :width: 80%

Rejudging
---------

In some situations it is necessary to rejudge one or more submissions. This means that the submission will 
re-enter the flow as if it had not been judged before. The submittime will be the original time, but the 
program will be compiled, run and tested again.

This can be useful when there was some kind of problem: a compiler that was broken and later fixed, or test 
data that was incorrect and later changed. When a submission is rejudged, the old judging data is replaced 
by the new one.

You can rejudge a single submission by pressing the ‘Rejudge’ button when viewing the submission details. 
It is also possible to rejudge all submissions for a given problem or result type by filtering based on 
a problem or result type., press the “start rejudging” button.

Teams will not get explicit notifications of rejudgings, other than a potentially changed outcome of their 
submissions. It might be desirable to combine rejudging with a clarification to the team or all teams 
explaining what has been rejudged and why.

Enforcement of time limits
--------------------------

Time limits within Andalus Judge are enforced primarily in CPU time. The way that time limits are 
calculated and passed through the system involves a number of steps.

Time limits are set per problem in seconds. Each language in turn may define a time factor (defaulting to 1) 
that multiplies it to get a specific time limit for that problem/language combination. The time limit is 
passed to runguard, the wrapper program that applies restrictions to submissions when they are being run, 
as both wall clock and CPU limit. This is used by runguard when reporting whether the actual time limit has 
been surpassed. The submitted program gets killed when CPU time has passed.

Definitions and Terms
---------------------

Judgehost is a computer with Andalus web interface, that is used to see users' submissions and 
rejudge the submissions.

Judge server  is a virtual machine or computer, that is the central entity that runs the Andalus 
Judge web interface and API that teams, jury members and the judgehosts connect to.

Workstation is a working computer with a browser to interact with the judge system.


Appendix
--------

.. admonition:: Problem format specification

    Andalus Judge supports the import of problems in a zip format.

    On top, Aandalus Judge defines a few extensions:
        ``info.ini`` (optional): metadata file, see below.

        ``problem.pdf`` (optional): problem statements as distributed to participants. 
        The file extension must be pdf formats.

        ``secret`` a folder that contain test case data for the problem

    The file ``info.ini`` contains key-value pairs, one pair per line, of the form key = value. 
    The = can optionally be surrounded by whitespace and the value may be quoted, which allows it to 
    contain newlines. 
    
    The following keys are supported (these correspond directly to the problem settings 
    in the admin web interface):
    ``title`` - the problem displayed name

    ``short_name`` - the problem short name displayed on scoreboard.(most of the time it is 
    represented by uppercase English letters)

    ``time_limit`` - time limit in seconds per test case

    ``error`` - the maximum absolute difference between the test case output and user output for 
    precision problems (defaults 0.0000)

    ``point`` - number of points for this problem (defaults to 1)

    ``ballon`` - balloon color of the problem in hexadecimal representation for example “#ff0000” 
    represent red color (defaults to white)

    The basename of the ``ZIP-file`` will be used as the problem short name (e.g. “A”). error, point and 
    balloon keys are optional. If they are present, the respective value will be overwritten; if not 
    present, then a default chosen when creating a new problem.

