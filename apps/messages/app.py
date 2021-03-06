import psycopg2
from jaeger_client import Config
from flask import Flask, request, session, request, redirect, url_for
from flask import _request_ctx_stack as stack
import os,sys

from jaeger_client import Config
import logging
from jaeger_client import Tracer, ConstSampler
from jaeger_client.reporter import NullReporter
from jaeger_client.codecs import B3Codec
from opentracing.ext import tags
from opentracing.propagation import Format
from opentracing_instrumentation.request_context import get_current_span, span_in_context

app = Flask(__name__)

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

def init_jaeger_tracer():
    config = Config(
        config={ # usually read from some yaml config
        'sampler': {
                'type': 'const',
                'param': 1,
            },
        'local_agent': {
            'reporting_host': 'jaeger-agent.istio-system',
            'reporting_port': '5775',
        },
        'logging': True
    },
    service_name='messages.default',
    validate=True,
    )
    tracer = config.initialize_tracer()

    if tracer is None:
        Config._initialized = False
        tracer = config.initialize_tracer()
    tracer.one_span_per_rpc = True
    tracer.codecs = {Format.HTTP_HEADERS: B3Codec()}
    return tracer

conn = psycopg2.connect(dbname='postgres', user='postgres', 
                        password='postgres', host=os.environ['DB_HOSTNAME'])
conn.autocommit = True

@app.route('/',methods=['post','get'])
def work_message():
    tracer = init_jaeger_tracer()
    request = stack.top.request
    print(dict(request.headers))
    span_ctx = tracer.extract(
                    Format.HTTP_HEADERS,
                    dict(request.headers)
                )
    rpc_tag = {tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER}

    if request.method == 'POST':
        with tracer.start_span('put message',child_of=span_ctx,tags=rpc_tag) as span:
            message = request.get_json(force=True)['message']
            cursor = conn.cursor()
            span.log_kv({'event': f"put message: '{message}' into PG"})
            try:
                cursor.execute(f"INSERT INTO messages (message) VALUES ('{message}')")
                cursor.close()
            except: 
                cursor.close()
                raise "PG put error"
            return 'done', 200
    else: 
        with tracer.start_span('get messages',child_of=span_ctx,tags=rpc_tag) as span:
            cursor = conn.cursor()
            try:
                cursor.execute('select message from messages')
                records = cursor.fetchall()
                cursor.close()
            except:
                cursor.close()
                raise 'PG get error'
            return {'messages': records}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5003, debug=True, threaded=True)