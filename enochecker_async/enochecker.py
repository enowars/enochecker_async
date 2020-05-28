import datetime
import logging
import traceback
import jsons
import tornado.ioloop
import tornado.web

from typing import Optional, Callable, Any, Dict, List, Union, Type
from motor import MotorCollection, MotorClient
from enochecker_core import CheckerTaskResult, CheckerTaskType, CheckerTaskMessage, CheckerResultMessage, EnoLogMessage
from enochecker_core import OfflineException, BrokenServiceException
from enochecker_core import CheckerInfoMessage

LOGGING_PREFIX = "##ENOLOGMESSAGE "

class BaseChecker():
    name = "BaseChecker"
    def __init__(self, service_name: str, checker_port: int, flags_per_round: int, noises_per_round: int, havocs_per_round: int) -> None:
        self.service_name = service_name
        self.name = service_name + "Checker"
        self.checker_port = checker_port
        self.flags_per_round = flags_per_round
        self.noises_per_round = noises_per_round
        self.havocs_per_round = havocs_per_round
        BaseChecker.name = self.name # Logs outside this scope need the name too!

class ELKFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.msg = record.msg % record.args
        return LOGGING_PREFIX + jsons.dumps(self.create_message(record))

    def create_message(self, record: logging.LogRecord):
        return EnoLogMessage(BaseChecker.name,
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
            record.checker_task.teamId if hasattr(record, "checker_task") else None,
            record.checker_task.team if hasattr(record, "checker_task") else None,
            record.checker_task.serviceId if hasattr(record, "checker_task") else None,
            record.checker.service_name if hasattr(record, "checker") else None,
            record.checker_task.method if hasattr(record, "checker_task") else None)

class EnoCheckerRequestHandler(tornado.web.RequestHandler):
    async def get(self):
        logging.info('GET /')
        checker = self.settings['checker']
        self.write(jsons.dumps(CheckerInfoMessage(checker.service_name, checker.flags_per_round,
            checker.noises_per_round, checker.havocs_per_round)))
    
    async def post(self):
        checker = self.settings['checker']
        scoped_logger = self.settings['logger']
        try:
            collection: MotorCollection = self.settings['mongo']['checker_storage']
            checker_task = jsons.loads(self.request.body, CheckerTaskMessage)

            # create LoggerAdapter
            extra = { 'checker_task': checker_task, 'checker': checker }
            scoped_logger = logging.LoggerAdapter(scoped_logger, extra=extra)
            scoped_logger.info("Received task (id={}, teamid={}, method={}, index={})".format(checker_task.runId, checker_task.teamId, checker_task.method, checker_task.flagIndex))

            # call method
            if checker_task.method == CheckerTaskType.CHECKER_TASK_TYPE_PUTFLAG.value:
                await checker.putflag(scoped_logger, checker_task, collection)
            elif checker_task.method == CheckerTaskType.CHECKER_TASK_TYPE_GETFLAG.value:
                await checker.getflag(scoped_logger, checker_task, collection)
            elif checker_task.method == CheckerTaskType.CHECKER_TASK_TYPE_PUTNOISE.value:
                await checker.putnoise(scoped_logger, checker_task, collection)
            elif checker_task.method == CheckerTaskType.CHECKER_TASK_TYPE_GETNOISE.value:
                await checker.getnoise(scoped_logger, checker_task, collection)
            elif checker_task.method == CheckerTaskType.CHECKER_TASK_TYPE_HAVOC.value:
                await checker.havoc(scoped_logger, checker_task, collection)
            else:
                raise Exception("Unknown rpc method {}".format(checker_task.method))
            scoped_logger.info("Task finished OK (id={}, teamid={}, method={}, index={})".format(checker_task.runId, checker_task.teamId, checker_task.method, checker_task.flagIndex))
            self.write(jsons.dumps(CheckerResultMessage(CheckerTaskResult.CHECKER_TASK_RESULT_OK.value)))
        except OfflineException as ex:
            stacktrace = ''.join(traceback.format_exception(None, ex, ex.__traceback__))
            scoped_logger.warn("Task finished DOWN: {}".format(stacktrace))
            self.write(jsons.dumps(CheckerResultMessage(CheckerTaskResult.CHECKER_TASK_RESULT_DOWN.value)))
            return
        except BrokenServiceException as ex:
            stacktrace = ''.join(traceback.format_exception(None, ex, ex.__traceback__))
            scoped_logger.warn("Task finished MUMBLE: {}".format(stacktrace))
            self.write(jsons.dumps(CheckerResultMessage(CheckerTaskResult.CHECKER_TASK_RESULT_MUMBLE.value)))
            return
        except Exception as ex:
            stacktrace = ''.join(traceback.format_exception(None, ex, ex.__traceback__))
            scoped_logger.error("Task finished INTERNAL_ERROR: {}".format(stacktrace))
            self.write(jsons.dumps(CheckerResultMessage(CheckerTaskResult.CHECKER_TASK_RESULT_INTERNAL_ERROR.value)))
            return

def create_app(checker: BaseChecker, mongo_url: str = "mongodb://mongodb:27017") -> None:
    logger = logging.getLogger(__name__)
    mongo = MotorClient(mongo_url)[checker.name]
    app = tornado.web.Application([
        (r"/", EnoCheckerRequestHandler),
        (r"/service", EnoCheckerRequestHandler)
    ], logger=logger, checker=checker, mongo=mongo)
    app.listen(checker.checker_port)
    tornado.ioloop.IOLoop.current().start()
