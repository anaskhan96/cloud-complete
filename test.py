import json
import requests
from pprint import pprint
import yaml
import copy
import os
from jinja2 import Environment, FileSystemLoader
from pprint import pprint
import httplib
import sys
from pymongo import MongoClient
import time

TESTS_DIR = 'tests'
TEAMS_FILE = 'teams.json'
REPORTS_DIR = 'reports'
client = MongoClient('mongodb://anask.xyz:27017')
db = client['ccbd-reports']
reports_collection = db['reports']

def get_invalid_methods(case):
    invalid_methods = ['GET', 'POST', 'DELETE']
    invalid_methods.remove(case['method'])

    return invalid_methods

def status_code_is_ok(status_code):
    return status_code == 200 or status_code == 201

def get_pretty_json_str(json_obj):
    return json.dumps(json_obj, indent=4, sort_keys=True)

def load_tests():
    tests = []

    for filename in os.listdir(TESTS_DIR):
        path = os.path.join(TESTS_DIR, filename)

        file = open(path)
        conf = yaml.load_all(file)

        test_title = ''
        test = []

        for doc in conf:
            if 'title' in doc:
                test_title = doc['title']
            else:
                case = {}

                if 'case_title' in doc:
                    case['case_title'] = doc['case_title']
                
                case['route'] = doc['route']
                case['method'] = doc['method']
                case['request'] = json.loads(doc['request'])
                case['expected_code'] = int(doc['code'])

                expected_response = json.loads(doc['response'])
                if expected_response == []:
                    expected_response = {}
                case['expected_response'] = expected_response

                repeat = 1
                if 'repeat' in doc:
                    repeat = doc['repeat']
                case['repeat'] = repeat
                
                invalid_methods = get_invalid_methods(case)
                if 'invalid_methods' in doc:
                    invalid_methods = json.loads(doc['invalid_methods'])
                case['invalid_methods'] = invalid_methods

                skip_invalid_methods_test = False
                if 'skip_invalid_methods_test' in doc:
                    skip_invalid_methods_test = bool(doc['skip_invalid_methods_test'])
                case['skip_invalid_methods_test'] = skip_invalid_methods_test

                if 'request_iter' in doc:
                    case['request_iter'] = doc['request_iter']
                
                if 'route_iter' in doc:
                    case['route_iter'] = bool(doc['route_iter'])
                
                if 'repeat_str' in doc:
                    case['repeat_str'] = doc['repeat_str']

                if 'response_iter' in doc:
                    case['response_iter'] = doc['response_iter']
                    case['response_repeat'] = doc['response_repeat']

                    for i in range(case['response_repeat']):
                        new_elem = copy.deepcopy(expected_response[-1])
                        new_elem[case['response_iter']] -= 1
                        expected_response.append(new_elem)

                    case['expected_response'] = expected_response

                test.append(case)
        
        file.close()

        tests.append({
            'title': test_title,
            'test': test
        })

    return tests

def load_teams():
    file = open(TEAMS_FILE)
    teams = json.load(file)
    file.close()

    return teams

def get_positive_subresult(result_str):
    return ['Positive', result_str]

def get_negative_subresult(expected_str, got_str):
    return ['Negative', expected_str, got_str]

def html_codify(text):
    return '<code>' + text + '</code>'

def status_code_str(code):
    return str(code) + ' ' + httplib.responses[code]

def make_request(uri, method, request):
    if method == 'GET':
        response = requests.get(uri)
    elif method == 'DELETE':
        response = requests.delete(uri)
    elif method == 'POST':
        response = requests.post(uri, json=request)

    return response

def test_case(case, uri):
    method = case['method']
    request = case['request']
    expected_response = case['expected_response']
    expected_code = case['expected_code']

    result = []

    try:
        response = make_request(uri, method, request)
        for _ in range(case['repeat'] - 1):
            if 'request_iter' in case:
                request[case['request_iter']] += 1
            elif 'route_iter' in case:
                parts = uri.split('/')
                parts[-1] = str(int(parts[-1]) + 1)
                uri = '/'.join(parts)
    
            response = make_request(uri, method, request)

        if expected_code == response.status_code:
            result.append(get_positive_subresult(
                'Expected status code returned (' + html_codify(status_code_str(expected_code)) + ')'
            ))
        else:
            result.append(get_negative_subresult(
                'Expected status code: (' + html_codify(status_code_str(expected_code)) + ')',
                'Got status code: (' + html_codify(status_code_str(response.status_code)) + ')'
            ))
        
        if status_code_is_ok(response.status_code):
            if method == 'GET':
                expected_response = get_pretty_json_str(expected_response)
                response = get_pretty_json_str(response.json())

                if expected_response == response:
                    result.append(get_positive_subresult(
                        'Expected response returned: ' + html_codify(expected_response)
                    ))
                else:
                    result.append(get_negative_subresult(
                        'Expected response: ' + html_codify(expected_response),
                        'Got response: ' + html_codify(response)
                    ))
            
            if not case['skip_invalid_methods_test']:
                for invalid_method in case['invalid_methods']:
                    if invalid_method == 'GET':
                        response = requests.get(uri)
                    elif invalid_method == 'DELETE':
                        response = requests.delete(uri)
                    elif invalid_method == 'POST':
                        response = requests.post(uri)
                    
                    if response.status_code == 405:
                        result.append(get_positive_subresult(
                            'Expected response code returned (' + html_codify(status_code_str(response.status_code)) + ') for method ' + html_codify(invalid_method)
                        ))
                    else:
                        result.append(get_negative_subresult(
                            'Expected response code for method ' + html_codify(invalid_method) + ': ' + html_codify(status_code_str(405)),
                            'Got response code: ' + html_codify(status_code_str(response.status_code))
                        ))
            

    except requests.exceptions.RequestException as err:
        result.append(get_negative_subresult(
            'Expected successful connection to server',
            'Got: ' + str(err)
        ))

    return result

def test_invalid_methods(case, uri):
    expected_code = case['expected_code']
    if not status_code_is_ok(expected_code):
        return []

    invalid_methods = case['invalid_methods']
    invalid_methods_allowed = copy.copy(invalid_methods)

    for invalid_method in invalid_methods:
        response = requests.get(uri)
        if response.status_code == 405:
            invalid_methods_allowed.remove(invalid_method)

    return invalid_methods_allowed

def get_uri(public_ip, case):
    return 'http://' + public_ip + case['route']

def run_tests(tests, teams):
    reports = {}

    for (team_id, public_ip) in teams.items():
        report = { 'public_ip': public_ip }

        print('Running tests for team ' + team_id)

        test_results = []

        for t in tests:
            test_title = t['title']
            test = t['test']

            test_result = []
            #pprint(test)

            for case in test:
                uri = get_uri(public_ip, case)
                #print(uri)

                case_result = copy.deepcopy(case)

                case_result['sub_results'] = test_case(case, uri)
                case_result['request'] = get_pretty_json_str(case_result['request'])

                test_result.append(case_result)
                #print(case_result)
            
            #pprint(test_result)
            #print('')

            test_results.append({
                'test_title': test_title,
                'test_result': test_result
            })

        report['test_results'] = test_results
        #print(test_results)

        reports[team_id] = report
        #print(report)
    
    return reports

tests = load_tests()
#pprint(tests)

teams = load_teams()
#pprint(teams)

if len(sys.argv) == 3 and sys.argv[1] == '--team':
    team_id = sys.argv[2]
    if team_id in teams:
        teams = { team_id: teams[team_id] }

#pprint(teams)

reports = run_tests(tests, teams)
#pprint(reports)

print('Done. Check \'reports\' folder')
print('Please wait till the reports are uploaded to the database')

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

    # Insert the report in the database
    report_document = {
        'team_id': team_id,
        'encoded_report': encoded_report,
        'date': round(time.time(), 2)
    }
    reports_collection.insert_one(report_document)
    print('Report for team ' + team_id + ' has been updated in the database')
    