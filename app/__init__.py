from flask import Flask
import os
from sqlalchemy import create_engine

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SECRET_KEY'] = '123asd46fsaFSD462448fsdf46484FS"$§§"$4654FDfds"'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://marcelcouturier:Lm428xpX1z@167.172.178.230/ubcdata'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'] , pool_pre_ping=True)

app.config['JSON_AS_ASCII'] = False

from app import routes