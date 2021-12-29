from django.shortcuts import render, get_object_or_404, redirect, HttpResponse
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from authentication.decorators import contestant_auth, admin_auth, admin_auth_and_submit_exist,\
    admin_auth_and_contest_exist, admin_or_jury_auth, admin_jury_auth_and_contest_exist,\
    admin_jury_auth_and_submit_exist, admin_site_jury_auth, admin_site_jury_auth_and_contest_exist,\
    admin_site_jury_auth_and_submit_exist
from django.db import IntegrityError
from django.core.files import File
from contest.models import Contest
from django.utils import timezone
from django.contrib import messages
from .forms import SubmitAnswer, SubmitWithEditor
from .models import Language, Submit, TestcaseOutput, ScorecacheJury, ScorecachePublic, RankcacheJury, RankcachePublic
from problem.models import TestCase, Problem
from control.models import Setting
from authentication.views import check_base_site
from authentication.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.core import serializers
import os
import time
import datetime
import math
import json
import subprocess
import re
import sys
from threading import Timer
import multiprocessing
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import BytesIO
from problem.views import update_statistics
import requests
from .judge_background import judge_background
from contest.views import rank_update_unfrozen, create_contest_session_admin, create_contest_session_contestant,\
    refresh_contest_session_admin, refresh_contest_session_contestant, refresh_contest_session_public
from authentication.pagination import pagination

def time_gap(submit_time, contest_start_time):
    td = submit_time - contest_start_time
    time_taken = td.seconds // 60 + td.days * 1400
    return time_taken


def setting_values():
    try:
        punish_value = Setting.objects.get(name="punish time").value
    except Setting.DoesNotExist:
        punish_value = 20

    try:
        rating_correct_value = Setting.objects.get(
            name="rating correct value").value
    except Setting.DoesNotExist:
        rating_correct_value = 20

    try:
        rating_punish_value = Setting.objects.get(
            name="rating punish value").value
    except Setting.DoesNotExist:
        rating_punish_value = 1

    return (punish_value, rating_correct_value, rating_punish_value)


def problem_lists(request):
    active_contest_id = request.session.get('active_contest_contestant')
    start_contest_id = request.session.get('start_contest_contestant')

    if not active_contest_id:
        return {'problem': [], 'contest_title': None, 'start_time': None}
    try:
        start_contest = Contest.objects.get(pk=start_contest_id)
        problem = start_contest.problem.all()
    except Contest.DoesNotExist:
        problem = []

    try:
        active_contest = Contest.objects.get(pk=active_contest_id)
        contest_title = active_contest.title
        start_time = active_contest.start_time
    except Contest.DoesNotExist:
        contest_title = None
        start_time = None

    problem = sorted(problem, key=lambda x: x.title.lower())
    problem, paginator = pagination(request, problem)
    return {'problem': problem, 'paginator': paginator, 'contest_title': contest_title, 'start_time': start_time, 'pro': 'hover'}


@login_required
@contestant_auth
def active_contest_problem(request):
    refresh_contest_session_contestant(request)  # refersh the contest session
    data = problem_lists(request)
    return render(request, 'problem.html', data)


def read_source_code(files):
    try:
        files.open(mode='r')  
    except (FileNotFoundError, ValueError):
        return "FileNotFoundError\nNo such file or directory"
    try:
        file_list = files.readlines()
    except UnicodeDecodeError:
        file_list = []
    submit_file = ''
    for i in file_list:
        submit_file += i
    files.close()
    return submit_file


def read_from_file(files):
    max_byte = 50
    files.open(mode='r')
    try:
        # file_list = files.readlines(max_byte)
        N = 100
        file_list = [line for line in [files.readline()
                                       for _ in range(N)] if len(line)]

    except UnicodeDecodeError:
        file_list = []
    submit_file = ''
    for i in file_list:
        submit_file += i
    files.seek(0, os.SEEK_END)
    file_size = files.tell()
    files.close()
    if file_size > max_byte:
        submit_file += "\n..."
    # print(files, file_list)
    return submit_file


def java_class_name_find(source, path):
    main_function_patter = r'(\s)*(public|static)(\s)+(public|static)(\s)+void(\s)+main(\s)*\('
    class_name_patter = r'(?s:.*)(\s)*class(\s)*(?P<class_name>[a-zA-Z_][a-zA-Z0-9_]*)'

    found = re.search(main_function_patter, source)
    if found is None:
        return path

    last_pos = found.end()
    text = source[:last_pos]

    class_params = re.search(class_name_patter, text)
    if class_params is None:
        return path
    
    class_name = f"{class_params.group('class_name')}.java"
    return class_name

    '''
    ind  = source.find('public static void main')
    if ind == -1:
        return path


    text = source[:ind]
    ind  = text.rfind('class')
    if ind == -1:
        return path

    text = text[ind + len('class'):]

    ind1  = text.find('{')
    if ind == -1:
        return path

    class_name = text[:ind1]
    class_name = class_name.replace(' ', '')

    if not class_name:
        return path
    return class_name+'.java'
    '''

def rank_update(submit):
    if not submit.user.role.short_name == "contestant":
        return
    if not submit.result:
        return
    if submit.submit_time < submit.contest.start_time:
        return
    if submit.submit_time >= submit.contest.end_time:
        return
    pro = submit.problem
    contest = submit.contest
    this_problem_prevous_correct_submit = Submit.objects.filter(
        contest=contest, problem=pro, result='Correct', submit_time__lte=submit.submit_time, user=submit.user).exclude(pk=submit.pk)
    if this_problem_prevous_correct_submit:
        return

    try:
        rank_cache = RankcacheJury.objects.get(
            user=submit.user, contest=contest)
    except RankcacheJury.DoesNotExist:
        rank_cache = RankcacheJury(user=submit.user, contest=contest)
        rank_cache.save()

    try:
        rank_cache_public = RankcachePublic.objects.get(
            user=submit.user, contest=contest)
    except RankcachePublic.DoesNotExist:
        rank_cache_public = RankcachePublic(user=submit.user, contest=contest)
        rank_cache_public.save()

    try:
        score_cache = ScorecacheJury.objects.get(
            rank_cache=rank_cache, problem=pro)
    except ScorecacheJury.DoesNotExist:
        score_cache = ScorecacheJury(rank_cache=rank_cache, problem=pro)
        score_cache.save()

    try:
        score_cache_public = ScorecachePublic.objects.get(
            rank_cache=rank_cache_public, problem=pro)
    except ScorecachePublic.DoesNotExist:
        score_cache_public = ScorecachePublic(
            rank_cache=rank_cache_public, problem=pro)
        score_cache_public.save()

    if score_cache.is_correct:
        return
    score_cache.submission += 1
    if submit.result == "Correct":
        score_cache.is_correct = True
        score_cache.correct_submit_time = submit.submit_time
    elif submit.result == "Compiler Error":
        pass
    else:
        score_cache.punish += 1
    score_cache.save()

    if submit.result == "Correct":
        punish_value, rating_correct_value, rating_punish_value = setting_values()
        rank_cache.point = (float(rank_cache.point) + float(pro.point))
        rank_cache.punish_time += punish_value * score_cache.punish + \
            time_gap(score_cache.correct_submit_time, contest.start_time)
        rank_cache.save()
        if contest.has_value:  # rating update
            user = submit.user
            user.rating += (rating_correct_value -
                            rating_punish_value * score_cache.punish)
            user.save()

    if contest.frozen_time and contest.unfrozen_time and contest.frozen_time <= submit.submit_time and submit.submit_time < contest.unfrozen_time:
        score_cache_public.submission += 1
        score_cache_public.pending += 1
        score_cache_public.save()
    else:
        rank_cache_public.point = rank_cache.point
        rank_cache_public.punish_time = rank_cache.punish_time
        rank_cache_public.save()

        score_cache_public.submission = score_cache.submission
        score_cache_public.punish = score_cache.punish
        score_cache_public.correct_submit_time = score_cache.correct_submit_time
        score_cache_public.is_correct = score_cache.is_correct
        score_cache_public.save()

def judge_rank_update(submit):

    if not submit.user.role.short_name == "contestant":
        return
    if not submit.result:
        return
    if submit.submit_time < submit.contest.start_time:
        return
    if submit.submit_time >= submit.contest.end_time:
        return
    pro = submit.problem
    contest = submit.contest
    this_problem_prevous_correct_submit = Submit.objects.filter(
        contest=contest, problem=pro, result='Correct', submit_time__lte=submit.submit_time, user=submit.user).exclude(pk=submit.pk)
    if this_problem_prevous_correct_submit:
        return

    try:
        rank_cache = RankcacheJury.objects.get(
            user=submit.user, contest=contest)
    except RankcacheJury.DoesNotExist:
        rank_cache = RankcacheJury(user=submit.user, contest=contest)
        rank_cache.save()

    try:
        rank_cache_public = RankcachePublic.objects.get(
            user=submit.user, contest=contest)
    except RankcachePublic.DoesNotExist:
        rank_cache_public = RankcachePublic(user=submit.user, contest=contest)
        rank_cache_public.save()

    try:
        score_cache = ScorecacheJury.objects.get(
            rank_cache=rank_cache, problem=pro)
    except ScorecacheJury.DoesNotExist:
        score_cache = ScorecacheJury(rank_cache=rank_cache, problem=pro)
        score_cache.save()

    try:
        score_cache_public = ScorecachePublic.objects.get(
            rank_cache=rank_cache_public, problem=pro)
    except ScorecachePublic.DoesNotExist:
        score_cache_public = ScorecachePublic(
            rank_cache=rank_cache_public, problem=pro)
        score_cache_public.save()

    if not score_cache.is_correct:
        score_cache.judging += 1
        score_cache.save()
    if not score_cache_public.is_correct:
        score_cache_public.judging += 1
        score_cache_public.save()


@login_required
@contestant_auth
def submit(request):
    refresh_contest_session_contestant(request) 
    current_contest_id = request.session.get('start_contest_contestant')
    problem_list = None
    all_current_contest_submits = []
    try:
        current_contest = Contest.objects.get(
            pk=current_contest_id, start_time__lte=timezone.now(), enable=True)
    except Contest.DoesNotExist:
        current_contest = None
    if current_contest:
        problem_list = current_contest.problem.all().order_by('short_name')
        if request.method == "POST":
            
            form = SubmitAnswer(request.POST, request.FILES)
            form.fields['problem'].queryset = problem_list
            if form.is_valid():
                post = form.save(commit=False)
                post.submit_time = timezone.now()
                post.user = request.user

                post.contest_id = current_contest_id
                post.submit_file = None
                post.server_id = 1
                post.save()
                post.submit_file = request.FILES.get('submit_file')
                post.result = 'Judging'
                post.save()
                
                judge_rank_update(post)
                judge_background.apply_async([post.id])

                this_contest = post.contest
                this_contest.last_update = timezone.now()
                this_contest.save()

                return redirect('submit')
        else:
            form = SubmitAnswer()
            form.fields['problem'].queryset = problem_list
        
        form1 = SubmitWithEditor()
        form1.fields['problem'].choices = [(None, '----------')] + [(i.id, i) for i in problem_list]
        form1.fields['language'].choices = [(None, '----------')]  + [(i.id, i) for i in Language.objects.filter(enable=True)]

    else:
        form = None
        form1 = None
    q = Q(problem=None)
    if current_contest:
        for pro in current_contest.problem.all():
            q = q | Q(problem=pro)
        all_current_contest_submits = Submit.objects.filter(
            q, contest_id=current_contest_id, user=request.user).order_by('submit_time').reverse()
        start_time = current_contest.start_time
        for i in all_current_contest_submits:
            if i.submit_time > current_contest.end_time:
                i.result = 'Too Late'
            i.contest_time = i.submit_time - start_time
            i.source_code = read_source_code(i.submit_file)
            i.language_mode = i.language.editor_mode

        a = [i for i in all_current_contest_submits]
        ls = []
        for i in a:
            ls.append((i.pk, str(i.submit_file)))
    else:
        all_current_contest_submits = None
        ls = []
    qs_json = json.dumps(ls)

    try:
        active_contest = Contest.objects.get(pk=request.session.get(
            'active_contest_contestant'), active_time__lte=timezone.now(), enable=True)
        contest_title = active_contest.title
        start_time = active_contest.start_time
    except Contest.DoesNotExist:
        contest_title = None
        start_time = None

    if current_contest:
        self_scoreboard = self_calculate_scoreboard(request, current_contest_id)
        total_problems = current_contest.problem.all().order_by('short_name')
    else:
        self_scoreboard = []
        total_problems = []

    all_current_contest_submits, paginator = pagination(request, all_current_contest_submits)
    context = {'form': form, 'form1': form1, 'all_current_contest_submits': all_current_contest_submits,
                'current_contest': current_contest, 'qs_json': qs_json, 'contest_title': contest_title, 
                'start_time': start_time, 'self_scoreboard': self_scoreboard, 'submit': 'hover',
                'total_problems': total_problems, 'paginator': paginator,
                }
    return render(request, 'submit.html', context)
                  

@login_required
@contestant_auth
def submit_editor(request):
    refresh_contest_session_contestant(request) 
    current_contest_id = request.session.get('start_contest_contestant')
    problem_list = None
    all_current_contest_submits = []
    try:
        current_contest = Contest.objects.get(
            pk=current_contest_id, start_time__lte=timezone.now(), enable=True)
    except Contest.DoesNotExist:
        current_contest = None
    if current_contest:
        problem_list = current_contest.problem.all().order_by('short_name')
        if request.method == "POST":
            form1 = SubmitWithEditor(request.POST, request.FILES)
            form1.fields['problem'].choices = [(None, '----------')] + [(i.id, i) for i in problem_list]
            form1.fields['language'].choices = [(None, '----------')]  + [(i.id, i) for i in Language.objects.filter(enable=True)]

            if form1.is_valid():
                post = Submit()
                now = timezone.now()
                post.submit_time = now
                post.user = request.user
                post.contest_id = current_contest_id
                lang = Language.objects.get(pk=int(request.POST['language']))
                post.language = lang
                pro =  Problem.objects.get(pk=int(request.POST['problem']))
                post.problem = pro
                post.submit_file = None
                post.server_id = 1
                post.save()

                source = request.POST['source']
                path = pro.title + '_' + str(request.user.id) + '_' + str(now) +'.' + lang.extension
                path = path.replace(' ', '').replace('/', '')

                if lang.name == 'Java':
                    path = java_class_name_find(source, path)

                code = open(path, 'w')
                code.write(source)
                code.close()
                code = open(path, 'rb')
                source_code = code.read()
                code.close()
                submit_file = InMemoryUploadedFile(BytesIO(source_code), 'file', path, 'file/text', sys.getsizeof(source_code), None)
                post.submit_file = submit_file
                
                post.result = 'Judging'
                post.save()

                judge_rank_update(post)
                judge_background.apply_async([post.id])

                this_contest = post.contest
                this_contest.last_update = timezone.now()
                this_contest.save()
                os.system(f'rm "{path}"')

                return redirect('submit')
        else:
            form1 = SubmitWithEditor()
            form1.fields['problem'].choices = [(None, '----------')] + [(i.id, i) for i in problem_list]
            form1.fields['language'].choices = [(None, '----------')]  + [(i.id, i) for i in Language.objects.filter(enable=True)]

        form = SubmitAnswer()
        form.fields['problem'].queryset = problem_list
        
    else:
        form = None
        form1 = None

    q = Q(problem=None)
    if current_contest:
        for pro in current_contest.problem.all():
            q = q | Q(problem=pro)
        all_current_contest_submits = Submit.objects.filter(
            q, contest_id=current_contest_id, user=request.user).order_by('submit_time').reverse()
        start_time = current_contest.start_time
        for i in all_current_contest_submits:
            if i.submit_time > current_contest.end_time:
                i.result = 'Too Late'
            i.contest_time = i.submit_time - start_time
            i.source_code = read_source_code(i.submit_file)
            i.language_mode = i.language.editor_mode

        a = [i for i in all_current_contest_submits]
        ls = []
        for i in a:
            ls.append((i.pk, str(i.submit_file)))
    else:
        all_current_contest_submits = None
        ls = []
    qs_json = json.dumps(ls)

    try:
        active_contest = Contest.objects.get(pk=request.session.get(
            'active_contest_contestant'), active_time__lte=timezone.now(), enable=True)
        contest_title = active_contest.title
        start_time = active_contest.start_time
    except Contest.DoesNotExist:
        contest_title = None
        start_time = None

    if current_contest:
        self_scoreboard = self_calculate_scoreboard(request, current_contest_id)
        total_problems = current_contest.problem.all().order_by('short_name')
    else:
        self_scoreboard = []
        total_problems = []

    all_current_contest_submits, paginator = pagination(request, all_current_contest_submits)
    context = {'form': form, 'form1': form1, 'current_contest': current_contest, 
                'qs_json': qs_json,  'all_current_contest_submits': all_current_contest_submits,
                'contest_title': contest_title, 'start_time': start_time, 'submit': 'hover',
                'self_scoreboard': self_scoreboard, 'total_problems': total_problems,
                'paginator': paginator,
               }
    return render(request, 'submit.html', context)


def scoreboard_summary(contest, scoreboard_type):
    total_problems = contest.problem.all().order_by('short_name')
    q = Q(problem=None)
    for pro in contest.problem.all():
        q = q | Q(problem=pro)
    problem_summary_dict = {i: [0, 0] for i in total_problems}

    if scoreboard_type == "public":
        user_rank_cache = RankcachePublic.objects.filter(contest=contest)
        user_score_cache = ScorecachePublic.objects.filter(
            q, rank_cache__contest=contest)
    else:
        user_rank_cache = RankcacheJury.objects.filter(contest=contest)
        user_score_cache = ScorecacheJury.objects.filter(
            q, rank_cache__contest=contest)
    total_user = 0
    total_point = 0
    total_time = 0
    for rank in user_rank_cache:
        total_user += 1
        total_point += rank.point
        total_time += rank.punish_time

    for score in user_score_cache:
        problem_summary_dict[score.problem][0] += score.submission
        if score.is_correct:
            problem_summary_dict[score.problem][1] += 1

    if total_point == int(total_point):
        total_point = int(total_point)
    summary = [total_user, 'summary', total_point, total_time]
    for pro in total_problems:
        this_problem = "%d/%d" % tuple(problem_summary_dict[pro])
        summary.append(this_problem)
    return summary


def first_solver(score_cache, problem_list, contest_start_time):
    first_solver_list = []
    for problem in problem_list:
        this_problem_submit = score_cache.filter(
            is_correct=True, problem=problem).order_by('correct_submit_time')
        this_problem_first_solver = []
        if this_problem_submit:
            first_time = time_gap(
                this_problem_submit[0].correct_submit_time, contest_start_time)
            for score in this_problem_submit:
                time = time_gap(score.correct_submit_time, contest_start_time)
                if time > first_time:
                    break
                else:
                    first_solver_list.append((score.rank_cache.user, problem))
    return first_solver_list


def calculate_problem_score_public(score_cache_public, total_problems, contest_start_time, first_solver_list):
    score_vs_problem = dict()
    for score in score_cache_public:
        pro = score.problem
        if score.is_correct:
            time = time_gap(score.correct_submit_time, contest_start_time)
            if (score.rank_cache.user, pro) in first_solver_list:
                score_vs_problem[pro] = (score.submission, time, "#26ac0c")
            else:
                score_vs_problem[pro] = (score.submission, time, "#2ef507")
        elif score.judging:
            if score.pending:
                if score.punish:
                    score_vs_problem[pro] = (
                        "%d+%d" % (score.punish, score.pending + score.judging), -1, "#A110A1")
                else:
                    score_vs_problem[pro] = (score.pending + score.judging, -1, "#A110A1")
            else:
                score_vs_problem[pro] = (score.punish + score.judging, -1, "#A110A1")
        elif score.pending:
            if score.punish:
                score_vs_problem[pro] = (
                    "%d+%d" % (score.punish, score.pending), -1, "#007F7F")
            else:
                score_vs_problem[pro] = (score.pending, -1, "#007F7F")
        
        else:
            score_vs_problem[pro] = (score.submission, -1, "#F67B51")
    problem_display = []
    for pro in total_problems:
        if pro in score_vs_problem:
            problem_display.append(score_vs_problem[pro])
        else:
            problem_display.append((0, -1, "#ffffff"))
    return problem_display


def calculate_problem_score_jury(score_cache_jury, total_problems, contest_start_time, first_solver_list):
    score_vs_problem = dict()
    for score in score_cache_jury:
        pro = score.problem
        if score.is_correct:
            time = time_gap(score.correct_submit_time, contest_start_time)
            if (score.rank_cache.user, pro) in first_solver_list:
                score_vs_problem[pro] = (
                    score.submission, time, "#26ac0c", pro.id)
            else:
                score_vs_problem[pro] = (
                    score.submission, time, "#2ef507", pro.id)
        elif score.judging:
            score_vs_problem[pro] = (score.punish + score.judging, -1, "#A110A1", pro.id)
        elif score.punish:
            score_vs_problem[pro] = (score.submission, -1, "#F67B51", pro.id)
    problem_display = []
    for pro in total_problems:
        if pro in score_vs_problem:
            problem_display.append(score_vs_problem[pro])
        else:
            problem_display.append((0, -1, "#ffffff", pro.id))
    return problem_display


def last_submit(score_cache, contest_end_time, contest_start_time):
    last = contest_start_time
    is_correct_submit = False
    for submit in score_cache:
        if submit.is_correct:
            if last < submit.correct_submit_time:
                last = submit.correct_submit_time
                is_correct_submit = True
    if is_correct_submit:
        return time_gap(last, contest_start_time)
    else:
        return time_gap(contest_end_time, contest_start_time)


def create_rank(table):
    for users in table:
        users[0] = -users[0]
    table.sort()
    for users in table:
        users[0] = -users[0]
    if table:
        table[0].append(1)
    for i in range(1, len(table)):
        if table[i][:3] == table[i-1][:3]:
            table[i].append('')
        else:
            table[i].append(i+1)
    return table


def calculate_scoreboard(request, contest_id, scoreboard_type):
    current_contest = Contest.objects.get(pk=contest_id)
    contest_start_time = current_contest.start_time
    total_users = current_contest.user.filter(role__short_name="contestant")
    total_problems = current_contest.problem.all().order_by('short_name')
    q = Q(problem=None)
    for pro in current_contest.problem.all():
        q = q | Q(problem=pro)

    now = timezone.now()
    if scoreboard_type == "public":
        rank_cache = RankcachePublic.objects.filter(contest=current_contest)
        score_cache = ScorecachePublic.objects.filter(
            q, rank_cache__contest=current_contest)
    else:
        rank_cache = RankcacheJury.objects.filter(contest=current_contest)
        score_cache = ScorecacheJury.objects.filter(
            q, rank_cache__contest=current_contest)

    first_solver_list = first_solver(
        score_cache, total_problems, contest_start_time)
    display = []
    for users in total_users:
        user_score_cache = score_cache.filter(rank_cache__user=users)
        if scoreboard_type == "public":
            problem_display = calculate_problem_score_public(
                user_score_cache, total_problems, contest_start_time, first_solver_list)
        else:
            problem_display = calculate_problem_score_jury(
                user_score_cache, total_problems, contest_start_time, first_solver_list)

        try:
            user_rank_cache = rank_cache.get(user=users)
            user_point = float(user_rank_cache.point)
            punish_time = user_rank_cache.punish_time
        except:
            continue

        if user_point == int(user_point):
            user_point = int(user_point)
        last_submit_time = last_submit(
            user_score_cache, current_contest.end_time, contest_start_time)
        flag = users.campus.flag()
        this_user_row = [user_point, punish_time, last_submit_time,
                         users.name, users.id, users.campus.name, flag, problem_display]
        display.append(this_user_row)
    rank = create_rank(display)
    return rank


# @login_required
# @contestant_auth
def public_scoreboard(request):
    now = timezone.now()
    if request.user.is_authenticated:  # the user is contestant
        # refresh contestant contest session
        refresh_contest_session_contestant(request)
        contest_id = request.session.get('start_contest_contestant')
        base_page = "contestant_base_site.html"
        role = "contestant"
    else:
        refresh_contest_session_public(request)
        contest_id = request.session.get('start_contest_public')
        base_page = "public_scoreboard_base_site.html"
        role = "public"
    frozen = None
    if contest_id:
        current_contest = Contest.objects.get(pk=contest_id)

        unfrozen_time = current_contest.unfrozen_time
        if not unfrozen_time:
            unfrozen_time = current_contest.end_time
        if current_contest.last_update < unfrozen_time and now >= unfrozen_time:
            current_contest.last_update = unfrozen_time
            rank_update_unfrozen(current_contest)
            current_contest.save()
        # if current_contest.last_update < current_contest.start_time and now >= current_contest.start_time:
        #     current_contest.last_update = current_contest.start_time
        #     current_contest.save()
        if current_contest.frozen_time and now >= current_contest.frozen_time and now < unfrozen_time:
            frozen = (current_contest.frozen_time, unfrozen_time)
        else:
            frozen = None
        total_problems = current_contest.problem.all().order_by('short_name')
        last_update = str(current_contest.last_update)
        scoreboard_in_session = request.session.get(
            'public_scoreboard_contest_id_' + str(contest_id))
        if now < current_contest.start_time:
            scoreboard = None
        elif scoreboard_in_session and scoreboard_in_session['last_update'] == last_update:
            scoreboard = scoreboard_in_session['scoreboard']
        else:
            scoreboard_public = calculate_scoreboard(
                request, contest_id, "public")
            summary = scoreboard_summary(current_contest, "public")
            scoreboard = {
                'scoreboard_public': scoreboard_public,
                'summary': summary,
            }
            request.session['public_scoreboard_contest_id_' + str(contest_id)] = {
                'last_update': last_update, 'scoreboard': scoreboard, 'contest_id': contest_id}

    else:
        scoreboard = total_problems = contest_title = current_contest = None

    if role == "contestant":
        try:
            active_contest = Contest.objects.get(pk=request.session.get(
                'active_contest_contestant'), active_time__lte=timezone.now(), enable=True)
            contest_title = active_contest.title
            start_time = active_contest.start_time
        except Contest.DoesNotExist:
            contest_title = None
            start_time = None
    else:
        try:
            active_contest = Contest.objects.get(pk=request.session.get(
                'active_contest_public'), active_time__lte=timezone.now(), enable=True)
            contest_title = active_contest.title
            start_time = active_contest.start_time
        except Contest.DoesNotExist:
            contest_title = None
            start_time = None

    context = {
        'scoreboard': scoreboard,
        'total_problems': total_problems,
        'contest': current_contest,
        'frozen': frozen,
        'contest_title': contest_title,
        'start_time': start_time,
        'base_page': base_page,
        'scor': 'hover',
        'role': role,
    }
    return render(request, 'public_scoreboard.html', context)


# @login_required
# @contestant_auth
def public_scoreboard_refresh(request):
    
    now = timezone.now()
    if request.user.is_authenticated:  # the user is contestant
        refresh_contest_session_contestant(request)
        contest_id = request.session.get('start_contest_contestant')
    else:
        contest_id = request.session.get('start_contest_public')
        refresh_contest_session_public(request)
    frozen = None
    if contest_id:
        current_contest = Contest.objects.get(pk=contest_id)

        unfrozen_time = current_contest.unfrozen_time
        if not unfrozen_time:
            unfrozen_time = current_contest.end_time
        if current_contest.last_update < unfrozen_time and now >= unfrozen_time:
            current_contest.last_update = unfrozen_time
            rank_update_unfrozen(current_contest)
            current_contest.save()
        # if current_contest.last_update < current_contest.start_time and now >= current_contest.start_time:
        #     current_contest.last_update = current_contest.start_time
        #     current_contest.save()
        if current_contest.frozen_time and now >= current_contest.frozen_time and now < unfrozen_time:
            frozen = (current_contest.frozen_time, unfrozen_time)
        else:
            frozen = None
        total_problems = current_contest.problem.all().order_by('short_name')
        last_update = str(current_contest.last_update)
        scoreboard_in_session = request.session.get(
            'public_scoreboard_contest_id_' + str(contest_id))
        if now < current_contest.start_time:
            scoreboard = None
        elif scoreboard_in_session and scoreboard_in_session['last_update'] == last_update:
            scoreboard = scoreboard_in_session['scoreboard']
        else:
            scoreboard_public = calculate_scoreboard(
                request, contest_id, "public")
            summary = scoreboard_summary(current_contest, "public")
            scoreboard = {
                'scoreboard_public': scoreboard_public,
                'summary': summary,
            }
            request.session['public_scoreboard_contest_id_' + str(contest_id)] = {
                'last_update': last_update, 'scoreboard': scoreboard, 'contest_id': contest_id}

    else:
        scoreboard = total_problems = current_contest = None

    context = {
        'scoreboard': scoreboard, 'total_problems': total_problems, 'contest': current_contest,
        'frozen': frozen, 'scor': 'hover'
    }
    return render(request, 'public_scoreboard_refresh.html', context)


@login_required
@contestant_auth
def ajax_get_language_list(request):
    active_contest_id = request.session.get('active_contest_contestant')
    try:
        contest = Contest.objects.get(id=active_contest_id)
    except Contest.DoesNotExist:
        contest = None
    language_list = [(lang.id, lang.extension)
                     for lang in Language.objects.filter(enable=True).order_by('name').reverse()]
    problem_list = [(pro.id, pro.title.lower(), pro.short_name.lower())
                    for pro in contest.problem.all()]
    response_data = {"language_list": language_list,
                     "problem_list": problem_list}
    return JsonResponse(response_data, content_type="application/json")


@login_required
@admin_site_jury_auth
def jury_scoreboard(request):
    refresh_contest_session_admin(request)
    now = timezone.now()
    contest_id = request.session.get('start_contest_admin')
    frozen = None
    if contest_id:
        current_contest = Contest.objects.get(pk=contest_id)

        total_problems = current_contest.problem.all().order_by('short_name')
        last_update = str(current_contest.last_update)
        scoreboard_in_session = request.session.get(
            'jury_scoreboard_contest_id_' + str(contest_id))
        if now < current_contest.start_time:
            scoreboard = None
        elif scoreboard_in_session and scoreboard_in_session['last_update'] == last_update:
            scoreboard = scoreboard_in_session['scoreboard']
        else:
            scoreboard_jury = calculate_scoreboard(request, contest_id, "jury")
            summary = scoreboard_summary(current_contest, "jury")
            scoreboard = {
                'scoreboard_jury': scoreboard_jury,
                'summary': summary,
            }
            request.session['jury_scoreboard_contest_id_' + str(contest_id)] = {
                'last_update': last_update, 'scoreboard': scoreboard, 'contest_id': contest_id}
    else:
        scoreboard = total_problems = contest_title = current_contest = None

    try:
        active_contest = Contest.objects.get(pk=request.session.get(
            'active_contest_admin'), active_time__lte=timezone.now(), enable=True)
        contest_title = active_contest.title
        start_time = active_contest.start_time
    except Contest.DoesNotExist:
        contest_title = None
        start_time = None
    base_page = check_base_site(request)

    context = {
        'scoreboard': scoreboard,
        'total_problems': total_problems,
        'contest': current_contest,
        'contest_title': contest_title,
        'start_time': start_time,
        "base_page": base_page,
        'scor': 'hover'
    }
    return render(request, 'jury_scoreboard.html', context)


@login_required
@admin_site_jury_auth
def jury_scoreboard_refresh(request):
    refresh_contest_session_admin(request)
    now = timezone.now()
    contest_id = request.session.get('start_contest_admin')
    frozen = None
    update = False
    if contest_id:
        current_contest = Contest.objects.get(pk=contest_id)

        total_problems = current_contest.problem.all().order_by('short_name')
        last_update = str(current_contest.last_update)
        scoreboard_in_session = request.session.get(
            'jury_scoreboard_contest_id_' + str(contest_id))
        if now < current_contest.start_time:
            scoreboard = None
        elif scoreboard_in_session and scoreboard_in_session['last_update'] == last_update:
            scoreboard = scoreboard_in_session['scoreboard']

        else:
            update = True
            scoreboard_jury = calculate_scoreboard(request, contest_id, "jury")
            summary = scoreboard_summary(current_contest, "jury")
            scoreboard = {
                'scoreboard_jury': scoreboard_jury,
                'summary': summary,
            }
            request.session['jury_scoreboard_contest_id_' + str(contest_id)] = {
                'last_update': last_update, 'scoreboard': scoreboard, 'contest_id': contest_id}
    else:
        scoreboard = total_problems = contest_title = current_contest = None

    if update:
        return render(request, 'jury_scoreboard_refresh.html', {'scoreboard': scoreboard, 'total_problems': total_problems, 'contest': current_contest, 'scor': 'hover'})
    else:
        return HttpResponse('')
    # if update:
    #     new_scoreboard  = render(request, 'jury_scoreboard_refresh.html', {'scoreboard': scoreboard, 'total_problems': total_problems, 'contest': current_contest, 'scor': 'hover'})
    # else:
    #     new_scoreboard = None
    # response_data = {"update": update, "scoreboard": new_scoreboard}
    # return JsonResponse(response_data, content_type="application/json")


@login_required
@admin_site_jury_auth
def deactivate_contest_scoreboard(request, contest_id):
    refresh_contest_session_admin(request)
    now = timezone.now()
    current_contest = Contest.objects.get(pk=contest_id)
    total_problems = current_contest.problem.all().order_by('short_name')
    scoreboard_jury = calculate_scoreboard(request, contest_id, "jury")
    summary = scoreboard_summary(current_contest, "jury")
    scoreboard = {
        'scoreboard_jury': scoreboard_jury,
        'summary': summary,
    }
    base_page = check_base_site(request)
    context = {'scoreboard': scoreboard, 'total_problems': total_problems,
               'contest': current_contest, 'base_page': base_page, 'scor': 'hover'}
    return render(request, 'view_deactivate_contest_scoreboard.html', context)


@login_required
# @admin_or_jury_auth
@admin_site_jury_auth
def view_submit_contest_select(request):
    now = timezone.now()
    refresh_contest_session_admin(request)  # refersh the contest session
    all_contest = Contest.objects.filter(
        start_time__lte=now).order_by("start_time").reverse()
    for contest in all_contest:
        if contest.enable == False:
            contest.status = "disable"
        elif now < contest.active_time:
            contest.status = "not active"
        elif now < contest.start_time:
            contest.status = "active"
        elif contest.start_time <= now and now < contest.end_time:
            contest.status = "on going"
        elif contest.end_time <= now and now < contest.deactivate_time:
            contest.status = "end"
        else:
            contest.status = "deactivate"
    
    all_contest, paginator = pagination(request, all_contest)

    base_page = check_base_site(request)
    context = {
        'all_contest': all_contest,
        'base_page': base_page,
        'paginator': paginator,
        'submit': 'hover'
    }
    return render(request, 'view_submit_select_contest.html', context)


@login_required
@admin_site_jury_auth_and_contest_exist
def view_submissions(request, contest_id):
    problem_id = request.GET.get('problem_id', 0)
    result = request.GET.get('result', "All")

    refresh_contest_session_admin(request)  # refersh the contest session
    contest = Contest.objects.get(pk=contest_id)
    
    try:
        problem_id = int(problem_id)
    except ValueError:
        return redirect('homepage')

    if not problem_id == 0:
        try:
            problem_title = Problem.objects.get(pk=problem_id).title
        except Problem.DoesNotExist:
            problem_title = None
    else:
        problem_title = "All problems"
        
    all_submission = Submit.objects.filter(
        contest=contest).order_by('submit_time').reverse()
    
    all_problems = set()
    for submit in all_submission:
        pro = (submit.problem.id, submit.problem.title)
        all_problems.add(pro)
    all_problems = sorted(all_problems, key=lambda x: x[1].lower())

    submission_list = all_submission
    if problem_id:
        submission_list = submission_list.filter(problem_id=problem_id)

    if not result == "All":
        submission_list = submission_list.filter(result=result)

    start_time = contest.start_time
    for i in submission_list:
        i.contest_time = i.submit_time - start_time
    all_results = ['Correct', 'Wrong Answer', 'Judging', 'Time Limit Exceeded', 'Run Time Error',  
                    'Compiler Error', 'Memory Limit Exceeded', 'No Output']
    
    submission_list, paginator = pagination(request, submission_list)

    base_page = check_base_site(request)
    context = {'submission_list': submission_list, "contest_title": contest.title,
               'all_problems': all_problems, 'contest_id': contest_id, 'paginator': paginator,
               'all_results': all_results, "selected_problem": problem_id, "problem_title": problem_title,
               'selected_result': result, 'base_page': base_page, 'submit': 'hover'
               }
    return render(request, 'view_submission.html', context)


@login_required
# @admin_or_jury_auth
@admin_site_jury_auth
def view_submission_filter(request):
    # refresh_contest_session_admin(request)  # refersh the contest session
    try:
        problem_id = int(request.GET.get('problem_id'))
        contest_id = int(request.GET.get('contest_id'))
    except ValueError:
        return redirect('homepage')

    result = request.GET.get('result')

    try:
        contest = Contest.objects.get(pk=contest_id)
    except Contest.DoesNotExist:
        return redirect('homepage')

    if not problem_id == 0:
        try:
            problem_title = Problem.objects.get(pk=problem_id).title
        except Problem.DoesNotExist:
            problem_title = None

    if problem_id == 0:
        if result == "All":
            submission_list = Submit.objects.filter(
                contest_id=contest_id).order_by('submit_time').reverse()
        else:
            submission_list = Submit.objects.filter(
                contest_id=contest_id, result=result).order_by('submit_time').reverse()
        problem_title = "All problems"    
    else:
        if result == "All":
            submission_list = Submit.objects.filter(
                contest_id=contest_id, problem_id=problem_id).order_by('submit_time').reverse()
        else:
            submission_list = Submit.objects.filter(
                contest_id=contest_id, problem_id=problem_id, result=result).order_by('submit_time').reverse()

    start_time = contest.start_time
    for i in submission_list:
        i.contest_time = i.submit_time - start_time
    
    submission_list, paginator = pagination(request, submission_list)
    
    context = {'submission_list': submission_list, 'problem_title': problem_title,
               'paginator': paginator, 'contest_title': contest.title, 
               'selected_problem': problem_id, 'selected_result': result, 'submit': 'hover'}
    return render(request, 'view_submission_filter.html', context)


@login_required
@admin_site_jury_auth_and_submit_exist
def submission_detail(request, submit_id):
    refresh_contest_session_admin(request)  # refersh the contest session
    submit = Submit.objects.get(pk=submit_id)
    submit_contest_time = submit.submit_time - submit.contest.start_time

    kwargs = {}
    temp_data={'testcase_id': str(submit.problem.id), "sudmission_dir": submit.output_path}                            
    kwargs['json'] = temp_data
    url = submit.server.address + "/submission_output"
    sample_user_output = requests.get(url, **kwargs).json()
      
    answer_file = submit.submit_file
    submit_file = read_source_code(answer_file)
    language_mode = submit.language.editor_mode
    error = submit.problem.error
    file_name = answer_file.name
    try:
        index = file_name[::-1].index('/')
        file_name = file_name[::-1][:index][::-1]
    except Exception:
        pass
    # detail about the test cases
    submit_detail = []

    all_user_testcases = TestcaseOutput.objects.filter(submit=submit).order_by('test_case')
    run_testcases = [i.test_case for i in all_user_testcases]
    testcase_correct_answer = TestCase.objects.filter(problem=submit.problem).order_by('name')
    all_user_answers = {}
    all_correct_answers = {}

    for each in all_user_testcases:
        try:
            all_user_answers[each.test_case.id] = sample_user_output[each.test_case.name]["data"]
        except KeyError:
            all_user_answers[each.test_case.id] = ""

    for each in testcase_correct_answer:
        all_correct_answers[each.id] = read_from_file(each.output).strip().split('\n')
    
    for each in all_user_testcases:
        execution_time = float(each.execution_time)
        if not execution_time == 0:
            execution_time = ('%f' % execution_time)

        memory_usage = float(each.memory_usage)
        if memory_usage == int(memory_usage):
            memory_usage = int(each.memory_usage)
        elif not memory_usage == 0:
            memory_usage = ('%f' % memory_usage)
            
        testcase_id = each.test_case.id
        result = each.result

        url = each.test_case.input.url
        file_path = url
        try:
            index = file_path[::-1].index('/')
            file_path = file_path[::-1][:index][::-1]
        except Exception:
            pass
        testcase_input_file = (url, file_path)

        url = each.test_case.output.url
        file_path = url
        try:
            index = file_path[::-1].index('/')
            file_path = file_path[::-1][:index][::-1]
        except Exception:
            pass
        testcase_output_file = (url, file_path)

        try:
            url = os.path.join(submit.server.address, sample_user_output[each.test_case.name]["path"])
            file_path = url
            try:
                index = file_path[::-1].index('/')
                file_path = file_path[::-1][:index][::-1]
            except Exception:
                pass
            user_output_file = (url, file_path)
        except KeyError:
            user_output_file = (None, None)

        answer_compare = []
        x = all_correct_answers[testcase_id]
        y = all_user_answers[testcase_id]
        # print(x, y, x==y)
        for k in range(min(len(x), len(y))):
            correct_line = x[k].split()
            user_line = y[k].split()
            if len(correct_line) != len(user_line):
                answer_compare.append((x[k], y[k], 'Wrong Answer'))
                continue
            for a, b in zip(correct_line, user_line):
                if a == b:
                    continue
                try:
                    a = float(a)
                    b = float(b)
                except ValueError:
                    answer_compare.append((x[k], y[k], 'Wrong Answer'))
                    break
                if math.fabs(a - b) > error:
                    answer_compare.append((x[k], y[k], 'Wrong Answer'))
                    break
            else:
                answer_compare.append((x[k], y[k], 'Correct'))
        for k in range(len(x), len(y)):
            answer_compare.append(('', y[k], 'Wrong Answer'))
        for k in range(len(y), len(x)):
            answer_compare.append((x[k], '', 'Wrong Answer'))
        submit_detail.append((testcase_id, result, answer_compare, testcase_input_file,
                              testcase_output_file, user_output_file, execution_time, memory_usage))
    for i in testcase_correct_answer:
        if i in run_testcases:
            continue
        else:
            submit_detail.append(
                (i.id, "Not Run", [], (None, None), (None, None), (None, None), 0, 0))
    base_page = check_base_site(request)
    context = {'this_submit': submit, 'submit_file': submit_file, 'language_mode': language_mode, 
                'file_name': file_name, 'submit_detail': submit_detail, 
                'submit_contest_time': submit_contest_time, 
                'submit': 'hover', 'base_page': base_page
            }
    return render(request, 'submission_detail.html', context)


@login_required
# @admin_or_jury_auth
@admin_site_jury_auth
def specific_problem_submission(request):
    problem_id = request.GET.get('problem_id')
    user_id = request.GET.get('user_id')
    contest_id = request.GET.get('contest_id')
    refresh_contest_session_admin(request)  # refersh the contest session
    current_contest = Contest.objects.get(pk=contest_id)
    this_problem_and_user_submissions = Submit.objects.filter(contest_id=contest_id, problem_id=problem_id, user_id=user_id,
                                                              submit_time__gte=current_contest.start_time, submit_time__lte=current_contest.end_time).order_by('submit_time')
    correct = False
    specific_submissions = list()
    if request.user.role.short_name == "site" and current_contest.created_by == request.user.campus:
        site_admin_permission = True
    else:
        site_admin_permission = False
    for submissions in this_problem_and_user_submissions:
        if correct:
            break
        elif submissions.result == 'Correct':
            correct = True
            specific_submissions.append(submissions)
        else:
            specific_submissions.append(submissions)

    start_time = current_contest.start_time
    for i in specific_submissions:
        i.contest_time = i.submit_time - start_time

    specific_submissions, paginator = pagination(request, specific_submissions)
    print(specific_submissions[0])
    base_page = check_base_site(request)
    context = {
        'submission_list': specific_submissions, 
        'contest_id': contest_id, 
        'paginator': paginator,
        'site_admin_permission': site_admin_permission,
        'base_page': base_page,
        'submit': 'hover'
        }
    return render(request, 'specific_problem_submission.html', context)


@login_required
@admin_auth
def rejudge_contest_select(request):
    now = timezone.now()
    refresh_contest_session_admin(request)  # refersh the contest session
    all_contest = Contest.objects.filter(
        start_time__lte=now).order_by("start_time").reverse()

    for contest in all_contest:
        if contest.enable == False:
            contest.status = "disable"
        elif now < contest.active_time:
            contest.status = "not active"
        elif now < contest.start_time:
            contest.status = "active"
        elif contest.start_time <= now and now < contest.end_time:
            contest.status = "on going"
        elif contest.end_time <= now and now < contest.deactivate_time:
            contest.status = "end"
        else:
            contest.status = "deactivate"
    
    all_contest, paginator = pagination(request, all_contest)

    context = {'all_contest': all_contest, 'paginator': paginator, 'rejudge': 'hover'}
    return render(request, 'rejudge_select_contest.html', context)


@login_required
@admin_auth_and_contest_exist
def rejudge_submission_list(request, contest_id):
    problem_id = request.GET.get('problem_id', 0)
    result = request.GET.get('result', "All")

    refresh_contest_session_admin(request)  # refersh the contest session
    contest = Contest.objects.get(pk=contest_id)
    
    try:
        problem_id = int(problem_id)
    except ValueError:
        return redirect('homepage')

    if not problem_id == 0:
        try:
            problem_title = Problem.objects.get(pk=problem_id).title
        except Problem.DoesNotExist:
            problem_title = None
    else:
        problem_title = "All problems"
        
    all_submission = Submit.objects.filter(
        contest=contest).order_by('submit_time').reverse()
    
    all_problems = set()
    for submit in all_submission:
        pro = (submit.problem.id, submit.problem.title)
        all_problems.add(pro)
    all_problems = sorted(all_problems, key=lambda x: x[1].lower())

    submission_list = all_submission
    if problem_id:
        submission_list = submission_list.filter(problem_id=problem_id)

    if not result == "All":
        submission_list = submission_list.filter(result=result)

    start_time = contest.start_time
    for i in submission_list:
        i.contest_time = i.submit_time - start_time
    all_results = ['Correct', 'Wrong Answer', 'Judging', 'Time Limit Exceeded', 'Run Time Error',  
                    'Compiler Error', 'Memory Limit Exceeded', 'No Output']
    
    submission_list, paginator = pagination(request, submission_list)

    context = {'submission_list': submission_list, "contest_title": contest.title,
               'all_problems': all_problems, 'contest_id': contest_id, 'paginator': paginator,
               'all_results': all_results, "selected_problem": problem_id, 
               "problem_title": problem_title, 'selected_result': result, 'rejudge': 'hover'
               }
    return render(request, 'rejudge_submission_list.html', context)


@login_required
@admin_auth
def rejudge_submission_filter(request):
    
    try:
        problem_id = int(request.GET.get('problem_id'))
        contest_id = int(request.GET.get('contest_id'))
    except ValueError:
        return redirect('homepage')
        
    result = request.GET.get('result')

    try:
        contest = Contest.objects.get(pk=contest_id)
    except Contest.DoesNotExist:
        return redirect('homepage')

    if not problem_id == 0:
        try:
            problem_title = Problem.objects.get(pk=problem_id).title
        except Problem.DoesNotExist:
            problem_title = None

    if problem_id == 0:
        if result == "All":
            submission_list = Submit.objects.filter(
                contest_id=contest_id).order_by('submit_time').reverse()
        else:
            submission_list = Submit.objects.filter(
                contest_id=contest_id, result=result).order_by('submit_time').reverse()
        problem_title = "All problems"    
    else:
        if result == "All":
            submission_list = Submit.objects.filter(
                contest_id=contest_id, problem_id=problem_id).order_by('submit_time').reverse()
        else:
            submission_list = Submit.objects.filter(
                contest_id=contest_id, problem_id=problem_id, result=result).order_by('submit_time').reverse()

    start_time = contest.start_time
    for i in submission_list:
        i.contest_time = i.submit_time - start_time
    
    submission_list, paginator = pagination(request, submission_list)

    context = {'submission_list': submission_list, 'problem_title': problem_title,
               'paginator': paginator, 'contest_title': contest.title, 
               'selected_problem': problem_id, 'selected_result': result, 'rejudge': 'hover'}
    return render(request, 'rejudge_filter.html', context)


@login_required
@admin_auth
def ajax_rejudge(request):
    refresh_contest_session_admin(request)  # refersh the contest session
    total_submits = request.GET.getlist('total_submit[]')
    contest_id = request.GET.get('contest_id')
    contest = Contest.objects.get(pk=contest_id)
    rejudge_submits = [int(i) for i in total_submits]
    result_dict = {}
    for submit_id in rejudge_submits:
        try:
            submit = Submit.objects.get(pk=submit_id)
            if submit.result == "Judging":
                result_dict[submit_id] = "Judging *"
                # continue
            if os.path.exists(submit.submit_file.path):
                submit.result = "Judging"
                submit.save()
                judge_background.apply_async([submit.id, True])
                result = submit.result
            else:
                result = "file not found"
        except Submit.DoesNotExist:
            result = "not submitted"

        result_dict[submit_id] = result
    contest.last_update = timezone.now()
    contest.save()
    response_data = {'result': result_dict}
    return JsonResponse(response_data, content_type="application/json")


@login_required
@admin_auth_and_submit_exist
def single_rejudge(request, submit_id):
    refresh_contest_session_admin(request)  # refersh the contest session
    single_submit = Submit.objects.get(pk=submit_id)
    single_submit.contest_time = single_submit.submit_time - \
        single_submit.contest.start_time
    submit = [single_submit]

    return render(request, 'single_user_rejudge.html', {'this_submit': submit, 'contest_id': single_submit.contest.pk, 'rejudge': 'hover'})


@login_required
@admin_auth
def multi_rejudge(request, problem_id, contest_id, user_id):
    refresh_contest_session_admin(request)  # refersh the contest session
    # contest_id = request.session.get('start_contest_admin')  # ???
    current_contest = Contest.objects.get(pk=contest_id)
    submit = Submit.objects.filter(contest_id=contest_id, problem_id=problem_id, user_id=user_id,
                                   submit_time__gte=current_contest.start_time, submit_time__lte=current_contest.end_time).order_by('submit_time')
    if not submit:
        return redirect('homepage')
    specific_submissions = list()
    for i in submit:
        if i.result == 'Correct':
            specific_submissions.append(i)
            break
        else:
            specific_submissions.append(i)
    start_time = current_contest.start_time
    for i in specific_submissions:
        i.contest_time = i.submit_time - start_time

    specific_submissions, paginator = pagination(request, specific_submissions)
    context = {'this_submit': specific_submissions, 'paginator': paginator, 
              'contest_id': specific_submissions[0].contest.pk, 'rejudge': 'hover'
            }
    return render(request, 'single_user_rejudge.html', context)



def self_calculate_scoreboard(request, contest_id):
    current_contest = Contest.objects.get(pk=contest_id)
    contest_start_time = current_contest.start_time
    total_problems = current_contest.problem.all().order_by('short_name')
    q = Q(problem=None)
    for pro in current_contest.problem.all():
        q = q | Q(problem=pro)

    now = timezone.now()
    rank_cache = RankcacheJury.objects.filter(contest=current_contest)
    score_cache = ScorecacheJury.objects.filter(
            q, rank_cache__contest=current_contest)

    user_score_cache = score_cache.filter(rank_cache__user=request.user)
    first_solver_list = first_solver(
        score_cache, total_problems, contest_start_time)

    problem_display = calculate_problem_score_jury(
        user_score_cache, total_problems, contest_start_time, first_solver_list)
    flag = request.user.campus.flag()

    try:
        user_rank_cache = rank_cache.get(user=request.user)
    except RankcacheJury.DoesNotExist:
        return [['?', 0, 0, request.user.name, request.user.campus.name, flag, problem_display]]

    try:
        user_point = float(user_rank_cache.point)
        punish_time = user_rank_cache.punish_time
    except:
        pass

    if user_point == int(user_point):
        user_point = int(user_point)
    
    rank = self_rank(request.user, rank_cache, score_cache, current_contest)
    user_row = [[rank, user_point, punish_time, request.user.name, request.user.campus.name, flag, problem_display]]
    return user_row

    
def self_rank(user, rank_cache, score_cache, contest):
    frozen_time = contest.frozen_time
    if frozen_time:
        if contest.frozen_time < timezone.now() and timezone.now() < contest.unfrozen_time:
            return '?'
    rank = []
    for user_rank_cache in rank_cache:
        user_score_cache = score_cache.filter(rank_cache__user=user)
        last_submit_time = last_submit(
            user_score_cache, contest.end_time, contest.start_time)
        rank.append((-user_rank_cache.point, user_rank_cache.punish_time, last_submit_time, user_rank_cache.user.id))
    rank.sort()
    count = 1
    if(rank[0][-1] == user.id):
        return 1
    for i in range(1, len(rank)):
        if rank[i][:3] != rank[i-1][:3]:
            count = i+1
        if rank[i][-1] == user.id:
            return count
        
    return '?' # the user has no any submission
