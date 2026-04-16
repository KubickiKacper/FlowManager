from fastapi import APIRouter, status

router = APIRouter()


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"description": "Service is healthy"},
    },
)
async def healthcheck():
    return {"status": "ok"}
