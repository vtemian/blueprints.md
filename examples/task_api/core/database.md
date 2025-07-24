# core.database
Database configuration and connection management

deps: sqlalchemy[create_engine, MetaData]; sqlalchemy.ext.declarative[declarative_base]; sqlalchemy.orm[sessionmaker, Session]; typing[Generator]; os

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

init_db() -> None:
  """Initialize database tables"""
  # Create all tables

get_db() -> Generator[Session, None, None]:
  """Database session dependency"""
  # Yield session with proper cleanup

notes: add connection pooling for production, implement database migrations, add health checks