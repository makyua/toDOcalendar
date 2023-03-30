# forms.py
from wtforms.form import Form
from wtforms.fields import (
    StringField, PasswordField, SubmitField, HiddenField,
    TextAreaField, IntegerField, SelectField, BooleanField,
    FloatField
)
from wtforms.fields.html5 import (
    DateField
)
from wtforms.validators import (
    DataRequired, Email, EqualTo,
    NumberRange
)
from wtforms import ValidationError

from flask_login import current_user
from flask import flash

from flaskr.models import User, Company, Task, Company_basic

#ログイン用のForm
class LoginForm(Form):
    email = StringField(
        'メール: ', validators=[DataRequired(), Email()]
        )
    password = PasswordField(
        'パスワード: ', 
        validators=[DataRequired(), 
        EqualTo('confirm_password', message="パスワードが一致しません")]
        )
    confirm_password = PasswordField(
        'パスワード再入力: ', validators=[DataRequired()]
        )
    submit = SubmitField('ログイン')

#登録用のForm
class RegisterForm(Form):
    email = StringField(
        'メール: ', validators=[DataRequired(), Email('メールアドレスが間違っています')]
        )
    username = StringField('名前: ', validators=[DataRequired()])
    submit = SubmitField('登録')

    #同じメールアドレスの人が登録されないように自作バリデーション
    def validate_email(self, field):
        #クライアントが入力したユーザーと同じユーザーがいないか引っ張り出す
        if User.select_user_by_email(field.data):
            raise ValidationError('メールアドレスは既に登録されています')

#パスワード設定用のフォーム
class ResetPasswordForm(Form):
    password = PasswordField(
        'パスワード: ',
        validators=[DataRequired(), EqualTo('confirm_password', message='パスワードが一致しません')]
    )
    confirm_password = PasswordField(
        'パスワード確認: ', validators=[DataRequired()]
        )
    submit = SubmitField('パスワードを更新する')
    #パスワードの長さを8文字以上にする
    def validate_password(self, field):
        if len(field.data) < 8:
            raise ValidationError('パスワードは8文字以上です')

# ユーザーの情報を編集する
class UserForm(Form):
    email = StringField(
        'メール: ', validators=[DataRequired(), Email('メールアドレスが誤っています')]
    )
    username = StringField('名前: ', validators=[DataRequired()])
    submit = SubmitField('登録情報更新')

    #全体のバリデーション
    def validate(self):
        if not super(Form, self).validate():
            return False
        #メールアドレスが既に存在していないかの確認
        #追加でもし存在していても今ログインしているユーザーと同じならエラーにはしない
        user = User.select_user_by_email(self.email.data)
        if user:
            if user.id != int(current_user.get_id()):
                flash('そのメールアドレスは既に登録されています')
                return False
        return True

# パスワード変更時のフォーム
class ChangePasswordForm(Form):
    password = PasswordField(
        'パスワード',
        validators=[DataRequired(), EqualTo('confirm_password', message='パスワードが一致しません')]
    )
    confirm_password = PasswordField(
        'パスワード確認: ', validators=[DataRequired()]
    )
    submit = SubmitField('パスワードの更新')
    def validate_password(self, field):
        if len(field.data) < 8:
            raise ValidationError('パスワードは8文字以上です')

# 会社名の登録と編集用のフォーム
class CompanyForm(Form):
    from_user_id = HiddenField()
    comname = StringField('会社名: ', validators=[DataRequired()])
    wishpoint = IntegerField('志望度: ', validators=[NumberRange(0, 100, '不正な値です')])
    step = SelectField('選考段階: ', choices=[('', ''), ('選考前', '選考前'), ('会社説明後', '会社説明後'), ('ES提出後', 'ES提出後'), ('1次面接後', '1次面接後'), ('2次面接後', '2次面接後'), ('最終面接後', '最終面接後'), ('内定獲得', '内定獲得'), ('辞退/不合格', '辞退/不合格')])
    scale = StringField('規模感: ')
    startmoney = IntegerField('資本金: ')
    numemploy = IntegerField('従業員数: ')
    comment = TextAreaField('コメント: ')
    submit = SubmitField('登録')

    # 同じ会社名を登録できないようにバリデーション
    def validate_comname(self, field):
        if Company.select_company_by_comname(field.data):
            raise ValidationError('その会社名は既に登録されてあります')

# 会社名の検索
class CompanySearchForm(Form):
    comname = StringField('会社名: ')
    submit = SubmitField('会社名検索')

# タスクの追加と編集用のフォーム
class toDoForm(Form):
    from_user_id = HiddenField()
    taskname = StringField('タスク名: ', validators=[DataRequired()])
    workday = DateField('作業予定日: ', validators=[DataRequired()])
    overday = DateField('締切日: ', validators=[DataRequired()])
    memo = TextAreaField('メモ: ')
    submit = SubmitField('登録')

    # 同じタスクを登録できないようにバリデーション
    def validate_comname(self, field):
        if Task.select_task_by_taskname(field.data):
            raise ValidationError('そのタスクは既に登録されてあります')

# タスク完了用のフォーム
class TaskDoneForm(Form):
    task_id = HiddenField()
    submit = SubmitField()

# 基本会社の登録のフォーム
class BasicCompanyForm(Form):
    from_user_id = HiddenField()
    comname = StringField('会社名: ', validators=[DataRequired()])
    occupation = StringField('職種: ')
    length = DateField('設立: ')
    scale = StringField('規模感: ')
    comstock = SelectField('株式公開: ', choices=[('', ''), ('非上場', '非上場'), ('東証一部', '東証一部'), ('東証二部', '東証二部'), ('マザーズ', 'マザーズ')])
    supplier = SelectField('主要取引先: ', choices=[('', ''), ('グループ会社', 'グループ会社'), ('大手・有名企業', '大手・有名企業'), ('官公庁', '官公庁'), ('その他', 'その他')])
    client = SelectField('顧客: ', choices=[('', ''), ('BtoB', 'BtoB'), ('BtoC', 'BtoC'), ('その他', 'その他')])
    submit = SubmitField('登録')

    # 同じ会社名を登録できないようにバリデーション
    def validate_comname(self, field):
        if Company_basic.select_company_by_comname(field.data):
            raise ValidationError('その会社名は既に登録されてあります')

# 基本会社の編集用のフォーム
class BasicCompanyEditForm(Form):
    from_user_id = HiddenField()
    comname = StringField('会社名: ', validators=[DataRequired()])
    occupation = StringField('職種: ')
    length = DateField('設立: ')
    scale = StringField('規模感: ')
    comstock = SelectField('株式公開: ', choices=[('', ''), ('非上場', '非上場'), ('東証一部', '東証一部'), ('東証二部', '東証二部'), ('マザーズ', 'マザーズ')])
    supplier = SelectField('主要取引先: ', choices=[('', ''), ('グループ会社', 'グループ会社'), ('大手・有名企業', '大手・有名企業'), ('官公庁', '官公庁'), ('その他', 'その他')])
    client = SelectField('顧客: ', choices=[('', ''), ('BtoB', 'BtoB'), ('BtoC', 'BtoC'), ('その他', 'その他')])
    submit = SubmitField('登録')

# 会社の選考状況登録
class BasicCompanyStepFrom(Form):
    aspiration = StringField('志望度: ', validators=[DataRequired()])
    step = SelectField('選考段階: ', choices=[('', ''), ('選考前', '選考前'), ('会社説明後', '会社説明後'), ('ES提出後', 'ES提出後'), ('1次面接後', '1次面接後'), ('2次面接後', '2次面接後'), ('最終面接後', '最終面接後'), ('内定獲得', '内定獲得'), ('辞退/不合格', '辞退/不合格')])
    status = StringField('求める人物像: ')
    good_comment = TextAreaField('良いところ: ')
    bad_comment = TextAreaField('懸念点: ')
    sonota_comment = TextAreaField('特記事項: ')
    submit = SubmitField('登録')

# # 会社を数字で比較する場合のテーブルの登録
class BasicCompanyNumberFrom(Form):
    capital = IntegerField('資本金: ')
    employee = IntegerField('従業員数: ')
    turnover = FloatField('離職率: ')
    start_salary = IntegerField('初任給: ')
    average_salary = IntegerField('平均年収: ')
    comment = TextAreaField('特記事項: ')
    submit = SubmitField('登録')

# イベントの登録:自由なフォーム使用のため未使用
class EventForm(Form):
    from_user_id = HiddenField()
    title = StringField('タイトル：', validators=[DataRequired()])
    allDayCheck = BooleanField('終日：')
    at_start = DateField('開始日時：', validators=[DataRequired()])
    at_end = DateField('終了時間：', validators=[DataRequired()])
    at_start_hm = DateField('開始日時：', validators=[DataRequired()])
    at_end_hm = DateField('終了時間：', validators=[DataRequired()])
    comment = TextAreaField('詳細：')
    submit = SubmitField('登録')

    # 開始日時が終了日時を超えないようにする
    def validate(self):
        if not super(EventForm, self).validate:
            return False
        if self.allDayCheck:
            if not self.at_end and self.at_start:
                return False
            if self.at_start > self.at_end:
                return False
        else:
            if not self.at_end_hm and self.at_start_hm:
                return False
            if self.at_start_hm > self.at_end_hm:
                return False
        
# イベント表示のバリデーション用のフォーム
class CalendarForm(Form):
    start_date = IntegerField(validators=[DataRequired()])
    end_date = IntegerField(validators=[DataRequired()])