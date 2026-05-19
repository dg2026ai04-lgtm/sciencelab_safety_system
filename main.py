import network
import socket
import time
import json
import neopixel
from machine import Pin, ADC
from wifi_config import WIFI_SSID, WIFI_PASSWORD

# =============================================
# 하드웨어 설정
# =============================================
gas_sensor = ADC(Pin(26))

TIMING   = (280, 515, 515, 745)
NUM_LEDS = 10
led      = neopixel.NeoPixel(Pin(16), NUM_LEDS, timing=TIMING)

# =============================================
# 전역 변수
# =============================================
sensor_data  = []
MAX_DATA     = 60
max_percent  = 0.0
min_percent  = 100.0
danger_count = 0
start_time   = time.time()

threshold = {
    "caution"  : 46,
    "danger"   : 69,
    "emergency": 87
}

# =============================================
# 네오픽셀 LED 제어
# =============================================
def led_off():
    for i in range(NUM_LEDS):
        led[i] = (0, 0, 0)
    led.write()

def led_set_all(r, g, b):
    for i in range(NUM_LEDS):
        led[i] = (r, g, b)
    led.write()

def update_led(percent):
    if percent >= threshold["emergency"]:
        for _ in range(3):
            led_set_all(150, 0, 0)
            time.sleep(0.05)
            led_off()
            time.sleep(0.05)
        return

    count = int((percent / 100) * NUM_LEDS) + 1
    count = min(count, NUM_LEDS)

    if percent < 50:
        ratio = percent / 50
        r = int(255 * ratio * 0.3)
        g = int(255 * 0.3)
        b = 0
    else:
        ratio = (percent - 50) / 50
        r = int(255 * 0.3)
        g = int(255 * (1 - ratio) * 0.3)
        b = 0

    for i in range(NUM_LEDS):
        if i < count:
            led[i] = (r, g, b)
        else:
            led[i] = (2, 2, 2)
    led.write()

# =============================================
# 센서값 변환
# =============================================
def get_gas_percentage(raw):
    return round((raw / 65535) * 100, 1)

def get_status(percent):
    if percent < threshold["caution"]:     return "safe"
    elif percent < threshold["danger"]:    return "caution"
    elif percent < threshold["emergency"]: return "danger"
    else:                                  return "emergency"

def get_status_korean(percent):
    if percent < threshold["caution"]:     return "안전"
    elif percent < threshold["danger"]:    return "주의"
    elif percent < threshold["emergency"]: return "위험"
    else:                                  return "긴급"

def get_elapsed():
    e = int(time.time() - start_time)
    return str(e // 60) + ":" + "{:02d}".format(e % 60)

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
# HTML
# =============================================
HTML = """<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>약품 실험실 안전 모니터링</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:sans-serif;background:#0f0f1a;color:white;padding:15px}
h1{text-align:center;font-size:1.4em;margin-bottom:15px;color:#00d4ff}
.sb{text-align:center;padding:15px;border-radius:12px;margin-bottom:15px;
font-size:1.8em;font-weight:bold;border:2px solid transparent}
.safe{background:#0d3b0d;border-color:#00ff00;color:#00ff00}
.caution{background:#3b3b0d;border-color:#ffff00;color:#ffff00}
.danger{background:#3b0d0d;border-color:#ff4444;color:#ff4444}
.emergency{background:#5c0000;border-color:#ff0000;color:#ff0000;
animation:blink .4s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
.grid4{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;margin-bottom:12px}
.card{background:#16213e;border-radius:10px;padding:12px;text-align:center;
border:1px solid #2a2a5a}
.lbl{font-size:.78em;color:#888;margin-bottom:6px}
.val{font-size:1.7em;font-weight:bold;color:#00d4ff;min-height:38px;
display:flex;align-items:center;justify-content:center}
.val-max{color:#ff4444}
.val-min{color:#00ff00}
.val-cnt{color:#ffaa00}
.val-time{color:#aaaaff}
.lgrid{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px;margin-bottom:12px}
.li{border-radius:6px;padding:7px 4px;text-align:center;font-size:.72em;font-weight:bold}
.ls{background:#0d3b0d;color:#00ff00}
.lc{background:#3b3b0d;color:#ffff00}
.ld{background:#3b0d0d;color:#ff4444}
.le{background:#5c0000;color:#ff6666}

/* ✅ 그래프 영역 크게! */
.cbox{background:#16213e;border-radius:12px;padding:20px;
border:1px solid #2a2a5a;margin-bottom:12px}
.ct{color:#aaa;font-size:.88em;margin-bottom:10px;font-weight:bold}
canvas{display:block;width:100%}

.tbox{background:#16213e;border-radius:10px;padding:15px;
border:1px solid #2a2a5a;margin-bottom:12px}
.tbox h3{color:#00d4ff;font-size:.92em;margin-bottom:12px}
.trow{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.trow label{color:#aaa;font-size:.82em;width:55px;flex-shrink:0}
.trow input[type=range]{flex:1;accent-color:#00d4ff;height:6px}
.trow span{color:#00d4ff;font-size:.85em;width:40px;text-align:right}
.tbtn{width:100%;padding:10px;background:#1a3a5c;border:1px solid #00d4ff;
border-radius:8px;color:#00d4ff;font-size:.92em;cursor:pointer;margin-top:5px}
.tbtn:hover{background:#0d4a7a}
.reset-btn{width:100%;padding:8px;background:#3b0d0d;border:1px solid #ff4444;
border-radius:8px;color:#ff4444;font-size:.85em;cursor:pointer;margin-bottom:12px}
.reset-btn:hover{background:#5c1010}
.cs{text-align:center;font-size:.75em;margin-top:8px;padding:5px}
.ok{color:#00ff00}.er{color:#ff4444}
</style></head><body>
<h1>💊🧪 약품 실험실 안전 모니터링</h1>
<div class="sb safe" id="sb">🟢 안전</div>

<div class="grid2">
<div class="card"><div class="lbl">📡 센서 원시값</div>
<div class="val" id="rv">---</div></div>
<div class="card"><div class="lbl">💨 현재 가스 농도</div>
<div class="val" id="gp">--.- %</div></div>
</div>

<div class="grid4">
<div class="card"><div class="lbl">📈 최고값</div>
<div class="val val-max" id="mx">0.0 %</div></div>
<div class="card"><div class="lbl">📉 최저값</div>
<div class="val val-min" id="mn">100.0 %</div></div>
<div class="card"><div class="lbl">⚠️ 위험 횟수</div>
<div class="val val-cnt" id="dc">0 회</div></div>
<div class="card"><div class="lbl">⏱️ 경과 시간</div>
<div class="val val-time" id="et">0:00</div></div>
</div>

<div class="lgrid">
<div class="li ls">🟢 안전</div>
<div class="li lc">🟡 주의</div>
<div class="li ld">🔴 위험</div>
<div class="li le">🚨 긴급</div>
</div>

<!-- ✅ 그래프 먼저! 크게! -->
<div class="cbox">
<div class="ct">📈 실시간 가스 농도 그래프</div>
<canvas id="cv" height="380"></canvas>
</div>

<div class="tbox">
<h3>⚙️ 위험 임계값 설정</h3>
<div class="trow">
<label>🟡 주의</label>
<input type="range" id="s1" min="10" max="60" value="46"
oninput="document.getElementById('v1').textContent=this.value+'%'">
<span id="v1">46%</span></div>
<div class="trow">
<label>🔴 위험</label>
<input type="range" id="s2" min="30" max="80" value="69"
oninput="document.getElementById('v2').textContent=this.value+'%'">
<span id="v2">69%</span></div>
<div class="trow">
<label>🚨 긴급</label>
<input type="range" id="s3" min="50" max="95" value="87"
oninput="document.getElementById('v3').textContent=this.value+'%'">
<span id="v3">87%</span></div>
<button class="tbtn" onclick="setThreshold()">✅ 임계값 적용</button>
</div>

<button class="reset-btn" onclick="resetData()">🔄 데이터 초기화</button>
<div class="cs" id="cs">연결 중...</div>

<script>
var cv=document.getElementById('cv');
var cx=cv.getContext('2d');
var da=[];
var ta=[];
var MX=60;
var th={caution:46,danger:69,emergency:87};

function draw(){
var W=cv.offsetWidth||900;
var H=380;
cv.width=W;cv.height=H;
var PL=48,PR=15,PT=20,PB=45,GW=W-PL-PR,GH=H-PT-PB;

// 배경
cx.fillStyle='#0d1526';cx.fillRect(0,0,W,H);

// 그리드 가로선
[0,10,20,30,40,50,60,70,80,90,100].forEach(function(p){
var y=PT+GH-(p/100)*GH;
cx.strokeStyle= p%25===0 ? '#1e2a4a' : '#131d33';
cx.lineWidth=1;
cx.beginPath();cx.moveTo(PL,y);cx.lineTo(PL+GW,y);cx.stroke();
cx.fillStyle= p%25===0 ? '#666' : '#333';
cx.font= p%25===0 ? 'bold 11px sans-serif' : '9px sans-serif';
cx.textAlign='right';
cx.fillText(p+'%',PL-5,y+4);});

// 임계선
[
{p:th.caution,  c:'rgba(255,220,0,.7)', t:'주의 '+th.caution+'%'},
{p:th.danger,   c:'rgba(255,80,80,.7)', t:'위험 '+th.danger+'%'},
{p:th.emergency,c:'rgba(255,0,0,1)',    t:'긴급 '+th.emergency+'%'}
].forEach(function(ln){
var y=PT+GH-(ln.p/100)*GH;
cx.strokeStyle=ln.c;cx.lineWidth=1.8;cx.setLineDash([7,5]);
cx.beginPath();cx.moveTo(PL,y);cx.lineTo(PL+GW,y);cx.stroke();
cx.setLineDash([]);
cx.fillStyle=ln.c;cx.font='bold 10px sans-serif';
cx.textAlign='left';cx.fillText(ln.t,PL+6,y-5);});

if(da.length<2){
// 데이터 없을 때 안내
cx.fillStyle='#333';cx.font='16px sans-serif';
cx.textAlign='center';
cx.fillText('데이터 수집 중...', W/2, H/2);
return;}

// 면적 채우기
cx.beginPath();
da.forEach(function(v,i){
var x=PL+(i/(MX-1))*GW;
var y=PT+GH-(v/100)*GH;
i===0?cx.moveTo(x,y):cx.lineTo(x,y);});
var lx=PL+((da.length-1)/(MX-1))*GW;
cx.lineTo(lx,PT+GH);cx.lineTo(PL,PT+GH);cx.closePath();
var grad=cx.createLinearGradient(0,PT,0,PT+GH);
grad.addColorStop(0,'rgba(0,212,255,0.25)');
grad.addColorStop(1,'rgba(0,212,255,0.01)');
cx.fillStyle=grad;cx.fill();

// 실선
cx.beginPath();
cx.strokeStyle='#00d4ff';cx.lineWidth=2.8;
cx.lineJoin='round';cx.lineCap='round';
da.forEach(function(v,i){
var x=PL+(i/(MX-1))*GW;
var y=PT+GH-(v/100)*GH;
i===0?cx.moveTo(x,y):cx.lineTo(x,y);});
cx.stroke();

// 최신 점 + 값
var lv=da[da.length-1];
var lxp=PL+((da.length-1)/(MX-1))*GW;
var lyp=PT+GH-(lv/100)*GH;
cx.beginPath();cx.arc(lxp,lyp,6,0,Math.PI*2);
cx.fillStyle='#00d4ff';cx.fill();
cx.strokeStyle='#0f0f1a';cx.lineWidth=2;
cx.stroke();
cx.fillStyle='white';cx.font='bold 13px sans-serif';
cx.textAlign='center';
cx.fillText(lv+'%',lxp,lyp-12);

// 시간축
cx.fillStyle='#555';cx.font='10px sans-serif';cx.textAlign='center';
var labelCount=6;
var step=Math.max(1,Math.floor(da.length/labelCount));
for(var i=0;i<da.length;i+=step){
var x=PL+(i/(MX-1))*GW;
cx.fillStyle='#444';cx.lineWidth=1;
cx.beginPath();cx.moveTo(x,PT+GH);cx.lineTo(x,PT+GH+5);cx.stroke();
cx.fillStyle='#666';
cx.fillText(ta[i]||'',x,PT+GH+18);}

// X축 선
cx.strokeStyle='#2a2a5a';cx.lineWidth=1;
cx.beginPath();cx.moveTo(PL,PT+GH);cx.lineTo(PL+GW,PT+GH);cx.stroke();}

var SC={
safe:{c:'sb safe',t:'🟢 안전'},
caution:{c:'sb caution',t:'🟡 주의'},
danger:{c:'sb danger',t:'🔴 위험'},
emergency:{c:'sb emergency',t:'🚨 긴급 대피!'}};

var ec=0;var busy=false;

function fetchData(){
if(busy)return;busy=true;
var xhr=new XMLHttpRequest();
xhr.timeout=3000;
xhr.open('GET','/data?t='+Date.now(),true);
xhr.onreadystatechange=function(){
if(xhr.readyState===4){
busy=false;
if(xhr.status===200){
try{
var d=JSON.parse(xhr.responseText.trim());
document.getElementById('rv').textContent=
d.raw!==undefined?String(d.raw):'---';
document.getElementById('gp').textContent=
d.percent!==undefined?String(d.percent)+' %':'--.- %';
document.getElementById('mx').textContent=
d.max_p!==undefined?String(d.max_p)+' %':'--';
document.getElementById('mn').textContent=
d.min_p!==undefined?String(d.min_p)+' %':'--';
document.getElementById('dc').textContent=
d.danger_cnt!==undefined?String(d.danger_cnt)+' 회':'0 회';
document.getElementById('et').textContent=
d.elapsed||'0:00';
if(d.status){
var s=SC[d.status]||SC.safe;
var sb=document.getElementById('sb');
sb.className=s.c;sb.textContent=s.t;}
if(d.percent!==undefined){
var now=new Date();
var ts=now.getHours()+':'+
String(now.getMinutes()).padStart(2,'0')+':'+
String(now.getSeconds()).padStart(2,'0');
da.push(Number(d.percent));
ta.push(ts);
if(da.length>MX){da.shift();ta.shift();}
draw();}
if(d.threshold){
th=d.threshold;
document.getElementById('s1').value=th.caution;
document.getElementById('v1').textContent=th.caution+'%';
document.getElementById('s2').value=th.danger;
document.getElementById('v2').textContent=th.danger+'%';
document.getElementById('s3').value=th.emergency;
document.getElementById('v3').textContent=th.emergency+'%';}
ec=0;
var now2=new Date().toLocaleTimeString();
var el=document.getElementById('cs');
el.className='cs ok';
el.textContent='✅ '+now2+' 업데이트';
}catch(e){
ec++;
var el=document.getElementById('cs');
el.className='cs er';
el.textContent='❌ 파싱오류';}}
else{ec++;
var el=document.getElementById('cs');
el.className='cs er';
el.textContent='❌ HTTP'+xhr.status;}
}};
xhr.ontimeout=function(){busy=false;ec++;
var el=document.getElementById('cs');
el.className='cs er';el.textContent='❌ 타임아웃';};
xhr.onerror=function(){busy=false;ec++;
var el=document.getElementById('cs');
el.className='cs er';el.textContent='❌ 연결실패';};
xhr.send();}

function setThreshold(){
var c=parseInt(document.getElementById('s1').value);
var d=parseInt(document.getElementById('s2').value);
var e=parseInt(document.getElementById('s3').value);
if(c>=d||d>=e){
alert('주의 < 위험 < 긴급 순서로 설정해야 해요!');return;}
var xhr=new XMLHttpRequest();
xhr.open('POST','/threshold',true);
xhr.setRequestHeader('Content-Type','application/json');
xhr.onreadystatechange=function(){
if(xhr.readyState===4&&xhr.status===200){
th={caution:c,danger:d,emergency:e};
alert('임계값이 적용됐어요! ✅');}};
xhr.send(JSON.stringify({caution:c,danger:d,emergency:e}));}

function resetData(){
if(!confirm('데이터를 초기화할까요?'))return;
var xhr=new XMLHttpRequest();
xhr.open('POST','/reset',true);
xhr.onreadystatechange=function(){
if(xhr.readyState===4&&xhr.status===200){
da=[];ta=[];
document.getElementById('mx').textContent='0.0 %';
document.getElementById('mn').textContent='100.0 %';
document.getElementById('dc').textContent='0 회';
document.getElementById('et').textContent='0:00';
draw();
alert('초기화됐어요! ✅');}};
xhr.send();}

window.addEventListener('load',function(){
draw();fetchData();setInterval(fetchData,1500);});
window.addEventListener('resize',draw);
</script></body></html>"""

# =============================================
# /data 응답
# =============================================
def send_data(conn):
    global max_percent, min_percent, danger_count

    raw     = gas_sensor.read_u16()
    percent = get_gas_percentage(raw)
    status  = get_status(percent)

    if percent > max_percent:
        max_percent = percent
    if percent < min_percent:
        min_percent = percent
    if status in ("danger", "emergency"):
        danger_count += 1

    update_led(percent)
    print(f"  raw={raw} | {percent}% | {get_status_korean(percent)}")

    sensor_data.append(percent)
    if len(sensor_data) > 60:
        sensor_data.pop(0)

    elapsed = get_elapsed()

    body = (
        '{"raw":'        + str(raw) +
        ',"percent":'    + str(percent) +
        ',"status":"'    + status + '"' +
        ',"max_p":'      + str(max_percent) +
        ',"min_p":'      + str(min_percent) +
        ',"danger_cnt":' + str(danger_count) +
        ',"elapsed":"'   + elapsed + '"' +
        ',"threshold":{"caution":'    + str(threshold["caution"]) +
        ',"danger":'                  + str(threshold["danger"]) +
        ',"emergency":'               + str(threshold["emergency"]) + '}}'
    )
    body_bytes = body.encode('utf-8')
    header = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: " + str(len(body_bytes)) + "\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Cache-Control: no-cache\r\n"
        "Connection: close\r\n\r\n"
    )
    conn.sendall(header.encode('utf-8'))
    conn.sendall(body_bytes)

# =============================================
# /threshold POST 처리
# =============================================
def handle_threshold(conn, request):
    global threshold
    try:
        body = request.split('\r\n\r\n')[-1]
        data = json.loads(body)
        threshold["caution"]   = int(data["caution"])
        threshold["danger"]    = int(data["danger"])
        threshold["emergency"] = int(data["emergency"])
        print(f"임계값 변경: {threshold}")
        conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
    except Exception as e:
        print(f"임계값 오류: {e}")
        conn.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 2\r\n\r\nER")

# =============================================
# /reset POST 처리
# =============================================
def handle_reset(conn):
    global max_percent, min_percent, danger_count, start_time, sensor_data
    max_percent  = 0.0
    min_percent  = 100.0
    danger_count = 0
    start_time   = time.time()
    sensor_data  = []
    print("데이터 초기화!")
    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")

# =============================================
# HTML 응답
# =============================================
def send_html(conn):
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

# =============================================
# 요청 처리
# =============================================
def handle_request(conn):
    try:
        request = conn.recv(2048).decode('utf-8', 'ignore')
        first   = request.split('\n')[0].strip()
        print(f"요청: {first}")

        if 'POST /threshold' in request:
            handle_threshold(conn, request)
        elif 'POST /reset' in request:
            handle_reset(conn)
        elif '/data' in request:
            send_data(conn)
        elif 'favicon' in request:
            conn.sendall(
                b"HTTP/1.1 204 No Content\r\n"
                b"Connection: close\r\n\r\n"
            )
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

led_set_all(0, 80, 0)
time.sleep(1)
led_off()

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
