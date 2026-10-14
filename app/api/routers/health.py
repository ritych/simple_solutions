from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Проверка, что процесс API отвечает")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"docs": "/docs", "health": "/health", "prices": "/api/v1/prices"}
