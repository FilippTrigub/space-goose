from typing import Dict, Optional

import httpx

from services import k8s_service


def resolve_endpoint_info(
    user_id: str, project_id: str, project_record: Optional[dict] = None
) -> Optional[Dict[str, Optional[str]]]:
    """Fetch latest ingress info; fall back to stored host if available."""
    info = k8s_service.get_project_endpoint(user_id, project_id)
    if info:
        return info

    if project_record:
        stored = project_record.get("endpoint")
        if stored:
            return {"host": stored, "ip": None, "lb_hostname": None}

    return None


def target_and_headers(endpoint_info: Dict[str, Optional[str]]):
    """Return HTTP target and headers for routing via shared ingress."""
    host = endpoint_info["host"]
    controller_ip = endpoint_info.get("ip")
    controller_hostname = endpoint_info.get("lb_hostname")
    target = controller_ip or controller_hostname or host
    headers = {"Host": host} if (controller_ip or controller_hostname) else {}
    return target, headers


async def goose_request(
    method: str,
    endpoint_info: Dict[str, Optional[str]],
    path: str,
    *,
    timeout: float = 10.0,
    json_payload=None,
    params=None,
    headers: Optional[Dict[str, str]] = None,
):
    """Send an HTTP request to the Goose API via the shared ingress."""
    target, base_headers = target_and_headers(endpoint_info)
    merged_headers = base_headers.copy()
    if headers:
        merged_headers.update(headers)

    url = f"http://{target}{path}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            method,
            url,
            json=json_payload,
            params=params,
            headers=merged_headers or None,
        )
    return response