from models.task import TaskTypeEnum, Task
from models.result import TransactionNotCreated, TransactionErrorTypeEnum, StatusEnum

from services.social_info_service import SocialInfoService
from services.ABC.task_handler import TaskHandler, TaskHandlerResult

from handlers.example.pass_quest import ExamplePassQuest
from handlers.example.register import ExampleRegister


class ExampleQuest(TaskHandler):
    def __init__(self, step, logger, client=None, account_info_retriever=None, transport_client=None):
        super().__init__(step, logger, client, account_info_retriever, transport_client)
        self.social_info_service = SocialInfoService(
            self.step.accountId,
            self.logger,
            self.transport_client,
            360,
        )

    async def handle_task(self) -> TaskHandlerResult:
        example_handler = await self.get_type_handler()

        if example_handler:
            result = await example_handler.handle_task()

            if result:
                return TaskHandlerResult(StatusEnum.CREATED)

        raise TransactionNotCreated(
            TransactionErrorTypeEnum.COMPLETE_QUEST_FAILED,
            error_message="Example quest is failed",
            class_name=self.__class__.__name__,
        )

    async def get_type_handler(self) -> TaskHandler:
        if self.step.task.type == TaskTypeEnum.PASS_QUEST:
            return ExamplePassQuest(
                step=self.step,
                logger=self.logger,
                client=self.client,
                account_info_retriever=self.account_info_retriever,
                transport_client=self.transport_client,
                social_info_service=self.social_info_service,
            )

        elif self.step.task.type == TaskTypeEnum.REGISTER:
            return ExampleRegister(
                step=self.step,
                logger=self.logger,
                client=self.client,
                account_info_retriever=self.account_info_retriever,
                transport_client=self.transport_client,
                social_info_service=self.social_info_service,
            )

        raise TransactionNotCreated(
            TransactionErrorTypeEnum.UNSUPPORTED_TASK_TYPE,
            critical=True,
            error_message=f"{self.step.task.type} is not supported",
            class_name=self.__class__.__name__,
        )
