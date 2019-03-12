import paramiko
import sys, os
import json
from jinja2 import Environment, FileSystemLoader
from pymongo import MongoClient
import time

TEAMS_FILE = 'container_teams.json'
TEST_SCRIPT = 'test_script.sh'
REPORTS_DIR = 'container_reports'
client = MongoClient('mongodb://anask.xyz:27017')
db = client['ccbd-reports']
container_reports_collection = db['container_reports']

def block_print():
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

def enable_print():
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

def run_tests(teams, test_script):
   reports = {}

   for (team_id, team_data) in teams.items():
      print('Running tests for team ' + team_id)
      report = {}

      private_key = team_data['private_key']
      key = paramiko.RSAKey.from_private_key_file(private_key)

      public_ip = team_data['ip']
      report['public_ip'] = public_ip

      username = team_data['username']
      report['username'] = username

      block_print()
      client = paramiko.SSHClient()
      client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      client.connect(hostname=public_ip, username=username, pkey=key)
      enable_print()

      _, stdout, stderr = client.exec_command(test_script)

      report['stdout'] = filter(
         lambda line: line,
         stdout.read().decode("utf-8").split('\n')
      )
      report['stderr'] = filter(
         lambda line: line,
         stderr.read().decode("utf-8").split('\n')
      )

      client.close()

      reports[team_id] = report
   
   return reports

def get_test_script():
    file = open(TEST_SCRIPT, 'r')
    contents = file.read()
    file.close()
    return contents 

def load_teams():
    file = open(TEAMS_FILE)
    teams = json.load(file)
    file.close()

    return teams

if len(sys.argv) == 3 and sys.argv[1] == '--team':
    team_id = sys.argv[2]
    if team_id in teams:
        teams = { team_id: teams[team_id] }

test_script = get_test_script()

# -----------------------------------------------------------------------

fs_loader = FileSystemLoader('.')
env = Environment(loader = fs_loader)

template = env.get_template('container_template.html')

def container_generate(teams_str):
   teams = json.loads(teams_str)
   print('Running tests...')
   reports = run_tests(teams, test_script)

   response = []

   for team_id in reports.keys():
       report = reports[team_id]
       html_report = template.render(team_id=team_id, report=report)
       encoded_report = html_report.encode("UTF-8")

       # Inserting the report in the database
       date = round(time.time(), 2)
       report_document = {
          'team_id': team_id,
          'encoded_report': encoded_report,
          'date': date
       }
       container_reports_collection.insert_one(report_document)
       print('Container Report for team ' + team_id + ' has been updated in the database.')
       data_chunk = {
            'team_id': team_id,
            'link': '/ccbd/containerReports/' + team_id + '/' + str(date)
       }
       response.append(data_chunk)
   return response

def student_generate(ip, username, private_key_str):
   teams = {}
   teams['TEAM_ID_NOT_APPLICABLE'] = {
      'ip': ip,
      'username': username,
      'private_key': private_key_str
   }
   print('Generating report for student')

   reports = run_tests(teams, test_script)
   report = reports['TEAM_ID_NOT_APPLICABLE']
   html_report = template.render(team_id='TEAM_ID_NOT_APPLICABLE', report=report)
   encoded_report = html_report.encode("UTF-8")
   print('Report generation for student complete.')

   return encoded_report
