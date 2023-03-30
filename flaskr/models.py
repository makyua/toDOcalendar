#models.py
from flaskr import db, login_manager
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy.orm import aliased
from sqlalchemy import and_

from datetime import datetime, timedelta
from uuid import uuid4 #uuidを作成するためのライブラリー、uuidはパスワードを作成する際などに便利な機能

# 認証ユーザーの呼び出し方を定義する⇒認証したいページに@login_requiredデコレートする
# さらにログインページのviewではis_authenticated()メソッドでログインの有無を確認できるので便利
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# flask_loginのuserMixinを継承したUserクラスを作る
class User(UserMixin, db.Model):
    
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True)
    email = db.Column(db.String(64), unique=True, index=True) #unique=Tにより、1つのemailは1つしか登録できない。同じemailのユーザーが登録できない。
    password = db.Column(
        db.String(128), 
        default=generate_password_hash('dbflaskapp').decode('utf-8') #デフォルトのパスワードとして、ユーザーが後で変更する
        )
    # 有効か無効かのフラグ
    is_active = db.Column(db.Boolean, unique=False, default=False)
    create_at = db.Column(db.DateTime, default=datetime.now)
    # カラムを追加したときに自動で作成される、管理者や運用の人がいつ更新されたかなどの流れを確認できる
    update_at = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, username, email):
        self.username = username
        self.email = email

    @classmethod
    def select_user_by_email(cls, email):
        return cls.query.filter_by(email=email).first() #カラムemailがemailのデータのみに絞り込み、SELECT+WHERE

    def validate_password(self, password):
        return check_password_hash(self.password, password) #self.passwordはテーブルに保持されているハッシュ化された値
    
    def create_new_user(self):
        db.session.add(self)

    @classmethod
    def select_user_by_id(cls, id):
        return cls.query.get(id)

    def save_new_password(self, new_password):
        self.password = generate_password_hash(new_password).decode('utf-8')
        self.is_active = True

    @classmethod
    def delete_user(cls, id):
        cls.query.filter_by(id=int(id)).delete()

#パスワードをリセットするときに利用する
class PasswordResetToken(db.Model):

    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(
        db.String(64),
        unique=True,
        index=True,
        server_default=str(uuid4) #ランダムにuuidの値を生成するのでそれを文字列型に変換してデフォルトにする
    )
    #uer tableに紐づける際に利用する外部キー
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    #Tokenが有効な時間
    expire_at = db.Column(db.DateTime, default=datetime.now)
    # カラムを追加したときに自動で作成される、管理者や運用の人がいつ更新されたかなどの流れを確認できる
    create_at = db.Column(db.DateTime, default=datetime.now)
    update_at = db.Column(db.DateTime, default=datetime.now)
    
    def __init__(self, token, user_id, expire_at):
        self.token = token
        self.user_id = user_id
        self.expire_at = expire_at

    @classmethod
    #パスワードを設定用のURLを生成
    def publish_token(cls, user):
        token = str(uuid4())
        new_token = cls(
            token, 
            user.id,
            #パスワードの設定期限を明日までに設定する
            datetime.now() + timedelta(days=1)
        )
        db.session.add(new_token)
        return token
    
    @classmethod
    def get_user_id_by_token(cls, token):
        now = datetime.now()
        #tokenを使った絞り込みと有効期限が切れていないことの確認
        record = cls.query.filter_by(token=str(token)).filter(cls.expire_at > now).first()
        if record:
            return record.user_id
        else:
            return None

    @classmethod
    def delete_token(cls, token):
        cls.query.filter_by(token=str(token)).delete()

# 会社
class Company(db.Model):

    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), index=True
    ) #誰が記入した企業研究結果か
    comname = db.Column(db.String(64), index=True)
    wishpoint = db.Column(db.Integer)
    step = db.Column(db.String(64))
    scale = db.Column(db.Integer)
    startmoney = db.Column(db.Integer)
    numemploy = db.Column(db.Integer)
    comment = db.Column(db.Text)
    create_at = db.Column(db.DateTime, default=datetime.now)
    update_at = db.Column(db.DateTime, default=datetime.now)

    def __init__(
        self, from_user_id, comname, wishpoint,
        step, scale, startmoney, numemploy, comment
        ):
        self.from_user_id = from_user_id
        self.comname = comname
        self.wishpoint = wishpoint
        self.step = step
        self.scale = scale
        self.startmoney = startmoney
        self.numemploy = numemploy
        self.comment = comment

    # データベース追加用
    def create_new_company(self):
        db.session.add(self)
    
    @classmethod
    def select_company_by_comname(cls, id):
        return cls.query.get(id)

    # ユーザーが作成した情報をすべて取得
    @classmethod
    def select_company_by_user_id(cls, id):
        return cls.query.filter_by(from_user_id=id).all()
    
    # idから一つだけ情報を取得
    @classmethod
    def select_company_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    # 会社名から検索
    @classmethod
    def search_by_comname(cls, comname, id):
        return cls.query.filter(
            cls.comname.like(f'%{comname}%'),
            cls.from_user_id == int(id)
        ).all()

    # idから会社の情報の削除、本当はユーザーのIDと会社情報を登録したユーザーのIDと等しいか検証
    @classmethod
    def delete_company(cls, id):
        cls.query.filter_by(id=int(id)).delete()

# タスクの管理
class Task(db.Model):

    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), index=True
    ) #誰が記入したか
    taskname = db.Column(db.String(64), index=True)
    workday = db.Column(db.DateTime)
    overday = db.Column(db.DateTime) 
    memo = db.Column(db.Text)
    # 有効か無効かのフラグ
    is_active = db.Column(db.Boolean, unique=False, default=True)
    create_at = db.Column(db.DateTime, default=datetime.now)
    # カラムを追加したときに自動で作成される、管理者や運用の人がいつ更新されたかなどの流れを確認できる
    update_at = db.Column(db.DateTime, default=datetime.now)

    def __init__(
        self, from_user_id, taskname, workday, overday,
        memo
        ):
        self.from_user_id = from_user_id
        self.taskname = taskname
        self.workday = workday
        self.overday = overday
        self.memo = memo

    @classmethod
    def select_task_by_taskname(cls, taskname):
        return cls.query.filter_by(taskname=taskname).first()

    def create_new_task(self):
        db.session.add(self)

    @classmethod
    def select_task_by_user_id(cls, user_id):
        return cls.query.filter_by(from_user_id=user_id).all()

    @classmethod
    def select_active_task_by_user_id(cls, user_id):
        return cls.query.filter_by(from_user_id=user_id, is_active=True).all()

    @classmethod
    def select_active_task_by_user_id_sort(cls, user_id):
        return cls.query.filter_by(from_user_id=user_id, is_active=True).order_by(cls.workday).all()

    @classmethod
    def select_all_task_by_user_id(cls, user_id):
        return cls.query.filter_by(from_user_id=user_id).all()

    @classmethod
    def select_all_task_by_user_id_sort(cls, user_id):
        return cls.query.filter_by(from_user_id=user_id).order_by(cls.workday).all()

    @classmethod
    def select_task_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    def update_status(self):
        self.is_active = False
        self.update_at = datetime.now()

# 会社の基本情報
class Company_basic(db.Model):

    __tablename__ = 'companies_basic'

    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), index=True
    ) #誰が記入した会社基本情報か
    comname = db.Column(db.String(64), index=True, unique=True) #会社名: かぶり禁止
    occupation = db.Column(db.String(64)) # 職種
    length = db.Column(db.DateTime) # 長寿か老舗か
    scale = db.Column(db.String(64)) # 規模感
    comstock = db.Column(db.String(64)) #上場しているか
    supplier = db.Column(db.String(64)) #主要取引相手
    client = db.Column(db.String(64)) #顧客
    is_active_step = db.Column(db.Boolean, unique=False, default=False) #stepテーブルがあるかどうか
    create_at = db.Column(db.DateTime, default=datetime.now)
    update_at = db.Column(db.DateTime, default=datetime.now)

    def __init__(
        self, from_user_id, comname, occupation,
        length, scale, comstock, supplier, client
        ):
        self.from_user_id = from_user_id
        self.comname = comname
        self.occupation = occupation
        self.length = length
        self.scale = scale
        self.comstock = comstock
        self.supplier = supplier
        self.client = client

    # ユーザーが作成した情報をすべて取得
    @classmethod
    def select_company_by_user_id(cls, id):
        return cls.query.filter_by(from_user_id=id).all()
    
    # 会社名から検索
    @classmethod
    def select_company_by_comname(cls, comname):
        return cls.query.filter_by(comname=comname).first()

    # 追加
    def create_new_company(self):
        db.session.add(self)

    @classmethod
    def select_company_by_id(cls, id):
        return cls.query.filter_by(id=id).first()

    # idから会社の情報の削除、本当はユーザーのIDと会社情報を登録したユーザーのIDと等しいか検証
    @classmethod
    def delete_company(cls, id):
        cls.query.filter_by(id=int(id)).delete()

    # stepの登録
    def update_step_active(self):
        self.is_active_step = True

    # company_numberとの外部結合して検索
    @classmethod
    def select_company_by_basic_and_number(cls, id):
        return cls.query.filter_by(from_user_id=id).outerjoin(
            Company_number,
            Company_number.basic_id == Company_basic.id
        ).with_entities(
            cls.id, cls.comname,
            Company_number.age, Company_number.average_salary,
            Company_number.capital, Company_number.employee,
            Company_number.turnover, Company_number.start_salary
        ).all()

# 会社の採用情報テーブル
class Company_step(db.Model):

    __tablename__ = 'companies_step'

    id = db.Column(db.Integer, primary_key=True)
    basic_id = db.Column(
        db.Integer, db.ForeignKey('companies_basic.id'), index=True
    ) # 外部キー
    comname = db.Column(db.String(64), index=True, unique=True) #会社名: かぶり禁止
    aspiration = db.Column(db.Integer)
    step = db.Column(db.String(64))
    status = db.Column(db.String(64))
    good_comment = db.Column(db.Text)
    bad_comment = db.Column(db.Text)
    sonota_comment = db.Column(db.Text)
    create_at = db.Column(db.DateTime, default=datetime.now)
    update_at = db.Column(db.DateTime, default=datetime.now)


    def __init__(
        self, basic_id, comname, aspiration,
        step, status, good_comment, bad_comment, sonota_comment
        ):
        self.basic_id = basic_id
        self.comname = comname
        self.aspiration = aspiration
        self.step = step
        self.status = status
        self.good_comment = good_comment
        self.bad_comment = bad_comment
        self.sonota_comment = sonota_comment

    # データベース追加用
    def create_new_step(self):
        db.session.add(self)

    # 基本情報からの検索
    @classmethod
    def select_step_by_basic_id(cls, id):
        return cls.query.filter_by(basic_id=id).first()

    # 基本情報からの検索
    @classmethod
    def select_step_by_id(cls, id):
        return cls.query.filter_by(id=id).first()
    
    # 基本情報からの検索
    @classmethod
    def select_step_by_name(cls, name):
        return cls.query.filter_by(comname=name).first()

# 会社を数字で比較する場合のテーブル
class Company_number(db.Model):

    __tablename__ = 'company_numbers'

    id = db.Column(db.Integer, primary_key=True)
    basic_id = db.Column(
        db.Integer, db.ForeignKey('companies_basic.id'), index=True
    ) # 外部キー
    from_user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), index=True
    ) #誰が記入した会社基本情報か
    comname = db.Column(db.String(64), index=True, unique=True) #会社名: かぶり禁止
    age = db.Column(db.Integer)
    capital = db.Column(db.Integer) #資本金
    employee = db.Column(db.Integer) #従業員数
    turnover = db.Column(db.Integer) #離職率
    start_salary = db.Column(db.Integer) #初任給
    average_salary = db.Column(db.Integer) #平均年収
    comment = db.Column(db.Text)
    create_at = db.Column(db.DateTime, default=datetime.now)
    update_at = db.Column(db.DateTime, default=datetime.now)

    def __init__(
        self, basic_id, from_user_id, comname, age,
        capital, employee, turnover, start_salary, average_salary,
        comment
        ):
        self.basic_id = basic_id
        self.from_user_id = from_user_id
        self.comname = comname
        self.age = age
        self.capital = capital
        self.employee = employee
        self.turnover = turnover
        self.start_salary = start_salary
        self.average_salary = average_salary
        self.comment = comment

    # 追加
    def create_new_number(self):
        db.session.add(self)

    @classmethod
    def select_companies_by_user_id(cls, id):
        return cls.query.filter_by(from_user_id=id).all()

    # 会社名から検索
    @classmethod
    def select_company_by_comname(cls, comname):
        return cls.query.filter_by(comname=comname).first()

# イベントデータ
class Event(db.Model):

    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    basic_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), index=True
    ) # 外部キー
    title = db.Column(db.String(64), index=True, unique=False) #会社名: かぶり禁止
    allDayCheck = db.Column(db.Boolean, unique=False)
    at_start = db.Column(db.DateTime)
    at_end = db.Column(db.DateTime)
    comment = db.Column(db.Text)
    is_active = db.Column(db.Boolean, unique=False, default=True)
    create_at = db.Column(db.DateTime, default=datetime.now)
    update_at = db.Column(db.DateTime, default=datetime.now)

    def __init__(
        self, basic_id, title, allDayCheck,
        at_start, at_end, comment, is_active
        ):
        self.basic_id = basic_id
        self.title = title
        self.allDayCheck = allDayCheck
        self.at_start = at_start
        self.at_end = at_end
        self.comment = comment
        self.is_active = is_active

    # データベース追加用
    def create_new_event(self):
        db.session.add(self)

    # イベント取得
    @classmethod
    def select_events(cls, user_id, start, end):
        return cls.query.filter(
            and_(
                Event.basic_id==user_id, 
                Event.is_active==True, 
                Event.at_start>=start,
                Event.at_end<=end
            )
        ).all()

    # idでイベント取得
    @classmethod
    def select_event_by_id(cls, user_id, id):
        return cls.query.filter(
            and_(
                Event.basic_id==user_id, 
                Event.is_active==True, 
                Event.id==id
            )
        ).first()

    @classmethod
    def delete_event(cls, id):
        cls.query.filter_by(id=id).delete()

# イベントデータ
class EventSec(db.Model):

    __tablename__ = 'events_2'

    id = db.Column(db.Integer, primary_key=True)
    basic_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), index=True
    ) # 外部キー
    title = db.Column(db.String(64), index=True, unique=False)
    allDayCheck = db.Column(db.Boolean, unique=False)
    at_start = db.Column(db.DateTime)
    at_end = db.Column(db.DateTime)
    comment = db.Column(db.Text)
    eventcolor = db.Column(db.String(64))
    is_active = db.Column(db.Boolean, unique=False, default=True)
    create_at = db.Column(db.DateTime, default=datetime.now)
    update_at = db.Column(db.DateTime, default=datetime.now)

    def __init__(
        self, basic_id, title, allDayCheck,
        at_start, at_end, comment, is_active, eventcolor="red"
        ):
        self.basic_id = basic_id
        self.title = title
        self.allDayCheck = allDayCheck
        self.at_start = at_start
        self.at_end = at_end
        self.comment = comment
        self.eventcolor = eventcolor
        self.is_active = is_active

    # データベース追加用
    def create_new_event(self):
        db.session.add(self)

    # イベント取得
    @classmethod
    def select_events(cls, user_id, start, end):
        return cls.query.filter(
            and_(
                EventSec.basic_id==user_id, 
                EventSec.is_active==True, 
                EventSec.at_start>=start,
                EventSec.at_end<=end
            )
        ).all()

    # idでイベント取得
    @classmethod
    def select_event_by_id(cls, user_id, id):
        return cls.query.filter(
            and_(
                EventSec.basic_id==user_id, 
                EventSec.is_active==True, 
                EventSec.id==id
            )
        ).first()

    @classmethod
    def delete_event(cls, id):
        cls.query.filter_by(id=id).delete()