import paramiko
import sys, os
import json
from jinja2 import Environment, FileSystemLoader
import time
import requests
from pymongo import MongoClient
import time

TEAMS_FILE = 'lb_teams.json'
REPORTS_DIR = 'lb_reports'
client = MongoClient('mongodb://anask.xyz:27017')
db = client['ccbd-reports']
lb_reports_collection = db['lb_reports']

def block_print():
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

def enable_print():
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

def execute_remotely(ip, username, key, script):
   block_print()
   client = paramiko.SSHClient()
   client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
   client.connect(hostname=ip, username=username, pkey=key)
   enable_print()

   _, stdout, stderr = client.exec_command(script)

   stdout = '\n'.join(filter(
      lambda line: line,
      stdout.read().decode("utf-8").split('\n')
   )) + '\n'
   stderr = '\n'.join(filter(
      lambda line: line,
      stderr.read().decode("utf-8").split('\n')
   )) + '\n'

   client.close()

   return stdout, stderr

def run_tests(teams):
   reports = {}

   for (team_id, team_data) in teams.items():
      print('Running tests for team ' + team_id)
      report = {}

      lb_dns = 'http://' + team_data['lb_dns']
      acts_ip = 'http://' + team_data['acts_ip']
      users_ip = 'http://' + team_data['users_ip']
      report['lb_dns'] = lb_dns
      report['acts_ip'] = acts_ip
      report['users_ip'] = users_ip

      acts_username = team_data['acts_username']
      users_username = team_data['users_username']
      report['acts_username'] = acts_username
      report['users_username'] = users_username

      acts_username = team_data['acts_username']
      users_username = team_data['users_username']
      report['acts_username'] = acts_username
      report['users_username'] = users_username

      report_stdout = ''
      report_stderr = ''

      # -------- test 1
      res = requests.get(acts_ip + '/api/v1/categories')
      if res.status_code >= 200 and res.status_code < 300:
         report_stdout += 'Acts microservice deployed at Acts IP ' + acts_ip + '\n'
      else:
         report_stderr += 'Acts microservice not deployed at Acts IP ' + acts_ip + '\n'

      # -------- test 2
      res = requests.get(users_ip + '/api/v1/users')
      if res.status_code >= 200 and res.status_code < 300:
         report_stdout += 'Users microservice deployed at Users IP ' + users_ip + '\n'
      else:
         report_stderr += 'Users microservice not deployed at Users IP ' + users_ip + '\n'

      

      # -------- test 3
      res = requests.delete(acts_ip + '/api/v1/_count')
      if res.status_code >= 200 and res.status_code < 300:
         report_stdout += 'Able to reset HTTP requests counter on Acts microservice\n'
      else:
         report_stderr += 'Unable to reset HTTP requests counter on Acts microservice\n'

      res = requests.delete(users_ip + '/api/v1/_count')
      if res.status_code >= 200 and res.status_code < 300:
         report_stdout += 'Able to reset HTTP requests counter on Users microservice\n'
      else:
         report_stderr += 'Unable to reset HTTP requests counter on Users microservice\n'

            

      # -------- test 4
      for i in range(2):
         requests.get(lb_dns + '/api/v1/users')
      
      for i in range(2):
         requests.get(lb_dns + '/api/v1/categories')
      
      for i in range(2):
         requests.get(lb_dns + '/api/v1/users')
      
      for i in range(2):
         requests.get(lb_dns + '/api/v1/categories')

      report_stdout += 'Made 4 GET requests to ' + lb_dns + '/api/v1/users\n'
      report_stdout += 'Made 4 GET requests to ' + lb_dns + '/api/v1/categories\n'


      acts_req_count = int(requests.get(acts_ip + '/api/v1/_count').json()[0])
      users_req_count = int(requests.get(users_ip + '/api/v1/_count').json()[0])

      if acts_req_count == 4:
         report_stdout += 'Request to Acts IP ' + acts_ip + '/api/v1/_count returned ' + str(acts_req_count) + '\n'
      else:
         report_stderr += 'Request to Acts IP ' + acts_ip + '/api/v1/_count returned ' + str(acts_req_count) + ' when 4 requests were actually made\n'
      
      if users_req_count == 4:
         report_stdout += 'Request to Users IP ' + users_ip + '/api/v1/_count returned ' + str(users_req_count) + '\n'
      else:
         report_stderr += 'Request to Users IP ' + users_ip + '/api/v1/_count returned ' + str(users_req_count) + ' when 4 requests were actually made\n'

      acts_private_key = team_data['acts_private_key']
      acts_key = paramiko.RSAKey.from_private_key_file(acts_private_key)

      stdout, stderr = execute_remotely(acts_ip.replace('http://',''), acts_username, acts_key, """
output=$(ps aux | grep dockerd | grep -v grep)
len=${#output}
if [ $len -gt 1 ]; then
   pid=$(echo $output | awk '{ print $2 }')
   echo "dockerd is running with PID $pid on Acts instance"
else
   echo "dockerd isn't running on Acts instance" >&2
   exit
fi

output=$(sudo docker ps | grep "acts")
len=${#output}
if [ $len -gt 1 ]; then
   ACTS_CID=$(echo $output | awk '{ print $1 }')
   echo "Image 'acts' is running with container ID $ACTS_CID on Acts instance"
else
   echo "Image 'acts' isn't running on Acts instance" >&2
   exit
fi

output=$(sudo docker port $ACTS_CID | grep "/tcp -> 0\.0\.0\.0:80")
len=${#output}
if [ $len -gt 1 ]; then
   echo "Acts container is listening on port 80"
else
   echo "Acts container isn't listening on port 80" >&2
   exit
fi

curl -s -o /dev/null --header "Content-Type: application/json" \
   --request POST \
   --data '["abc"]' \
   localhost/api/v1/categories
""")
      report_stdout += stdout
      report_stderr += stderr

      users_private_key = team_data['users_private_key']
      users_key = paramiko.RSAKey.from_private_key_file(users_private_key)

      stdout, stderr = execute_remotely(users_ip.replace('http://',''), users_username, users_key, """
output=$(ps aux | grep dockerd | grep -v grep)
len=${#output}
if [ $len -gt 1 ]; then
   pid=$(echo $output | awk '{ print $2 }')
   echo "dockerd is running with PID $pid on Users instance"
else
   echo "dockerd isn't running on Users instance" >&2
   exit
fi

output=$(sudo docker ps | grep "users")
len=${#output}
if [ $len -gt 1 ]; then
   USERS_CID=$(echo $output | awk '{ print $1 }')
   echo "Image 'users' is running with container ID $USERS_CID on Users instance"
else
   echo "Image 'users' isn't running on Users instance" >&2
   exit
fi

output=$(sudo docker port $USERS_CID | grep "/tcp -> 0\.0\.0\.0:80")
len=${#output}
if [ $len -gt 1 ]; then
   echo "Users container is listening on port 80"
else
   echo "Users container isn't listening on port 80" >&2
   exit
fi

sudo apt install -y tcpflow > /dev/null 2> /dev/null

curl -s -o /dev/null --header "Content-Type: application/json" \
   --request POST \
   --data '{"username":"xyz","password":"3d725109c7e7c0bfb9d709836735b56d943d263f"}' \
   localhost/api/v1/users

rm -f logs
touch logs
sudo timeout 1000 tcpflow -p -c -i eth0 port 80 >> logs 2> /dev/null &
sleep 7
""")
      report_stdout += stdout
      report_stderr += stderr

      requests.post(acts_ip + '/api/v1/acts', json=json.loads('{"actId":1, "username":"xyz", "timestamp":"10-10-2019:45-23-03", "caption":"#helloworld", "categoryName":"abc", "imgB64":"bWF5byBvciBtdXN0Pw=="}'))

      stdout, stderr = execute_remotely(users_ip.replace('http://',''), users_username, users_key, """
output=$(grep 'GET /api/v1/users' logs)
len=${#output}
if [ $len -gt 1 ]; then
   echo "Acts microservice did make GET request to users microservice for list of users"
else
   echo "Acts microservice didn't make GET request to users microservice for list of users" >&2
   exit
fi
""")
      report_stdout += stdout
      report_stderr += stderr

      requests.delete(acts_ip + '/api/v1/acts/1')
      requests.delete(acts_ip + '/api/v1/categories/abc')
      requests.delete(users_ip + '/api/v1/users/xyz')

      report['stdout'] = filter(lambda l: l, report_stdout.split('\n'))
      report['stderr'] = filter(lambda l: l, report_stderr.split('\n'))

      reports[team_id] = report
   
   return reports 

def load_teams():
    file = open(TEAMS_FILE)
    teams = json.load(file)
    file.close()

    return teams

if len(sys.argv) == 3 and sys.argv[1] == '--team':
    team_id = sys.argv[2]
    if team_id in teams:
        teams = { team_id: teams[team_id] }


# -----------------------------------------------------------------------

fs_loader = FileSystemLoader('.')
env = Environment(loader = fs_loader)

template = env.get_template('lb_template.html')

def lb_generate(teams_str):
   teams = json.loads(teams_str)
   print('Running tests...')
   reports = run_tests(teams)

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
       lb_reports_collection.insert_one(report_document)
       print('Load balancing report for team ' + team_id + ' has been updated in the database.')
       data_chunk = {
          'team_id': team_id,
          'link': '/ccbd/lbReports' + team_id + '/' + str(date)
       }
       response.append(data_chunk)
   return response
