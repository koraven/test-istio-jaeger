from app import app
import time
import redis
import socket
import os, sys
from jaeger_client import Config
import logging
from jaeger_client import Tracer, ConstSampler
from jaeger_client.reporter import NullReporter
from jaeger_client.codecs import B3Codec
from opentracing.ext import tags
from opentracing.propagation import Format
from opentracing_instrumentation.request_context import get_current_span, span_in_context
from flask import Flask, request, session, request, redirect, url_for
from flask import _request_ctx_stack as stack

redis_addr = os.environ['REDIS_ADDR']

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

#tracer = Tracer(
#    one_span_per_rpc=True,
#    service_name='count',
#    reporter=NullReporter(),
#    sampler=ConstSampler(decision=True),
#    extra_codecs={Format.HTTP_HEADERS: B3Codec()}
#)

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
    service_name='count.default',
    validate=True,
    )
    tracer = config.initialize_tracer()

    if tracer is None:
        Config._initialized = False
        tracer = config.initialize_tracer()
    tracer.one_span_per_rpc = True
    tracer.codecs = {Format.HTTP_HEADERS: B3Codec()}
    return tracer
#tracer = init_jaeger_tracer()


#cache = redis.StrictRedis(host=redis_addr, port=6379,password='5E5zTXj1bp')
cache = redis.StrictRedis(host=redis_addr, port=6379,password='sOmE_sEcUrE_pAsS')
def get_hit_count():
    retries = 5
    while True:
        try:

            return cache.incr('hits')
        except redis.exceptions.ConnectionError as exc:
            if retries == 0:
                raise exc
            retries -= 1
            time.sleep(0.1)

@app.route('/')
@app.route('/index')
def index():
    tracer = init_jaeger_tracer()
    request = stack.top.request
    print(request)
    print('\n')
    print(dict(request.headers))
    span_ctx = tracer.extract(
                    Format.HTTP_HEADERS,
                    dict(request.headers)
                )
    rpc_tag = {tags.SPAN_KIND: tags.SPAN_KIND_RPC_SERVER}

    #header = request.headers.get('x-request-id')

    with tracer.start_span('index',child_of=span_ctx,tags=rpc_tag) as span:
        span.log_kv({'event': 'got request to /index'})
        #span.set_tag('guid:x-request-id', header)
        with tracer.start_span('Redis increment', child_of=span,tags=rpc_tag) as child_span:
            #child_span.set_tag('guid:x-request-id', header)
            count = get_hit_count()
        if count > 5:
            cache.set('hits',0)
            exit(1)
        else:
            return {'counter': count, 'hostname': socket.gethostname()}
    #tracer.close()
