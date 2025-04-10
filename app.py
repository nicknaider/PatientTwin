from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Настройка подключения к базе данных SQLite.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patient_twin.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель для пациента (Модуль A)
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(80), nullable=False)
    disease = db.Column(db.String(80), nullable=False)
    frequency = db.Column(db.Integer, nullable=False)
    health_indicators = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<Patient {self.patient_name}>"

# Обновлённая модель для структурированных измерений (Модуль B)
class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(80), nullable=False)
    # Структурированные параметры:
    temperature = db.Column(db.Float, nullable=True)    # температура (°C)
    systolic = db.Column(db.Integer, nullable=True)       # систолическое давление (мм рт. ст.)
    diastolic = db.Column(db.Integer, nullable=True)      # диастолическое давление (мм рт. ст.)
    chest_pain = db.Column(db.Boolean, nullable=True)       # наличие боли в груди (True/False)
    timestamp = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f"<Reading {self.patient_name} at {self.timestamp}>"

# Функция для анализа структурированного измерения
def analyze_structured_reading(reading):
    alerts = []
    # Анализ температуры
    if reading.temperature is not None and reading.temperature > 37.0:
        alerts.append("Высокая температура")
    # Анализ систолического давления
    if reading.systolic is not None and reading.systolic > 140:
        alerts.append("Высокое систолическое давление")
    # Анализ диастолического давления
    if reading.diastolic is not None and reading.diastolic > 90:
        alerts.append("Высокое диастолическое давление")
    # Анализ симптома с вопросом "Да/Нет" (например, боль в груди)
    if reading.chest_pain:
        alerts.append("Боль в груди")
    return alerts

@app.route('/')
def home():
    return 'Добро пожаловать в модуль А: Базовая автоматизация бизнес-процесса'

# Маршрут для планирования мониторинга (Модуль A)
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

# Новый маршрут для ввода структурированных измерений (Модуль B)
@app.route('/structured_readings', methods=['GET', 'POST'])
def structured_readings():
    if request.method == 'POST':
        patient_name = request.form.get('patient_name')
        # Получение числовых значений; преобразуем в нужный тип, при ошибке записываем None
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
        chest_pain_value = request.form.get('chest_pain')  # должно быть "yes" или "no"
        chest_pain = True if chest_pain_value == "yes" else False

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

        return redirect(url_for('structured_readings'))

    readings = Reading.query.all()
    # Для каждого измерения определим предупреждения
    for r in readings:
        r.alerts = analyze_structured_reading(r)
    return render_template("structured_readings.html", readings=readings)

if __name__ == '__main__':
    with app.app_context():
        # При первом запуске создаются таблицы в базе (если файла patient_twin.db ещё нет)
        db.create_all()
    app.run(debug=True)
