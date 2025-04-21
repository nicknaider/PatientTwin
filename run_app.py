import threading
import webview
from app import app, db, User
from werkzeug.security import generate_password_hash

def start_flask():
    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            admin = User(username='admin',
                         password=generate_password_hash('admin'),
                         role='admin')
            db.session.add(admin)
            db.session.commit()

    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    app.run(host='127.0.0.1', port=5000)

if __name__ == '__main__':
    t = threading.Thread(target=start_flask, daemon=True)
    t.start()

    webview.create_window(
        title='Медицинская система',
        url='http://127.0.0.1:5000',
        width=1024,
        height=768,
        resizable=True
    )
    webview.start()
