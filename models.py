from sqlalchemy import Column, Integer, BigInteger, String, Boolean
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(BigInteger, unique=True, index=True)
    is_verified = Column(Boolean, default=False)
    code = Column(String, nullable=True)  # 4-значный код
