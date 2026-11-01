import logging,os,json
from contextlib import asynccontextmanager
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse,FileResponse
from fastapi.staticfiles import StaticFiles
from app.database.session import SessionLocal,engine
from app.database.session import Base
from app.config import ROOT,MODELS,DATA_NOTICE
from app.routes import energy,operations,data
from app.services.engine import initialize

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s %(message)s')
@asynccontextmanager
async def lifespan(app:FastAPI):
    Base.metadata.create_all(engine)
    if os.getenv('HELIOGRID_SKIP_INIT')!='1':
        if not (MODELS/'registry.json').exists():
            from app.ml.training import train_all
            train_all()
        with SessionLocal() as db: initialize(db)
    yield
app=FastAPI(title='HelioGrid · Renewable Energy Intelligence API',description=DATA_NOTICE+' All optimization is advisory. USD and kg CO₂ are illustrative.',version='1.0.0',lifespan=lifespan,docs_url='/api/docs',openapi_url='/api/openapi.json',redoc_url='/api/redoc')
origins=os.getenv('HELIOGRID_CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(',')
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=['GET','POST','PATCH'],allow_headers=['Content-Type'])
@app.middleware('http')
async def security_headers(request:Request,call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    if request.url.path.startswith('/api'): response.headers['Cache-Control']='no-store'
    return response
@app.exception_handler(ValueError)
async def value_error(request:Request,exc:ValueError): return JSONResponse(status_code=422,content={'detail':str(exc)})
@app.exception_handler(RuntimeError)
async def runtime_error(request:Request,exc:RuntimeError):
    logging.getLogger('heliogrid').exception('Request failed')
    return JSONResponse(status_code=503,content={'detail':str(exc)})
@app.get('/api/health',tags=['System'])
def health(): return {'status':'ok','service':'HelioGrid','models_ready':(MODELS/'registry.json').exists(),'source':DATA_NOTICE}
app.include_router(energy.router,prefix='/api'); app.include_router(operations.router,prefix='/api'); app.include_router(data.router,prefix='/api')
# A production-style single-port deployment is available after npm run build.
frontend=ROOT/'frontend'/'dist'
if frontend.exists():
    app.mount('/',StaticFiles(directory=frontend,html=True),name='frontend')
