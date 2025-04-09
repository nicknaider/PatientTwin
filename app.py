from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Временное хранилище для данных о пациентах
patients = []

@app.route('/')
def home():
    return 'Добро пожаловать в модуль А: Базовая автоматизация бизнес-процесса'

@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if request.method == 'POST':
        # Получение данных из формы
        patient_name = request.form.get('patient_name')
        disease = request.form.get('disease')
        frequency = request.form.get('frequency')
        health_indicators = request.form.get('health_indicators')  # Новое поле для показателей здоровья
        
        # Добавляем данные в список
        patients.append({
            'patient_name': patient_name,
            'disease': disease,
            'frequency': frequency,
            'health_indicators': health_indicators
        })
        
        # После сохранения перенаправляем на страницу для избежания повторной отправки
        return redirect(url_for('schedule'))
    
    # При GET-запросе передаём список пациентов в шаблон
    return render_template('schedule.html', patients=patients)

if __name__ == '__main__':
    app.run(debug=True)
