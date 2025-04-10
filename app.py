from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Настройка подключения к базе данных SQLite.
# Файл базы "patient_twin.db" будет создан в корневой директории проекта.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patient_twin.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель для пациента (планирование мониторинга)
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)           # Имя пациента
    disease = db.Column(db.String(80), nullable=False)          # Заболевание
    checkup_interval = db.Column(db.Integer, nullable=False)    # Периодичность опроса (дней)
    vital_signs = db.Column(db.String(200), nullable=False)     # Основные показатели (кратко)

    def __repr__(self):
        return f"<Patient {self.name}>"

# Модель для измерений (данных мониторинга)
class Measurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(80), nullable=False)      # Имя пациента
    temperature = db.Column(db.Float, nullable=True)             # Температура (°C)
    systolic_pressure = db.Column(db.Integer, nullable=True)       # Систолическое давление (мм рт. ст.)
    diastolic_pressure = db.Column(db.Integer, nullable=True)      # Диастолическое давление (мм рт. ст.)
    chest_pain = db.Column(db.Boolean, nullable=True)              # Наличие боли в груди (True/False)
    heart_rate = db.Column(db.Integer, nullable=True)              # Пульс (уд/мин)
    oxygen_saturation = db.Column(db.Integer, nullable=True)         # Насыщение кислородом (%)
    timestamp = db.Column(db.String(80), nullable=False)           # Дата и время измерения

    def __repr__(self):
        return f"<Measurement {self.patient_name} at {self.timestamp}>"

# Функция для анализа измерений
def analyze_measurement(measurement):
    warnings = []
    if measurement.temperature is not None and measurement.temperature > 37.0:
        warnings.append("Высокая температура")
    if measurement.systolic_pressure is not None and measurement.systolic_pressure > 140:
        warnings.append("Систолическое давление выше нормы")
    if measurement.diastolic_pressure is not None and measurement.diastolic_pressure > 90:
        warnings.append("Диастолическое давление выше нормы")
    if measurement.chest_pain:
        warnings.append("Боль в груди")
    if measurement.heart_rate is not None and (measurement.heart_rate < 60 or measurement.heart_rate > 100):
        warnings.append("Ненормальный пульс")
    if measurement.oxygen_saturation is not None and measurement.oxygen_saturation < 95:
        warnings.append("Низкое насыщение кислородом")
    return warnings

@app.route('/')
def home():
    return render_template("home.html")

# Страница планирования мониторинга (добавление пациента)
@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if request.method == 'POST':
        name = request.form.get('patient_name')
        disease = request.form.get('disease')
        interval = request.form.get('frequency')
        vital_signs = request.form.get('health_indicators')
        
        new_patient = Patient(
            name=name,
            disease=disease,
            checkup_interval=int(interval),
            vital_signs=vital_signs
        )
        db.session.add(new_patient)
        db.session.commit()
        return redirect(url_for('schedule'))
    
    patients = Patient.query.all()
    return render_template('schedule.html', patients=patients)

# Страница ввода измерений (добавление данных мониторинга)
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
        try:
            heart_rate = int(request.form.get('pulse'))
        except (ValueError, TypeError):
            heart_rate = None
        try:
            oxygen = int(request.form.get('oxygen_saturation'))
        except (ValueError, TypeError):
            oxygen = None

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_measurement = Measurement(
            patient_name=patient_name,
            temperature=temperature,
            systolic_pressure=systolic,
            diastolic_pressure=diastolic,
            chest_pain=chest_pain,
            heart_rate=heart_rate,
            oxygen_saturation=oxygen,
            timestamp=timestamp
        )
        db.session.add(new_measurement)
        db.session.commit()
        return redirect(url_for('readings_view'))
    
    measurements = Measurement.query.all()
    for m in measurements:
        m.alerts = analyze_measurement(m)
    return render_template("readings.html", readings=measurements)

# Страница отчётов (сортировка по умолчанию или по выбранному полю)
@app.route('/reports')
def reports():
    sort_field = request.args.get('sort_field', 'default')
    sort_order = request.args.get('sort_order', 'desc')

    if sort_field == 'default':
        query = Measurement.query.order_by(Measurement.timestamp.desc())
    else:
        sort_options = {
            'patient_name': Measurement.patient_name,
            'temperature': Measurement.temperature,
            'systolic': Measurement.systolic_pressure,
            'diastolic': Measurement.diastolic_pressure,
            'pulse': Measurement.heart_rate,
            'oxygen_saturation': Measurement.oxygen_saturation,
            'timestamp': Measurement.timestamp
        }
        if sort_field in sort_options:
            column = sort_options[sort_field]
            if sort_order == 'desc':
                query = Measurement.query.order_by(column.desc())
            else:
                query = Measurement.query.order_by(column.asc())
        else:
            query = Measurement.query.order_by(Measurement.timestamp.desc())

    measurements = query.all()
    for m in measurements:
        m.alerts = analyze_measurement(m)
        
    return render_template("reports.html", readings=measurements, sort_field=sort_field, sort_order=sort_order)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создаёт таблицы, если их ещё нет
    app.run(debug=True)
