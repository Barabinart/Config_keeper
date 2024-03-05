from fastapi import FastAPI, HTTPException, Response
from netmiko import ConnectHandler
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Подключение к базе данных
DATABASE_URL = "sqlite:///./configurations.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Модель для хранения конфигураций
class Configuration(Base):
    __tablename__ = "configurations"

    id = Column(Integer, primary_key=True, index=True)
    device = Column(String)
    config = Column(String)
    saved_at = Column(DateTime)


# Создание таблицы в базе данных
Base.metadata.create_all(bind=engine)

app = FastAPI()


# Метод сохранения конфигурации в базу данных
def save_configuration(ip, username, password):
    device = {
        "device_type": "cisco_ios",
        "host": ip,
        "username": username,
        "password": password,
    }
    try:
        ssh_session = ConnectHandler(**device)
        configuration = ssh_session.send_command("show running-config")
        ssh_session.disconnect()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect to device: {str(e)}")

    db = SessionLocal()
    last_config = db.query(Configuration).filter(Configuration.device == ip).order_by(
        Configuration.saved_at.desc()).first()
    # print(last_config)
    if last_config and last_config.config == configuration:
        print(last_config.config)
        return "Конфигурация идентична последней, сохранение не требуется"

    new_config = Configuration(device=ip, config=configuration, saved_at=datetime.now())
    db.add(new_config)
    db.commit()
    return "Конфигурация успешно сохранена"


# Метод для просмотра последней конфигурации
def get_last_configuration(device):
    db = SessionLocal()
    last_config = db.query(Configuration).filter(Configuration.device == device).order_by(
        Configuration.saved_at.desc()).first()
    if last_config:
        return last_config.config
    else:
        return "Конфигурации для данного устройства не найдено"


@app.post("/save_config")
def save_config(ip: str, username: str, password: str):
    save_result = save_configuration(ip, username, password)
    return save_result


@app.get("/get_last_config")
def get_last_config(hostname: str):
    last_config = Response(content=get_last_configuration(hostname), media_type="text/plain")
    return last_config


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
