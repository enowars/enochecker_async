import datetime
import logging
import traceback
from typing import Optional

import jsons
import tornado.ioloop
import tornado.web
from enochecker_core import (
    BrokenServiceException,
    CheckerInfoMessage,
    CheckerMethod,
    CheckerResultMessage,
    CheckerTaskMessage,
    CheckerTaskResult,
    EnoLogMessage,
    OfflineException,
)
from motor import MotorClient, MotorCollection

LOGGING_PREFIX = "##ENOLOGMESSAGE "


class BaseChecker:
    name = "BaseChecker"

    def __init__(
        self, service_name: str, checker_port: int, flags_per_round: int, noises_per_round: int, havocs_per_round: int
    ) -> None:
        self.service_name = service_name
        self.name = service_name + "Checker"
        self.checker_port = checker_port
        self.flags_per_round = flags_per_round
        self.noises_per_round = noises_per_round
        self.havocs_per_round = havocs_per_round
        BaseChecker.name = self.name  # Logs outside this scope need the name too!


class ELKFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if record.args is not None:
            record.msg = record.msg % record.args

        return LOGGING_PREFIX + jsons.dumps(
            self.create_message(record), key_transformer=jsons.KEY_TRANSFORMER_CAMELCASE
        )

    def to_level(self, levelname: str) -> int:
        if levelname == "CRITICAL":
            return 4
        if levelname == "ERROR":
            return 3
        if levelname == "WARNING":
            return 2
        if levelname == "INFO":
            return 1
        if levelname == "DEBUG":
            return 0
        return 0

    def create_message(self, record: logging.LogRecord):
        checker_task: Optional[CheckerTaskMessage] = getattr(record, "checker_task", None)
        checker: Optional[BaseChecker] = getattr(record, "checker", None)
        return EnoLogMessage(
            tool=BaseChecker.name,
            type="infrastructure",
            severity=record.levelname,
            severity_level=self.to_level(record.levelname),
            timestamp=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            message=record.msg,
            module=record.module,
            function=record.funcName,
            service_name=checker.service_name if checker else None,
            task_id=checker_task.task_id if checker_task else None,
            method=checker_task.method.value if checker_task else None,
            team_id=checker_task.team_id if checker_task else None,
            team_name=checker_task.team_name if checker_task else None,
            current_round_id=checker_task.current_round_id if checker_task else None,
            related_round_id=checker_task.related_round_id if checker_task else None,
            flag=checker_task.flag if checker_task else None,
            variant_id=checker_task.variant_id if checker_task else None,
            task_chain_id=checker_task.task_chain_id if checker_task else None,
        )


class EnoCheckerRequestHandler(tornado.web.RequestHandler):
    async def get(self):
        logging.info("GET /")
        checker = self.settings["checker"]
        self.write(
            jsons.dumps(
                CheckerInfoMessage(
                    service_name=checker.service_name,
                    flag_variants=checker.flags_per_round,
                    noise_variants=checker.noises_per_round,
                    havoc_variants=checker.havocs_per_round,
                ),
                key_transformer=jsons.KEY_TRANSFORMER_CAMELCASE,
            )
        )

    async def post(self):
        checker = self.settings["checker"]
        scoped_logger = self.settings["logger"]
        try:
            collection: MotorCollection = self.settings["mongo"]["checker_storage"]
            checker_task = jsons.loads(
                self.request.body, CheckerTaskMessage, key_transformer=jsons.KEY_TRANSFORMER_SNAKECASE, strict=True
            )

            # create LoggerAdapter
            extra = {"checker_task": checker_task, "checker": checker}
            scoped_logger = logging.LoggerAdapter(scoped_logger, extra=extra)
            scoped_logger.info(
                "Received task (id={}, teamid={}, method={}, index={})".format(
                    checker_task.run_id, checker_task.team_id, checker_task.method, checker_task.flag_index
                )
            )

            # call method
            if checker_task.method == CheckerMethod.PUTFLAG:
                await checker.putflag(scoped_logger, checker_task, collection)
            elif checker_task.method == CheckerMethod.GETFLAG:
                await checker.getflag(scoped_logger, checker_task, collection)
            elif checker_task.method == CheckerMethod.PUTNOISE:
                await checker.putnoise(scoped_logger, checker_task, collection)
            elif checker_task.method == CheckerMethod.GETNOISE:
                await checker.getnoise(scoped_logger, checker_task, collection)
            elif checker_task.method == CheckerMethod.HAVOC:
                await checker.havoc(scoped_logger, checker_task, collection)
            else:
                raise Exception("Unknown rpc method {}".format(checker_task.method))
            scoped_logger.info(
                "Task finished OK (id={}, teamid={}, method={}, index={})".format(
                    checker_task.run_id, checker_task.team_id, checker_task.method, checker_task.flag_index
                )
            )
            self.write(
                jsons.dumps(
                    CheckerResultMessage(result=CheckerTaskResult.OK),
                    use_enum_name=False,
                    key_transformer=jsons.KEY_TRANSFORMER_CAMELCASE,
                )
            )
        except OfflineException as ex:
            ex_str = str(ex)
            stacktrace = "".join(traceback.format_exception(None, ex, ex.__traceback__))
            scoped_logger.warn(f"Task finished DOWN: {stacktrace}".replace("%", "%%"))
            self.write(
                jsons.dumps(
                    CheckerResultMessage(result=CheckerTaskResult.DOWN, message=ex_str if ex_str else None),
                    use_enum_name=False,
                    key_transformer=jsons.KEY_TRANSFORMER_CAMELCASE,
                )
            )
        except BrokenServiceException as ex:
            ex_str = str(ex)
            stacktrace = "".join(traceback.format_exception(None, ex, ex.__traceback__))
            scoped_logger.warn(f"Task finished MUMBLE: {stacktrace}".replace("%", "%%"))
            self.write(
                jsons.dumps(
                    CheckerResultMessage(result=CheckerTaskResult.MUMBLE, message=ex_str if ex_str else None),
                    use_enum_name=False,
                    key_transformer=jsons.KEY_TRANSFORMER_CAMELCASE,
                )
            )
        except Exception as ex:
            stacktrace = "".join(traceback.format_exception(None, ex, ex.__traceback__))
            scoped_logger.error(f"Task finished INTERNAL_ERROR: {stacktrace}".replace("%", "%%"))
            self.write(
                jsons.dumps(
                    CheckerResultMessage(result=CheckerTaskResult.INTERNAL_ERROR, message=stacktrace),
                    use_enum_name=False,
                    key_transformer=jsons.KEY_TRANSFORMER_CAMELCASE,
                )
            )


def create_app(checker: BaseChecker, mongo_url: str = "mongodb://mongodb:27017") -> None:
    logger = logging.getLogger(__name__)
    mongo = MotorClient(mongo_url)[checker.name]
    app = tornado.web.Application(
        [(r"/", EnoCheckerRequestHandler), (r"/service", EnoCheckerRequestHandler)],
        logger=logger,
        checker=checker,
        mongo=mongo,
    )
    app.listen(checker.checker_port)
    tornado.ioloop.IOLoop.current().start()
