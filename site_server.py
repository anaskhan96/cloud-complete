from flask import Flask, render_template, request, render_template_string, send_from_directory, jsonify, Response
from werkzeug import secure_filename
from flask_basicauth import BasicAuth
from pymongo import MongoClient
from datetime import datetime
from test import generate
from container_test import container_generate
from container_test import student_generate
from werkzeug.utils import secure_filename
import os

client = MongoClient('mongodb://anask.xyz:27017')
db = client["ccbd-reports"]
reports_collection = db["reports"]
container_reports_collection = db["container_reports"]

app = Flask(__name__)
app.config['BASIC_AUTH_USERNAME'] = 'ccbd-evaluator'
app.config['BASIC_AUTH_PASSWORD'] = 'ccbdevalsecret'
basic_auth = BasicAuth(app)

@app.route('/ccbd', methods=['GET'])
@basic_auth.required
def home():
    return render_template('home.html')

@app.route('/ccbd/generate', methods=['POST'])
@basic_auth.required
def teamsupload():
    file = request.files['teams']
    try:
        res = generate(file.read())
        return jsonify({'success':True, 'data': res})
        #return Response(generate(file.read()), mimetype='application/json')
    except:
        return jsonify({'success':False})

@app.route('/ccbd/containerGenerate', methods=['POST'])
@basic_auth.required
def container_teamsupload():
    team_file = request.files['containerTeams']
    private_key_files = request.files.getlist('privateKeys[]')
    for private_key_file in private_key_files:
        private_key_file.save(secure_filename(private_key_file.filename))
    response = {}
    try:
        res = container_generate(team_file.read())
        response['success'] = True
        response['data'] = res
    except:
        response['success'] = False
    
    for private_key_file in private_key_files:
        os.remove(secure_filename(private_key_file.filename))
    
    return jsonify(response)

@app.route('/ccbd/reports', methods=['GET'])
@basic_auth.required
def all_reports():
    report_documents_cursor = reports_collection.find({})
    items = []
    for report in report_documents_cursor:
        items.append({
            'team': report['team_id'],
            'link': request.path + '/' + report['team_id'] + '/' + str(report['date']),
            'date': datetime.fromtimestamp(report['date']).strftime('%Y-%m-%d %H:%M:%S')
        })
    return render_template('reports.html', items=items, test="rest")

@app.route('/ccbd/containerReports', methods=['GET'])
@basic_auth.required
def all_container_reports():
    report_documents_cursor = container_reports_collection.find({})
    items = []
    for report in report_documents_cursor:
        items.append({
            'team': report['team_id'],
            'link': request.path + '/' + report['team_id'] + '/' + str(report['date']),
            'date': datetime.fromtimestamp(report['date']).strftime('%Y-%m-%d %H:%M:%S')
        })
    return render_template('reports.html', items=items, test="container")

@app.route('/ccbd/reports/<team_id>', methods=['GET'])
@app.route('/ccbd/reports/<team_id>/<date>', methods=['GET'])
@basic_auth.required
def report(team_id, date=None):
    if not date:
        report_documents_cursor = reports_collection.find({
            'team_id': team_id
        })
        items = []
        for report in report_documents_cursor:
            items.append({
                'team': report['team_id'],
                'link': request.path + '/' + report['team_id'] + '/' + str(report['date']),
                'date': datetime.fromtimestamp(report['date']).strftime('%Y-%m-%d %H:%M:%S')
            })
        return render_template('reports.html', items=items, test="rest")

    report_document = reports_collection.find_one({
        'team_id': team_id,
        'date': float(date)
    })
    encoded_report = report_document['encoded_report']
    return render_template_string(encoded_report)

@app.route('/ccbd/containerReports/<team_id>', methods=['GET'])
@app.route('/ccbd/containerReports/<team_id>/<date>', methods=['GET'])
@basic_auth.required
def container_report(team_id, date=None):
    if not date:
        report_documents_cursor = container_reports_collection.find({
            'team_id': team_id
        })
        items = []
        for report in report_documents_cursor:
            items.append({
                'team': report['team_id'],
                'link': request.path + '/' + report['team_id'] + '/' + str(report['date']),
                'date': datetime.fromtimestamp(report['date']).strftime('%Y-%m-%d %H:%M:%S')
            })
        return render_template('reports.html', items=items, test="container")
    
    report_document = container_reports_collection.find_one({
        'team_id': team_id,
        'date': float(date)
    })
    encoded_report = report_document['encoded_report']
    return render_template_string(encoded_report)

@app.route('/ccbd/studentViewing', methods=['GET'])
def student_view():
    return render_template('studentView.html')

@app.route('/ccbd/studentViewing/<ip>/<username>', methods=['POST'])
def student_generate_report(ip, username):
    private_key_file = request.files['privateKey']
    private_key_file.save(secure_filename(private_key_file.filename))
    response = {}
    try:
        res = student_generate(ip, username, secure_filename(private_key_file.filename))
        response['success'] = True
        response['data'] = res
    except:
        response['success'] = False
    
    os.remove(secure_filename(private_key_file.filename))
    return jsonify(response)

if __name__ == '__main__':
    app.run(port=8080)