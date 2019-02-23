from flask import Flask

app = Flask(__name__)

@app.route('/ccbd')
def hello():
    return "Testing"

if __name__ == '__main__':
    app.run(port=8080)