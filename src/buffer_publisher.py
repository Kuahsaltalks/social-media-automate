"""
Buffer API automated publisher for X, LinkedIn, and Threads.

Uses Buffer's modern GraphQL API (api.buffer.com) with Personal Access Tokens.
Supports single or multi-account posting.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import urllib.request
import urllib.parse
import urllib.error

class BufferPublisher:
    def __init__(self, access_tokens: Optional[List[str]] = None):
        """
        access_tokens: list of Buffer Personal API Keys.
        If not provided, reads BUFFER_API_KEY or BUFFER_API_KEY_1, BUFFER_API_KEY_2 from environment.
        """
        if access_tokens:
            self.tokens = access_tokens
        else:
            self.tokens = []
            primary = os.environ.get("BUFFER_API_KEY", os.environ.get("BUFFER_API_KEY_1", ""))
            secondary = os.environ.get("BUFFER_API_KEY_2", "")
            if primary and primary != "your_buffer_personal_api_key_here":
                self.tokens.append(primary)
            if secondary and secondary != "your_second_buffer_api_key_here":
                self.tokens.append(secondary)

        self.graphql_url = "https://api.buffer.com"

    def _execute_query(self, token: str, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against Buffer API."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "SocialMediaAutomate/1.0"
        }
        payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
        req = urllib.request.Request(self.graphql_url, data=payload, headers=headers)
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            return {"error": f"HTTP {e.code}: {e.reason}", "details": err_body}
        except Exception as e:
            return {"error": str(e)}

    def get_connected_channels(self) -> List[Dict[str, Any]]:
        """Fetch all connected channels across all organizations in all configured Buffer accounts."""
        if not self.tokens:
            return []

        all_channels = []
        org_query = """
        query GetAccountOrgs {
            account {
                id
                email
                organizations {
                    id
                    name
                }
            }
        }
        """
        channels_query = """
        query GetChannels($input: ChannelsInput!) {
            channels(input: $input) {
                id
                name
                service
                serviceId
                displayName
                avatar
            }
        }
        """

        for token in self.tokens:
            account_res = self._execute_query(token, org_query)
            account_data = account_res.get("data", {}).get("account", {})
            orgs = account_data.get("organizations", [])
            for org in orgs:
                org_id = org.get("id")
                if org_id:
                    ch_res = self._execute_query(token, channels_query, {"input": {"organizationId": org_id}})
                    channels = ch_res.get("data", {}).get("channels", [])
                    for ch in channels:
                        ch["_token"] = token
                        ch["_org_name"] = org.get("name")
                        ch["_account_email"] = account_data.get("email")
                        all_channels.append(ch)

        return all_channels

    def upload_image_to_cdn(self, file_path: Path) -> Optional[str]:
        """Uploads a local image to a high-speed CDN to obtain a public URL for Buffer API."""
        if not file_path or not file_path.exists():
            return None

        # 1. Try freeimage.host API
        try:
            import base64
            with open(file_path, "rb") as f:
                b64_img = base64.b64encode(f.read()).decode("utf-8")
            data = urllib.parse.urlencode({
                "key": "6d207e02198a847aa98d0a2a901485a5",
                "action": "upload",
                "source": b64_img,
                "format": "json"
            }).encode("utf-8")
            req = urllib.request.Request("https://freeimage.host/api/1/upload", data=data, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode())
                img_url = res.get("image", {}).get("url")
                if img_url:
                    print(f"[✔ Buffer Media Upload] Image hosted at: {img_url}")
                    return img_url
        except Exception as e:
            print(f"[Warning] freeimage upload failed: {e}")

        # 2. Try tmpfiles.org fallback
        try:
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            body = bytearray()
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode())
            body.extend(b"Content-Type: image/png\r\n\r\n")
            body.extend(file_bytes)
            body.extend(f"\r\n--{boundary}--\r\n".encode())

            req = urllib.request.Request(
                "https://tmpfiles.org/api/v1/upload",
                data=bytes(body),
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode())
                raw_url = res.get("data", {}).get("url", "")
                if raw_url:
                    direct_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                    print(f"[✔ Buffer Media Upload] Image hosted at: {direct_url}")
                    return direct_url
        except Exception as e:
            print(f"[Warning] tmpfiles upload failed: {e}")

        return None

    def publish_post(self, platform: str, text: str, share_now: bool = False, media_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Publishes or queues content to the matching channel:
        - 'x' / 'twitter' -> Twitter/X channel
        - 'threads' -> Threads channel
        - 'linkedin' -> LinkedIn channel
        - 'instagram' -> Instagram channel
        """
        if not self.tokens:
            return {
                "status": "dry_run",
                "platform": platform,
                "note": "No BUFFER_API_KEY set in .env."
            }

        channels = self.get_connected_channels()
        if not channels:
            return {"status": "error", "message": "No channels found for your Buffer token(s)."}

        # Service mapping
        service_mapping = {
            "x": ["twitter", "x"],
            "threads": ["threads"],
            "linkedin": ["linkedin"],
            "instagram": ["instagram"]
        }
        target_services = service_mapping.get(platform.lower(), [platform.lower()])
        
        target_channel = next((ch for ch in channels if ch.get("service", "").lower() in target_services), None)
        if not target_channel:
            return {
                "status": "channel_not_connected",
                "message": f"No connected channel found matching '{platform}'. Connected channels: {[c.get('service') for c in channels]}"
            }

        # Upload media if present
        assets = []
        if media_path and Path(media_path).exists():
            img_url = self.upload_image_to_cdn(Path(media_path))
            if img_url:
                assets.append({"image": {"url": img_url}})

        mutation = """
        mutation CreatePost($input: CreatePostInput!) {
            createPost(input: $input) {
                ... on PostActionSuccess {
                    post {
                        id
                        text
                        status
                        channelId
                    }
                }
                ... on NotFoundError {
                    message
                }
                ... on UnauthorizedError {
                    message
                }
                ... on UnexpectedError {
                    message
                }
                ... on RestProxyError {
                    message
                    code
                }
                ... on LimitReachedError {
                    message
                }
                ... on InvalidInputError {
                    message
                }
            }
        }
        """
        variables = {
            "input": {
                "channelId": target_channel["id"],
                "text": text,
                "mode": "shareNow" if share_now else "addToQueue",
                "schedulingType": "automatic",
                "needsApproval": False,
                "assets": assets
            }
        }

        res = self._execute_query(target_channel["_token"], mutation, variables)
        return {
            "platform": platform,
            "channel_name": target_channel.get("displayName") or target_channel.get("name"),
            "service": target_channel.get("service"),
            "media_attached": bool(assets),
            "response": res
        }
