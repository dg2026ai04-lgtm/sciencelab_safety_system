import network
import socket
import time
import json
import neopixel
from machine import Pin, ADC
from wifi_config import WIFI_SSID, WIFI_PASSWORD

gas_sensor = ADC(Pin(26))
TIMING     = (280, 515, 515, 745)
NUM_LEDS   = 10
led        = neopixel.NeoPixel(Pin(16), NUM_LEDS, timing=TIMING)

sensor_data  = []
max_percent  = 0.0
min_percent  = 100.0
danger_count = 0
start_time   = time.time()
threshold    = {"caution":46,"danger":69,"emergency":87}

def led_off():
    for i in range(NUM_LEDS): led[i]=(0,0,0)
    led.write()

def led_set_all(r,g,b):
    for i in range(NUM_LEDS): led[i]=(r,g,b)
    led.write()

def update_led(percent):
    if percent >= threshold["emergency"]:
        for _ in range(3):
            led_set_all(150,0,0); time.sleep(0.05)
            led_off(); time.sleep(0.05)
        return
    count = min(int((percent/100)*NUM_LEDS)+1, NUM_LEDS)
    if percent >= threshold["danger"]:
        color = (80,0,0)
    elif percent >= threshold["caution"]:
        color = (80,80,0)
    else:
        color = (0,80,0)
    for i in range(NUM_LEDS):
        led[i] = color if i<count else (2,2,2)
    led.write()

def get_gas_percentage(raw):
    return round((raw/65535)*100, 1)

def get_status(p):
    if p < threshold["caution"]:     return "safe"
    elif p < threshold["danger"]:    return "caution"
    elif p < threshold["emergency"]: return "danger"
    else:                            return "emergency"

def get_status_korean(p):
    if p < threshold["caution"]:     return "안전"
    elif p < threshold["danger"]:    return "주의"
    elif p < threshold["emergency"]: return "위험"
    else:                            return "긴급"

def get_elapsed():
    e = int(time.time()-start_time)
    return str(e//60)+":"+"{:02d}".format(e%60)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    print("Wi-Fi 연결 중", end="")
    t = 0
    while not wlan.isconnected():
        print(".", end=""); time.sleep(0.5); t+=1
        if t>20: print("\n실패!"); return None
    ip = wlan.ifconfig()[0]
    print(f"\n연결 성공! IP: {ip}")
    return ip

HTML = b"""<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>약품 실험실 안전 모니터링</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#f0f4f8;color:#2d3748;padding:16px}
h1{text-align:center;font-size:1.35em;margin-bottom:16px;color:#2b6cb0;font-weight:700;letter-spacing:-.5px}

/* 상태 배너 */
.sb{text-align:center;padding:16px;border-radius:14px;margin-bottom:14px;
font-size:1.8em;font-weight:700;box-shadow:0 4px 15px rgba(0,0,0,.1)}
.safe{background:linear-gradient(135deg,#38a169,#48bb78);color:white}
.caution{background:linear-gradient(135deg,#d69e2e,#ecc94b);color:white}
.danger{background:linear-gradient(135deg,#c53030,#e53e3e);color:white}
.emergency{background:linear-gradient(135deg,#822727,#c53030);color:white;
animation:bk .4s infinite}
@keyframes bk{0%,100%{opacity:1}50%{opacity:.6}}

/* 카드 */
.g2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
.g4{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;margin-bottom:12px}
.card{background:white;border-radius:12px;padding:14px;text-align:center;
box-shadow:0 2px 10px rgba(0,0,0,.07);border:1px solid #e2e8f0}
.lb{font-size:.72em;color:#718096;margin-bottom:6px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.vl{font-size:1.7em;font-weight:700;color:#2b6cb0;min-height:36px;
display:flex;align-items:center;justify-content:center}
.mx{color:#e53e3e}.mn{color:#38a169}.dc{color:#d69e2e}.tm{color:#805ad5}

/* 단계 표시 */
.lg{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;margin-bottom:12px}
.li{border-radius:10px;padding:8px 4px;text-align:center;font-size:.72em;
font-weight:700;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.ls{background:linear-gradient(135deg,#c6f6d5,#9ae6b4);color:#276749}
.lc{background:linear-gradient(135deg,#fefcbf,#faf089);color:#744210}
.ld{background:linear-gradient(135deg,#fed7d7,#feb2b2);color:#822727}
.le{background:linear-gradient(135deg,#822727,#c53030);color:white}

/* LED 박스 */
.led-box{background:white;border-radius:12px;padding:14px;
box-shadow:0 2px 10px rgba(0,0,0,.07);border:1px solid #e2e8f0;
margin-bottom:12px;text-align:center}
.led-box h3{color:#2b6cb0;font-size:.85em;margin-bottom:10px;font-weight:700}
.led-row{display:flex;justify-content:center;gap:10px}
.led-dot{width:30px;height:30px;border-radius:50%;background:#e2e8f0;
border:2px solid #cbd5e0;transition:all .3s}

/* 그래프 */
.cb{background:white;border-radius:14px;padding:18px;
box-shadow:0 2px 10px rgba(0,0,0,.07);border:1px solid #e2e8f0;margin-bottom:12px}
.ct{color:#4a5568;font-size:.85em;margin-bottom:10px;font-weight:700}
canvas{display:block;width:100%}

/* 임계값 설정 */
.tb{background:white;border-radius:12px;padding:14px;
box-shadow:0 2px 10px rgba(0,0,0,.07);border:1px solid #e2e8f0;margin-bottom:12px}
.tb h3{color:#2b6cb0;font-size:.88em;margin-bottom:3px;font-weight:700}
.tb p{color:#a0aec0;font-size:.72em;margin-bottom:12px}
.tr{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.tr label{color:#4a5568;font-size:.8em;width:55px;flex-shrink:0;font-weight:600}
.tr input[type=range]{flex:1;accent-color:#4299e1;cursor:pointer;height:5px}
.tr span{font-size:.9em;width:42px;text-align:right;font-weight:700}
.c1{color:#d69e2e}.c2{color:#e53e3e}.c3{color:#822727}
.br{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}
.bt{padding:10px;background:linear-gradient(135deg,#3182ce,#4299e1);
border:none;border-radius:8px;color:white;font-size:.88em;cursor:pointer;font-weight:600}
.bt:hover{background:linear-gradient(135deg,#2c5282,#3182ce)}
.bd{padding:10px;background:linear-gradient(135deg,#dd6b20,#ed8936);
border:none;border-radius:8px;color:white;font-size:.88em;cursor:pointer;font-weight:600}
.bd:hover{background:linear-gradient(135deg,#c05621,#dd6b20)}
.rb{width:100%;padding:9px;
background:linear-gradient(135deg,#e53e3e,#fc8181);
border:none;border-radius:8px;color:white;
font-size:.83em;cursor:pointer;margin-bottom:12px;font-weight:600}
.rb:hover{background:linear-gradient(135deg,#c53030,#e53e3e)}
.cs{text-align:center;font-size:.73em;padding:5px;border-radius:8px}
.ok{color:#38a169;background:#f0fff4;border:1px solid #c6f6d5}
.er{color:#e53e3e;background:#fff5f5;border:1px solid #fed7d7}
.pt{color:#d69e2e;font-size:.72em;text-align:center;margin-top:6px;
background:#fffff0;border-radius:6px;padding:4px;display:none;
border:1px solid #faf089}
.pn{border-color:#d69e2e!important;border-width:2px!important}
</style></head><body>
<h1>💊🧪 약품 실험실 안전 모니터링</h1>
<div class="sb safe" id="sb">🟢 안전</div>
<div class="g2">
<div class="card"><div class="lb">📡 센서 원시값</div><div class="vl" id="rv">---</div></div>
<div class="card"><div class="lb">💨 현재 가스 농도</div><div class="vl" id="gp">--.- %</div></div>
</div>
<div class="g4">
<div class="card"><div class="lb">📈 최고값</div><div class="vl mx" id="mx">0.0%</div></div>
<div class="card"><div class="lb">📉 최저값</div><div class="vl mn" id="mn">100%</div></div>
<div class="card"><div class="lb">⚠️ 위험 횟수</div><div class="vl dc" id="dc">0회</div></div>
<div class="card"><div class="lb">⏱️ 경과</div><div class="vl tm" id="et">0:00</div></div>
</div>
<div class="lg">
<div class="li ls">🟢 안전<br><span id="r1">0~46%</span></div>
<div class="li lc">🟡 주의<br><span id="r2">46~69%</span></div>
<div class="li ld">🔴 위험<br><span id="r3">69~87%</span></div>
<div class="li le">🚨 긴급<br><span id="r4">87%~</span></div>
</div>
<div class="led-box">
<h3>💡 네오픽셀 LED 현재 상태</h3>
<div class="led-row" id="ledrow"></div>
</div>
<div class="cb">
<div class="ct">📈 실시간 가스 농도 그래프</div>
<canvas id="cv" height="340"></canvas>
</div>
<div class="tb" id="tb">
<h3>⚙️ 위험 임계값 설정</h3>
<p>슬라이더 조절 후 ✅ 적용 버튼을 눌러주세요</p>
<div class="tr"><label>🟡 주의</label>
<input type="range" id="s1" min="10" max="60" value="46" oninput="onSl(1,this.value)">
<span class="c1" id="v1">46%</span></div>
<div class="tr"><label>🔴 위험</label>
<input type="range" id="s2" min="30" max="80" value="69" oninput="onSl(2,this.value)">
<span class="c2" id="v2">69%</span></div>
<div class="tr"><label>🚨 긴급</label>
<input type="range" id="s3" min="50" max="95" value="87" oninput="onSl(3,this.value)">
<span class="c3" id="v3">87%</span></div>
<div class="pt" id="pt">⏳ 변경됨 - 적용 버튼을 눌러주세요!</div>
<div class="br">
<button class="bt" onclick="setTh()">✅ 임계값 적용</button>
<button class="bd" onclick="loadDef()">↩️ 기본값 복원</button>
</div></div>
<button class="rb" onclick="resetData()">🔄 측정 데이터 초기화</button>
<div class="cs" id="cs">연결 중...</div>
<script src="/js"></script>
</body></html>"""

JS = b"""
var cv=document.getElementById('cv');
var cx=cv.getContext('2d');
var da=[],ta=[],MX=60;
var th={caution:46,danger:69,emergency:87};
var sliding=false,stimer=null;

var ledrow=document.getElementById('ledrow');
for(var i=0;i<10;i++){
var d=document.createElement('div');
d.className='led-dot';d.id='ld'+i;
ledrow.appendChild(d);}

function updateLedUI(percent,status){
var color,glow,border;
if(status==='emergency'){color='#fc5c5c';glow='0 0 14px #e53e3e';border='#e53e3e';}
else if(status==='danger'){color='#fc8181';glow='0 0 12px #e53e3e';border='#e53e3e';}
else if(status==='caution'){color='#f6e05e';glow='0 0 12px #d69e2e';border='#d69e2e';}
else{color='#68d391';glow='0 0 12px #38a169';border='#38a169';}
var count=Math.min(Math.floor((percent/100)*10)+1,10);
for(var i=0;i<10;i++){
var dot=document.getElementById('ld'+i);
if(i<count){
dot.style.background=color;
dot.style.borderColor=border;
dot.style.boxShadow=glow;}
else{
dot.style.background='#e2e8f0';
dot.style.borderColor='#cbd5e0';
dot.style.boxShadow='none';}}}

function loadSaved(){
var s=localStorage.getItem('th');
if(s){try{th=JSON.parse(s);setSUI(th);}catch(e){}}
}
function setSUI(s){
document.getElementById('s1').value=s.caution;
document.getElementById('v1').textContent=s.caution+'%';
document.getElementById('s2').value=s.danger;
document.getElementById('v2').textContent=s.danger+'%';
document.getElementById('s3').value=s.emergency;
document.getElementById('v3').textContent=s.emergency+'%';
setRL(s);}
function setRL(s){
document.getElementById('r1').textContent='0~'+s.caution+'%';
document.getElementById('r2').textContent=s.caution+'~'+s.danger+'%';
document.getElementById('r3').textContent=s.danger+'~'+s.emergency+'%';
document.getElementById('r4').textContent=s.emergency+'%~';}
function onSl(n,v){
sliding=true;
document.getElementById('v'+n).textContent=v+'%';
document.getElementById('pt').style.display='block';
document.getElementById('tb').classList.add('pn');
if(stimer)clearTimeout(stimer);
stimer=setTimeout(function(){sliding=false;},8000);}

function draw(){
var W=cv.offsetWidth||800,H=340;
cv.width=W;cv.height=H;
var PL=46,PR=12,PT=18,PB=42,GW=W-PL-PR,GH=H-PT-PB;

// 밝은 배경
cx.fillStyle='#f7fafc';cx.fillRect(0,0,W,H);

// 그리드
[0,10,20,30,40,50,60,70,80,90,100].forEach(function(p){
var y=PT+GH-(p/100)*GH;
cx.strokeStyle=p%25===0?'#cbd5e0':'#edf2f7';
cx.lineWidth=p%25===0?1.2:0.8;
cx.beginPath();cx.moveTo(PL,y);cx.lineTo(PL+GW,y);cx.stroke();
cx.fillStyle=p%25===0?'#4a5568':'#a0aec0';
cx.font=p%25===0?'bold 11px sans-serif':'9px sans-serif';
cx.textAlign='right';cx.fillText(p+'%',PL-5,y+4);});

// 임계선
[{p:th.caution,c:'rgba(214,158,46,.8)',t:'주의'+th.caution+'%'},
{p:th.danger,c:'rgba(229,62,62,.8)',t:'위험'+th.danger+'%'},
{p:th.emergency,c:'rgba(130,39,39,1)',t:'긴급'+th.emergency+'%'}
].forEach(function(ln){
var y=PT+GH-(ln.p/100)*GH;
cx.strokeStyle=ln.c;cx.lineWidth=1.8;cx.setLineDash([7,5]);
cx.beginPath();cx.moveTo(PL,y);cx.lineTo(PL+GW,y);cx.stroke();
cx.setLineDash([]);cx.fillStyle=ln.c;cx.font='bold 10px sans-serif';
cx.textAlign='left';cx.fillText(ln.t,PL+5,y-4);});

if(da.length<2){
cx.fillStyle='#a0aec0';cx.font='15px sans-serif';cx.textAlign='center';
cx.fillText('데이터 수집 중...',W/2,H/2);return;}

// 면적
cx.beginPath();
da.forEach(function(v,i){
var x=PL+(i/(MX-1))*GW,y=PT+GH-(v/100)*GH;
i===0?cx.moveTo(x,y):cx.lineTo(x,y);});
var lx=PL+((da.length-1)/(MX-1))*GW;
cx.lineTo(lx,PT+GH);cx.lineTo(PL,PT+GH);cx.closePath();
var g=cx.createLinearGradient(0,PT,0,PT+GH);
g.addColorStop(0,'rgba(66,153,225,.3)');
g.addColorStop(1,'rgba(66,153,225,.02)');
cx.fillStyle=g;cx.fill();

// 실선
cx.beginPath();cx.strokeStyle='#3182ce';cx.lineWidth=2.8;
cx.lineJoin='round';cx.lineCap='round';
da.forEach(function(v,i){
var x=PL+(i/(MX-1))*GW,y=PT+GH-(v/100)*GH;
i===0?cx.moveTo(x,y):cx.lineTo(x,y);});
cx.stroke();

// 최신 점
var lv=da[da.length-1];
var lxp=PL+((da.length-1)/(MX-1))*GW;
var lyp=PT+GH-(lv/100)*GH;
cx.beginPath();cx.arc(lxp,lyp,6,0,Math.PI*2);
cx.fillStyle='#3182ce';cx.fill();
cx.strokeStyle='white';cx.lineWidth=2;cx.stroke();
cx.fillStyle='#2d3748';cx.font='bold 12px sans-serif';
cx.textAlign='center';cx.fillText(lv+'%',lxp,lyp-12);

// 시간축
var step=Math.max(1,Math.floor(da.length/6));
for(var i=0;i<da.length;i+=step){
var x=PL+(i/(MX-1))*GW;
cx.strokeStyle='#e2e8f0';cx.lineWidth=1;
cx.beginPath();cx.moveTo(x,PT+GH);cx.lineTo(x,PT+GH+4);cx.stroke();
cx.fillStyle='#718096';cx.font='9px sans-serif';cx.textAlign='center';
cx.fillText(ta[i]||'',x,PT+GH+16);}
cx.strokeStyle='#cbd5e0';cx.lineWidth=1.5;
cx.beginPath();cx.moveTo(PL,PT+GH);cx.lineTo(PL+GW,PT+GH);cx.stroke();}

var SC={
safe:{c:'sb safe',t:'🟢 안전'},
caution:{c:'sb caution',t:'🟡 주의'},
danger:{c:'sb danger',t:'🔴 위험'},
emergency:{c:'sb emergency',t:'🚨 긴급 대피!'}};
var ec=0,busy=false;

function fetchData(){
if(busy)return;busy=true;
var xhr=new XMLHttpRequest();
xhr.timeout=3000;
xhr.open('GET','/data?t='+Date.now(),true);
xhr.onreadystatechange=function(){
if(xhr.readyState!==4)return;
busy=false;
if(xhr.status===200){
try{
var d=JSON.parse(xhr.responseText.trim());
document.getElementById('rv').textContent=d.raw!==undefined?String(d.raw):'---';
document.getElementById('gp').textContent=d.percent!==undefined?String(d.percent)+' %':'--.- %';
document.getElementById('mx').textContent=d.max_p!==undefined?String(d.max_p)+'%':'--';
document.getElementById('mn').textContent=d.min_p!==undefined?String(d.min_p)+'%':'--';
document.getElementById('dc').textContent=d.danger_cnt!==undefined?String(d.danger_cnt)+'회':'0회';
document.getElementById('et').textContent=d.elapsed||'0:00';
if(d.status){
var s=SC[d.status]||SC.safe;
var sb=document.getElementById('sb');
sb.className=s.c;sb.textContent=s.t;
updateLedUI(d.percent,d.status);}
if(d.percent!==undefined){
var n=new Date();
var ts=n.getHours()+':'+String(n.getMinutes()).padStart(2,'0')+':'+String(n.getSeconds()).padStart(2,'0');
da.push(Number(d.percent));ta.push(ts);
if(da.length>MX){da.shift();ta.shift();}
draw();}
if(d.threshold&&!sliding){th=d.threshold;}
ec=0;
var el=document.getElementById('cs');
el.className='cs ok';
el.textContent='✅ '+new Date().toLocaleTimeString()+' 업데이트';
}catch(e){
ec++;
var el=document.getElementById('cs');
el.className='cs er';
el.textContent='❌ 파싱오류';}}
else{ec++;
var el=document.getElementById('cs');
el.className='cs er';
el.textContent='❌ HTTP'+xhr.status;}};
xhr.ontimeout=function(){busy=false;ec++;
var el=document.getElementById('cs');
el.className='cs er';el.textContent='❌ 타임아웃';};
xhr.onerror=function(){busy=false;ec++;
var el=document.getElementById('cs');
el.className='cs er';el.textContent='❌ 연결실패';};
xhr.send();}

function setTh(){
var c=parseInt(document.getElementById('s1').value);
var d=parseInt(document.getElementById('s2').value);
var e=parseInt(document.getElementById('s3').value);
if(c>=d||d>=e){alert('주의 < 위험 < 긴급 순서로 설정하세요!');return;}
var xhr=new XMLHttpRequest();
xhr.open('POST','/threshold',true);
xhr.setRequestHeader('Content-Type','application/json');
xhr.onreadystatechange=function(){
if(xhr.readyState===4&&xhr.status===200){
th={caution:c,danger:d,emergency:e};
localStorage.setItem('th',JSON.stringify(th));
sliding=false;
document.getElementById('pt').style.display='none';
document.getElementById('tb').classList.remove('pn');
setRL(th);draw();
alert('✅ 임계값 저장 완료!\\n주의:'+c+'%  위험:'+d+'%  긴급:'+e+'%\\n새로고침해도 유지됩니다!');}};
xhr.send(JSON.stringify({caution:c,danger:d,emergency:e}));}

function loadDef(){
if(!confirm('기본값으로 복원할까요?\\n주의:46%  위험:69%  긴급:87%'))return;
setSUI({caution:46,danger:69,emergency:87});
sliding=true;
document.getElementById('pt').style.display='block';
document.getElementById('tb').classList.add('pn');}

function resetData(){
if(!confirm('측정 데이터를 초기화할까요?'))return;
var xhr=new XMLHttpRequest();
xhr.open('POST','/reset',true);
xhr.onreadystatechange=function(){
if(xhr.readyState===4&&xhr.status===200){
da=[];ta=[];
document.getElementById('mx').textContent='0.0%';
document.getElementById('mn').textContent='100%';
document.getElementById('dc').textContent='0회';
document.getElementById('et').textContent='0:00';
draw();alert('✅ 초기화 완료!');}};
xhr.send();}

window.addEventListener('load',function(){
loadSaved();draw();fetchData();setInterval(fetchData,1500);});
window.addEventListener('resize',draw);
"""

def send_data(conn):
    global max_percent,min_percent,danger_count
    raw     = gas_sensor.read_u16()
    percent = get_gas_percentage(raw)
    status  = get_status(percent)
    if percent>max_percent: max_percent=percent
    if percent<min_percent: min_percent=percent
    if status in("danger","emergency"): danger_count+=1
    update_led(percent)
    print(f"  raw={raw} | {percent}% | {get_status_korean(percent)}")
    sensor_data.append(percent)
    if len(sensor_data)>60: sensor_data.pop(0)
    elapsed=get_elapsed()
    body=(
        '{"raw":'+str(raw)+
        ',"percent":'+str(percent)+
        ',"status":"'+status+'"'+
        ',"max_p":'+str(max_percent)+
        ',"min_p":'+str(min_percent)+
        ',"danger_cnt":'+str(danger_count)+
        ',"elapsed":"'+elapsed+'"'+
        ',"threshold":{"caution":'+str(threshold["caution"])+
        ',"danger":'+str(threshold["danger"])+
        ',"emergency":'+str(threshold["emergency"])+'}}')
    body_bytes=body.encode('utf-8')
    header=(
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: "+str(len(body_bytes))+"\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Cache-Control: no-cache\r\n"
        "Connection: close\r\n\r\n")
    conn.sendall(header.encode('utf-8'))
    conn.sendall(body_bytes)

def send_js(conn):
    header=(
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/javascript\r\n"
        "Content-Length: "+str(len(JS))+"\r\n"
        "Connection: close\r\n\r\n").encode()
    conn.sendall(header)
    for i in range(0,len(JS),256):
        conn.sendall(JS[i:i+256])

def handle_threshold(conn,request):
    global threshold
    try:
        body=request.split('\r\n\r\n')[-1]
        data=json.loads(body)
        threshold["caution"]  =int(data["caution"])
        threshold["danger"]   =int(data["danger"])
        threshold["emergency"]=int(data["emergency"])
        print(f"임계값 변경: {threshold}")
        conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
    except Exception as e:
        print(f"임계값 오류: {e}")
        conn.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 2\r\n\r\nER")

def handle_reset(conn):
    global max_percent,min_percent,danger_count,start_time,sensor_data
    max_percent=0.0; min_percent=100.0; danger_count=0
    start_time=time.time(); sensor_data=[]
    print("데이터 초기화!")
    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")

def send_html(conn):
    header=(
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "Content-Length: "+str(len(HTML))+"\r\n"
        "Connection: close\r\n\r\n").encode()
    conn.sendall(header)
    for i in range(0,len(HTML),256):
        conn.sendall(HTML[i:i+256])

def handle_request(conn):
    try:
        request=conn.recv(2048).decode('utf-8','ignore')
        first=request.split('\n')[0].strip()
        print(f"요청: {first}")
        if 'POST /threshold' in request: handle_threshold(conn,request)
        elif 'POST /reset' in request: handle_reset(conn)
        elif 'GET /js' in request: send_js(conn)
        elif '/data' in request: send_data(conn)
        elif 'favicon' in request:
            conn.sendall(b"HTTP/1.1 204 No Content\r\nConnection: close\r\n\r\n")
        else: send_html(conn)
    except Exception as e:
        print(f"오류: {e}")
    finally:
        conn.close()

print("="*40)
print("  약품 실험실 스마트 안전 관리 시스템")
print("  Raspberry Pi Pico 2 WH + MQ2 센서")
print("="*40)

led_set_all(0,80,0); time.sleep(1); led_off()

ip=connect_wifi()
if ip is None:
    print("Wi-Fi 연결 실패!"); raise SystemExit

server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
server.bind(('0.0.0.0',80))
server.listen(5)
print(f"웹서버 → http://{ip}")
print("="*40)

while True:
    try:
        conn,addr=server.accept()
        handle_request(conn)
    except Exception as e:
        print(f"서버 오류: {e}")
