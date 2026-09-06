from dotenv import load_dotenv
load_dotenv()  # must run before service modules read os.getenv at import time

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import resume, applications, tailor, discovery, dashboard, notify, blacklist, referrals
from .routers import portals, github


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle — starts the background scheduler
    (GitHub polling, etc.) when the server boots."""
    from .services.background_tasks import start_scheduler, stop_scheduler
    from .database import run_light_migrations
    Base.metadata.create_all(bind=engine)
    run_light_migrations()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Launchpad API", version="2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this if you deploy publicly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router)
app.include_router(applications.router)
app.include_router(tailor.router)
app.include_router(discovery.router)
app.include_router(dashboard.router)
app.include_router(notify.router)
app.include_router(blacklist.router)
app.include_router(referrals.router)
app.include_router(portals.router)
app.include_router(github.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
