import sys
import logging
from flask import Flask, render_template, request
import requests, json
from flask import _request_ctx_stack as stack
import os, sys

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
    service_name='fix-messages.default',
    validate=True,
    )
    tracer = config.initialize_tracer()

    if tracer is None:
        Config._initialized = False
        tracer = config.initialize_tracer()
    tracer.one_span_per_rpc = True
    tracer.codecs = {Format.HTTP_HEADERS: B3Codec()}
    return tracer



@app.route('/',methods=['post'])
def work_message():
    tracer = init_jaeger_tracer()
    request_top = stack.top.request
    print(dict(request_top.headers))
    headers = {}
    print(f"TYPE top_headers: {type(request_top.headers)}")
    span_ctx = tracer.extract(
                    Format.HTTP_HEADERS,
                    dict(request_top.headers)
                )
    rpc_tag = {tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER}
    
    with tracer.start_span('fix_messages',child_of=span_ctx,tags=rpc_tag) as span:
        carrier = {}
        tracer.inject(
            span_context=span.context,
            format=Format.HTTP_HEADERS,
            carrier=carrier)
        print(carrier)
        print(type(carrier))
        headers.update(carrier)
        print(headers)
        message = request.get_json(force=True)['message']
        message = '\U0001F612' + message.upper()
        res = requests.post(os.environ['MESSAGE'], json={'message': message},headers=headers)
        return res.text, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5002, debug=True, threaded=True)