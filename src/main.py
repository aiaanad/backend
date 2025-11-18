from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from api.v1.routes import router as v1_router
from core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="API",
    description="",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(v1_router, prefix="/v1")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

api_url = "/api/v1"
system_api_url = f"{api_url}/system"

# Include routers
# app.include_router(auth.router,  prefix=api_url, tags=["Auth"])


@app.get("/")
async def root():
    return {"message": "System API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
