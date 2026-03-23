import requests
from typing import TypedDict, Literal

class HttpRequestParameters(TypedDict):
    host: str
    csrf_token: str
    statefulness: Literal["stateless", "stateful"]
    request_number: int
    session: requests.Session
    client: str


def request(
    http_request_parameters: HttpRequestParameters,
    uri: str,
    method: Literal["GET", "POST", "PUT", "DELETE"],
    body: str | None,
    params: dict,
    content_type: str | None = "application/xml",
    accept: str = "*/*",
    cookies: dict | None = None,
) -> requests.Response:

    # Add sap-client to params if not already present
    if "sap-client" not in params:
        params["sap-client"] = http_request_parameters["client"]

    headers = {
        "Accept": accept,
        "Cache-Control": "no-cache",
        "x-csrf-token": http_request_parameters["csrf_token"],
        "X-sap-adt-sessiontype": http_request_parameters["statefulness"],
    }
    
    # Only add Content-Type if explicitly provided
    if content_type is not None:
        headers["content-type"] = content_type

    config = {
        "params": params,
        "headers": headers,
        "url": http_request_parameters["host"] + uri,
        "data": body,
    }
    if cookies:
        config["cookies"] = cookies

    session = http_request_parameters["session"]
    if method == "POST":
        response = session.post(**config)
    elif method == "GET":
        response = session.get(**config)
    elif method == "PUT":
        response = session.put(**config)
    elif method == "DELETE":
        response = session.delete(**config)
    else:
        raise ValueError(f"Unsupported method: {method}")
    return response
