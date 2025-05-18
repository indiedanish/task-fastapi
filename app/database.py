import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Convert the URL to an async version
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Remove sslmode parameter as asyncpg doesn't support it directly
if "sslmode=" in ASYNC_DATABASE_URL:
    ASYNC_DATABASE_URL = ASYNC_DATABASE_URL.split("?")[0]

# Create engine with SSL if needed
connect_args = {}
if os.getenv("DATABASE_SSL", "false").lower() == "true":
    connect_args["ssl"] = True

# Create async engine
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,
    future=True,
    connect_args=connect_args
)

# Create async session
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Create base class for models
Base = declarative_base()

# Dependency to get a database session
async def get_db():
    """
    Dependency function that yields db sessions
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()