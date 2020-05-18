import psycopg2
from jaeger_client import Config
from flask import Flask, request, session, request, redirect, url_for
from flask import _request_ctx_stack as stack

app = Flask(__name__)
conn = psycopg2.connect(dbname='postgres', user='postgres', 
                        password='postgres', host='localhost')
conn.autocommit = True

@app.route('/',methods=['post','get'])
def work_message():
    if request.method == 'POST':
        message = request.get_json(force=True)['message']
        with conn.cursor() as cursor:
            cursor.execute(f"INSERT INTO messages (message) VALUES ('{message}')")
        return 'done', 200
    else: 
        with conn.cursor as cursor:
            cursor.execute('select * from messages')
            records = cursor.fetchall()
        return {'messages': records}, 200



if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5001, debug=True, threaded=True)