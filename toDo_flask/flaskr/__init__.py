# __init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

from flaskr.utils.template_filters import money_format

# ログインマネージャー作成
login_manager = LoginManager() #Flask_loginライブラリとアプリケーションを協調して動作させる
login_manager.login_view = 'app.view' #ログインするviewの関数設定、login_viewのrouteを作成
login_manager.login_message = 'ログインしてください' #ログイン画面にリダイレクトした場合のメッセージ

basedir = os.path.abspath(os.path.dirname(__name__)) #sqlのデータを格納するファイルのパス指定
db = SQLAlchemy() #DBのインスタンス生成
migrate = Migrate()

config = {
    'development': 'config/development/settings.cfg',
    'production': 'config/production/settings.cfg'
}

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'mysite' 
    # config_file = config[os.getenv('ENVIRONMENT', 'development')]
    config_file = config['development']
    app.config.from_pyfile(config_file)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    from flaskr.views import bp #viewファイルからアプリの情報を取得して登録、マッピングはviewsファイル内で
    app.register_blueprint(bp) #bpはViewやURIの機能、アプリの単位でグループ分けしたいときに使う
    app.add_template_filter(money_format) #自作テンプレートフィルターの作成
    db.init_app(app) #アプリがDBを使えるように登録
    migrate.init_app(app, db) #マイグレーション: プログラムのコードからDBにテーブルを編集、作成すること。ここではmigrateするDBを設定
    login_manager.init_app(app) #アプリケーションをログインに設定する。FLASK-Loginはセッションを利用するのでSECRET_KEYを設定しなければならない
    return app