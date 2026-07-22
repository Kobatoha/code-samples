import json
import time

from models.task import TaskTypeEnum, Task
from models.result import TransactionNotCreated, TransactionErrorTypeEnum, StatusEnum

from services.ABC.task_handler import TaskHandler, TaskHandlerResult
from services.common_utils import CommonUtils

from handlers.social.social import SocialHandler

from utils.headers import get_default_headers
from utils.utils import deep_get_safe, sign_message, get_query_param

SUPPORTED_TASKS = ["Connect Social", "Follow Channel", "Build Node"]


class SocialQuestHandler(TaskHandler):

    async def handle_task(self):
        if not self.step.task.type == TaskTypeEnum.PASS_QUEST:
            raise TransactionNotCreated(
                TransactionErrorTypeEnum.UNSUPPORTED_TASK_TYPE,
                critical=True,
                error_message=f"Task is not supported: {self.step.task.type.value} is not a valid task type. "
                f"Expected {TaskTypeEnum.PASS_QUEST.value}",
                class_name=self.__class__.__name__,
            )
        if not self.step.task.extra:
            raise TransactionNotCreated(
                TransactionErrorTypeEnum.NO_INFO,
                critical=True,
                error_message="Extra field is empty",
                class_name=self.__class__.__name__,
            )

        access_token = await self._connect_wallet()

        headers = await self.get_headers()
        headers.update({"Authorization": access_token})
        invite_code = get_query_param(self.step.task.extra, "invite_code")
        if invite_code:
            SUPPORTED_TASKS.append("Bind Referral Code")

        tasks = await self.get_tasks(headers)
        completed_tasks = []

        for task in tasks:
            # ищем нужное задание по названию
            if task.get("name") not in SUPPORTED_TASKS:
                continue

            # если задание уже выполнено
            if task.get("is_completed"):
                self.logger.log(f"Task already completed: {task.get("name")}, received {task.get("points")} points")
                completed_tasks.append(task.get("id"))
                continue

            result = await self.example_type_handler(task, headers)
            if result:

                message = await self.verify_task(headers, task.get("id"))

                if message == "OK" or message == "Task already completed":
                    completed_tasks.append(task.get("id"))

                else:
                    raise TransactionNotCreated(
                        TransactionErrorTypeEnum.NO_SOCIALS,
                        error_message=f"Verify failed: {message}",
                        class_name=self.__class__.__name__,
                    )

        if len(completed_tasks) == len(SUPPORTED_TASKS):
            self.logger.log("All tasks completed.")
            return TaskHandlerResult(StatusEnum.CREATED)

        raise TransactionNotCreated(
            TransactionErrorTypeEnum.COMPLETE_QUEST_FAILED,
            error_message="example quest is failed.",
            class_name=self.__class__.__name__,
        )

    async def _get_msg_and_signature(self) -> tuple[dict[str, str | int], str]:
        wallet_address = await self.client.info_retriever.address()
        timestamp = int(time.time())
        msg = {"wallet_address": wallet_address, "timestamp": timestamp}
        msg_str = json.dumps(msg, separators=(',', ':'))
        pkey = await self.client.info_retriever.pkey()

        return msg, await sign_message(msg_str, pkey)

    async def get_headers(self) -> dict:
        user_agent = await self.account_info_retriever.ua()
        headers = get_default_headers(user_agent)
        return headers

    async def _connect_wallet(self) -> str:
        msg, signature = await self._get_msg_and_signature()

        body = {"signature": signature, "message": msg}

        response = await self.transport_client.post("https://api.example.com/api/v1/users/connect/", json=body)
        response.raise_for_status("example: Connect request failed.")

        return response.json.get("data", {}).get("access_token")

    async def get_tasks(self, headers: dict) -> dict:
        response = await self.transport_client.get("https://api.example.com/api/v1/reward/tasks/", headers)
        response.raise_for_status("reward/tasks request failed.")

        return deep_get_safe(response.json, ["data", "objects"])

    async def verify_task(self, headers: dict, task_id: int) -> str:
        url = "https://api.example.com/api/v1/reward/claim-task-completion/"
        body = {"task_id": task_id}
        response = await self.transport_client.post(url, headers, body)

        return response.json.get("msg")

    async def connect_social(self, headers: dict) -> bool:
        social = SocialHandler(
            self.step,
            self.logger,
            self.client,
            account_info_retriever=self.account_info_retriever,
            transport_client=self.transport_client,
        )
        if await self.is_social_linked(headers, "social"):
            return True

        return await self._connect_social(headers, social)

    async def follow_channel(self, task: dict) -> bool:
        task_description = task.get("description")
        self.logger.log("Task type - follow social", task_description)

        user_to_follow = [user for user in task_description.split() if "@" in user][0][1:]
        social = SocialHandler(
            self.step,
            self.logger,
            self.client,
            account_info_retriever=self.account_info_retriever,
            transport_client=self.transport_client,
        )
        await social.start()

        return await social.social_follow(user_to_follow)

    async def get_oauth_data(self, headers: dict) -> dict:
        url = ("https://www.googleapis.com/identitytoolkit/v3/relyingparty/createAuthUri?"
               "key=YOUR_API_KEY")
        params = {
            "providerId": "social.com",
            "continueUri": "https://example.com/__/auth/handler",
            "customParameter": {},
        }
        response = await self.transport_client.post(url, headers, json=params, allow_redirects=False)
        return response.json

    async def get_id_token(self, headers: dict, request_uri: str, session_id: str) -> str:
        url = ("https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?"
               "key=YOUR_API_KEY")
        connect_params = {
            "requestUri": request_uri,
            "returnIdpCredential": True,
            "returnSecureToken": True,
            "sessionId": session_id,
        }
        response = await self.transport_client.post(url, headers, json=connect_params)
        return response.json.get("idToken")

    @staticmethod
    @CommonUtils.with_retry(attempts=10)
    async def get_request_uri(social: SocialHandler, auth_uri: str, referer_url: str) -> str:
        return await social.social_register({"redirect_url": auth_uri, "referer_url": referer_url})

    async def _connect_social(self, headers: dict, social: SocialHandler) -> bool:
        oauth_data = await self.get_oauth_data(headers)

        auth_uri = oauth_data.get("authUri")
        session_id = oauth_data.get("sessionId")

        request_uri = await self.get_request_uri(social, auth_uri, "https://example.com/")

        id_token = await self.get_id_token(headers, request_uri, session_id)
        params = {"platform_name": "social", "social_callback_data": id_token}
        url = "https://api.example.com/api/v1/users/social-connect/"
        response = await self.transport_client.post(url, headers, json=params)

        return response.json.get("msg") == "OK"

    async def is_social_linked(self, headers: dict, param: str) -> bool:
        url = "https://api.example.com/api/v1/users/profile/"
        response = await self.transport_client.get(url, headers)
        social_links = deep_get_safe(response.json, ["data", "social_links"])

        if social_links:
            for social in social_links:
                if social.get("platform_name") == param:
                    return True
        return False

    async def bind_invite_code(self, headers: dict) -> bool:
        invite_code = get_query_param(self.step.task.extra, "invite_code")
        url = "https://api.example.com/api/v1/reward/bind-invite-code/"
        params = {"invite_code": invite_code}
        response = await self.transport_client.post(url, headers, json=params)

        return response.json.get("msg") == "OK"

    async def example_type_handler(self, task: dict, headers: dict) -> bool:
        if task.get("name") == "Connect Account":
            return await self.connect_social(headers)

        elif task.get("name") == "Follow Account":
            return await self.follow_channel(task)

        elif task.get("name") == "Bind Referral Code":
            return await self.bind_invite_code(headers)

        elif task.get("name") == "Build A example Node":
            return True

        raise TransactionNotCreated(
            TransactionErrorTypeEnum.UNSUPPORTED_TASK_TYPE,
            error_message=f"Task is not supported",
            class_name=self.__class__.__name__,
        )

    async def wait_for_confirmation(self, task: Task, tx_hash: str):
        return TaskHandlerResult(tx_hash)
