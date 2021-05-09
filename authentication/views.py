from django.shortcuts import render, render_to_response, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from authentication.decorators import admin_auth, admin_auth_and_user_exist, admin_auth_and_campus_exist,\
    jury_auth, contestant_auth, admin_site_jury_auth, public_auth, public_auth_and_problem_exist
from authentication.models import User, Role, Campus
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.db import IntegrityError
from authentication.validators import email_validate
from contest.models import Contest
from contest.views import create_contest_session_admin, create_contest_session_contestant, refresh_contest_session_public,\
    refresh_contest_session_admin, refresh_contest_session_contestant
import csv
from django.views.generic import CreateView
from authentication.forms import PublicUserRegistrationForm, EditMyProfile, EditUserProfile, AddUser,\
    CSVUserUpload, ChangePassword, EditCampus, CampusRegister
from django.contrib.auth.forms import AuthenticationForm
from public.models import Statistics
from competitive.models import Submit
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .pagination import pagination, page_number_pagination

# Create your views here.
def index(request):
    form = AuthenticationForm()
    if request.user.is_authenticated:
        return redirect('homepage')
    else:
        return render(request, 'registration/login.html', {'form': form})


def check_base_site(request):
    if request.user.role.short_name == 'admin':
        base = 'admin_base_site.html'
    elif request.user.role.short_name == 'jury':
        base = 'jury_base_site.html'
    elif request.user.role.short_name == 'contestant':
        base = 'contestant_base_site.html'
    elif request.user.role.short_name == 'public':
        base = 'public_base_site.html'
    elif request.user.role.short_name == 'site':
        base = 'site_base_site.html'

    return base


@login_required
def homepage(request):
    if request.user.role.short_name == 'super':
        return redirect('/admin/')
    elif request.user.role.short_name == 'admin':
        create_contest_session_admin(request)
        return render(request, 'admin_index.html', {'myicpc': 'hover'})
    elif request.user.role.short_name == 'site':
        create_contest_session_admin(request)
        return render(request, 'site_index.html', {'myicpc': 'hover'})
    elif request.user.role.short_name == 'jury':
        create_contest_session_admin(request)
        return render(request, 'jury_index.html')
    elif request.user.role.short_name == 'contestant':
        create_contest_session_contestant(request)
        return redirect('submit')
    elif request.user.role.short_name == 'public':
        return render(request, 'public_index.html')


def register(request):
    if request.method == "POST":
        form = PublicUserRegistrationForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            try:
                role = Role.objects.get(short_name='public')
                post.role = role
                post.save()
                messages.success(request, "user "+post.name +
                                 " was register successfully.")
            except Role.DoesNotExist:
                pass
            return redirect('/home/')
    else:
        form = PublicUserRegistrationForm()
    return render(request, 'register.html', {'form': form})


@login_required
def profile(request):
    if request.method == "POST":
        form = EditMyProfile(request.POST, instance=request.user)
        if form.is_valid():
            post = form.save(commit=False)
            post.save()
            messages.success(request, "successfully update.")
            return redirect('profile')
    else:
        form = EditMyProfile(instance=request.user)

    base = check_base_site(request)
    return render(request, 'profile.html', {'form': form, 'base_site': base})


@login_required
def change_password(request):
    if request.method == "POST":

        form = ChangePassword(request.POST, password=request.user.password)
        if form.is_valid():
            new_password = request.POST.get('new_password')
            request.user.set_password(new_password)
            request.user.save()
            messages.success(request, "The password was changed successfully.")
    else:
        form = ChangePassword(password=request.user.password)

    base = check_base_site(request)
    return render(request, 'change_password.html', {'form': form,  'base_site': base})


@login_required
@admin_auth
def user_list(request):

    contestant_user = User.objects.filter(
        role__short_name="contestant").order_by('username')
    admin_user = User.objects.filter(
        role__short_name="admin").order_by('username')
    site_admin_user = User.objects.filter(
        role__short_name="site").order_by('username')
    jury_user = User.objects.filter(
        role__short_name="jury").order_by('username')
    public_user = User.objects.filter(
        role__short_name="public").order_by('username')

    page_number = request.GET.get('page', 1)
    role = request.GET.get('role', "contestant")
    contestant_page_number = 1
    jury_page_number = 1
    public_page_number = 1
    admin_page_number = 1
    site_admin_page_number = 1

    if role == 'contestant': contestant_page_number=page_number
    elif role == 'jury': jury_page_number=page_number
    elif role == 'admin': admin_page_number=page_number
    elif role == 'public': public_page_number=page_number
    elif role == 'site_admin': site_admin_page_number=page_number

    contestant_user, contestant_paginator = page_number_pagination(request, contestant_user, contestant_page_number)
    jury_user, jury_paginator = page_number_pagination(request, jury_user, jury_page_number)
    public_user, public_paginator = page_number_pagination(request, public_user, public_page_number)
    admin_user, admin_paginator = page_number_pagination(request, admin_user, admin_page_number)
    site_admin_user, site_admin_paginator = page_number_pagination(request, site_admin_user, site_admin_page_number)

    context = {
        'contestant_user': contestant_user,
        'admin_user': admin_user,
        'jury_user': jury_user,
        'public_user': public_user,
        'site_admin_user': site_admin_user,
        'contestant_paginator': contestant_paginator,
        'admin_paginator': admin_paginator,
        'jury_paginator': jury_paginator,
        'public_paginator': public_paginator,
        'site_admin_paginator': site_admin_paginator,
        "role": role,
        'user': 'hover'
    }
    return render(request, 'user_list.html', context)


@login_required
@admin_auth_and_user_exist
def delete_user(request, user_id):
    user = User.objects.get(pk=user_id)
    return render(request, 'delete_user.html', {'this_user': user, 'user': 'hover'})


@login_required
@admin_auth_and_user_exist
def delete_user_done(request, user_id):
    user = User.objects.get(pk=user_id)
    # user_participated_contest = Contest.objects.filter(user=user)
    # for contest in user_participated_contest:
    #     contest.last_update = timezone.now()
    #     contest.save()
    user.delete()
    messages.success(request, "user " + user.name +
                     " was deleted successfully.")
    return redirect('user')


@login_required
@admin_auth_and_user_exist
def edit_user(request, user_id):
    user = User.objects.get(pk=user_id)
    if request.method == "POST":
        form = EditUserProfile(request.POST, instance=user)
        if form.is_valid():
            post = form.save(commit=False)
            post.save()
            messages.success(request, "The user " +
                             user.username+" was update successfully.")
            return redirect('user')
    else:
        form = EditUserProfile(instance=user)

    return render(request, 'edit_user.html', {'form': form, 'user_id': user.id, 'user': 'hover'})


@login_required
@admin_auth
def user_register(request):
    role_list = Role.objects.all().exclude(short_name='super')
    if request.method == "POST":
        form = AddUser(request.POST)
        form.fields['role'].queryset = role_list
        if form.is_valid():
            chars = 'abcdefghijklmnopqrstuvwxyz0123456789@#$%&*'
            secret_key = get_random_string(8, chars)
            post = form.save(commit=False)
            post.set_password(secret_key)
            post.save()
            messages.success(request, "user "+post.name +
                             " was added successfully.")
            return redirect('user_register')
    else:
        form = AddUser()
        form.fields['role'].queryset = role_list
    form1 = CSVUserUpload()
    return render(request, 'user_register.html', {'form': form, 'form1': form1, 'user': 'hover'})


def validate_data(request, username, name, email, line_number):
    if not username:
        messages.error(request, "invalid username in line " + str(line_number))
        return 0
    else:
        try:
            User.objects.get(username=username)
            messages.error(request, "username " +
                           username + " was already exists.")
            return 0
        except User.DoesNotExist:
            pass

    if not name:
        messages.error(request, "invalid name for user " + username)
        return 0

    if not email_validate(email):
        messages.error(request, "invalid email for user " + username)
        return 0

    return 1


def register_csv(request, csv_file):
    if not (csv_file.content_type == 'text/csv' or csv_file.content_type == 'application/vnd.ms-excel'):
        messages.error(request, "The file is not csv format.")
        return redirect('user_register_csv')
    else:
        decoded_file = csv_file.read().decode('utf-7').splitlines()
        reader = csv.DictReader(decoded_file)
        line_number = 0
        for row in reader:
            # basic info
            try:
                username = row['username'].strip()
                name = row['name'].strip()
                email = row['email'].strip()
                role = row['role'].strip()
                campus_short_name = row['campus']
            except KeyError:
                messages.error(request, "invalid column header in csv file.Column headers must be contain username,"
                               " name, email, role and campus.")
                return redirect('user_register_csv')

            # validate data
            val = validate_data(request, username, name, email, line_number)

            if val == 0:
                continue

            # role info
            try:
                role = Role.objects.get(short_name=role)
                if role.short_name == 'super':
                    messages.error(
                        request, "the role of {} is super admin, it is not valid".format(username))
                    continue
            except Role.DoesNotExist:
                messages.error(request, "invalid role for user " + username)
                continue

            # campus info
            if not campus_short_name.replace(' ', '') == '':
                try:
                    campus = Campus.objects.get(short_name=campus_short_name)
                except Campus.DoesNotExist:
                    messages.error(
                        request, "invalid campus for user " + username)
                    continue
            else:
                campus = None
            try:
                chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
                if 'password' in row:
                    secret_key = row['password']
                else:
                    secret_key = get_random_string(8, chars)
                obj, created = User.objects.get_or_create(
                    username=username,
                    name=name,
                    email=email,
                    campus=campus,
                    role=role,
                )
                obj.set_password(secret_key)
                obj.save()

            except IntegrityError:
                messages.error(
                    request, "invalid information for user " + username)
            line_number += 1
    if not line_number:
        messages.error(request, " no user register.")
    else:
        messages.success(request, str(line_number) +
                         " user register successfully.")
    return redirect('user_register_csv')


@login_required
@admin_auth
def user_register_csv(request):
    if request.method == "POST":
        form1 = CSVUserUpload(request.POST, request.FILES)
        if form1.is_valid():
            file = request.FILES.get('file')
            register_csv(request, file)
            return redirect('user_register')
    else:
        form1 = CSVUserUpload()
    form = AddUser()
    return render(request, 'user_register.html', {'form': form, 'form1': form1, 'user': 'hover'})


def generate_users_password_csv(request, total_users):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="User Password Generate.csv"'
    writer = csv.writer(response)
    writer.writerow(['#', 'Username', 'Name', 'Email', 'Role', 'Password'])
    for user in total_users:
        writer.writerow(user)
    return response


@login_required
@admin_auth
def generate_user_password(request, role_type):
    role = Role.objects.get(short_name=role_type)
    return render(request, 'generate_password.html', {'role': role})


@login_required
@admin_auth
def generate_password_done(request, role_id):
    role = Role.objects.get(pk=role_id)
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
    total_users = []
    count = 1
    all_users = User.objects.filter(role=role)
    for user in all_users:
        secret_key = get_random_string(6, chars)
        user.set_password(secret_key)
        user.save()
        total_users.append((count, user.username, user.name, user.email,
                            user.role.role, secret_key))
        count += 1
    excel = generate_users_password_csv(request, total_users)
    return excel

    return redirect('user_list')


@login_required
@admin_auth
def setting(request):
    return render(request, 'setting.html')


@login_required
@admin_auth
def campus_list(request):
    campus_list = Campus.objects.all().order_by('name')
    campus_list, paginator = pagination(request, campus_list)
    return render(request, 'campus_list.html', {'campus_list': campus_list, "paginator": paginator})


@login_required
@admin_auth_and_campus_exist
def edit_campus(request, campus_id):
    campus = Campus.objects.get(pk=campus_id)
    if request.method == "POST":
        form = EditCampus(request.POST, request.FILES, instance=campus)
        if form.is_valid():
            post = form.save(commit=False)
            post.save()
            messages.success(request, "The campus " +
                             campus.name+" was update successfully.")
            return redirect('edit_campus', campus.id)
    else:
        form = EditCampus(instance=campus)

    return render(request, 'edit_campus.html', {'form': form, 'campus_id': campus.id})


@login_required
@admin_auth_and_campus_exist
def delete_campus(request, campus_id):
    campus = Campus.objects.get(pk=campus_id)
    return render(request, 'delete_campus.html', {'this_campus': campus})


@login_required
@admin_auth_and_campus_exist
def delete_campus_done(request, campus_id):
    campus = Campus.objects.get(pk=campus_id)
    campus.delete()
    messages.success(request, "campus " + campus.name +
                     " was deleted successfully.")
    return redirect('campus_list')


@login_required
@admin_auth
def campus_register(request):
    if request.method == "POST":
        form = CampusRegister(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.save()
            messages.success(request, "campus "+post.name +
                             " was added successfully.")
            return redirect('campus_list')
    else:
        form = CampusRegister()
    return render(request, 'campus_register.html', {'form': form})




@login_required
# @admin_or_jury_auth
@admin_site_jury_auth
def rating(request):
    user_rating = User.objects.filter(
        role__short_name='contestant', rating__gt=0).order_by('rating').reverse()

    user_rank = [[rank + 1, row] for rank, row in enumerate(user_rating)]
    rank = 1
    for i in range(1, len(user_rank)):
        if user_rank[i-1][1].rating == user_rank[i][1].rating:
            # user_rank[i][0] = ''
            user_rank[i][0] = rank
        else:
            rank = i + 1
        

    user_rank, paginator = pagination(request, user_rank)
    base_page = check_base_site(request)
    context = {
        "user_rank": user_rank,
        'paginator': paginator,
        "base_page": base_page,
        'rating': 'hover'
    }
    return render(request, 'rating.html', context)



def difficulty(statistics):
    try:
        ratio = 8.9 * \
            float(statistics.accurate_submissions) / \
            statistics.total_submissions
    except ZeroDivisionError:
        ratio = 8.9
    difficulty = round(9.9 - ratio, 1)
    return difficulty


def university_ranklists(role):
    statistics = Statistics.objects.filter(is_active=True)
    active_problem = {stat.problem: stat for stat in statistics}
    user_list = User.objects.filter(role__short_name=role)
    university_list = set([user.campus for user in user_list])
    university_user_list_dict = {campus: [] for campus in university_list}
    university_dict = {campus.id: campus for campus in university_list}
    for user in user_list:
        university_user_list_dict[user.campus].append(user)

    rating_list = list()
    for campus in university_user_list_dict:
        user_list = university_user_list_dict[campus]
        univ_rate = 0.0
        for user in user_list:
            problem = set()
            submit_list = Submit.objects.filter(user=user, result="Correct")
            for sub in submit_list:
                problem.add(sub.problem)
            user_rate = 0.0
            for pro in problem:
                if not pro in active_problem:
                    continue
                user_rate += difficulty(active_problem[pro])
            univ_rate += user_rate
        rating_list.append([round(univ_rate, 1), campus.id, len(user_list)])

    rating_list.sort(reverse=True)

    if rating_list:
        rating_list[0].append(1)
    for i in range(1, len(rating_list)):
        if rating_list[i][0] == rating_list[i-1][0]:
            rating_list[i].append('')
        else:
            rating_list[i].append(i+1)

    university_ranklists = list()
    for i in rating_list:
        univ_rank = {'rank': i[-1], 'university': university_dict[i[1]],
                     'user_count': i[2],  'point': i[0]}
        university_ranklists.append(univ_rank)
    return university_ranklists


def country_ranklists(role):
    statistics = Statistics.objects.filter(is_active=True)
    active_problem = {stat.problem: stat for stat in statistics}
    user_list = User.objects.filter(role__short_name=role)
    country_list = set([user.campus.country for user in user_list])
    country_user_list_dict = {country: [] for country in country_list}
    for user in user_list:
        country_user_list_dict[user.campus.country].append(user)

    rating_list = list()
    for country in country_user_list_dict:
        user_list = country_user_list_dict[country]
        country_rate = 0.0
        university_set = set()
        for user in user_list:
            university_set.add(user.campus)
            problem = set()
            submit_list = Submit.objects.filter(user=user, result="Correct")
            for sub in submit_list:
                problem.add(sub.problem)

            user_rate = 0.0
            for pro in problem:
                if not pro in active_problem:
                    continue
                user_rate += difficulty(active_problem[pro])
            country_rate += user_rate
        rating_list.append([round(country_rate, 1), country,
                            len(user_list), len(university_set)])

    rating_list.sort(reverse=True)

    if rating_list:
        rating_list[0].append(1)
    for i in range(1, len(rating_list)):
        if rating_list[i][0] == rating_list[i-1][0]:
            rating_list[i].append('')
        else:
            rating_list[i].append(i+1)

    country_ranklists = list()
    for i in rating_list:
        country_rank = {'rank': i[-1], 'country': i[1],
                        'user_count': i[2], 'university_count': i[3], 'point': i[0]}
        country_ranklists.append(country_rank)
    return country_ranklists


def user_ranklists(role):
    statistics = Statistics.objects.filter(is_active=True)
    active_problem = {i.problem: i for i in statistics}
    user_list = User.objects.filter(role__short_name=role)
    user_dict = {i.id: i for i in user_list}
    rating_list = list()
    for user in user_list:
        problem = set()
        submit_list = Submit.objects.filter(user=user, result="Correct")
        for sub in submit_list:
            problem.add(sub.problem)
        rate = 0.0
        for pro in problem:
            if not pro in active_problem:
                continue
            rate += difficulty(active_problem[pro])
        rating_list.append([round(rate, 1), user.id])

    rating_list.sort(reverse=True)

    rank_number = 1
    if rating_list:
        rating_list[0].append(rank_number)
    
    for i in range(1, len(rating_list)):
        if rating_list[i][0] == rating_list[i-1][0]:
            rating_list[i].append(rank_number)
            # rating_list[i].append('')
        else:
            rank_number = i + 1
            rating_list[i].append(rank_number)

    user_ranklists = list()
    for i in rating_list:
        user_rank = {'rank': i[-1], 'user': user_dict[i[1]], 'point': i[0]}
        user_ranklists.append(user_rank)
    return user_ranklists


@login_required
@public_auth
def ranklists(request):
    user_rank = user_ranklists("public")
    university_rank = university_ranklists("public")
    country_rank = country_ranklists("public")
    
    page_number = request.GET.get('page', 1)
    rank_type = request.GET.get('type', "user")
    user_page_number = 1
    university_page_number = 1
    country_page_number = 1
    
    if rank_type == 'user': user_page_number=page_number
    elif rank_type == 'university': university_page_number=page_number
    elif rank_type == 'country': country_page_number=page_number
   
    user_rank, user_paginator = page_number_pagination(request, user_rank, user_page_number)
    university_rank, university_paginator = page_number_pagination(request, university_rank, university_page_number)
    country_rank, country_paginator = page_number_pagination(request, country_rank, country_page_number)
    
    context = {
                'user_ranklists': user_rank,
                'university_ranklists': university_rank,
                'country_ranklists': country_rank,
                'user_paginator': user_paginator,
                'university_paginator': university_paginator,
                'country_paginator': country_paginator
                }

    return render(request, 'ranklists.html', context)

@login_required
@admin_site_jury_auth
def leaderboard(request):
    user_rank = user_ranklists("contestant")
    university_rank = university_ranklists("contestant")
    country_rank = country_ranklists("contestant")

    page_number = request.GET.get('page', 1)
    rank_type = request.GET.get('type', "user")
    user_page_number = 1
    university_page_number = 1
    country_page_number = 1
    
    if rank_type == 'user': user_page_number=page_number
    elif rank_type == 'university': university_page_number=page_number
    elif rank_type == 'country': country_page_number=page_number
   
    user_rank, user_paginator = page_number_pagination(request, user_rank, user_page_number)
    university_rank, university_paginator = page_number_pagination(request, university_rank, university_page_number)
    country_rank, country_paginator = page_number_pagination(request, country_rank, country_page_number)
    
    base_page = check_base_site(request)
    context = {
                'user_ranklists': user_rank,
                'university_ranklists': university_rank,
                'country_ranklists': country_rank,
                'user_paginator': user_paginator,
                'university_paginator': university_paginator,
                'country_paginator': country_paginator,
                'rank_type': rank_type,
                'base_page': base_page,
                'leaderboard': 'hover'
                }
    return render(request, 'leaderboard.html', context)
