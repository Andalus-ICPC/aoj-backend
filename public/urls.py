from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path('problem/', views.public_problem_list, name='public_problem'),
    path('submit/', views.public_submit, name='public_submit'),
    # path('submit/process/', views.ajax_submit_process, name='ajax_submit_process'),
    path('submit/specific-problem/<int:problem_id>/', views.submit_specific_problem, name='submit_specific_problem'),
    path('submit/specific-problem-editor/<int:problem_id>/', views.submit_specific_problem_with_editor, name='submit_specific_problem_with_editor'),
    
    path('submissions', views.public_user_submission, name='public_user_submission'),
    path('submit-detail/<int:submit_id>/', views.public_submission_detail, name='public_submission_detail'),
    path('rejudge/filter/', views.public_rejudge_submission_filter, name='public_rejudge_submission_filter'),
    path('submission/filter/', views.public_view_submission_filter, name='public_view_submission_filter'),
    path('single-rejudge/<int:submit_id>/', views.public_single_rejudge, name='public_single_rejudge'),
    path('multi-rejudge/<int:problem_id>/<int:contest_id>/<int:user_id>/', views.public_multi_rejudge, name='public_multi_rejudge'),
    path('rejudge/process/', views.ajax_public_rejudge, name='ajax_public_rejudge'),
    path('rejudge/submission-list', views.public_rejudge_submission_list, name='public_rejudge_submission_list'),
    path('submit-with-editor/', views.public_submit_with_editor, name='public_submit_with_editor'),
    path('submit/language-and-problem/', views.public_ajax_get_language_list, name='public_ajax_get_language_list'),
   ]
