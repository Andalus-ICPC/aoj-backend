from django.shortcuts import render, render_to_response, redirect
from django.http import JsonResponse
from problem.models import Problem
from public.forms import SubmitAnswer, SubmitSpecificProblem, SubmitWithEditor, SubmitSpecificProblemWithEditor
from competitive.models import Submit, Language, TestcaseOutput, TestCase
from competitive.views import read_source_code, read_from_file, java_class_name_find
from django.contrib.auth.decorators import login_required
from authentication.decorators import public_auth, public_auth_and_problem_exist, admin_auth, \
        admin_jury_auth_and_submit_exist, admin_or_jury_auth, admin_jury_auth_and_contest_exist, \
        admin_auth_and_submit_exist, admin_site_jury_auth, admin_site_jury_auth_and_contest_exist,\
        admin_site_jury_auth_and_submit_exist
from django.utils import timezone
from public.models import Statistics
from django.db import IntegrityError
from authentication.models import User
from authentication.views import check_base_site
from contest.models import Contest
from problem.views import update_statistics
import math
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import BytesIO
import sys, os
from competitive.judge_background import judge_background
import requests
from authentication.pagination import pagination
# Create your views here.


def difficulty(statistics):
    try:
        ratio = 8.9 * \
            float(statistics.accurate_submissions) / \
            statistics.total_submissions
    except ZeroDivisionError:
        ratio = 8.9
    difficulty = round(9.9 - ratio, 1)
    return difficulty


@login_required
@public_auth
def public_problem_list(request):
    # problem_list = Problem.objects.filter(is_public=True).order_by('title')
    problem_list = Statistics.objects.filter(problem__is_public=True, is_active=True).order_by("problem__title")
    for stats in problem_list:
        stats.difficulty = difficulty(stats)
        try:
            stats.submissions_ratio = 100 * stats.accurate_submissions // stats.total_submissions
        except ZeroDivisionError:
            stats.submissions_ratio = 100

        try:
            stats.user_ratio = 100 * stats.accurate_users // stats.total_users
        except ZeroDivisionError:
            stats.user_ratio = 100
    for stat in problem_list:
        submit = Submit.objects.filter(user=request.user, problem=stat.problem)
        if submit.filter(result="Correct"):
            stat.status = "Solved"
        elif submit:
            stat.status = "Not Solved"
        else:
            stat.status = "Not Try"
    problem_list, paginator = pagination(request, problem_list)
    context = {'problem_list': problem_list, 'paginator': paginator, 'pro': 'hover'}
    return render(request, 'problem_list.html', context)



@login_required
@public_auth
def public_submit(request):
    problem_list = Problem.objects.filter(is_public=True).order_by('title')
    if request.method == "POST":
        form = SubmitAnswer(request.POST, request.FILES)
        form.fields['problem'].queryset = problem_list
        if form.is_valid():
            post = form.save(commit=False)
            post.submit_time = timezone.now()
            post.user = request.user
            post.submit_file = None
            post.server_id = 1
            post.save()

            post.submit_file = request.FILES.get('submit_file')
            post.result = 'Judging'
            post.save()
            judge_background.apply_async([post.id])
            # result = judge(file_name=post.submit_file.path,
            #                problem=post.problem, language=post.language, submit=post)
            # post.result = result
            # post.save()
            update_statistics(post)
            return redirect('public_submit')
    else:
        form = SubmitAnswer()
        form.fields['problem'].queryset = problem_list
    all_submits = Submit.objects.filter(
        user=request.user).order_by('submit_time').reverse()
    for i in all_submits:
        i.source_code = read_source_code(i.submit_file)
        i.language_mode = i.language.editor_mode
    form1 = SubmitWithEditor()
    form1.fields['problem'].choices = [(None, '----------')] + [(i.id, i) for i in problem_list]
    form1.fields['language'].choices = [(None, '----------')]  + [(i.id, i) for i in Language.objects.filter(enable=True)]
    
    all_submits, paginator = pagination(request, all_submits)
    context = {'form': form, 'form1': form1, 'all_submits': all_submits, "paginator": paginator, 'submit': 'hover'}
    return render(request, 'public_submit.html', context)



@login_required
@public_auth
def public_submit_with_editor(request):
    problem_list = Problem.objects.filter(is_public=True).order_by('title')
    if request.method == "POST":
        form1 = SubmitWithEditor(request.POST)
        form1.fields['problem'].choices = [(None, '----------')]  + [(i.id, i) for i in problem_list]
        form1.fields['language'].choices =[(None, '----------')]  + [(i.id, i) for i in Language.objects.filter(enable=True)]
        if form1.is_valid():
            post = Submit()
            now = timezone.now()
            post.submit_time = now
            post.user = request.user
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
            # result = judge(file_name=post.submit_file.path,
            #                problem=post.problem, language=post.language, submit=post)
            # post.result = result
            # post.save()
            judge_background.apply_async([post.id])
            os.system(f'rm "{path}"')
            update_statistics(post)
            return redirect('public_submit')
    else:
        form1 = SubmitWithEditor()
        form1.fields['problem'].choices = [(None, '----------')]  +  [(i.id, i) for i in problem_list]
        form1.fields['language'].choices = [(None, '----------')]  + [(i.id, i) for i in Language.objects.filter(enable=True)]

    all_submits = Submit.objects.filter(
        user=request.user).order_by('submit_time').reverse()
    for i in all_submits:
        i.source_code = read_source_code(i.submit_file)
        i.language_mode = i.language.editor_mode
    form = SubmitAnswer()
    form.fields['problem'].queryset = problem_list

    all_submits, paginator = pagination(request, all_submits)
    context = {'form': form, 'form1': form1, 'all_submits': all_submits, "paginator": paginator, 'submit': 'hover'}
    
    return render(request, 'public_submit.html', context)


@login_required
@public_auth_and_problem_exist
def submit_specific_problem(request, problem_id):
    problem = Problem.objects.get(pk=problem_id)
    initial_info = {'specific_problem': problem.title}
    if request.method == "POST":
        form = SubmitSpecificProblem(
            request.POST, request.FILES, initial=initial_info)
        if form.is_valid():
            post = form.save(commit=False)
            post.submit_time = timezone.now()
            post.user = request.user
            post.problem = problem
            post.submit_file = None
            post.server_id = 1
            post.save()
            post.submit_file = request.FILES.get('submit_file')
            post.result = 'Judging'
            post.save()
            judge_background.apply_async([post.id])

            update_statistics(post)
            return redirect('submit_specific_problem', problem_id)
    else:
        form = SubmitSpecificProblem(initial=initial_info)
    all_submits = Submit.objects.filter(
        user=request.user, problem=problem, problem__is_public=True).order_by('submit_time').reverse()
    for i in all_submits:
        i.source_code = read_source_code(i.submit_file)
        i.language_mode = i.language.editor_mode

    form1 = SubmitSpecificProblemWithEditor(initial=initial_info)
    form1.fields['language'].choices = [(None, '----------')]  + [(i.id, i) for i in Language.objects.filter(enable=True)]

    all_submits, paginator = pagination(request, all_submits)
    context = {'form': form, 'form1': form1, 'all_submits': all_submits, 'problem': problem, "paginator": paginator, 'submit': 'hover'}
    
    return render(request, 'public_specific_problem_submit.html', context)



@login_required
@public_auth
def submit_specific_problem_with_editor(request, problem_id):
    problem = Problem.objects.get(pk=problem_id)
    initial_info = {'specific_problem': problem.title}
    if request.method == "POST":
        form1 = SubmitSpecificProblemWithEditor(request.POST, initial=initial_info)
        form1.fields['language'].choices =[(None, '----------')]  + [(i.id, i) for i in Language.objects.filter(enable=True)]
        if form1.is_valid():
            post = Submit()
            now = timezone.now()
            post.submit_time = now
            post.user = request.user
            lang = Language.objects.get(pk=int(request.POST['language']))
            post.language = lang
            post.problem = problem
            post.submit_file = None
            post.server_id = 1
            post.save()

            path = problem.title + '_' + str(request.user.id) + '_' + str(now) +'.' + lang.extension
            path = path.replace(' ', '').replace('/', '')

            source = request.POST['source']
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
            judge_background.apply_async([post.id])

            os.system(f'rm "{path}"')
            update_statistics(post)
            return redirect('submit_specific_problem', problem_id)
    else:
        form1 = SubmitSpecificProblemWithEditor(initial=initial_info)
        form1.fields['language'].choices = [(None, '----------')]  + [(i.id, i) for i in Language.objects.filter(enable=True)]

    all_submits = Submit.objects.filter(
        user=request.user).order_by('submit_time').reverse()
    for i in all_submits:
        i.source_code = read_source_code(i.submit_file)
        i.language_mode = i.language.editor_mode
    form = SubmitSpecificProblem(initial=initial_info)

    all_submits, paginator = pagination(request, all_submits)
    context = {'form': form, 'form1': form1, 'all_submits': all_submits, 'problem': problem,
               "paginator": paginator, 'submit': 'hover'}
    
    return render(request, 'public_specific_problem_submit.html', context)


@login_required
@admin_site_jury_auth
def public_user_submission(request):
    
    problem_id = request.GET.get('problem_id', 0)
    result = request.GET.get('result', "All")

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
     
    all_submission = Submit.objects.filter(user__role__short_name='public').order_by('submit_time').reverse()
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

    all_results = ['Correct', 'Wrong Answer', 'Judging', 'Time Limit Exceeded', 'Run Time Error',  
                    'Compiler Error', 'Memory Limit Exceeded', 'No Output']
    
    submission_list, paginator = pagination(request, submission_list)

    base_page = check_base_site(request)
    context = {'submission_list': submission_list, 'all_problems': all_problems, 'paginator': paginator,
               'all_results': all_results, "selected_problem": problem_id, "problem_title": problem_title,
               'selected_result': result, 'base_page': base_page, 'submit': 'hover'
               }
    return render(request, 'public_view_submission.html', context)


@login_required
@admin_site_jury_auth
def public_view_submission_filter(request):
    try:
        problem_id = int(request.GET.get('problem_id'))
    except ValueError:
        return redirect('homepage')

    result = request.GET.get('result')

    if not problem_id == 0:
        try:
            problem_title = Problem.objects.get(pk=problem_id).title
        except Problem.DoesNotExist:
            problem_title = None

    if problem_id == 0:
        if result == "All":
            submission_list = Submit.objects.filter(user__role__short_name='public').order_by('submit_time').reverse()
        else:
            submission_list = Submit.objects.filter(user__role__short_name='public', result=result).order_by('submit_time').reverse()
        problem_title = "All problems"    
    else:
        if result == "All":
            submission_list = Submit.objects.filter(user__role__short_name='public', problem_id=problem_id).order_by('submit_time').reverse()
        else:
            submission_list = Submit.objects.filter(user__role__short_name='public', problem_id=problem_id, result=result).order_by('submit_time').reverse()

    submission_list, paginator = pagination(request, submission_list)
    
    context = {'submission_list': submission_list, 'problem_title': problem_title,
               'paginator': paginator, 'selected_problem': problem_id, 
               'selected_result': result, 'submit': 'hover'}
    return render(request, 'public_view_submission_filter.html', context)


@login_required
@admin_site_jury_auth_and_submit_exist
def public_submission_detail(request, submit_id):
    submit = Submit.objects.get(pk=submit_id)

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
    context = {'submit': submit, 'submit_file': submit_file, 'language_mode': language_mode, 'file_name': file_name,
               'submit_detail': submit_detail, 'base_page': base_page}
    return render(request, 'public_submission_detail.html', context)



@login_required
@admin_auth
def public_rejudge_submission_list(request):
   
    problem_id = request.GET.get('problem_id', 0)
    result = request.GET.get('result', "All")

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
        user__role__short_name='public').order_by('submit_time').reverse()
    
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

    all_results = ['Correct', 'Wrong Answer', 'Judging', 'Time Limit Exceeded', 'Run Time Error',  
                    'Compiler Error', 'Memory Limit Exceeded', 'No Output']
    
    submission_list, paginator = pagination(request, submission_list)

    context = {'submission_list': submission_list, 'all_problems': all_problems, 'paginator': paginator,
               'all_results': all_results, "selected_problem": problem_id, "problem_title": problem_title,
               'selected_result': result, 'rejudge': 'hover'
               }
    return render(request, 'public_rejudge_submission_list.html', context)


@login_required
@admin_auth
def public_rejudge_submission_filter(request):
    try:
        problem_id = int(request.GET.get('problem_id'))
    except ValueError:
        return redirect('homepage')
        
    result = request.GET.get('result')

    if not problem_id == 0:
        try:
            problem_title = Problem.objects.get(pk=problem_id).title
        except Problem.DoesNotExist:
            problem_title = None

    if problem_id == 0:
        if result == "All":
            submission_list = Submit.objects.filter(
                user__role__short_name='public').order_by('submit_time').reverse()
        else:
            submission_list = Submit.objects.filter(
                user__role__short_name='public', result=result).order_by('submit_time').reverse()
        problem_title = "All problems"    
    else:
        if result == "All":
            submission_list = Submit.objects.filter(
                user__role__short_name='public', problem_id=problem_id).order_by('submit_time').reverse()
        else:
            submission_list = Submit.objects.filter(
                user__role__short_name='public', problem_id=problem_id, result=result).order_by('submit_time').reverse()
    
    submission_list, paginator = pagination(request, submission_list)

    context = {'submission_list': submission_list, 'problem_title': problem_title,
               'paginator': paginator, 'selected_problem': problem_id, 
               'selected_result': result, 'rejudge': 'hover'}
    return render(request, 'public_rejudge_filter.html', context)


@login_required
@admin_auth
def ajax_public_rejudge(request):
    total_submits = request.GET.getlist('total_submit[]')
    rejudge_submits = [int(i) for i in total_submits]
    result_dict = {}
    for submit_id in rejudge_submits:
        try:
            submit = Submit.objects.get(pk=submit_id)
            previous_result = submit.result
            if submit.result == "Judging":
                result_dict[submit_id] = "Judging *"
                continue
            if os.path.exists(submit.submit_file.path):
                submit.result = "Judging"
                submit.save()
                judge_background.apply_async([submit.id, True, True, previous_result])
                result = submit.result
            else:
                result = "file not found"
            
        except Submit.DoesNotExist:
            result = 'no submitted'
        result_dict[submit_id] = result
    response_data = {'result': result_dict}
    return JsonResponse(response_data, content_type="application/json")


@login_required
@admin_auth_and_submit_exist
def public_single_rejudge(request, submit_id):
    single_submit = Submit.objects.get(pk=submit_id)
    submit = [single_submit]

    return render(request, 'public_single_user_rejudge.html', {'submit': submit, 'rejudge': 'hover'})


@login_required
@admin_auth
def public_multi_rejudge(request, problem_id, contest_id, user_id):
    
    submit = Submit.objects.filter(user__role__short_name='public', 
                        problem_id=problem_id, user_id=user_id).order_by('submit_time')
    if not submit:
        return redirect('homepage')
    
    specific_submissions = list()
    for i in submit:
        if i.result == 'Correct':
            specific_submissions.append(i)
            break
        else:
            specific_submissions.append(i)
    
    specific_submissions, paginator = pagination(request, specific_submissions)
    context = {'submit': specific_submissions, 'contest_id': specific_submissions[0].contest.pk,
               'paginator': paginator, 'rejudge': 'hover'
               }
    return render(request, 'public_single_user_rejudge.html', context)



@login_required
@public_auth
def public_ajax_get_language_list(request):
    public_problem = Problem.objects.filter(is_public=True).order_by('title')
    language_list = [(lang.id, lang.extension)
                     for lang in Language.objects.filter(enable=True).order_by('name').reverse()]
    problem_list = [(pro.id, pro.title.lower())
                    for pro in public_problem]
    response_data = {"language_list": language_list,
                     "problem_list": problem_list}
    return JsonResponse(response_data, content_type="application/json")
