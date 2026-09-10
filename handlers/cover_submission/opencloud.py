import config
import os
import asyncio
import aiohttp
import json

ROBLOX_API_KEY = os.getenv("ROBLOX_OPENCLOUD")

UNIVERSE_ID = "9381876880"
PLACE_ID = "137899023865628"

async def run_luau(script: str):
    BASE_URL = "https://apis.roblox.com/cloud/v2"
    HEADERS = {
        "x-api-key": ROBLOX_API_KEY,
        "Content-Type": "application/json",
    }

    url = (
        f"{BASE_URL}/universes/{UNIVERSE_ID}"
        f"/places/{PLACE_ID}"
        f"/luau-execution-session-tasks"
    )

    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(
        headers=HEADERS,
        timeout=timeout
    ) as session:
        async with session.post(
            url,
            json={"script": script}
        ) as response:
            if response.status not in (200, 201):
                text = await response.text()
                raise RuntimeError(
                    f"Failed to start Luau task:\n"
                    f"HTTP {response.status}\n"
                    f"{text}"
                )

            task = await response.json()

        task_path = task["path"]

        while True:
            async with session.get(
                f"{BASE_URL}/{task_path}"
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(
                        f"Failed checking task:\n"
                        f"HTTP {response.status}\n"
                        f"{text}"
                    )

                data = await response.json()

            state = data.get("state")

            if state != "PROCESSING":
                break

            await asyncio.sleep(1)

        async with session.get(
            f"{BASE_URL}/{task_path}/logs"
        ) as response:
            messages = []

            if response.status == 200:
                logs_data = await response.json()

                for entry in logs_data.get(
                    "luauExecutionSessionTaskLogs",
                    []
                ):
                    messages.extend(entry.get("messages", []))

        return {
            "state": state,
            "logs": messages,
            "result": data.get("output"),
            "error": data.get("error"),
        }

async def upload_file(file_path: str, display_name: str, description: str = ""):
    BASE_URL = "https://apis.roblox.com"

    extension = os.path.splitext(file_path)[1].lower()

    content_types = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav"
    }

    request_data = {
        "assetType": "Audio",
        "displayName": display_name,
        "description": description,
        "creationContext": {
            "creator": {
                "groupId": config.group_id
            }
        }
    }

    form = aiohttp.FormData()
    form.add_field(
        "request",
        json.dumps(request_data),
        content_type="application/json"
    )

    with open(file_path, "rb") as file:
        form.add_field(
            "fileContent",
            file,
            filename=os.path.basename(file_path),
            content_type=content_types[extension]
        )

        headers = {
            "x-api-key": ROBLOX_API_KEY
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(
                f"{BASE_URL}/assets/v1/assets",
                data=form
            ) as response:
                if response.status not in (200, 201):
                    text = await response.text()
                    raise RuntimeError(
                        f"Failed to upload asset:\n"
                        f"HTTP {response.status}\n"
                        f"{text}"
                    )

                operation = await response.json()

            operation_path = operation["path"]

            operation_id = operation["operationId"]

            while True:
                async with session.get(
                    f"{BASE_URL}/assets/v1/operations/{operation_id}"
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise RuntimeError(
                            f"Failed checking upload:\n"
                            f"HTTP {response.status}\n"
                            f"{text}"
                        )

                    data = await response.json()

                if data.get("done"):
                    break

                await asyncio.sleep(1)

            if "error" in data:
                raise RuntimeError(
                    f"Asset upload failed: {data['error']}"
                )

            asset = data.get("response", {})

            return {
                "asset_id": asset.get("assetId"),
                "path": asset.get("path"),
                "display_name": asset.get("displayName"),
                "asset_type": asset.get("assetType"),
                "operation": operation_path
            }