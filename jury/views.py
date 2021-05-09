from django.shortcuts import render
from problem.models import Problem
from contest.models import Contest
from authentication.models import User
from competitive.models import Submit
from django.contrib.auth.decorators import login_required
from authentication.decorators import jury_auth, jury_auth_and_contest_exist, site_or_jury_auth
from django.utils import timezone
from authentication.pagination import pagination, page_number_pagination


@login_required
def jury_homepage(request):
    return render(request, 'jury_homepage.html')


@login_required
@jury_auth
def jury_user_list(request):
    contestant_user = User.objects.filter(role__short_name="contestant").order_by('username')
    admin_user = User.objects.filter(role__short_name="admin").order_by('username')
    jury_user = User.objects.filter(role__short_name="jury").order_by('username')
    site_admin_user = User.objects.filter(role__short_name="site").order_by('username')
    public_user = User.objects.filter(role__short_name="public").order_by('username')

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

    return render(request, 'jury_user_list.html', context)


@login_required
@jury_auth
def jury_view_problem(request):
    total_problems = Problem.objects.all().order_by('pk').reverse()
    total_problems, paginator = pagination(request, total_problems)

    return render(request, 'jury_problem_list.html', {'problem': total_problems, 'paginator': paginator, 'pro': 'hover'})


@login_required
@jury_auth
def jury_contest_list(request):
    total_contest = Contest.objects.all().order_by('start_time').reverse()
    now = timezone.now()
    for contest in total_contest:
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
        
    total_contest, paginator = pagination(request, total_contest)

    return render(request, 'jury_contest_list.html', {'contest': total_contest, 'paginator': paginator, 'cont': 'hover'})


@login_required
@jury_auth_and_contest_exist
def jury_contest_detail(request, contest_id):
    contest = Contest.objects.get(pk=contest_id)
    problem = contest.problem.all()
    user = contest.user.all()
    
    page_number = request.GET.get('page', 1)
    page_type = request.GET.get('type', "problem")
    problem_page_number = 1
    user_page_number = 1


    if page_type == 'problem': problem_page_number=page_number
    elif page_type == 'user': user_page_number=page_number
  
    problem, problem_paginator = page_number_pagination(request, problem, problem_page_number, 10)
    user, user_paginator = page_number_pagination(request, user, user_page_number, 10)

    context = {
        'contest': contest,
        'problem': problem,
        'user': user,
        'problem_paginator': problem_paginator,
        'user_paginator': user_paginator, 
        'cont': 'hover'
    }
    return render(request, 'jury_contest_detail.html', context)
