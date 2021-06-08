from flask import Flask, send_file, request, Response
from prometheus_client import start_http_server, Counter, generate_latest, Gauge
import docker
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)

CONTENT_TYPE_LATEST = str('text/plain; version=0.0.4; charset=utf-8')
MBFACTOR = float(1 << 20)

memory_gauge = Gauge(
    'memory_usage_in_mb_docker',
    'Amount of memory in megabytes currently in use by this container.',
    ['name']
)

client = docker.from_env(version='1.23')

@app.route('/metrics', methods=['GET'])
def get_data():
    for container in client.containers.list():
        stats = container.stats(stream = False)
        memory_gauge.labels(container.name).set(int(stats.get('memory_stats').get('usage')) / MBFACTOR)
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
