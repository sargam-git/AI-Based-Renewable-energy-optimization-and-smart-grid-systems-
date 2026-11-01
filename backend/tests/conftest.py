import os,sys,tempfile
from pathlib import Path
import pytest
# Isolate every test process from the user's running database/model files.
TMP=Path(tempfile.mkdtemp(prefix='heliogrid-test-'))
os.environ['HELIOGRID_DATA_DIR']=str(TMP/'data')
os.environ['HELIOGRID_MODEL_DIR']=str(TMP/'models')
os.environ['HELIOGRID_DB']=str(TMP/'test.db')
os.environ['HELIOGRID_SKIP_INIT']='1'
os.environ['OMP_NUM_THREADS']='1'; os.environ['OPENBLAS_NUM_THREADS']='1'
from app.ml.training import train_all
from app.database.session import Base,engine,SessionLocal
from app.services.engine import initialize

@pytest.fixture(scope='session',autouse=True)
def prepared():
    train_all(60); Base.metadata.create_all(engine)
    with SessionLocal() as db: initialize(db)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture()
def db():
    with SessionLocal() as session: yield session

@pytest.fixture(scope='session')
def client(prepared):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c: yield c
