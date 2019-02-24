from flask import Flask, render_template, request, render_template_string, send_from_directory
from flask_basicauth import BasicAuth
from pymongo import MongoClient
from datetime import datetime
import os

client = MongoClient('mongodb://anask.xyz:27017')
db = client["ccbd-reports"]
reports_collection = db["reports"]

app = Flask(__name__)
app.config['BASIC_AUTH_USERNAME'] = 'ccbd-evaluator'
app.config['BASIC_AUTH_PASSWORD'] = 'ccbdevalsecret'
basic_auth = BasicAuth(app)

@app.route('/ccbd')
def hello():
    return "Testing"

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
    return render_template('reports.html', items=items)

@app.route('/ccbd/reports/<team_id>/<date>')
@basic_auth.required
def report(team_id, date):
    report_document = reports_collection.find_one({
        'team_id': team_id,
        'date': float(date)
    })
    encoded_report = report_document['encoded_report']
    return render_template_string(encoded_report)

if __name__ == '__main__':
    app.run(port=8080)