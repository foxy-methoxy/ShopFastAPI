import httpx
from fastapi import FastAPI, HTTPException, Depends, Response, Request

import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette import status

app = FastAPI(
    title="API Gateway",
)
security = HTTPBearer()

SECRET_KEY = 'super-secret-key'

ROUTES: dict[str, str] = {
    "/users": "http://user-service:8100",
    "/products": "http://product-service:8100",
    "/orders": "http://order-service:8100"
}

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gateway(
        service: str,
        path: str,
        request: Request,
        token_data: dict = Depends(verify_token),

) -> Response:
    prefix = f"/{service}"
    target_url = ROUTES.get(prefix)

    if not target_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    full_url = f"{target_url}/{path}"
    if request.query_params:
        full_url = f"{full_url}?{request.query_params}"

    headers = dict(request.headers)
    headers["X-User-Id"] = str(token_data.get("user_id"), "")
    headers["X-User-Email"] = str(token_data.get("email"), "")
    del headers["host"]

    body = await request.body()

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.request(
            method=request.method,
            url=full_url, headers=headers, content=body)

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers)
    )

