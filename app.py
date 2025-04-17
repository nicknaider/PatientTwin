from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func

app = Flask(__name__)

# Подключение к SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patient_twin.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель пациента
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    disease = db.Column(db.String(80), nullable=False)
    frequency = db.Column(db.Integer, nullable=False)
    health_indicators = db.Column(db.String(200), nullable=False)
    readings = db.relationship('Reading', backref='patient', lazy=True)

# Модель измерения
class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    patient_name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    temperature = db.Column(db.Float, nullable=True)
    systolic = db.Column(db.Integer, nullable=True)
    diastolic = db.Column(db.Integer, nullable=True)
    overall_condition = db.Column(db.String(200), nullable=True)
    cough = db.Column(db.String(10), nullable=True)
    sore_throat = db.Column(db.Boolean, nullable=True)
    shortness_of_breath = db.Column(db.Boolean, nullable=True)
    chest_pain = db.Column(db.Boolean, nullable=True)
    timestamp = db.Column(db.String(80), nullable=False)

# Функция генерации предупреждений
def analyze_reading(reading):
    alerts = []
    if reading.temperature is not None and reading.temperature > 37.0:
        alerts.append("Температура выше нормы")
    if reading.systolic is not None and reading.systolic > 140:
        alerts.append("Систолическое давление > 140")
    if reading.diastolic is not None and reading.diastolic > 90:
        alerts.append("Диастолическое давление > 90")
    if reading.chest_pain:
        alerts.append("Боль в груди")
    if reading.sore_throat:
        alerts.append("Боль в горле")
    if reading.shortness_of_breath:
        alerts.append("Одышка")
    return alerts

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if request.method == 'POST':
        patient_name = request.form.get('patient_name', '').strip()
        age_str = request.form.get('age', '').strip()
        disease = request.form.get('disease', '').strip()
        frequency_str = request.form.get('frequency', '0').strip()
        health_indicators = request.form.get('health_indicators', '').strip()

        try:
            age = int(age_str)
        except ValueError:
            age = None
        try:
            frequency = int(frequency_str)
        except ValueError:
            frequency = 0

        new_patient = Patient(
            patient_name=patient_name,
            age=age,
            disease=disease,
            frequency=frequency,
            health_indicators=health_indicators
        )
        db.session.add(new_patient)
        db.session.commit()
        return redirect(url_for('schedule'))
    patients = Patient.query.all()
    return render_template('schedule.html', patients=patients)

@app.route('/readings', methods=['GET', 'POST'])
def readings_view():
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        patient = Patient.query.get(patient_id)
        if not patient:
            return "Пациент не найден", 400

        try:
            temperature = float(request.form.get('temperature', '0.0'))
        except ValueError:
            temperature = None
        try:
            systolic = int(request.form.get('systolic', '0'))
        except ValueError:
            systolic = None
        try:
            diastolic = int(request.form.get('diastolic', '0'))
        except ValueError:
            diastolic = None

        chest_pain = (request.form.get('chest_pain') == 'yes')
        sore_throat = (request.form.get('sore_throat') == 'yes')
        cough = request.form.get('cough', 'нет').strip()
        shortness_of_breath = (request.form.get('shortness_of_breath') == 'yes')
        overall_condition = request.form.get('overall_condition', '').strip()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_reading = Reading(
            patient_id=patient.id,
            patient_name=patient.patient_name,
            age=patient.age,
            temperature=temperature,
            systolic=systolic,
            diastolic=diastolic,
            chest_pain=chest_pain,
            sore_throat=sore_throat,
            cough=cough,
            shortness_of_breath=shortness_of_breath,
            overall_condition=overall_condition,
            timestamp=timestamp
        )
        db.session.add(new_reading)
        db.session.commit()
        return redirect(url_for('readings_view'))
    readings = Reading.query.order_by(Reading.timestamp.desc()).all()
    for r in readings:
        r.alerts = analyze_reading(r)
    patients = Patient.query.all()
    return render_template('readings.html', readings=readings, patients=patients)

@app.route('/delete_reading/<int:reading_id>', methods=['POST'])
def delete_reading(reading_id):
    reading = Reading.query.get_or_404(reading_id)
    db.session.delete(reading)
    db.session.commit()
    return redirect(url_for('readings_view'))

@app.route('/reports')
def reports():
    search_query = request.args.get('search', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    sort_field = request.args.get('sort_field', 'default')
    sort_order = request.args.get('sort_order', 'desc')

    query = Reading.query
    if search_query:
        # Используем простое приведение к нижнему регистру для фильтрации
        query = query.filter(func.lower(Reading.patient_name).like(f"%{search_query.lower()}%"))
    if start_date:
        query = query.filter(Reading.timestamp >= f"{start_date} 00:00:00")
    if end_date:
        query = query.filter(Reading.timestamp <= f"{end_date} 23:59:59")
    all_readings = query.order_by(Reading.timestamp.desc()).all()

    groups = {}
    for r in all_readings:
        groups.setdefault(r.patient_name, []).append(r)
    patient_groups = []
    for name, rec_list in groups.items():
        latest = rec_list[0]
        patient_groups.append((name, latest, rec_list))
    
    if sort_field == 'default':
        patient_groups.sort(key=lambda g: g[1].timestamp, reverse=True)
    else:
        sort_options = {
            'patient_name': lambda m: m.patient_name.lower() if m.patient_name else "",
            'temperature': lambda m: m.temperature if m.temperature is not None else (
                -float('inf') if sort_order=='asc' else float('inf')
            ),
            'systolic': lambda m: m.systolic if m.systolic is not None else (
                -float('inf') if sort_order=='asc' else float('inf')
            ),
            'diastolic': lambda m: m.diastolic if m.diastolic is not None else (
                -float('inf') if sort_order=='asc' else float('inf')
            ),
            'timestamp': lambda m: m.timestamp
        }
        if sort_field in sort_options:
            key_func = sort_options[sort_field]
            reverse = (sort_order == 'desc')
            patient_groups.sort(key=lambda grp: key_func(grp[1]), reverse=reverse)
        else:
            patient_groups.sort(key=lambda g: g[1].timestamp, reverse=True)
    
    for group in patient_groups:
        group[1].alerts = analyze_reading(group[1])
        for r in group[2]:
            r.alerts = analyze_reading(r)
    
    return render_template('reports.html',
                           groups=patient_groups,
                           search=search_query,
                           start_date=start_date,
                           end_date=end_date,
                           sort_field=sort_field,
                           sort_order=sort_order)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
