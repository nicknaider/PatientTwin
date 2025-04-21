import os
import sys
import logging
import secrets
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, abort, session,
    jsonify, make_response, send_file
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from logging.handlers import RotatingFileHandler
from io import BytesIO
import pandas as pd

app = Flask(__name__)
app.secret_key = os.urandom(24)

handler = RotatingFileHandler('patient_twin.log', maxBytes=1_000_000, backupCount=3)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

db_file = os.path.join(base_dir, 'patient_twin.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_file}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, авторизуйтесь для доступа к этому разделу.'
login_manager.login_message_category = 'warning'

class User(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role     = db.Column(db.String(10), nullable=False, default='user')

class Patient(db.Model):
    id                = db.Column(db.Integer, primary_key=True)
    patient_name      = db.Column(db.String(120), nullable=False)
    age               = db.Column(db.Integer, nullable=True)
    disease           = db.Column(db.String(80), nullable=False)
    frequency         = db.Column(db.Integer, nullable=False)
    health_indicators = db.Column(db.String(200), nullable=False)
    readings          = db.relationship('Reading', backref='patient', lazy=True)

class Reading(db.Model):
    id                  = db.Column(db.Integer, primary_key=True)
    patient_id          = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    patient_name        = db.Column(db.String(120), nullable=False)
    age                 = db.Column(db.Integer, nullable=True)
    temperature         = db.Column(db.Float, nullable=True)
    systolic            = db.Column(db.Integer, nullable=True)
    diastolic           = db.Column(db.Integer, nullable=True)
    overall_condition   = db.Column(db.String(200), nullable=True)
    cough               = db.Column(db.String(10), nullable=True)
    sore_throat         = db.Column(db.Boolean, nullable=True)
    shortness_of_breath = db.Column(db.Boolean, nullable=True)
    chest_pain          = db.Column(db.Boolean, nullable=True)
    timestamp           = db.Column(db.DateTime, nullable=False, default=datetime.now)

class ReferenceRange(db.Model):
    __tablename__ = 'reference_range'
    id        = db.Column(db.Integer, primary_key=True)
    indicator = db.Column(db.String(50), nullable=False) 
    age_min   = db.Column(db.Integer, nullable=False)
    age_max   = db.Column(db.Integer, nullable=False)
    value_min = db.Column(db.Float, nullable=False)
    value_max = db.Column(db.Float, nullable=False)

@app.template_filter('fmt_dt')
def format_datetime(value, fmt='%Y-%m-%d %H:%M'):
    if value is None:
        return ''
    return value.strftime(fmt)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def analyze_reading(reading):
    alerts = []
    age = reading.age or 0
    if reading.temperature is not None:
        refs = ReferenceRange.query.filter_by(indicator='temperature') \
               .filter(ReferenceRange.age_min <= age, ReferenceRange.age_max >= age).all()
        if refs:
            if not any(r.value_min <= reading.temperature <= r.value_max for r in refs):
                alerts.append("Температура выше нормы")
        else:
            if reading.temperature > 37.0:
                alerts.append("Температура выше нормы")

    if reading.systolic is not None:
        if reading.systolic > 140:
            alerts.append("Систолическое давление > 140")

    if reading.diastolic is not None:
        if reading.diastolic > 90:
            alerts.append("Диастолическое давление > 90")

    if reading.chest_pain:
        alerts.append("Боль в груди")
    if reading.sore_throat:
        alerts.append("Боль в горле")
    if reading.shortness_of_breath:
        alerts.append("Одышка")

    return alerts

@app.errorhandler(404)
def not_found(e): return render_template('404.html'), 404
@app.errorhandler(500)
def server_error(e): return render_template('500.html'), 500
@app.errorhandler(403)
def forbidden(e): return render_template('403.html'), 403

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user, remember='remember' in request.form)
            return redirect(request.args.get('next') or url_for('home'))
        flash("Неверный логин или пароль", 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/change_password', methods=['GET','POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old = request.form['old_password']
        new = request.form['new_password']
        conf = request.form['confirm_password']
        if not check_password_hash(current_user.password, old):
            flash("Старый пароль неверен",'danger')
        elif new != conf:
            flash("Новые пароли не совпадают",'danger')
        else:
            current_user.password = generate_password_hash(new)
            db.session.commit()
            flash("Пароль изменён",'success')
            return redirect(url_for('home'))
    return render_template('change_password.html')

@app.route('/admin/new_doctor', methods=['GET','POST'])
@login_required
def new_doctor():
    if current_user.role != 'admin':
        abort(403)
    session.setdefault('new_docs', [])
    if request.method == 'POST':
        uname = request.form['username'].strip()
        if not User.query.filter_by(username=uname).first():
            pwd = secrets.token_urlsafe(8)
            doc = User(username=uname, password=generate_password_hash(pwd), role='user')
            db.session.add(doc); db.session.commit()
            session['new_docs'].append({'username':uname,'password':pwd})
            flash(f"Врач {uname} создан, пароль: {pwd}",'success')
        else:
            flash("Такой врач уже существует",'danger')
        return redirect(url_for('new_doctor'))
    return render_template('new_doctor.html', created_doctors=session['new_docs'])

@app.route('/admin/references', methods=['GET','POST'])
@login_required
def references():
    if current_user.role != 'admin':
        abort(403)
    if request.method == 'POST':
        ref = ReferenceRange(
            indicator=request.form['indicator'],
            age_min=int(request.form['age_min']),
            age_max=int(request.form['age_max']),
            value_min=float(request.form['value_min']),
            value_max=float(request.form['value_max'])
        )
        db.session.add(ref); db.session.commit()
        flash("Референс добавлен",'success')
        return redirect(url_for('references'))
    refs = ReferenceRange.query.order_by(ReferenceRange.indicator, ReferenceRange.age_min).all()
    return render_template('references.html', refs=refs, indicators=['temperature','systolic','diastolic'])

@app.route('/admin/references/<int:ref_id>/delete', methods=['POST'])
@login_required
def delete_reference(ref_id):
    if current_user.role != 'admin':
        abort(403)
    r = ReferenceRange.query.get_or_404(ref_id)
    db.session.delete(r); db.session.commit()
    flash("Референс удалён",'info')
    return redirect(url_for('references'))

@app.route('/')
@login_required
def home():
    return render_template('home.html')

@app.route('/schedule', methods=['GET','POST'])
@login_required
def schedule():
    if request.method == 'POST':
        name = request.form['patient_name'].strip()
        age = int(request.form['age']) if request.form['age'].isdigit() else None
        freq = int(request.form['frequency']) if request.form['frequency'].isdigit() else 0
        p = Patient(
            patient_name=name,
            age=age,
            disease=request.form['disease'].strip(),
            frequency=freq,
            health_indicators=request.form['health_indicators'].strip()
        )
        db.session.add(p); db.session.commit()
        flash("Пациент добавлен",'success')
        return redirect(url_for('schedule'))
    return render_template('schedule.html', patients=Patient.query.all())

@app.route('/delete_patient/<int:patient_id>', methods=['POST'])
@login_required
def delete_patient(patient_id):
    p = Patient.query.get_or_404(patient_id)
    Reading.query.filter_by(patient_id=p.id).delete()
    db.session.delete(p); db.session.commit()
    flash("Пациент удалён",'info')
    return redirect(url_for('schedule'))

@app.route('/readings', methods=['GET','POST'])
@login_required
def readings_view():
    if request.method == 'POST':
        pid = request.form['patient_id']
        patient = db.session.get(Patient, pid)
        if not patient:
            flash("Пациент не найден",'danger')
            return redirect(url_for('readings_view'))
        def to_f(v):
            try: return float(v)
            except: return None
        def to_i(v):
            try: return int(v)
            except: return None
        r = Reading(
            patient_id=patient.id,
            patient_name=patient.patient_name,
            age=patient.age,
            temperature=to_f(request.form.get('temperature','')),
            systolic=to_i(request.form.get('systolic','')),
            diastolic=to_i(request.form.get('diastolic','')),
            overall_condition=request.form.get('overall_condition','').strip(),
            cough=request.form.get('cough','нет').strip(),
            chest_pain=request.form.get('chest_pain')=='yes',
            sore_throat=request.form.get('sore_throat')=='yes',
            shortness_of_breath=request.form.get('shortness_of_breath')=='yes'
        )
        db.session.add(r); db.session.commit()
        flash("Измерение сохранено",'success')
        return redirect(url_for('readings_view'))
    readings = Reading.query.order_by(Reading.timestamp.desc()).all()
    for rec in readings:
        rec.alerts = analyze_reading(rec)
    return render_template('readings.html', readings=readings, patients=Patient.query.all())

@app.route('/delete_reading/<int:reading_id>', methods=['POST'])
@login_required
def delete_reading(reading_id):
    r = Reading.query.get_or_404(reading_id)
    db.session.delete(r); db.session.commit()
    flash("Измерение удалено",'info')
    return redirect(url_for('readings_view'))

@app.route('/reports')
@login_required
def reports():
    search = request.args.get('search','').strip()
    start  = request.args.get('start_date','').strip()
    end    = request.args.get('end_date','').strip()
    sf     = request.args.get('sort_field','default')
    so     = request.args.get('sort_order','desc')

    q = Reading.query
    if search:
        q = q.filter(func.lower(Reading.patient_name).like(f"%{search.lower()}%"))
    if start:
        q = q.filter(Reading.timestamp >= f"{start} 00:00:00")
    if end:
        q = q.filter(Reading.timestamp <= f"{end} 23:59:59")
    all_r = q.order_by(Reading.timestamp.desc()).all()

    groups = {}
    for rec in all_r:
        groups.setdefault(rec.patient_name, []).append(rec)
    patient_groups = [(name, recs[0], recs) for name, recs in groups.items()]

    if sf != 'default' and sf in ['patient_name','temperature','systolic','diastolic']:
        keyf = {
            'patient_name': lambda r: r.patient_name.lower(),
            'temperature':  lambda r: r.temperature or 0,
            'systolic':     lambda r: r.systolic or 0,
            'diastolic':    lambda r: r.diastolic or 0
        }[sf]
        patient_groups.sort(key=lambda g: keyf(g[1]), reverse=(so=='desc'))
    else:
        patient_groups.sort(key=lambda g: g[1].timestamp, reverse=True)

    for _, latest, hist in patient_groups:
        latest.alerts = analyze_reading(latest)
        for rec in hist:
            rec.alerts = analyze_reading(rec)

    return render_template(
        'reports.html',
        groups=patient_groups,
        search=search,
        start_date=start,
        end_date=end,
        sort_field=sf,
        sort_order=so
    )

@app.route('/reports/history/<int:patient_id>')
@login_required
def report_history(patient_id):
    readings = Reading.query.filter_by(patient_id=patient_id).order_by(Reading.timestamp).all()
    if not readings:
        abort(404, description="Нет данных по этому пациенту")
    data = [{
        'timestamp': r.timestamp.isoformat(),
        'temperature': r.temperature,
        'systolic': r.systolic,
        'diastolic': r.diastolic
    } for r in readings]
    return jsonify(data)

@app.route('/reports/export/<int:patient_id>')
@login_required
def export_report(patient_id):
    fmt = request.args.get('format','csv').lower()
    readings = Reading.query.filter_by(patient_id=patient_id).order_by(Reading.timestamp).all()
    if not readings:
        abort(404, description="Нет данных по этому пациенту")
    rows = []
    for r in readings:
        rows.append({
            'Дата':           r.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'Температура':    r.temperature,
            'Систолическое':  r.systolic,
            'Диастолическое': r.diastolic,
            'Самочувствие':   r.overall_condition,
            'Кашель':         r.cough,
            'Горло':          'Да' if r.sore_throat else 'Нет',
            'Одышка':         'Да' if r.shortness_of_breath else 'Нет',
            'Грудь':          'Да' if r.chest_pain else 'Нет',
            'Предупреждения': '; '.join(r.alerts) if hasattr(r, 'alerts') and r.alerts else ''
        })
    df = pd.DataFrame(rows)
    if fmt == 'excel':
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Отчет')
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name=f'report_{patient_id}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        csv_data = df.to_csv(index=False)
        resp = make_response(csv_data)
        resp.headers['Content-Disposition'] = f'attachment; filename=report_{patient_id}.csv'
        resp.mimetype = 'text/csv'
        return resp

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            admin = User(
                username='admin',
                password=generate_password_hash('admin'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin created: admin / admin")
    app.logger.info("Starting application")
    app.run(debug=False)
