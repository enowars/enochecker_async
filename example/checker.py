import time
import asyncio
import logging
import sys
import aiohttp

from enochecker_async import BaseChecker, BrokenServiceException, create_app, OfflineException, ELKFormatter, CheckerTaskMessage
from logging import LoggerAdapter
from motor import MotorCollection

class TestChecker(BaseChecker):
    port = 9012

    def __init__(self):
        super(TestChecker, self).__init__("TestService", 8080)

    async def test(self, logger: LoggerAdapter, collection: MotorCollection):
        document = { 'key': 'value'}
        result = await collection.insert_one(document)
        logger.info('result %s' % repr(result.inserted_id))

    async def putflag(self, logger: LoggerAdapter, task: CheckerTaskMessage, collection: MotorCollection) -> None:
        await self.test(logger, collection)
        
    async def getflag(self, logger: LoggerAdapter, task: CheckerTaskMessage, collection: MotorCollection) -> None:
        await self.test(logger, collection)
        
    async def putnoise(self, logger: LoggerAdapter, task: CheckerTaskMessage, collection: MotorCollection) -> None:
        await self.test(logger, collection)

    async def getnoise(self, logger: LoggerAdapter, task: CheckerTaskMessage, collection: MotorCollection) -> None:
        await self.test(logger, collection)

    async def havoc(self, logger: LoggerAdapter, task: CheckerTaskMessage, collection: MotorCollection) -> None:
        pass

    async def exploit(self, logger: LoggerAdapter, task: CheckerTaskMessage, collection: MotorCollection) -> None:
        pass


logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
#handler.setFormatter(ELKFormatter("%(message)s")) ELK-ready output
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

app = create_app(TestChecker(), "mongodb://127.0.0.1:27017")
#app = create_app(TestChecker()) mongodb://mongodb:27017