# EnoChecker Async [![Build Status](https://dev.azure.com/ENOFLAG/ENOWARS/_apis/build/status/enochecker_async%20CI?branchName=master)](https://dev.azure.com/ENOFLAG/ENOWARS/_build) ![](https://tokei.rs/b1/github/enowars/enochecker_async)

This is the asynchronous python variant of the ENOWARS checkerlib.

### Implementing an asynchronous checker
Consumers must extend the BaseChecker class:
```python
class DemoChecker(BaseChecker):
    port = 8000

    def __init__(self):
        super(DemoChecker, self).__init__("Demo", 8080, 2, 0, 0) # 2 flags, 0 noises, 0 havocs

    async def putflag(self, logger: LoggerAdapter, task: CheckerTaskMessage, collection: MotorCollection) -> None:
        pass

    async def getflag(self, logger: LoggerAdapter, task: CheckerTaskMessage, collection: MotorCollection) -> None:
        pass

    async def putnoise(self, logger: LoggerAdapter, task: CheckerTaskMessage, collection: MotorCollection) -> None:
        pass

    async def getnoise(self, logger: LoggerAdapter, task: CheckerTaskMessage, collection: MotorCollection) -> None:
        pass

    async def havoc(self, logger: LoggerAdapter, task: CheckerTaskMessage, collection: MotorCollection) -> None:
        pass
```

For a full example, check out the [WASP checker](https://github.com/enowars/service-wasp/blob/master/checker/checker.py).

### Testing your checker

[enochecker_cli](https://github.com/enowars/enochecker_cli) is a nice cli tool that you can use to send tasks to your checker.
