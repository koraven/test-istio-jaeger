import sys
import logging
from flask_bootstrap import Bootstrap
from flask import Flask, render_template, request, redirect
import requests, json
from flask import _request_ctx_stack as stack

app = Flask(__name__)
Bootstrap(app)

def get_dollar():
    dollar = json.loads(requests.get('https://api.exchangeratesapi.io/latest?base=USD&symbols=RUB').text)['rates']['RUB']
    return dollar

def put_message(message):
    res = requests.post('http://127.0.0.1:5001', json={'message': message})
    print(res.text)

def get_messages():
    res = json.loads(requests.get('http://127.0.0.1:5001').text)['messages']
    return res

def get_count():
    count_info = json.loads(requests.get('http://127.0.0.1:5001').text)
    return count_info

@app.route('/',methods=['post','get'])
def default():
    return redirect('index')

@app.route('/index',methods=['get','post'])
def index():
    #print(stack.top.request.headers)
    if request.method == 'POST':
        message = request.form.get('message')
        print(message)
        put_message(message)
        return redirect('index')
    else:
        #count_info = get_count()
        count_info = 1
        dollar_info = get_dollar()
        messages = get_messages()
        print(messages)
        return render_template('index.html', count = count_info, dollar=dollar_info)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, threaded=True)