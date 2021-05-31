from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('request/', views.request_clarification, name='request_clarification'),
    path('view/', views.view_clarification, name='view_clarification'),
    path('view-jury/', views.view_jury_clarification, name='view_jury_clarification'),
    path('list/', views.clarification_list, name='clarification_list'),
    path('answered/', views.answered_clarification, name='answered_clarification'),
    path('new/', views.new_clarification_by_admin, name='new_clarification'),
    path('answer/<int:clarification_id>/<int:page_number>/', views.clarification_answer, name='clarification_answer'),
    path('edit/<int:clarification_id>/', views.edit_clarification, name='edit_clarification'),
    path('site-list/', views.site_clarification_list, name='site_clarification_list'),
    path('site-answered/', views.site_answered_clarification, name='site_answered_clarification'),
    path('site-new/', views.site_new_clarification_by_admin, name='site_new_clarification'),
    path('site-answer/<int:clarification_id>/<int:page_number>/', views.site_clarification_answer, name='site_clarification_answer'),
    path('site-edit/<int:clarification_id>/', views.site_edit_clarification, name='site_edit_clarification'),
   ]