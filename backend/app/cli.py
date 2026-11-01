import argparse,json
from app.config import MODELS
from app.database.session import SessionLocal,Base,engine
from app.services.engine import initialize

parser=argparse.ArgumentParser(description='HelioGrid data, model and database preparation')
parser.add_argument('command',choices=['prepare','train','init','metrics'])
parser.add_argument('--days',type=int,default=120)
args=parser.parse_args()
if args.command in ['prepare','train']:
    if not (MODELS/'registry.json').exists() or args.command=='train':
        from app.ml.training import train_all
        result=train_all(args.days); print(json.dumps({k:v.get('metrics') for k,v in result['targets'].items()},indent=2))
if args.command in ['prepare','init']:
    Base.metadata.create_all(engine)
    with SessionLocal() as db: initialize(db)
    print('Database initialized; synthetic history and first optimization persisted.')
if args.command=='metrics': print((MODELS/'registry.json').read_text())
