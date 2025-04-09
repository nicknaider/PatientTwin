from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Список для хранения данных о пациентах (временное хранилище)
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
        
        # Сохранение данных в списке
        patients.append({
            'patient_name': patient_name,
            'disease': disease,
            'frequency': frequency
        })
        
        # Перенаправление для избежания повторной отправки данных
        return redirect(url_for('schedule'))
    
    # Передача списка пациентов в шаблон при GET-запросе
    return render_template('schedule.html', patients=patients)

if __name__ == '__main__':
    app.run(debug=True)
