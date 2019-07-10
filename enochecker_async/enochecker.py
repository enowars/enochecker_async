import datetime
import logging
import traceback
from typing import Optional, Callable, Any, Dict, List, Union, Type

import jsons
import tornado.ioloop
import tornado.web

from .util import CheckerTaskResult, CheckerTaskType, CheckerTaskMessage, CheckerResultMessage, EnoLogMessage
from .util import OfflineException, BrokenServiceException

class BaseChecker():
    def __init__(self, service_name: str, checker_port: int) -> None:
        self.service_name = service_name
        self.name = service_name + "Checker"
        self.checker_port = checker_port

class ELKFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return jsons.dumps(self.create_message(record))

    def create_message(self, record: logging.LogRecord):
        return EnoLogMessage(record.checker.name if hasattr(record, "checker") else None,
            "infrastructure",
            record.levelname,
            datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            record.checker.name if hasattr(record, "checker") else None,
            record.funcName,
            record.checker_task.flag if hasattr(record, "checker_task") else None,
            record.checker_task.flagIndex if hasattr(record, "checker_task") else None,
            record.checker_task.runId if hasattr(record, "checker_task") else None,
            record.checker_task.round if hasattr(record, "checker_task") else None,
            record.msg,
            record.checker_task.team if hasattr(record, "checker_task") else None,
            record.checker.service_name if hasattr(record, "checker") else None)

class EnoCheckerRequestHandler(tornado.web.RequestHandler):
    def initialize(self, logger: logging.Logger, checker: BaseChecker):
        self.logger = logger
        self.checker = checker

    async def get(self):
        logging.info("GET /")
        self.write('<h1>Welcome to {}Checker</h1>'.format(checker.service_name))
    
    async def post(self):
        checker_task = jsons.loads(self.request.body, CheckerTaskMessage)

        # create LoggerAdapter
        extra = { 'checker_task': checker_task, 'checker': checker }
        scoped_logger = logging.LoggerAdapter(self.logger, extra=extra)
        scoped_logger.info("Received task (id={}, teamid={}, method={}, index={})".format(checker_task.runId, checker_task.teamId, checker_task.method, checker_task.flagIndex))

        # call method
        try:
            if checker_task.method == CheckerTaskType.CHECKER_TASK_TYPE_PUTFLAG:
                await checker.putflag(scoped_logger, checker_task)
            elif checker_task.method == CheckerTaskType.CHECKER_TASK_TYPE_GETFLAG:
                await checker.getflag(scoped_logger, checker_task)
            elif checker_task.method == CheckerTaskType.CHECKER_TASK_TYPE_PUTNOISE:
                await checker.putnoise(scoped_logger, checker_task)
            elif checker_task.method == CheckerTaskType.CHECKER_TASK_TYPE_GETNOISE:
                await checker.getnoise(scoped_logger, checker_task)
            elif checker_task.method == CheckerTaskType.CHECKER_TASK_TYPE_HAVOC:
                await checker.havoc(scoped_logger, checker_task)
            else:
                raise Exception("Unknown rpc method {}".format(checker_task.method))
            scoped_logger.info("Task finished OK (id={}, teamid={}, method={}, index={})".format(checker_task.runId, checker_task.teamId, checker_task.method, checker_task.flagIndex))
            self.write(jsons.dumps(CheckerResultMessage(CheckerTaskResult.CHECKER_TASK_RESULT_OK)))
        except OfflineException as ex:
            stacktrace = ''.join(traceback.format_exception(None, ex, ex.__traceback__))
            scoped_logger.warn("Task finished DOWN: {}".format(stacktrace))
            self.write( jsons.dumps(CheckerResultMessage(CheckerTaskResult.CHECKER_TASK_RESULT_DOWN)))
            return
        except BrokenServiceException as ex:
            stacktrace = ''.join(traceback.format_exception(None, ex, ex.__traceback__))
            scoped_logger.warn("Task finished MUMBLE: {}".format(stacktrace))
            self.write(jsons.dumps(CheckerResultMessage(CheckerTaskResult.CHECKER_TASK_RESULT_MUMBLE)))
            return
        except Exception as ex:
            stacktrace = ''.join(traceback.format_exception(None, ex, ex.__traceback__))
            scoped_logger.error("Task finished INTERNAL_ERROR: {}".format(stacktrace))
            self.write(jsons.dumps(CheckerResultMessage(CheckerTaskResult.CHECKER_TASK_RESULT_INTERNAL_ERROR)))
            return

def create_app(checker: BaseChecker) -> None:
    logger = logging.getLogger(__name__)
    app = tornado.web.Application([
        (r"/", EnoCheckerRequestHandler, dict(logger=logger, checker=checker)),
    ])
    app.listen(checker.checker_port)
    tornado.ioloop.IOLoop.current().start()
