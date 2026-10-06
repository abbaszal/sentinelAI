from database.base import Base
from database.session import engine

# Important:
# importing models registers them with SQLAlchemy
from database import models


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")