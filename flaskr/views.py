import datetime
import time
from flask import(
    Blueprint, abort, request, render_template,
    redirect, url_for, flash, session, jsonify
)
from flask_login import (
    current_user, login_user, logout_user,
    login_required
    )
from itsdangerous import json
from sqlalchemy import false, true
from flaskr.models import (
    Task, User, PasswordResetToken, 
    Company, Company_basic, Company_step,
    Event, Company_number, EventSec
)
from flaskr import db

from flaskr.forms import (
    LoginForm, RegisterForm, ResetPasswordForm,
    UserForm, ChangePasswordForm, CompanyForm,
    CompanySearchForm, toDoForm, TaskDoneForm,
    BasicCompanyForm, BasicCompanyStepFrom,
    EventForm, CalendarForm, BasicCompanyNumberFrom,
    BasicCompanyEditForm
)

# ブループリントはアプリを分割できる＝プログラムの保守性を向上
bp = Blueprint('app', __name__, url_prefix='') #第一引数はbpの名前、第二引数はbpのパッケージ名、第三引数はアプリのルートパス

@bp.route('/') #htmlへのパスは「Blueprintの引数で指定した url_prefix」+ 「@Blueprintインスタンス.route('パス')」
def home():
    return render_template('home.html')

#登録画面
@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        user = User(
            email = form.email.data,
            username = form.username.data
        )
        #ユーザー名とメールアドレスを登録
        with db.session.begin(subtransactions=True):
            user.create_new_user()
        db.session.commit()

        #パスワードの設定
        token = ''
        with db.session.begin(subtransactions=True):
            token = PasswordResetToken.publish_token(user)
        db.session.commit()
        #本当はメールに飛ばすほうが良い、ユーザーの登録したメールアドレスが正しいことが確認できる
        print(
            f'パスワード設定用URL: http://127.0.0.1:5000/reset_password/{token}'
            )
        flash('パスワード設定用のURLを送りました。ご確認ください')
        return redirect(url_for('app.login'))
    return render_template('register.html', form=form)

# flask_loginの機能で簡単にログイン・ログアウトを管理できる
@bp.route('/logout')
def logout():
    logout_user() #ログアウト
    return redirect(url_for('app.home')) #ログアウトしたらホームに飛ばす

@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        user = User.select_user_by_email(form.email.data)
        if user and user.is_active and user.validate_password(form.password.data): #ユーザーが検索されたか、ユーザーがアクティブか、パスワードがあっているか
            login_user(user, remember=True)
            next = request.args.get('next')
            if not next:
                next = url_for('app.home')
            return redirect(next)
        elif not user:
            flash('存在しないユーザーです')
        elif not user.is_active:
            flash('無効なユーザーです。パスワードを再設定してください')
        elif not user.validate_password(form.password.data):
            flash('メールアドレスとパスワードの組み合わせが誤っています')
    return render_template('login.html', form=form)

#パスワード設定用URLの作成
@bp.route('/reset_password/<uuid:token>', methods=['GET', 'POST'])
def reset_password(token):
    form = ResetPasswordForm(request.form)
    #tokenに紐づいたユーザIDを得て、そのユーザIDでパスワードを設定する
    reset_user_id = PasswordResetToken.get_user_id_by_token(token)
    if not reset_user_id:
        abort(500)
    if request.method == 'POST' and form.validate():
        password = form.password.data
        #ユーザIDからユーザーテーブルからレコード（インスタンス）を取得
        user = User.select_user_by_id(reset_user_id)
        with db.session.begin(subtransactions=True):
            user.save_new_password(password)
            PasswordResetToken.delete_token(token)
        db.session.commit()
        flash('パスワードを更新しました')
        return redirect(url_for('app.login'))
    return render_template('reset_password.html', form=form)

# ユーザーを削除する
@bp.route('/delete')
def delete():
    # 今ログインしているユーザのID取得
    user_id = current_user.get_id()
    # ユーザのインスタンス取得
    user = User.select_user_by_id(user_id)
    # 削除
    with db.session.begin(subtransactions=True):
        user.delete_user(user_id)
    db.session.commit()
    flash('ユーザーを削除しました')
    return redirect(url_for('app.login'))

# ユーザーの情報を編集する
@bp.route('/user', methods=['GET', 'POST'])
@login_required #ログインしていないと見れないデコレータ⇒flask_loginでログインを管理しているためできる
def user():
    form = UserForm(request.form)
    if request.method == 'POST' and form.validate():
        #今ログインしているユーザのインスタンス取得
        user_id = current_user.get_id()
        user = User.select_user_by_id(user_id)
        with db.session.begin(subtransactions=True):
            #名前の変更反映
            user.username = form.username.data
            #メールアドレスの変更反映
            user.email = form.email.data
        db.session.commit()
        flash('ユーザ情報の更新に成功しました')
    return render_template('user.html', form=form)

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm(request.form)
    if request.method == 'POST' and form.validate():
        user = User.select_user_by_id(current_user.get_id())
        password = form.password.data
        with db.session.begin(subtransactions=True):
            user.save_new_password(password)
        db.session.commit()
        flash('パスワードの更新に成功しました')
        return redirect(url_for('app.user'))
    return render_template('change_password.html', form=form)

# 会社名前の検索(将来的には会社名や志望度などで分岐)
@bp.route('/cp_data/<op>', methods=['GET', 'POST'])
@login_required
def cp_data(op):
    form = CompanySearchForm(request.form)
    companies = None
    # フォームからgetメソッドでとってきている
    comname = request.args.get('comname', "", type=str)
    # メソッドをgetにすることで今どのページにいるかわかるらしい(ページネーション機能は未定)
    if comname:
        companies = Company.search_by_comname(comname, current_user.get_id())
    else:
        companies = Company.select_company_by_user_id(current_user.get_id())
    return render_template(
        'cp_data.html', form=form, companies=companies,
        comname=comname
    )
    

@bp.route('/cp_reg', methods=['GET', 'POST'])
@login_required
def cp_reg():
    form = CompanyForm(request.form)
    if request.method == 'POST' and form.validate():
        company = Company(
            from_user_id = current_user.get_id(),
            comname = form.comname.data,
            wishpoint = form.wishpoint.data,
            step = form.step.data,
            scale = form.scale.data,
            startmoney = form.startmoney.data,
            numemploy = form.numemploy.data,
            comment = form.comment.data
        )
        with db.session.begin(subtransactions=True):
            company.create_new_company()
        db.session.commit()
        flash('会社を登録しました。')
        return redirect(url_for('app.cp_reg'))
    return render_template('cp_reg.html', form=form)

@bp.route('/cp_edit/<id>', methods=['GET', 'POST'])
@login_required
def cp_edit(id):
    form = CompanyForm(request.form)
    company = Company.select_company_by_id(id)
    if request.method == 'POST' and form.validate():
        with db.session.begin(subtransactions=True):
            company.comname = form.comname.data
            company.wishpoint = form.wishpoint.data
            company.step = form.step.data
            company.scale = form.scale.data
            company.startmoney = form.startmoney.data
            company.numemploy = form.numemploy.data
            company.comment = form.comment.data
        db.session.commit()
        flash('会社の情報の更新に成功しました')
    return render_template(
        'cp_edit.html', company=company,
        form=form
    )

# 会社の情報削除
@bp.route('/cp_del/<id>')
@login_required
def cp_del(id):
    # ユーザのインスタンス取得
    company = Company.select_company_by_id(id)
    # 削除
    with db.session.begin(subtransactions=True):
        company.delete_company(id)
    db.session.commit()
    flash('会社情報を削除しました')
    return redirect(url_for('app.cp_data'))

# 会社名前の検索(将来的には会社名や志望度などで分岐)
# bp.route('/company_search')
# @login_required
# def company_search():
#     form = CompanySearchForm(request.form)
#     session['url'] = 'app.company_search'
#     companies = None
#     # フォームからgetメソッドでとってきている
#     comname = request.args.get('comname', None, type=str)
#     # メソッドをgetにすることで今どのページにいるかわかるらしい(ページネーション機能は未定)
#     if comname:
#         companies = Company.search_by_comname(comname, current_user.get_id())

#     return render_template('cp_data.html', form=form, companies=companies)

# todoリストのホーム画面
@bp.route('/toDo_home', methods=['GET', 'POST'])
@login_required
def toDo_home():
    # この関数に戻ってくるためにセッションの登録
    # session['url'] = 'app.toDo_home'
    # 完了処理、別画面から完了する場合は別関数を作成する
    form = TaskDoneForm(request.form)
    if request.method == 'POST':
        task = Task.select_task_by_id(form.task_id.data)
        with db.session.begin(subtransactions=True):
            task.update_status()
        db.session.commit()
    tasks = Task.select_active_task_by_user_id(current_user.get_id())
    return render_template(
        'toDo_home.html', tasks=tasks,
        form=form, check=False
    )

# todoリストのホーム画面(sortバージョン)
@bp.route('/toDo_home_sort', methods=['GET', 'POST'])
@login_required
def toDo_home_sort():
    # この関数に戻ってくるためにセッションの登録
    # session['url'] = 'app.toDo_home'
    # 完了処理、別画面から完了する場合は別関数を作成する
    form = TaskDoneForm(request.form)
    if request.method == 'POST':
        task = Task.select_task_by_id(form.task_id.data)
        with db.session.begin(subtransactions=True):
            task.update_status()
        db.session.commit()
    tasks = Task.select_active_task_by_user_id_sort(current_user.get_id())
    return render_template(
        'toDo_home.html', tasks=tasks,
        form=form, check=False
    )

# todoリストの一部表示
@bp.route('/toDo_home2', methods=['GET', 'POST'])
@login_required
def toDo_home2():
    form = TaskDoneForm(request.form)
    if request.method == 'POST':
        task = Task.select_task_by_id(form.task_id.data)
        with db.session.begin(subtransactions=True):
            task.update_status()
        db.session.commit()
    tasks = Task.select_all_task_by_user_id(current_user.get_id())
    return render_template(
        'toDo_home.html', tasks=tasks,
        form=form, check=True
    )

# todoリストの一部表示にソートをかける
@bp.route('/toDo_home2_sort', methods=['GET', 'POST'])
@login_required
def toDo_home2_sort():
    form = TaskDoneForm(request.form)
    if request.method == 'POST':
        task = Task.select_task_by_id(form.task_id.data)
        with db.session.begin(subtransactions=True):
            task.update_status()
        db.session.commit()
    tasks = Task.select_all_task_by_user_id_sort(current_user.get_id())
    return render_template(
        'toDo_home.html', tasks=tasks,
        form=form, check=True
    )

# タスクの追加
@bp.route('/toDo_reg', methods=['GET', 'POST'])
@login_required
def toDo_reg():
    form = toDoForm(request.form)
    if request.method == 'POST' and form.validate():
        task = Task(
            from_user_id=current_user.get_id(), 
            taskname=form.taskname.data, 
            workday=form.workday.data, 
            overday=form.overday.data,
            memo=form.memo.data
        )
        with db.session.begin(subtransactions=True):
            task.create_new_task()
        db.session.commit()
        flash('タスクを登録しました。')
        return redirect(url_for('app.toDo_reg'))
    return render_template('toDo_reg.html', form=form)

@bp.route('/toDo_edit/<id>', methods=['GET', 'POST'])
@login_required
def toDo_edit(id):
    form = toDoForm(request.form)
    task = Task.select_task_by_id(id)
    if request.method == 'POST' and form.validate():
        with db.session.begin(subtransactions=True):
            task.taskname = form.taskname.data
            task.overday = form.overday.data
            task.workday = form.workday.data
            task.memo = form.memo.data
        db.session.commit()
        flash('タスクの情報の更新に成功しました')
    return render_template('toDo_edit.html', task=task,form=form)

# タスクの削除
@bp.route('/toDo_del/<id>')
@login_required
def toDo_del(id):
    return redirect(url_for('app.toDo_home'))

# 会社基本情報の表示
@bp.route('/basic_company')
@login_required
def basic_company():
    basic_companies = Company_basic.select_company_by_user_id(current_user.get_id())
    return render_template(
        'basic_company.html', basic_companies=basic_companies)

# 会社基本情報の登録
@bp.route('/basic_company_reg', methods=['GET', 'POST'])
@login_required
def basic_company_reg():
    form = BasicCompanyForm(request.form)
    if request.method == 'POST' and form.validate():
        company = Company_basic(
            from_user_id = current_user.get_id(),
            comname = form.comname.data,
            occupation = form.occupation.data,
            length = form.length.data,
            scale = form.scale.data,
            comstock = form.comstock.data,
            supplier = form.supplier.data,
            client = form.client.data
        )
        with db.session.begin(subtransactions=True):
            company.create_new_company()
        db.session.commit()
        flash('会社基本情報を登録しました。')
        return redirect(url_for('app.basic_company_reg'))
    return render_template('basic_company_reg.html', form=form)

# 会社基本情報の編集
@bp.route('/basic_company_edit/<id>', methods=['GET', 'POST'])
@login_required
def basic_company_edit(id):
    form = BasicCompanyEditForm(request.form)
    company = Company_basic.select_company_by_id(id)
    if request.method == 'POST' and form.validate():
        with db.session.begin(subtransactions=True):
            company.comname = form.comname.data
            company.occupation = form.occupation.data
            company.length = form.length.data
            company.scale = form.scale.data
            company.comstock = form.comstock.data
            company.supplier = form.supplier.data
            company.client = form.client.data
        db.session.commit()
        flash('会社の情報の更新に成功しました')
    return render_template(
        'basic_company_edit.html', company=company,
        form=form
    )

# 会社の基本情報削除
@bp.route('/basic_company_del/<id>')
@login_required
def basic_company_del(id):
    # ユーザのインスタンス取得
    company = Company_basic.select_company_by_id(id)
    # 削除
    with db.session.begin(subtransactions=True):
        company.delete_company(id)
    db.session.commit()
    flash('会社情報を削除しました')
    return redirect(url_for('app.basic_company'))

# 会社の選考状況の登録
@bp.route('/basic_company_step_reg/<id>', methods=['GET', 'POST'])
@login_required
def basic_company_step_reg(id):
    form = BasicCompanyStepFrom(request.form)
    company = Company_basic.select_company_by_id(id)
    if Company_step.select_step_by_basic_id(id):
        flash("登録済みです。後で仕様変更予定")
    else:
        if request.method == 'POST' and form.validate():
            company_step = Company_step(
                basic_id = company.id,
                comname = company.comname,
                aspiration = form.aspiration.data,
                step = form.step.data,
                status = form.status.data,
                good_comment = form.good_comment.data,
                bad_comment = form.bad_comment.data,
                sonota_comment = form.sonota_comment.data
            )
            with db.session.begin(subtransactions=True):
                company_step.create_new_step() #新規データ登録
                company.update_step_active() #stepの追加確認
            db.session.commit()
            flash('会社選考情報を登録しました。')
            return redirect(url_for('app.basic_company'))
    return render_template(
        'basic_company_step_reg.html', form=form,
        company = company
    )

@bp.route('/basic_company_desc/<id>')
@login_required
def basic_company_desc(id):
    company = Company_basic.select_company_by_id(id)
    company_step = Company_step.select_step_by_basic_id(id)
    return render_template(
        'basic_company_desc.html', company=company,
        company_step=company_step
    )

@bp.route('/basic_company_step_edit/<name>', methods=['GET', 'POST'])
@login_required
def basic_company_step_edit(name):
    form = BasicCompanyStepFrom(request.form)
    #このIDはstepテーブルのID
    company = Company_step.select_step_by_name(name)
    if request.method == 'POST' and form.validate():
        with db.session.begin(subtransactions=True):
            company.aspiration = form.aspiration.data
            company.step = form.step.data
            company.status = form.status.data
            company.good_comment = form.good_comment.data
            company.bad_comment = form.bad_comment.data
            company.sonota_comment = form.sonota_comment.data
        db.session.commit()
        flash('会社の情報の更新に成功しました')
    return render_template(
        'basic_company_step_edit.html', company=company,
        form=form
    )

@bp.route('/calendar', methods=['GET', 'POST'])
@login_required
def calendar():
    if request.method == 'POST':
        #登録
        if int(request.form['decide']) == 0:

            # バリデーションはjavascriptで済ます
            # at_startとat_end: 定義
            if 'allDayCheck' in request.form:
                allDayCheck = True
                at_start = datetime.datetime.strptime(request.form['at_start'], "%Y-%m-%d")
                at_end = datetime.datetime.strptime(request.form['at_end'], "%Y-%m-%d")
                at_end += datetime.timedelta(days=1);
            else:
                allDayCheck = False
                # 場合によってフォーマットが変わる困ったエラー：事前にフォーマットを把握したいが、、
                try:
                    at_start = datetime.datetime.strptime(request.form['at_start_hm'], "%Y-%m-%dT%H:%M")
                except:
                    at_start = datetime.datetime.strptime(request.form['at_start_hm'], "%Y-%m-%dT%H:%M:%S")
                try:
                    at_end = datetime.datetime.strptime(request.form['at_end_hm'], "%Y-%m-%dT%H:%M")
                except:
                    at_end = datetime.datetime.strptime(request.form['at_end_hm'], "%Y-%m-%dT%H:%M:%S")


            if 'comment' in request.form:
                comment = request.form['comment']
            else:
                comment = ""

            #色を入力するところ
            eventcolor = request.form['colorselect']

            event = EventSec(
                basic_id = current_user.get_id(),
                title = request.form['title'],
                allDayCheck = allDayCheck,
                at_start = at_start,
                at_end = at_end,
                comment = comment,
                eventcolor = eventcolor,
                is_active = True
            )
            with db.session.begin(subtransactions=True):
                event.create_new_event()
            db.session.commit()
            flash('イベントを登録しました')
            # print(request.form['title'], allDayCheck, at_start, at_end, comment)
            return redirect(url_for('app.calendar'))

        #更新
        elif int(request.form['decide']) == 1:
            # IDで検索
            if int(request.form['tableNum']) == 1:
                event = Event.select_event_by_id(current_user.get_id(), int(request.form['id']))
            elif int(request.form['tableNum']) == 2:
                event = EventSec.select_event_by_id(current_user.get_id(), int(request.form['id']))
                
            if 'allDayCheck' in request.form:
                allDayCheck = True
                at_start = datetime.datetime.strptime(request.form['at_start'], "%Y-%m-%d")
                at_end = datetime.datetime.strptime(request.form['at_end'], "%Y-%m-%d")
                at_end += datetime.timedelta(days=1);
            else:
                allDayCheck = False
                # 場合によってフォーマットが変わる困ったエラー：事前にフォーマットを把握したいが、、
                try:
                    at_start = datetime.datetime.strptime(request.form['at_start_hm'], "%Y-%m-%dT%H:%M")
                except:
                    at_start = datetime.datetime.strptime(request.form['at_start_hm'], "%Y-%m-%dT%H:%M:%S")
                try:
                    at_end = datetime.datetime.strptime(request.form['at_end_hm'], "%Y-%m-%dT%H:%M")
                except:
                    at_end = datetime.datetime.strptime(request.form['at_end_hm'], "%Y-%m-%dT%H:%M:%S")
            if int(request.form['tableNum']) == 1:
                with db.session.begin(subtransactions=True):
                    event.title = request.form['title']
                    event.allDayCheck = allDayCheck
                    event.at_start = at_start
                    event.at_end = at_end
                    event.comment = request.form['comment']
                db.session.commit()
            elif int(request.form['tableNum']) == 2:
                with db.session.begin(subtransactions=True):
                    event.title = request.form['title']
                    event.allDayCheck = allDayCheck
                    event.at_start = at_start
                    event.at_end = at_end
                    event.comment = request.form['comment']
                    event.eventcolor = request.form['colorselect']
                db.session.commit()
            flash('イベントの情報の更新に成功しました')
            return redirect(url_for('app.calendar'))
    return render_template('myCalendar.html')

# ドロップイベント作成
@bp.route('/dropEvents', methods=['POST'])
@login_required
def dropEvents():
    if request.method == 'POST':
        #データの整形
        #booleanではなく、文字列で帰ってくる
        if request.form['allDay'] == 'true':
            at_start = datetime.datetime.strptime(request.form['at_start'], "%Y-%m-%d")
            at_end = datetime.datetime.strptime(request.form['at_end'], "%Y-%m-%d")
            at_end += datetime.timedelta(days=1)
        else:
            # 場合によってフォーマットが変わる困ったエラー：事前にフォーマットを把握したいが、、
            try:
                at_start = datetime.datetime.strptime(request.form['at_start'], "%Y-%m-%dT%H:%M")
            except:
                at_start = datetime.datetime.strptime(request.form['at_start'], "%Y-%m-%dT%H:%M:%S")
            try:
                at_end = datetime.datetime.strptime(request.form['at_end'], "%Y-%m-%dT%H:%M")
            except:
                at_end = datetime.datetime.strptime(request.form['at_end'], "%Y-%m-%dT%H:%M:%S")
        # 更新
        if int(request.form['tableNum']) == 1:
            #既存のイベント情報取得
            event = Event.select_event_by_id(current_user.get_id(), int(request.form['id']))
            with db.session.begin(subtransactions=True):
                event.at_start = at_start
                event.at_end = at_end
            db.session.commit()
        elif int(request.form['tableNum']) == 2:
            #既存のイベント情報取得
            event = EventSec.select_event_by_id(current_user.get_id(), int(request.form['id']))
            with db.session.begin(subtransactions=True):
                event.at_start = at_start
                event.at_end = at_end
            db.session.commit()
    return "OK"

@bp.route('/eventList', methods=['GET', 'POST'])
@login_required
def eventList():
    # JSONの解析
    list = []
    if request.method == 'POST':
        datas = request.get_json()
        # print(datas)
        # フォームでバリデーション
        calendarForm = CalendarForm(request.form)
        if calendarForm.validate() == False:
            pass

        # リクエストの取得
        start_date = datas["start_date"]
        end_date = datas["end_date"]
        # start_date = request.args.get('start', '')
        # end_date = request.args.get('end', '')
        # print(end_date)
        # print(start_date)

        # 日付に変換。JavaScriptのタイムスタンプはミリ秒なので秒に変換
        formatted_start_date = time.strftime(
            "%Y-%m-%d", time.localtime(start_date / 1000))
        formatted_end_date = time.strftime(
            "%Y-%m-%d", time.localtime(end_date / 1000))

        # FullCalendarの表示範囲のみ表示
        events = Event.select_events(current_user.get_id(), formatted_start_date, formatted_end_date)
        # events = Event.select_events(current_user.get_id(), start_date, end_date)

        # fullcalendarのため配列で返却
        #残りの変数: backgroundColor, borderColor, editable
        #前のテーブル
        for event in events:
            list.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "allDay": event.allDayCheck,
                    "start": event.at_start.strftime('%Y-%m-%dT%H:%M:%S'),
                    "end": event.at_end.strftime('%Y-%m-%dT%H:%M:%S'),
                    "description": event.comment, #イベントの詳細
                    "extendedProps": {
                        "tableNum": '1'
                    },
                }
            )
        
        #新しいテーブル
        events = EventSec.select_events(current_user.get_id(), formatted_start_date, formatted_end_date)

        for event in events:
            #カラーナンバー: カラーの初期値を設定するためだがJSの書き方次第で回避したいところ
            if event.eventcolor == "primary":
                colornum = 0
            elif event.eventcolor == "blue":
                colornum = 1
            elif event.eventcolor == "red":
                colornum = 2
            elif event.eventcolor == "green":
                colornum = 3

            list.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "allDay": event.allDayCheck,
                    "start": event.at_start.strftime('%Y-%m-%dT%H:%M:%S'),
                    "end": event.at_end.strftime('%Y-%m-%dT%H:%M:%S'),
                    "description": event.comment, #イベントの詳細
                    "color": event.eventcolor,
                    #未定義オブジェクトの設定方法
                    "extendedProps": {
                        "tableNum": '2', #テーブル番号
                        "colorNum": colornum
                    },
                }
            )
        # print(formatted_end_date, formatted_start_date)
        # print(list)
    # if len(list):
        # print('こっち！')
    return jsonify(list)
    # else:
    #     return jsonify([
    #     {
    #         "title": 'Business Lunch',
    #         "start": datetime.datetime(2022, 4, 3, 13, 0).strftime('%Y-%m-%dT%H:%M:%S'),
    #         # "start": '2022-04-03T13:00:00',
            
    #     },
    #     {
    #         "title": 'Business Lunch2',
    #         "start": '2022-04-04T13:00:00',
    #     }
    #     ])
            
@bp.route('/calendar_del', methods=['GET', 'POST'])
@login_required
def calendar_del():
    if request.method == 'POST':
        if int(request.form['tableNum_del']) == 1:
            # IDで検索
            event = Event.select_event_by_id(current_user.get_id(), int(request.form['d_id']))
            with db.session.begin(subtransactions=True):
                event.delete_event(int(request.form['d_id']))
            db.session.commit()

        elif int(request.form['tableNum_del']) == 2:
            # IDで検索
            event = EventSec.select_event_by_id(current_user.get_id(), int(request.form['d_id']))
            with db.session.begin(subtransactions=True):
                event.delete_event(int(request.form['d_id']))
            db.session.commit()
        
        flash('イベントのデータを削除しました')
    return redirect(url_for('app.calendar'))

# csvのユーザーファイルの読み込み
@bp.route('/user_csv')
def user_csv():
    # 定数の設定
    FILE_NAME = "user_test.csv"
    # csvファイル取得
    import csv
    FILE_NAME = f"flaskr/csv/{FILE_NAME}"
    csv_file = open(FILE_NAME, "r", encoding="ms932", errors="", newline="" )
    f = csv.reader(csv_file, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"', skipinitialspace=True)
    header = next(f)
    print(header)
    for row in f:
        user = User(
            email = row[2],
            username = row[1]
        )
        # user.id = row[0]
        user.password = row[3]
        if row[4] == "TRUE":
            user.is_active = 1
        else:
            user.is_active = 0

        #ユーザー名とメールアドレスを登録
        with db.session.begin(subtransactions=True):
            user.create_new_user()
        db.session.commit()
    return render_template("csv.html")

# taskファイルの読み込み
@bp.route('/task_csv')
@login_required
def task_csv():
    # 定数の設定
    FILE_NAME = "task.csv"
    # csvファイル取得
    import csv
    FILE_NAME = f"flaskr/csv/{FILE_NAME}"
    csv_file = open(FILE_NAME, "r", errors="", encoding="utf-8", newline="" )
    f = csv.reader(csv_file, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"', skipinitialspace=True)
    header = next(f)
    print(header)
    for row in f:
        task = Task(
            from_user_id=current_user.get_id(), 
            taskname=row[2], 
            workday=datetime.datetime.strptime(row[3], '%Y-%m-%d %H:%M:00'), 
            overday=datetime.datetime.strptime(row[4], '%Y-%m-%d %H:%M:00'), 
            memo=row[5]
        )
        if row[6] == "TRUE":
            user.is_active = 1
        else:
            user.is_active = 0

        #ユーザー名とメールアドレスを登録
        with db.session.begin(subtransactions=True):
            task.create_new_task()
        db.session.commit()
    return render_template("csv.html")

@bp.route('/basic_company_number')
@login_required
def basic_company_number():
    # ここで取得するテーブルはcompany_numberとcompany_basicを左結合して検索
    basic_companies = Company_basic.select_company_by_basic_and_number(current_user.get_id())
    age_companies = Company_basic.select_company_by_user_id(current_user.get_id())
    ages = [(datetime.datetime.today() - basic_company.length).days//365 for basic_company in age_companies]
    return render_template('basic_company_number.html'
    , basic_companies=basic_companies, ages = ages)

@bp.route('/basic_company_number_edit/<comname>', methods=['GET', 'POST'])
@login_required
def basic_company_number_edit(comname):
    form = BasicCompanyNumberFrom(request.form)
    company = Company_number.select_company_by_comname(comname)
    if company:
        comment = company.comment # 謎のバグ回避(jinjaとJSの相性の悪さを回避)
        if request.method == 'POST' and form.validate():
            with db.session.begin(subtransactions=True):
                company.capital = form.capital.data
                company.employee = form.employee.data
                company.turnover = form.turnover.data
                company.start_salary = form.start_salary.data
                company.average_salary = form.average_salary.data
                company.comment = form.comment.data
            db.session.commit()
            flash('会社選考情報を更新しました。')
            
        return render_template(
            'basic_company_number_edit.html', form=form,
            company = company , comment = comment
        )
    else:
        company = Company_basic.select_company_by_comname(comname)
        comment = "" # 謎のバグ回避(jinjaとJSの相性の悪さを回避)
        age = datetime.datetime.today() - company.length
        age = age.days//365
        if request.method == 'POST' and form.validate():
                company_number = Company_number(
                    basic_id = company.id,
                    from_user_id=current_user.get_id(),
                    comname = company.comname,
                    age = age,
                    capital = form.capital.data,
                    employee = form.employee.data,
                    turnover = form.turnover.data,
                    start_salary = form.start_salary.data,
                    average_salary = form.average_salary.data,
                    comment = form.comment.data
                )
                with db.session.begin(subtransactions=True):
                    company_number.create_new_number() #新規データ登録
                db.session.commit()
                flash('会社選考情報を登録しました。')
                return redirect(url_for('app.basic_company'))
        return render_template(
            'basic_company_number_edit.html', form=form,
            company = company, comment = comment
        )