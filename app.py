from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func

app = Flask(__name__)

# Настройка подключения к SQLite. Файл базы "patient_twin.db" будет создан в корневой директории.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///patient_twin.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель пациента (для планирования мониторинга)
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(80), nullable=False)  # будем отображать как ФИО
    disease = db.Column(db.String(80), nullable=False)
    frequency = db.Column(db.Integer, nullable=False)
    health_indicators = db.Column(db.String(200), nullable=False)

# Модель для структурированных измерений
class Reading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(80), nullable=False)  # поле ФИО
    temperature = db.Column(db.Float, nullable=True)         # Температура (°C)
    systolic = db.Column(db.Integer, nullable=True)            # Систолическое давление (мм рт. ст.)
    diastolic = db.Column(db.Integer, nullable=True)           # Диастолическое давление (мм рт. ст.)
    chest_pain = db.Column(db.Boolean, nullable=True)          # Боль в груди (True/False)
    timestamp = db.Column(db.String(80), nullable=False)         # Дата-время измерения ("YYYY-MM-DD HH:MM:SS")

# Функция для анализа измерений и генерации предупреждений
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
    
    readings = Reading.query.order_by(Reading.timestamp.desc()).all()
    for r in readings:
        r.alerts = analyze_structured_reading(r)
    return render_template("readings.html", readings=readings)

@app.route('/delete_reading/<int:reading_id>', methods=['POST'])
def delete_reading(reading_id):
    reading = Reading.query.get_or_404(reading_id)
    db.session.delete(reading)
    db.session.commit()
    return redirect(url_for('readings_view'))

@app.route('/reports')
def reports():
    # Получение параметров поиска и фильтрации из запроса
    search_query = request.args.get('search', '').strip()
    start_date = request.args.get('start_date', '').strip()  # Формат: YYYY-MM-DD
    end_date = request.args.get('end_date', '').strip()      # Формат: YYYY-MM-DD
    sort_field = request.args.get('sort_field', 'default')
    sort_order = request.args.get('sort_order', 'desc')

    query = Reading.query

    # Фильтрация по ФИО: обрезаем пробелы, переводим в нижний регистр, применяем trim и lower к значению из БД
    if search_query:
        processed = search_query.lower()
        query = query.filter(func.lower(func.trim(Reading.patient_name)).like(f"%{processed}%"))
    
    # Фильтрация по дате, если заданы поля
    if start_date:
        query = query.filter(Reading.timestamp >= f"{start_date} 00:00:00")
    if end_date:
        query = query.filter(Reading.timestamp <= f"{end_date} 23:59:59")
    
    all_measurements = query.order_by(Reading.timestamp.desc()).all()
    
    # Группировка измерений по ФИО
    groups = {}
    for m in all_measurements:
        name = m.patient_name
        groups.setdefault(name, []).append(m)
    
    # Для каждого пациента выбираем только самое свежее измерение и сохраняем историю
    patient_groups = []
    for name, measurements in groups.items():
        latest = measurements[0]
        patient_groups.append((name, latest, measurements))
    
    # Применяем сортировку к последним измерениям
    if sort_field == 'default':
        patient_groups.sort(key=lambda g: g[1].timestamp, reverse=True)
    else:
        sort_options = {
            'patient_name': lambda m: m.patient_name.lower() if m.patient_name else "",
            'temperature': lambda m: m.temperature if m.temperature is not None else (-float('inf') if sort_order=='asc' else float('inf')),
            'systolic': lambda m: m.systolic if m.systolic is not None else (-float('inf') if sort_order=='asc' else float('inf')),
            'diastolic': lambda m: m.diastolic if m.diastolic is not None else (-float('inf') if sort_order=='asc' else float('inf')),
            'timestamp': lambda m: m.timestamp
        }
        if sort_field in sort_options:
            key_func = sort_options[sort_field]
            reverse = (sort_order == 'desc')
            patient_groups.sort(key=lambda grp: key_func(grp[1]), reverse=reverse)
        else:
            patient_groups.sort(key=lambda g: g[1].timestamp, reverse=True)

    # Применяем анализ измерений для предупреждений
    for group in patient_groups:
        group[1].alerts = analyze_structured_reading(group[1])
        for m in group[2]:
            m.alerts = analyze_structured_reading(m)

    return render_template("reports.html",
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
