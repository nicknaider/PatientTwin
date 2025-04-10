from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Настройка подключения к SQLite. Файл базы "patient_twin.db" создастся в корне проекта.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patient_twin.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель пациента (для планирования мониторинга)
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(80), nullable=False)
    disease = db.Column(db.String(80), nullable=False)
    frequency = db.Column(db.Integer, nullable=False)
    health_indicators = db.Column(db.String(200), nullable=False)

# Модель для структурированных измерений
class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(80), nullable=False)
    temperature = db.Column(db.Float, nullable=True)    # Температура (°C)
    systolic = db.Column(db.Integer, nullable=True)       # Систолическое давление (мм рт. ст.)
    diastolic = db.Column(db.Integer, nullable=True)      # Диастолическое давление (мм рт. ст.)
    chest_pain = db.Column(db.Boolean, nullable=True)     # Боль в груди (True/False)
    timestamp = db.Column(db.String(80), nullable=False)    # Дата-время измерения

# Функция для анализа структурированного измерения
def analyze_structured_reading(reading):
    alerts = []
    if reading.temperature is not None and reading.temperature > 37.0:
        alerts.append("Высокая т.")
    if reading.systolic is not None and reading.systolic > 140:
        alerts.append("Сист. >140")
    if reading.diastolic is not None and reading.diastolic > 90:
        alerts.append("Диаст. >90")
    if reading.chest_pain:
        alerts.append("Боль в груди")
    return alerts

@app.route('/')
def home():
    return render_template("home.html")

# Окно планирования мониторинга
@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if request.method == 'POST':
        patient_name = request.form.get('patient_name')
        disease = request.form.get('disease')
        frequency = request.form.get('frequency')
        health_indicators = request.form.get('health_indicators')
        
        new_patient = Patient(
            patient_name=patient_name,
            disease=disease,
            frequency=int(frequency),
            health_indicators=health_indicators
        )
        db.session.add(new_patient)
        db.session.commit()
        return redirect(url_for('schedule'))
    
    patients = Patient.query.all()
    return render_template('schedule.html', patients=patients)

# Страница для ввода структурированных измерений
@app.route('/readings', methods=['GET', 'POST'])
def readings_view():
    if request.method == 'POST':
        patient_name = request.form.get('patient_name')
        try:
            temperature = float(request.form.get('temperature'))
        except (ValueError, TypeError):
            temperature = None
        try:
            systolic = int(request.form.get('systolic'))
        except (ValueError, TypeError):
            systolic = None
        try:
            diastolic = int(request.form.get('diastolic'))
        except (ValueError, TypeError):
            diastolic = None
        chest_pain_val = request.form.get('chest_pain')
        chest_pain = True if chest_pain_val == 'yes' else False

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_reading = Reading(
            patient_name=patient_name,
            temperature=temperature,
            systolic=systolic,
            diastolic=diastolic,
            chest_pain=chest_pain,
            timestamp=timestamp
        )
        db.session.add(new_reading)
        db.session.commit()
        return redirect(url_for('readings_view'))
    
    readings = Reading.query.all()
    for r in readings:
        r.alerts = analyze_structured_reading(r)
    return render_template("readings.html", readings=readings)

# Страница отчётов
@app.route('/reports')
def reports():
    readings = Reading.query.all()
    for r in readings:
        r.alerts = analyze_structured_reading(r)
    return render_template("reports.html", readings=readings)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
