from django.shortcuts import render, redirect, HttpResponse
import requests
from django.contrib import messages
from authentication.decorators import admin_auth, admin_auth_and_server_exist
from django.contrib.auth.decorators import login_required
from problem.models import Problem, TestCase
import requests
from .models import JudgeServer
from .forms import AddJudgeserver
from zipfile import ZipFile
import os
from os.path import basename
import hashlib
import json

# Create your views here.

@login_required
@admin_auth
def judgeserver_list(request):
   judgeservers = JudgeServer.objects.all()
   for judgeserver in judgeservers:
      if not judgeserver.is_enabled:
         continue
      try:
         info = requests.get(judgeserver.address + '/info', timeout=10).json()
         judgeserver.server_name = info['hostname']
         judgeserver.server_cpu_number = info['cpu_core']
         judgeserver.server_cpu_usage = info['cpu']
         judgeserver.status = 'Normal'
         judgeserver.command_runner_version = info['CommandRunner_version']
         judgeserver.save()

         pro = {i for i in judgeserver.problem.all()}
         problem = {i for i in Problem.objects.all()}
         if problem.difference(pro):
            judgeserver.dump = True
         else:
            judgeserver.dump = False
         judgeserver.save()

      except Exception as e:
         judgeserver.server_name = 'unknown'
         judgeserver.server_cpu_number = None
         judgeserver.server_cpu_usage = None
         judgeserver.command_runner_version = 'unknown'
         judgeserver.status = 'Abnormal'
         judgeserver.dump = False
         judgeserver.save()

   return render(request, 'judgeserver_list.html', {'judgeservers': judgeservers, 'server': 'hover'})


@login_required
@admin_auth
def add_judgeserver(request):
   if request.method == "POST":
         form = AddJudgeserver(request.POST)
         if form.is_valid():
            post = form.save(commit=False)
            post.save()
            try:
               info = requests.get(post.address + '/info', timeout=10).json()
               form.save_m2m()
               for problem in post.problem.all():
                  testcase_transfer_to_server(post, problem)
               messages.success(request, "The server " +
                              post.address+" was registered successfully.")
            except:
               messages.success(request, "The server " +
                              post.address+" was registered successfully, but the server is not connected.")
            return redirect('judgeserver_list')
   else:
        form = AddJudgeserver()
   return render(request, 'add_judgeserver.html', {'form': form, 'server': 'hover'})

@admin_auth
@admin_auth_and_server_exist
def edit_judgeserver(request, judgeserver_id):
   judgeserver = JudgeServer.objects.get(pk=judgeserver_id)
   past_problem = {i for i in judgeserver.problem.all()}
   if request.method == "POST":
      form = AddJudgeserver(request.POST, instance=judgeserver)
    
      if form.is_valid():
         post = form.save(commit=False)
         post.save()
         try:
            info = requests.get(post.address + '/info', timeout=10).json()
            form.save_m2m()
            current_problem = {i for i in post.problem.all()}

            upload_problem = current_problem.difference(past_problem)
            remove_problem = past_problem.difference(current_problem)
            for problem in upload_problem:
               testcase_transfer_to_server(post, problem)
            
            try:
               requests.get(judgeserver.address + '/info', timeout=10).json()
               for problem in remove_problem:
                     try:
                        requests.post(post.address + "/remove_testcase",  data={'testcase_id': str(problem.id)}, timeout=10)
                     except:
                        pass
            except Exception:
               pass
            messages.success(request, "The server " +
                              post.address+" was update successfully.")
         except:
               messages.success(request, "The server " +
                              post.address+" was update successfully, but the server is not connected.")
               
         return redirect('judgeserver_list')
   else:
      form = AddJudgeserver(instance=judgeserver)
   return render(request, 'edit_judgeserver.html', {'form': form, 'judgeserver_id': judgeserver.id, 'server': 'hover'})


@login_required
@admin_auth_and_server_exist
def delete_judgeserver(request, judgeserver_id):
    judgeserver = JudgeServer.objects.get(pk=judgeserver_id)
    return render(request, 'delete_judgeserver.html', {'judgeserver': judgeserver, 'server': 'hover'})


@login_required
@admin_auth_and_server_exist
def delete_judgeserver_done(request, judgeserver_id):
   judgeserver = JudgeServer.objects.get(id=judgeserver_id)
   try:
      requests.get(judgeserver.address + '/info', timeout=10).json()
      for problem in judgeserver.problem.all():
         try:
            requests.post(judgeserver.address + "/remove_testcase",  data={'testcase_id': str(problem.id)}, timeout=10)
         except:
            pass
   except Exception:
      pass

   judgeserver.delete()
   messages.success(request, "The judgeserver " +
                     judgeserver.address + " was deleted successfully.")
   return redirect('judgeserver_list')


def _get_sha256(output_file):
		with open(output_file, 'rb') as f:
			content = f.read()
		return hashlib.sha256(content.rstrip()).hexdigest()


def testcase_name(path):
   index = path.rfind('/')
   return path[index + 1:]


def testcase_info(problem, path):
   testcase = TestCase.objects.filter(problem=problem)
   count = len(testcase)
   info = ""
   info += '{"number_of_testcases": %d, "testcases": {' %count
   info_list = []
   for test in testcase:
      temp_info = ""
      output_file = testcase_name(test.output.path)
      input_file = testcase_name(test.input.path)
      sha256 = _get_sha256(test.output.path)
      temp_info += '"%s": { "input_name": "%s", "output_name": "%s",' % (test.name, input_file, output_file)
      temp_info += '"sha256_output": "%s"}' % sha256
      info_list.append(temp_info)
   info += ",".join(info_list)
   info += "}}"

   info_file = open(path, "w")
   info_file.write(info)
   info_file.close()
   return info


@login_required
@admin_auth_and_server_exist
def dump_judgeserver(request, judgeserver_id):
   judgeserver = JudgeServer.objects.get(pk=judgeserver_id)
   try:
      info = requests.get(judgeserver.address + '/info').json()
   except:
      messages.warning(request, "The server " +
                     judgeserver.address + " is not connected.")
      return redirect('judgeserver_list')
   
   all_problem = [pro for pro in Problem.objects.all()]
   server_problem = [pro for pro in judgeserver.problem.all()]
   dump_problem = [pro for pro in all_problem if not pro in server_problem]
   for problem in dump_problem:
      testcase_transfer_to_server(judgeserver, problem)
   messages.success(request, "The problem testcase was transfer to judgeserver " +
                     judgeserver.address + " successfully.")
   return redirect('judgeserver_list')
  
def testcase_transfer_to_server(judgeserver, problem):
   BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

   pro_path = problem.pdf.path
   index = pro_path.rfind('/')
   pro_path = pro_path[:index]
   dirName = pro_path + "/testcase"

   filePath = os.path.join(dirName, "info")
   testcase_info(problem, filePath)
   path = os.path.join(BASE_DIR, '%d.zip' %problem.id)
   with ZipFile(path , 'w') as zipObj:
      for folderName, subfolders, filenames in os.walk(dirName):
         for filename in filenames:

            filePath = os.path.join(folderName, filename)
            zipObj.write(filePath,  basename(filePath))
   try:
      requests.post(judgeserver.address + "/upload_testcase",  files={'file': open(path, "rb")}, data={'testcase_id': str(problem.id)})
   except:
      os.remove(path)
      return
   judgeserver.problem.add(problem)
   judgeserver.save()
   os.remove(path)


