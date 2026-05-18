import network
import socket
import time
import json
from machine import Pin, ADC
from wifi_config import WIFI_SSID, WIFI_PASSWORD

# =============================================
# 하드웨어 설정
# =============================================
gas_sensor = ADC(Pin(26))

led_green  = Pin(13, Pin.OUT)
led_yellow = Pin(12, Pin.OUT)
led_red    = Pin(11, Pin.OUT)

sensor_data = []
MAX_DATA    = 50

def all_led_off():
    led_green.value(0)
    led_yellow.value(0)
    led_red.value(0)

def update_led(raw):
    if raw < 30000:
        all_led_off()
        led_green.value(1)
    elif raw < 45000:
        all_led_off()
        led_yellow.value(1)
    elif raw < 57000:
        all_led_off()
        led_red.value(1)
    else:
        all_led_off()
        for _ in range(3):
            led_red.value(1)
            time.sleep(0.05)
            led_red.value(0)
            time.sleep(0.05)

def get_gas_percentage(raw):
    return round((raw / 65535) * 100, 1)

def get_status(raw):
    if raw < 30000:   return "safe"
    elif raw < 45000: return "caution"
    elif raw < 57000: return "danger"
    else:             return "emergency"

def get_status_korean(raw):
    if raw < 30000:   return "안전"
    elif raw < 45000: return "주의"
    elif raw < 57000: return "위험"
    else:             return "긴급"

# =============================================
# Wi-Fi 연결
# =============================================
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    print("Wi-Fi 연결 중", end="")
    timeout = 0
    while not wlan.isconnected():
        print(".", end="")
        time.sleep(0.5)
        timeout += 1
        if timeout > 20:
            print("\n실패!")
            return None
    ip = wlan.ifconfig()[0]
    print(f"\n연결 성공! IP: {ip}")
    return ip

# =============================================
# HTML (최소화 버전)
# =============================================
HTML = """<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>약품 실험실 안전 모니터링</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:sans-serif;background:#0f0f1a;color:white;padding:15px}
h1{text-align:center;font-size:1.4em;margin-bottom:15px;color:#00d4ff}
.sb{text-align:center;padding:18px;border-radius:12px;margin-bottom:15px;
font-size:1.8em;font-weight:bold;border:2px solid transparent}
.safe{background:#0d3b0d;border-color:#00ff00;color:#00ff00}
.caution{background:#3b3b0d;border-color:#ffff00;color:#ffff00}
.danger{background:#3b0d0d;border-color:#ff4444;color:#ff4444}
.emergency{background:#5c0000;border-color:#ff0000;color:#ff0000;animation:blink .4s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:15px}
.card{background:#16213e;border-radius:10px;padding:15px;text-align:center;border:1px solid #2a2a5a}
.lbl{font-size:.8em;color:#888;margin-bottom:8px}
.val{font-size:2em;font-weight:bold;color:#00d4ff;min-height:45px;display:flex;align-items:center;justify-content:center}
.lgrid{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px;margin-bottom:15px}
.li{border-radius:6px;padding:8px 4px;text-align:center;font-size:.72em;font-weight:bold}
.ls{background:#0d3b0d;color:#00ff00}
.lc{background:#3b3b0d;color:#ffff00}
.ld{background:#3b0d0d;color:#ff4444}
.le{background:#5c0000;color:#ff6666}
.cbox{background:#16213e;border-radius:10px;padding:15px;border:1px solid #2a2a5a;margin-bottom:10px}
.ct{color:#aaa;font-size:.85em;margin-bottom:8px}
.cs{text-align:center;font-size:.75em;color:#555;margin-top:8px}
.ok{color:#00ff00}.er{color:#ff4444}
</style></head><body>
<h1>💊🧪 약품 실험실 안전 모니터링</h1>
<div class="sb safe" id="sb">🟢 안전</div>
<div class="grid">
<div class="card"><div class="lbl">📡 센서 원시값</div>
<div class="val" id="rv">---</div></div>
<div class="card"><div class="lbl">💨 가스 농도</div>
<div class="val" id="gp">--.- %</div></div>
</div>
<div class="lgrid">
<div class="li ls">🟢 안전<br>0~46%</div>
<div class="li lc">🟡 주의<br>46~69%</div>
<div class="li ld">🔴 위험<br>69~87%</div>
<div class="li le">🚨 긴급<br>87%이상</div>
</div>
<div class="cbox">
<div class="ct">📈 실시간 가스 농도 그래프</div>
<canvas id="cv" height="260"></canvas>
</div>
<div class="cs" id="cs">연결 중...</div>
<script>
var cv=document.getElementById('cv');
var cx=cv.getContext('2d');
var da=[];var MX=60;
var LN=[{p:46,c:'rgba(255,255,0,.6)',t:'주의46%'},{p:69,c:'rgba(255,80,80,.6)',t:'위험69%'},{p:87,c:'rgba(255,0,0,.9)',t:'긴급87%'}];
function draw(){
var W=cv.offsetWidth||700,H=260;
cv.width=W;cv.height=H;
var PL=40,PR=10,PT=15,PB=20,GW=W-PL-PR,GH=H-PT-PB;
cx.fillStyle='#16213e';cx.fillRect(0,0,W,H);
[0,25,50,75,100].forEach(function(p){
var y=PT+GH-(p/100)*GH;
cx.strokeStyle='#1e2a4a';cx.lineWidth=1;
cx.beginPath();cx.moveTo(PL,y);cx.lineTo(PL+GW,y);cx.stroke();
cx.fillStyle='#555';cx.font='10px sans-serif';cx.textAlign='right';
cx.fillText(p+'%',PL-3,y+4);});
LN.forEach(function(ln){
var y=PT+GH-(ln.p/100)*GH;
cx.strokeStyle=ln.c;cx.lineWidth=1.5;cx.setLineDash([5,4]);
cx.beginPath();cx.moveTo(PL,y);cx.lineTo(PL+GW,y);cx.stroke();
cx.setLineDash([]);cx.fillStyle=ln.c;cx.font='9px sans-serif';
cx.textAlign='left';cx.fillText(ln.t,PL+3,y-3);});
if(da.length<2)return;
cx.beginPath();
da.forEach(function(v,i){
var x=PL+(i/(MX-1))*GW,y=PT+GH-(v/100)*GH;
i===0?cx.moveTo(x,y):cx.lineTo(x,y);});
var lx=PL+((da.length-1)/(MX-1))*GW;
cx.lineTo(lx,PT+GH);cx.lineTo(PL,PT+GH);cx.closePath();
cx.fillStyle='rgba(0,212,255,.08)';cx.fill();
cx.beginPath();cx.strokeStyle='#00d4ff';cx.lineWidth=2.5;
da.forEach(function(v,i){
var x=PL+(i/(MX-1))*GW,y=PT+GH-(v/100)*GH;
i===0?cx.moveTo(x,y):cx.lineTo(x,y);});
cx.stroke();
var lv=da[da.length-1];
var lxp=PL+((da.length-1)/(MX-1))*GW;
var lyp=PT+GH-(lv/100)*GH;
cx.beginPath();cx.arc(lxp,lyp,5,0,Math.PI*2);
cx.fillStyle='#00d4ff';cx.fill();
cx.fillStyle='#00d4ff';cx.font='bold 11px sans-serif';
cx.textAlign='center';cx.fillText(lv+'%',lxp,lyp-10);}
var SC={safe:{c:'sb safe',t:'🟢 안전'},caution:{c:'sb caution',t:'🟡 주의'},danger:{c:'sb danger',t:'🔴 위험'},emergency:{c:'sb emergency',t:'🚨 긴급 대피!'}};
var ec=0;
function fetchData(){
fetch('/data',{cache:'no-store'})
.then(function(r){if(!r.ok)throw new Error('err');return r.text();})
.then(function(t){
var d=JSON.parse(t);
document.getElementById('rv').textContent=d.raw!==undefined?String(d.raw):'---';
document.getElementById('gp').textContent=d.percent!==undefined?String(d.percent)+' %':'--.- %';
if(d.status){var s=SC[d.status]||SC.safe;var sb=document.getElementById('sb');sb.className=s.c;sb.textContent=s.t;}
if(d.percent!==undefined){da.push(Number(d.percent));if(da.length>MX)da.shift();draw();}
ec=0;var now=new Date().toLocaleTimeString();
var el=document.getElementById('cs');el.className='cs ok';el.textContent='✅ '+now+' 업데이트';})
.catch(function(e){
ec++;
document.getElementById('rv').textContent='오류';
document.getElementById('gp').textContent='오류';
var el=document.getElementById('cs');el.className='cs er';el.textContent='❌ 연결 오류 ('+ec+'번째)';});}
window.addEventListener('load',function(){draw();fetchData();setInterval(fetchData,1000);});
window.addEventListener('resize',draw);
</script></body></html>"""

# =============================================
# HTTP 요청 처리
# =============================================
def send_data(conn):
    """✅ /data → JSON 빠르게 응답"""
    raw     = gas_sensor.read_u16()
    percent = get_gas_percentage(raw)
    status  = get_status(raw)
    korean  = get_status_korean(raw)

    update_led(raw)
    print(f"  raw={raw} | {percent}% | {korean}")

    sensor_data.append(percent)
    if len(sensor_data) > MAX_DATA:
        sensor_data.pop(0)

    body = json.dumps({
        "raw"    : raw,
        "percent": percent,
        "status" : status,
        "korean" : korean
    })
    resp = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: " + str(len(body)) + "\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Connection: close\r\n\r\n"
        + body
    )
    conn.sendall(resp.encode())

def send_html(conn):
    """✅ HTML → 512바이트씩 나눠서 전송"""
    encoded = HTML.encode('utf-8')
    header  = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "Content-Length: " + str(len(encoded)) + "\r\n"
        "Connection: close\r\n\r\n"
    )
    conn.sendall(header.encode())
    for i in range(0, len(encoded), 512):
        conn.sendall(encoded[i:i+512])

def handle_request(conn):
    try:
        request = conn.recv(1024).decode('utf-8', 'ignore')
        first   = request.split('\n')[0].strip()
        print(f"요청: {first}")

        if 'GET /data' in request:
            send_data(conn)
        elif 'GET /favicon.ico' in request:
            conn.sendall(b"HTTP/1.1 204 No Content\r\nConnection: close\r\n\r\n")
        else:
            send_html(conn)

    except Exception as e:
        print(f"오류: {e}")
    finally:
        conn.close()

# =============================================
# 메인 실행
# =============================================
print("=" * 40)
print("  약품 실험실 스마트 안전 관리 시스템")
print("  Raspberry Pi Pico 2 WH + MQ2 센서")
print("=" * 40)

ip = connect_wifi()
if ip is None:
    print("Wi-Fi 연결 실패!")
    raise SystemExit

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', 80))
server.listen(5)

print(f"웹서버 → http://{ip}")
print("=" * 40)

while True:
    try:
        conn, addr = server.accept()
        handle_request(conn)
    except Exception as e:
        print(f"서버 오류: {e}")
