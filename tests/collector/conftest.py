import logging
import time
import os
import platform
import pytest

import os
import shutil
import shlex
import socket
import subprocess
from testingframework.collector_package.collector_nightly import NightlyPackage
#from testingframework.collector.osxlocal import LocalCollector
from testingframework.collector_factory.collectorfactory import CollectorFactory
from testingframework.sumo.aws import AWSSumo
from testingframework.connector.base import Connector


LOGGER = logging.getLogger()


def pytest_generate_tests(metafunc):
    for funcargs in getattr(metafunc.function, 'funcarglist', ()):
        if 'testname' in funcargs:
            testname = "%s" % funcargs['testname']
        metafunc.addcall(funcargs=funcargs, id=testname)


def params(funcarglist):
    """
    method used with generated/parameterized tests, can be used to decorate
    your test function with the parameters.  Each dict in your list
    represents on generated test.  The keys in that dict are the parameters
    to be used for that generated test
    """
    def wrapper(function):
        function.funcarglist = funcarglist
        return function
    return wrapper


@pytest.fixture(scope="session")
def remote_sumo(request):
    '''
    Sumo Deployment
    '''
    LOGGER.info("Inside remote sumo deployment fixture")
    sumo_api_url = request.config.option.sumo_api_url \
               if hasattr(request.config.option, 'sumo_api_url') else \
               ''
    remote_sumo = AWSSumo(sumo_api_url)
    return remote_sumo

@pytest.fixture(scope="session")
def local_collector(request):
    '''
    Collector
    '''
    LOGGER.info("Inside local collector fixture")
    collector_url = request.config.option.collector_url \
                    if hasattr(request.config.option, 'collector_url') else \
                    ''
    deployment = request.config.option.deployment \
                    if hasattr(request.config.option, 'deployment') else \
                    ''
    username = request.config.option.username \
               if hasattr(request.config.option, 'username') else \
               'Administrator'
    password = request.config.option.password \
               if hasattr(request.config.option, 'password') else \
               'Testing123@'
    archive_dir = os.path.join(os.environ['TEST_ARTIFACTS'], 'archives')
    if os.path.exists(archive_dir):
        shutil.rmtree(archive_dir)
    os.mkdir(archive_dir)
    #collector = LocalCollector(archive_dir)
    collector = CollectorFactory.getCollector(archive_dir)
    collector.set_deployment(deployment)
    collector.set_credentials_to_use(username, password)
    collector.set_url(collector_url)
    collector.install_from_archive()

    def fin():
        try:
            LOGGER.info("Teardown: uninstall collector.")
            collector.uninstall()
        except Exception, err:
            LOGGER.warn("Failed to tear down collector %s" % err)
    request.addfinalizer(fin)
    return collector

@pytest.fixture(scope="class")
def connector_remotesumo(request, remote_sumo):
    '''
    This is setup & teardown. Creates restconnector,
    cleans connector in finalizer for remote sumo.
    '''
    LOGGER.info("Inside connector_remotesumo.")
    username = request.config.option.username \
               if hasattr(request.config.option, 'username') else \
               'Administrator'
    password = request.config.option.password \
               if hasattr(request.config.option, 'password') else \
               'Testing123@'

    remote_sumo.create_logged_in_connector(contype=Connector.REST,
                                           username=username,
                                           password=password)
    restconn = remote_sumo.connector(Connector.REST, username)
    restconn.config = request.config

    def fin():
        try:
            LOGGER.info("Teardown: removing remote sumo connectors")
            collector_api = "%s%s" % (request.config.option.sumo_api_url, 'collectors')
            collector_api = collector_api.replace('https://', '')
            resp, cont = restconn.make_request("GET", collector_api)
            cont_json = json.loads(cont)
            for eachCollector in cont_json['collectors']:
                if eachCollector['name'] == socket.gethostname() and \
                   eachCollector['alive']:
                    collector_id = eachCollector['id']
                    break
            individual_collector = "%s/%s" % (collector_api, eachCollector['id'])
            resp, cont = restconn.make_request('DELETE', individual_collector)
            verifier.verify_true(resp.status == 200)
            remote_sumo.remove_connector(Connector.REST, username)
        except Exception, err:
            LOGGER.warn("Failed to tear down rest connectors %s" % err)
    request.addfinalizer(fin)
    return restconn
