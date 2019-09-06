"""
    This module is executed in remote subprocesses and helps to
    control a remote testing session and relay back information.
    It assumes that 'py' is importable and does not have dependencies
    on the rest of the xdist code.  This means that the xdist-plugin
    needs not to be installed in remote environments.
"""

import sys
import os
import time

import py
import _pytest.hookspec
import pytest
from execnet.gateway_base import dumps, DumpError


class WorkerInteractor(object):
    def __init__(self, config, channel):
        self.config = config
        self.workerid = config.workerinput.get("workerid", "?")
        self.log = py.log.Producer("worker-%s" % self.workerid)
        if not config.option.debug:
            py.log.setconsumer(self.log._keywords, None)
        self.channel = channel
        config.pluginmanager.register(self)

    def sendevent(self, name, **kwargs):
        self.log("sending", name, kwargs)
        self.channel.send((name, kwargs))

    def pytest_internalerror(self, excrepr):
        for line in str(excrepr).split("\n"):
            self.log("IERROR>", line)

    def pytest_sessionstart(self, session):
        self.session = session
        workerinfo = getinfodict()
        self.sendevent("workerready", workerinfo=workerinfo)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_sessionfinish(self, exitstatus):
        # in pytest 5.0+, exitstatus is an IntEnum object
        self.config.workeroutput["exitstatus"] = int(exitstatus)
        yield
        self.sendevent("workerfinished", workeroutput=self.config.workeroutput)

    def pytest_collection(self, session):
        self.sendevent("collectionstart")

    def pytest_runtestloop(self, session):
        self.log("entering main loop")
        torun = []
        while 1:
            try:
                name, kwargs = self.channel.receive()
            except EOFError:
                return True
            self.log("received command", name, kwargs)
            if name == "runtests":
                torun.extend(kwargs["indices"])
            elif name == "runtests_all":
                torun.extend(range(len(session.items)))
            self.log("items to run:", torun)
            # only run if we have an item and a next item
            while len(torun) >= 2:
                self.run_one_test(torun)
            if name == "shutdown":
                if torun:
                    self.run_one_test(torun)
                break
        return True

    def run_one_test(self, torun):
        items = self.session.items
        self.item_index = torun.pop(0)
        item = items[self.item_index]
        if torun:
            nextitem = items[torun[0]]
        else:
            nextitem = None

        start = time.time()
        self.config.hook.pytest_runtest_protocol(item=item, nextitem=nextitem)
        duration = time.time() - start
        self.sendevent(
            "runtest_protocol_complete", item_index=self.item_index, duration=duration
        )

    def pytest_collection_finish(self, session):
        self.sendevent(
            "collectionfinish",
            topdir=str(session.fspath),
            ids=[item.nodeid for item in session.items],
        )

    def pytest_runtest_logstart(self, nodeid, location):
        self.sendevent("logstart", nodeid=nodeid, location=location)

    # the pytest_runtest_logfinish hook was introduced in pytest 3.4
    if hasattr(_pytest.hookspec, "pytest_runtest_logfinish"):

        def pytest_runtest_logfinish(self, nodeid, location):
            self.sendevent("logfinish", nodeid=nodeid, location=location)

    def pytest_runtest_logreport(self, report):
        data = self.config.hook.pytest_report_to_serializable(
            config=self.config, report=report
        )
        data["item_index"] = self.item_index
        data["worker_id"] = self.workerid
        assert self.session.items[self.item_index].nodeid == report.nodeid
        self.sendevent("testreport", data=data)

    def pytest_collectreport(self, report):
        # send only reports that have not passed to master as optimization (#330)
        if not report.passed:
            data = self.config.hook.pytest_report_to_serializable(
                config=self.config, report=report
            )
            self.sendevent("collectreport", data=data)

    # the pytest_logwarning hook was deprecated since pytest 4.0
    if hasattr(
        _pytest.hookspec, "pytest_logwarning"
    ) and not _pytest.hookspec.pytest_logwarning.pytest_spec.get("warn_on_impl"):

        def pytest_logwarning(self, message, code, nodeid, fslocation):
            self.sendevent(
                "logwarning",
                message=message,
                code=code,
                nodeid=nodeid,
                fslocation=str(fslocation),
            )

    # the pytest_warning_captured hook was introduced in pytest 3.8
    if hasattr(_pytest.hookspec, "pytest_warning_captured"):

        def pytest_warning_captured(self, warning_message, when, item):
            self.sendevent(
                "warning_captured",
                warning_message_data=serialize_warning_message(warning_message),
                when=when,
                # item cannot be serialized and will always be None when used with xdist
                item=None,
            )


def serialize_warning_message(warning_message):
    if isinstance(warning_message.message, Warning):
        message_module = type(warning_message.message).__module__
        message_class_name = type(warning_message.message).__name__
        message_str = str(warning_message.message)
        # check now if we can serialize the warning arguments (#349)
        # if not, we will just use the exception message on the master node
        try:
            dumps(warning_message.message.args)
        except DumpError:
            message_args = None
        else:
            message_args = warning_message.message.args
    else:
        message_str = warning_message.message
        message_module = None
        message_class_name = None
        message_args = None
    if warning_message.category:
        category_module = warning_message.category.__module__
        category_class_name = warning_message.category.__name__
    else:
        category_module = None
        category_class_name = None

    result = {
        "message_str": message_str,
        "message_module": message_module,
        "message_class_name": message_class_name,
        "message_args": message_args,
        "category_module": category_module,
        "category_class_name": category_class_name,
    }
    # access private _WARNING_DETAILS because the attributes vary between Python versions
    for attr_name in warning_message._WARNING_DETAILS:
        if attr_name in ("message", "category"):
            continue
        attr = getattr(warning_message, attr_name)
        # Check if we can serialize the warning detail, marking `None` otherwise
        # Note that we need to define the attr (even as `None`) to allow deserializing
        try:
            dumps(attr)
        except DumpError:
            result[attr_name] = repr(attr)
        else:
            result[attr_name] = attr
    return result


def getinfodict():
    import platform

    return dict(
        version=sys.version,
        version_info=tuple(sys.version_info),
        sysplatform=sys.platform,
        platform=platform.platform(),
        executable=sys.executable,
        cwd=os.getcwd(),
    )


def remote_initconfig(option_dict, args):
    from _pytest.config import Config

    option_dict["plugins"].append("no:terminal")
    config = Config.fromdictargs(option_dict, args)
    config.option.looponfail = False
    config.option.usepdb = False
    config.option.dist = "no"
    config.option.distload = False
    config.option.numprocesses = None
    config.option.maxprocesses = None
    config.args = args
    return config


if __name__ == "__channelexec__":
    channel = channel  # noqa
    workerinput, args, option_dict, change_sys_path = channel.receive()

    if change_sys_path:
        importpath = os.getcwd()
        sys.path.insert(0, importpath)
        os.environ["PYTHONPATH"] = (
            importpath + os.pathsep + os.environ.get("PYTHONPATH", "")
        )

    os.environ["PYTEST_XDIST_WORKER"] = workerinput["workerid"]
    os.environ["PYTEST_XDIST_WORKER_COUNT"] = str(workerinput["workercount"])

    config = remote_initconfig(option_dict, args)
    config._parser.prog = os.path.basename(workerinput["mainargv"][0])
    config.workerinput = workerinput
    config.workeroutput = {}
    # TODO: deprecated name, backward compatibility only. Remove it in future
    config.slaveinput = config.workerinput
    config.slaveoutput = config.workeroutput
    interactor = WorkerInteractor(config, channel)
    config.hook.pytest_cmdline_main(config=config)
