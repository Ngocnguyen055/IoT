import os, sqlite3, time
from contextlib import contextmanager
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'a29243364ce0b85893337a266970a71405522a8ccc0bd25de88cba497f6a216b')
DEVICE_KEY = os.environ.get('DEVICE_KEY', '3445fc58fe14088666f4c8e49ea8a3c167f4f8df72004eeacbcf771f18c820ce')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ngocnguyen123')
DB = os.environ.get('DB_PATH', 'iot_ngoc.sqlite3')

@contextmanager
def connect():
    db = sqlite3.connect(DB, timeout=15)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()

def init_db():
    with connect() as db:
        db.executescript('''
          CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL, ts INTEGER NOT NULL,
            event TEXT NOT NULL, lat REAL, lon REAL, gps_satellites INTEGER,
            bpm INTEGER, spo2 INTEGER, battery_pct REAL, battery_voltage REAL, current_ma REAL
          );
          CREATE INDEX IF NOT EXISTS idx_readings_device_ts ON readings(device_id, ts);
          CREATE TABLE IF NOT EXISTS commands (
            device_id TEXT PRIMARY KEY, cmd TEXT NOT NULL DEFAULT 'NONE'
          );
        ''')

init_db()

def device_auth(f):
    @wraps(f)
    def inner(*a, **k):
        if request.headers.get('X-Device-Key') != DEVICE_KEY:
            return jsonify(error='device unauthorized'), 401
        return f(*a, **k)
    return inner

def admin_auth(f):
    @wraps(f)
    def inner(*a, **k):
        if not session.get('admin'):
            return jsonify(error='login required'),401
        return f(*a,**k)
    return inner

@app.get('/login')
def login_page():
    return render_template('login.html')

@app.post('/login')
def login():
    from hmac import compare_digest
    if compare_digest(request.form.get('password',''), ADMIN_PASSWORD):
        session.clear();session['admin']=True
        return redirect('/')
    return render_template('login.html', error='Sai mật khẩu'),401

@app.post('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.get('/')
def dashboard():
    if not session.get('admin'):return redirect('/login')
    return render_template('index.html')

@app.post('/api/device/telemetry')
@device_auth
def telemetry():
    d=request.get_json(silent=True)
    if not isinstance(d,dict):return jsonify(error='JSON required'),400
    allowed = {'telemetry','button','high_bpm','low_spo2','remote'}
    event=d.get('event','telemetry')
    if event not in allowed:return jsonify(error='bad event'),400
    device_id=str(d.get('device_id',''))
    if not 1<=len(device_id)<=64:return jsonify(error='bad device_id'),400
    def finite_num(name, lo, hi):
        v=d.get(name)
        if v is None:return None
        try: v=float(v)
        except (TypeError,ValueError):raise ValueError(name)
        if not lo<=v<=hi:raise ValueError(name)
        return v
    try:
        lat=finite_num('lat',-90,90);lon=finite_num('lon',-180,180)
        if (lat is None)!=(lon is None):return jsonify(error='lat/lon together'),400
        sat=finite_num('gps_satellites',0,100)
        bpm=finite_num('bpm',0,300);spo2=finite_num('spo2',0,100)
        pct=finite_num('battery_pct',0,100)
        volt=finite_num('battery_voltage',0,100);ma=finite_num('current_ma',-10000,10000)
    except ValueError as e:return jsonify(error=f'bad field: {e}'),400
    with connect() as db:
        db.execute('''INSERT INTO readings(device_id,ts,event,lat,lon,gps_satellites,bpm,spo2,battery_pct,battery_voltage,current_ma)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                   (device_id,int(time.time()),event,lat,lon,sat,bpm,spo2,pct,volt,ma))
        if event=='remote':
            db.execute("UPDATE commands SET cmd='NONE' WHERE device_id=?",(device_id,))
    return jsonify(ok=True)

@app.get('/api/device/command')
@device_auth
def device_command():
    device_id=request.args.get('device_id','')
    with connect() as db:
        row=db.execute('SELECT cmd FROM commands WHERE device_id=?',(device_id,)).fetchone()
    # plain-text for small AT modems; LOCATE is idempotent until successful POST.
    return (row['cmd'] if row else 'NONE'),200,{'Content-Type':'text/plain'}

@app.get('/api/status')
@admin_auth
def status():
    with connect() as db:
        data=db.execute('SELECT * FROM readings ORDER BY id DESC LIMIT 150').fetchall()
        rows=[dict(x) for x in data]
        last_location=db.execute('SELECT device_id,lat,lon,ts FROM readings WHERE lat IS NOT NULL AND lon IS NOT NULL ORDER BY id DESC LIMIT 1').fetchone()
        alerts=db.execute("SELECT * FROM readings WHERE event!='telemetry' ORDER BY id DESC LIMIT 20").fetchall()
        cmds=db.execute('SELECT device_id,cmd FROM commands').fetchall()
    return jsonify(latest=rows[0] if rows else None,history=rows,
                   last_location=dict(last_location) if last_location else None,
                   alerts=[dict(r) for r in alerts],commands=[dict(r) for r in cmds], now=int(time.time()))

@app.get('/api/track')
@admin_auth
def track():
    # GPS points already stored by the existing telemetry endpoint.
    # Only return the last 24 hours, capped at 1000 points to keep the UI responsive.
    device_id=request.args.get('device_id', 'ngoc-01')
    if not 1 <= len(device_id) <= 64:
        return jsonify(error='bad device_id'), 400
    try:
        hours=int(request.args.get('hours','24'))
    except (TypeError,ValueError):
        return jsonify(error='bad hours'), 400
    if not 1 <= hours <= 168:
        return jsonify(error='hours out of range'), 400
    since=int(time.time())-hours*3600
    with connect() as db:
        data=db.execute("""SELECT id,ts,lat,lon,gps_satellites,event
             FROM readings WHERE device_id=? AND ts>=? AND lat IS NOT NULL AND lon IS NOT NULL
             ORDER BY id DESC LIMIT 1000""",(device_id,since)).fetchall()
    return jsonify(device_id=device_id, hours=hours, points=[dict(r) for r in reversed(data)])

@app.post('/api/command')
@admin_auth
def issue_command():
    d=request.get_json(silent=True) or {}
    device_id=str(d.get('device_id','ngoc-01'))
    if not 1<=len(device_id)<=64:return jsonify(error='bad device'),400
    if d.get('command')!='LOCATE':return jsonify(error='bad command'),400
    with connect() as db:
        db.execute("INSERT INTO commands(device_id,cmd) VALUES(?, 'LOCATE') ON CONFLICT(device_id) DO UPDATE SET cmd='LOCATE'",(device_id,))
    return jsonify(ok=True,message='Đã xếp lệnh; chờ thiết bị kết nối')

if __name__ == '__main__':
    app.run(host='127.0.0.1',port=5000,debug=False)
