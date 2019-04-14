import paramiko
import sys, os
import json
from jinja2 import Environment, FileSystemLoader
import time
import requests

TEAMS_FILE = 'teams.json'
REPORTS_DIR = 'reports'

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
      report_stdout=''
      report_stderr=''

      selfie_ip = 'http://' + team_data['selfieless_ip']
      acts_ip = 'http://' + team_data['acts_ip']
      acts_username = team_data['acts_username']
      acts_private_key = team_data['acts_private_key']
      acts_key = paramiko.RSAKey.from_private_key_file(acts_private_key)

      report['selfie_ip'] = selfie_ip
      report['acts_ip'] = acts_ip
      report['acts_username'] = acts_username

      requests.post(selfie_ip + '/api/v1/users', 
         json={"username":"xyz","password":"3d725109c7e7c0bfb9d709836735b56d943d263f"})

      stdout, stderr = execute_remotely(acts_ip.replace('http://',''), acts_username, acts_key, """
sudo pkill tcpflow

no_of_containers=$(sudo docker ps | grep acts | wc -l)
if (( $no_of_containers == 0 )); then
   echo "No acts containers running" >&2
   exit
fi
if (( $no_of_containers != 1 )); then
   echo "More than 1 acts containers running" >&2
   exit
fi

output=$(sudo docker ps | grep "acts")
OG_ACTS_CID=$(echo $output | awk '{ print $1 }')
echo "One Acts container running with ID $OG_ACTS_CID"

output=$(sudo docker port $OG_ACTS_CID | grep "/tcp -> 0\.0\.0\.0:8000")
len=${#output}
if (( $len > 1 )); then
   echo "Acts container $OG_ACTS_CID is listening on port 8000"
else
   echo "Acts container $OG_ACTS_CID isn't listening on port 8000" >&2
   exit
fi

status_code=$(curl -o /dev/null -s -w "%{http_code}" localhost:8000/api/v1/_health)
if (( $status_code != 200 )); then
   echo "Acts container $OG_ACTS_CID not healthy" >&2
   exit
else
   echo "Acts container $OG_ACTS_CID is healthy"
fi

sudo apt install -y tcpflow > /dev/null 2> /dev/null

for i in {1..20}; do
   status_code=$(curl -o /dev/null -s -w "%{http_code}" localhost/api/v1/categories)
   if (( $status_code > 299 )); then
      echo "Unable to make 20 successful API requests to orchestrator" >&2
      exit
   fi
done
echo "20 successful API requests made to orchestrator"

echo "Script slept for 2 minutes"
sleep 141

no_of_containers=$(sudo docker ps | grep acts | wc -l)
if (( $no_of_containers != 2 )); then
   echo "Expected 2 acts containers to be running. Found ${no_of_containers}" >&2
   exit
fi

output=$(sudo docker ps | grep "acts" | head -1)
SEC_ACTS_CID=$(echo $output | awk '{ print $1 }')
echo "Second Acts container now running with ID $SEC_ACTS_CID"

output=$(sudo docker port $SEC_ACTS_CID | grep "/tcp -> 0\.0\.0\.0:8001")
len=${#output}
if (( $len > 1 )); then
   echo "Acts container $SEC_ACTS_CID is listening on port 8001"
else
   echo "Acts container $SEC_ACTS_CID isn't listening on port 8001" >&2
   exit
fi

rm -f logs8000
rm -f logs8001
touch logs8000
touch logs8001
sudo timeout 100 tcpflow -p -c -i lo port 8000 >> logs8000 2> /dev/null &
sudo timeout 100 tcpflow -p -c -i lo port 8001 >> logs8001 2> /dev/null &
sleep 5

for i in {1..6}; do
   status_code=$(curl -o /dev/null -s -w "%{http_code}" localhost/api/v1/categories)
   if (( $status_code > 299 )); then
      echo "Unable to make 6 successful API requests to orchestrator" >&2
      exit
   fi
done
echo "6 successful API requests made to orchestrator"

sleep 5

req_count_8000=$(grep /api/v1/categories logs8000 | wc -l)
req_count_8001=$(grep /api/v1/categories logs8001 | wc -l)

if (( $req_count_8000 == 3 )) && (( $req_count_8001 == 3)); then
   echo "API requests evenly distributed b/w 2 Acts containers in round-robin manner"
else
   echo "API requests were NOT evenly distributed b/w 2 Acts containers (round-robin manner)" >&2
   exit
fi

status_code=$(curl --request POST -o /dev/null -s -w "%{http_code}" localhost:8000/api/v1/_crash)
if (( $status_code != 200 )); then
   echo "Unable to crash container ${OG_ACTS_CID} with /api/v1/_crash" >&2
   exit
fi 
echo "Successfully crashed container ${OG_ACTS_CID} with /api/v1/_crash"

#echo "Sleeping for 20 seconds"
sleep 20

no_of_containers=$(sudo docker ps | grep acts | wc -l)
if (( $no_of_containers != 2 )); then
   echo "Expected 2 Acts containers to be running. Found ${no_of_containers}" >&2
   exit
fi

output=$(sudo docker ps | grep "acts" | head -1)
OG_REPLACED_ACTS_CID=$(echo $output | awk '{ print $1 }')
echo "Replacement Acts container running with ID $OG_REPLACED_ACTS_CID"

output=$(sudo docker port $OG_REPLACED_ACTS_CID | grep "/tcp -> 0\.0\.0\.0:8000")
len=${#output}
if (( $len > 1 )); then
   echo "Replacement Acts container $OG_REPLACED_ACTS_CID is listening on port 8000"
else
   echo "Replacement Acts container $OG_REPLACED_ACTS_CID isn't listening on port 8000" >&2
   exit
fi

status_code=$(curl -o /dev/null -s -w "%{http_code}" localhost:8000/api/v1/_health)
if (( $status_code != 200 )); then
   echo "Replacement Acts container $OG_REPLACED_ACTS_CID not healthy" >&2
   exit
else
   echo "Replacement Acts container $OG_REPLACED_ACTS_CID is healthy"
fi

echo "Script slept for 2 minutes"
sleep 120

no_of_containers=$(sudo docker ps | grep "acts" | wc -l)
if (( $no_of_containers != 1 )); then
   echo "Orchestrator didn't scale down. Expected 1 Acts container to be running. Found ${no_of_containers}" >&2
   exit
fi

output=$(sudo docker ps | grep "acts" | head -1)
LAST_ACTS_CID=$(echo $output | awk '{ print $1 }')
echo "Orchestrator successfully scaled down containers. Only 1 Acts container running with ID $LAST_ACTS_CID"
""")
      report_stdout += stdout
      report_stderr += stderr

      requests.delete(selfie_ip + '/api/v1/users/xyz')
      
      report['stdout'] = filter(lambda l: l, report_stdout.split('\n'))
      report['stderr'] = filter(lambda l: l, report_stderr.split('\n'))

      reports[team_id] = report
   
   return reports 

def load_teams():
    file = open(TEAMS_FILE)
    teams = json.load(file)
    file.close()

    return teams

teams = load_teams()

if len(sys.argv) == 3 and sys.argv[1] == '--team':
    team_id = sys.argv[2]
    if team_id in teams:
        teams = { team_id: teams[team_id] }

reports = run_tests(teams)

print('Done. Check \'reports\' folder')

# -----------------------------------------------------------------------

fs_loader = FileSystemLoader('.')
env = Environment(loader = fs_loader)

template = env.get_template('template.html')

for team_id in reports.keys():
    report = reports[team_id]
    html_report = template.render(team_id=team_id, report=report)
    encoded_report = html_report.encode("UTF-8")

    filename = team_id + '.html'
    path = os.path.join(REPORTS_DIR, filename)

    file = open(path, 'w') 
    file.write(encoded_report)
    file.close()
   