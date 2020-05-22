import sys, os
import logging
from flask_bootstrap import Bootstrap
from flask import Flask, render_template, request, redirect
import requests, json
from flask import _request_ctx_stack as stack

from jaeger_client import Tracer, ConstSampler, Config
from jaeger_client.reporter import NullReporter
from jaeger_client.codecs import B3Codec
from opentracing.ext import tags
from opentracing.propagation import Format
from opentracing_instrumentation.request_context import get_current_span, span_in_context

app = Flask(__name__)
Bootstrap(app)

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
    service_name='frontend.default',
    validate=True,
    )
    tracer = config.initialize_tracer()

    if tracer is None:
        Config._initialized = False
        tracer = config.initialize_tracer()
    tracer.codecs = {Format.HTTP_HEADERS: B3Codec()}
    return tracer

tracer = init_jaeger_tracer()

def getForwardHeaders(request):
    headers = {}
    span_ctx = tracer.extract(
                    Format.HTTP_HEADERS,
                    dict(request.headers)
                )
    # x-b3-*** headers can be populated using the opentracing span
    print(span_ctx)
    carrier = {}
    tracer.inject(
        span_context=span_ctx,
        format=Format.HTTP_HEADERS,
        carrier=carrier)

    headers.update(carrier)
    print('HEADERS:' + str(headers))
    incoming_headers = ['x-request-id', 'x-datadog-trace-id', 'x-datadog-parent-id', 'x-datadog-sampled']

    # Add user-agent to headers manually
    if 'user-agent' in request.headers:
        headers['user-agent'] = request.headers.get('user-agent')

    for ihdr in incoming_headers:
        val = request.headers.get(ihdr)
        if val is not None:
            headers[ihdr] = val
            # print "incoming: "+ihdr+":"+val

    return headers

def get_dollar(request,headers):
    span_ctx = tracer.extract(
                    Format.HTTP_HEADERS,
                    dict(request.headers)
                )
    rpc_tag = {tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER}
    with tracer.start_span('get exchange rate',child_of=span_ctx,tags=rpc_tag) as span:
        dollar = json.loads(requests.get('https://api.exchangeratesapi.io/latest?base=USD&symbols=RUB',headers=headers).text)['rates']['RUB']
    return dollar

def put_message(message,headers):
    res = requests.post(os.environ['FIX_MESSAGE'], json={'message': message},headers=headers)
    print(res.text)

def get_messages(headers):
    res = json.loads(requests.get(os.environ['MESSAGE'],headers=headers).text)['messages']
    if not isinstance(res,list):
        print(res.text)
        return res.text
    return res

def get_count(headers):
    count_info = json.loads(requests.get(os.environ['COUNT'],headers=headers).text)
    return count_info

@app.route('/',methods=['post','get'])
def default():
    return redirect('index')

@app.route('/index',methods=['get','post'])
def index():
    #print(stack.top.request.headers)
    headers = getForwardHeaders(request)
    if request.method == 'POST':
        message = request.form.get('message')
        print(message)
        put_message(message,headers)
        return redirect('index')
    else:
        count_info = get_count(headers)
        dollar_info = get_dollar(request,headers)
        messages = get_messages(headers)
        print(messages)
        return render_template('index.html', count = count_info, dollar=dollar_info,messages=messages)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, threaded=True)