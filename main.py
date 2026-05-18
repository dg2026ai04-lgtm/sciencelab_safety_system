import network, socket, time, json
from machine import ADC, Pin, PWM
from wifi_config import WIFI_SSID, WIFI_PASSWORD

# ════════════════════════════════════════════
#  센서 & LED 설정
# ════════════════════════════════════════════
gas_sensor = ADC(Pin(26))          # MQ-2 → GP26 (ADC0)

led_r = PWM(Pin(13)); led_r.freq(1000)
led_g = PWM(Pin(14)); led_g.freq(1000)
led_b = PWM(Pin(15)); led_b.freq(1000)

def set_rgb(r, g, b):
    led_r.duty_u16(int(r / 255 * 65535))
    led_g.duty_u16(int(g / 255 * 65535))
    led_b.duty_u16(int(b / 255 * 65535))

def led_off():
    led_r.duty_u16(0)
    led_g.duty_u16(0)
    led_b.duty_u16(0)

# ════════════════════════════════════════════
#  상태 정의
# ════════════════════════════════════════════
#  상태명 : (R, G, B, 설명)
STATE_MAP = {
    "SAFE"    : (  0, 255,   0, "정상 — 안전"),
    "NOTICE"  : (  0, 200, 255, "미세 감지"),
    "WARNING" : (255, 165,   0, "주의 — 농도 상승"),
    "HIGH"    : (255,  60,   0, "경고 — 높은 농도"),
    "DANGER"  : (255,   0,   0, "위험 — 대피 권고"),
    "CRITICAL": (255,   0, 150, "긴급 — 즉시 대피!"),
}

STATE_ORDER = ["SAFE","NOTICE","WARNING","HIGH","DANGER","CRITICAL"]

def get_state(val):
    if   val < 10000: return "SAFE"
    elif val < 20000: return "NOTICE"
    elif val < 35000: return "WARNING"
    elif val < 45000: return "HIGH"
    elif val < 55000: return "DANGER"
    else:             return "CRITICAL"

# ════════════════════════════════════════════
#  LED 효과 함수
# ════════════════════════════════════════════
def breathe(r, g, b, step=8, delay=6):
    """부드러운 숨쉬기 (1사이클)"""
    for i in range(0, 256, step):
        set_rgb(int(r*i/255), int(g*i/255), int(b*i/255))
        time.sleep_ms(delay)
    for i in range(255, -1, -step):
        set_rgb(int(r*i/255), int(g*i/255), int(b*i/255))
        time.sleep_ms(delay)

def blink(r, g, b, times=2, on_ms=200, off_ms=150):
    """점멸"""
    for _ in range(times):
        set_rgb(r, g, b); time.sleep_ms(on_ms)
        led_off();         time.sleep_ms(off_ms)

def fast_pulse(r, g, b, cycles=3, step=25, delay=4):
    """빠른 펄스"""
    for _ in range(cycles):
        for i in range(0, 256, step):
            set_rgb(int(r*i/255), int(g*i/255), int(b*i/255))
            time.sleep_ms(delay)
        for i in range(255, -1, -step):
            set_rgb(int(r*i/255), int(g*i/255), int(b*i/255))
            time.sleep_ms(delay)

def sos(r, g, b):
    """SOS 점멸 — 극위험"""
    for dur in [150,150,150, 400,400,400, 150,150,150]:
        set_rgb(r, g, b); time.sleep_ms(dur)
        led_off();         time.sleep_ms(100)

def rainbow_flash():
    """상태 악화 시 무지개 전환 플래시"""
    for r,g,b in [(255,0,0),(255,128,0),(255,255,0),
                  (0,255,0),(0,0,255),(128,0,255)]:
        set_rgb(r,g,b); time.sleep_ms(60)
    led_off()

# ════════════════════════════════════════════
#  LED 메인 업데이트 (★ 핵심 함수)
# ════════════════════════════════════════════
prev_state = None

def update_led(state):
    global prev_state
    r, g, b, desc = STATE_MAP[state]

    # 상태 악화 시 → 무지개 플래시 먼저
    if (prev_state is not None
            and STATE_ORDER.index(state) > STATE_ORDER.index(prev_state)):
        rainbow_flash()

    prev_state = state

    # 상태별 LED 효과
    if   state == "SAFE"    : breathe(r, g, b, step=6, delay=8)
    elif state == "NOTICE"  : breathe(r, g, b, step=8, delay=5)
    elif state == "WARNING" : blink(r, g, b, times=2, on_ms=300, off_ms=200)
    elif state == "HIGH"    : blink(r, g, b, times=3, on_ms=150, off_ms=100)
    elif state == "DANGER"  : fast_pulse(r, g, b, cycles=3)
    elif state == "CRITICAL": sos(r, g, b)

    print(f"[LED] {state:8s} | ADC값 표시 중 | {desc}")

# ════════════════════════════════════════════
#  Wi-Fi 연결 (보조)
# ════════════════════════════════════════════
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    print("Wi-Fi 연결 중", end="")
    for _ in range(20):
        if wlan.isconnected(): break
        # 연결 중 : 파란색 점멸
        set_rgb(0, 0, 200); time.sleep_ms(300)
        led_off();           time.sleep_ms(300)
        print(".", end="")
    if wlan.isconnected():
        # 성공 : 흰색 3번
        for _ in range(3):
            set_rgb(255,255,255); time.sleep_ms(100)
            led_off();            time.sleep_ms(100)
        ip = wlan.ifconfig()[0]
        print(f"\n연결 성공 → http://{ip}")
        return ip
    print("\nWi-Fi 실패 — 오프라인 모드로 실행")
    return None

# ════════════════════════════════════════════
#  HTML (보조 — 간단하게 유지)
# ════════════════════════════════════════════
HTML = """<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MQ-2 MONITOR</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0b0f1a;color:#e2e8f0;font-family:monospace;padding:20px}
h1{color:#00aaff;font-size:1.2rem;letter-spacing:4px;margin-bottom:4px}
.sub{color:#4b6280;font-size:.65rem;letter-spacing:3px;margin-bottom:16px}
.live{display:inline-flex;align-items:center;gap:6px;
  background:rgba(0,170,255,.07);border:1px solid rgba(0,170,255,.25);
  border-radius:999px;padding:4px 14px;font-size:.65rem;
  letter-spacing:2px;color:#00aaff;margin-bottom:20px}
.dot{width:7px;height:7px;border-radius:50%;background:#00ff88;
  box-shadow:0 0 6px #00ff8888;animation:lp 1s infinite}
@keyframes lp{0%,100%{opacity:1}50%{opacity:.2}}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:12px;margin-bottom:20px}
.card{background:#111827;border:1px solid #1e3a5f;border-radius:12px;
  padding:16px;transition:border-color .4s,box-shadow .4s,background .4s}
.cl{font-size:.6rem;letter-spacing:2px;color:#4b6280;margin-bottom:8px}
.cv{font-size:1.5rem;font-weight:bold;transition:color .3s,text-shadow .3s}
.cu{font-size:.6rem;color:#4b6280;margin-top:4px}
.panel{background:#0d1525;border:1px solid #1e3a5f;border-radius:12px;padding:16px}
.pt{font-size:.65rem;letter-spacing:2px;color:#4b6280;margin-bottom:10px}
#alert{display:none;border-radius:8px;padding:10px 16px;
  margin-bottom:16px;font-size:.8rem;letter-spacing:2px;
  animation:ab .6s infinite alternate}
@keyframes ab{from{opacity:1}to{opacity:.4}}
</style></head><body>
<h1>MQ-2 GAS MONITOR</h1>
<div class="sub">RASPBERRY PI PICO 2 WH / ADC0 GP26</div>
<div class="live"><span class="dot"></span>LIVE</div>
<div id="alert">⚠ <span id="atxt"></span></div>
<div class="cards">
  <div class="card"><div class="cl">▸ ADC RAW</div>
    <div class="cv" id="vr">—</div><div class="cu">0~65535</div></div>
  <div class="card"><div class="cl">▸ VOLTAGE</div>
    <div class="cv" id="vv">—</div><div class="cu">VOLTS</div></div>
  <div class="card"><div class="cl">▸ LEVEL</div>
    <div class="cv" id="vp">—</div><div class="cu">%</div></div>
  <div class="card" id="cs"><div class="cl">▸ STATUS</div>
    <div class="cv" id="vs">—</div>
    <div class="cu" id="sh">INITIALIZING</div></div>
</div>
<div class="panel">
  <div class="pt">▸ WAVEFORM</div>
  <canvas id="gc" height="110"></canvas>
</div>
<script>
const MAX=60,VREF=3.3,ADC_MAX=65535;
const S={
  SAFE    :{c:'#00ff88',bg:'rgba(0,255,136,.07)',h:'ALL CLEAR',alert:false},
  NOTICE  :{c:'#00ccff',bg:'rgba(0,204,255,.07)',h:'SLIGHT DETECTION',alert:false},
  WARNING :{c:'#ffaa00',bg:'rgba(255,170,0,.07)',h:'CAUTION',alert:true},
  HIGH    :{c:'#ff6600',bg:'rgba(255,102,0,.07)',h:'HIGH LEVEL',alert:true},
  DANGER  :{c:'#ff2244',bg:'rgba(255,34,68,.07)',h:'HAZARDOUS!',alert:true},
  CRITICAL:{c:'#ff00aa',bg:'rgba(255,0,170,.07)',h:'EVACUATE NOW!',alert:true},
};
function getState(v){
  return v<10000?'SAFE':v<20000?'NOTICE':v<35000?'WARNING':
         v<45000?'HIGH':v<55000?'DANGER':'CRITICAL';
}
let lb=[],dt=[],prev=null,ela=0;
const chart=new Chart(document.getElementById('gc').getContext('2d'),{
  type:'line',
  data:{labels:lb,datasets:[{data:dt,borderColor:'#00ff88',
    backgroundColor:'rgba(0,255,136,.06)',borderWidth:2,
    pointRadius:1,tension:.35,fill:true}]},
  options:{responsive:true,animation:{duration:150},
    scales:{
      x:{ticks:{color:'#2a3f5f',maxTicksLimit:6,font:{size:9}},
         grid:{color:'rgba(30,58,95,.4)'}},
      y:{ticks:{color:'#2a3f5f',font:{size:9}},
         grid:{color:'rgba(30,58,95,.4)'}}},
    plugins:{legend:{display:false}}}
});
function updateUI(v,state){
  const cfg=S[state],c=cfg.c;
  document.getElementById('vr').textContent=v.toLocaleString();
  document.getElementById('vv').textContent=(v/ADC_MAX*VREF).toFixed(3);
  document.getElementById('vp').textContent=(v/ADC_MAX*100).toFixed(1);
  document.getElementById('vs').textContent=state;
  document.getElementById('sh').textContent=cfg.h;
  ['vr','vv','vp','vs'].forEach(id=>{
    const el=document.getElementById(id);
    el.style.color=c; el.style.textShadow=`0 0 10px ${c}`;
  });
  const cs=document.getElementById('cs');
  cs.style.borderColor=c;
  cs.style.boxShadow=`0 0 18px ${c}44`;
  cs.style.background=cfg.bg;
  const al=document.getElementById('alert');
  if(cfg.alert){
    al.style.display='block';
    al.style.background=cfg.bg;
    al.style.border=`1px solid ${c}`;
    al.style.color=c;
    document.getElementById('atxt').textContent=
      `${state} — ${cfg.h} [ ${v.toLocaleString()} ]`;
  } else { al.style.display='none'; }
  if(state!==prev){
    chart.data.datasets[0].borderColor=c;
    chart.data.datasets[0].backgroundColor=cfg.bg;
    prev=state;
  }
}
async function fetchData(){
  try{
    const j=await(await fetch('/data')).json();
    ela+=.5;
    if(lb.length>=MAX){lb.shift();dt.shift();}
    lb.push(ela.toFixed(1)+'s');
    dt.push(j.value);
    updateUI(j.value, j.state);
    chart.update();
  }catch(e){console.warn(e);}
}
setInterval(fetchData,500);
fetchData();
</script></body></html>"""

# ════════════════════════════════════════════
#  웹 서버 (논블로킹 — 메인 루프 방해 안 함)
# ════════════════════════════════════════════
def send_response(conn, status, ctype, body):
    b = body.encode() if isinstance(body, str) else body
    conn.sendall(
        f"HTTP/1.1 {status}\r\nContent-Type:{ctype};charset=utf-8\r\n"
        f"Content-Length:{len(b)}\r\nConnection:close\r\n\r\n".encode() + b
    )

def parse_path(req):
    try:    return req.decode().split("\r\n")[0].split(" ")[1]
    except: return "/"

def handle_web(srv, val, state):
    """웹 요청이 있을 때만 처리 (논블로킹)"""
    srv.setblocking(False)
    conn = None
    try:
        conn, addr = srv.accept()
        conn.settimeout(2.0)
        path = parse_path(conn.recv(1024))
        if path == "/data":
            send_response(conn, "200 OK", "application/json",
                          json.dumps({"value": val, "state": state}))
        else:
            send_response(conn, "200 OK", "text/html", HTML)
    except OSError:
        pass   # 요청 없으면 그냥 통과
    finally:
        if conn: conn.close()

# ════════════════════════════════════════════
#  메인 루프 (★ 센서 + LED가 주인공)
# ════════════════════════════════════════════
def main():
    # Wi-Fi & 서버 (실패해도 센서/LED는 동작)
    ip  = connect_wifi()
    srv = None
    if ip:
        srv = socket.socket()
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(socket.getaddrinfo(ip, 80)[0][-1])
        srv.listen(3)
        print(f"웹 서버 → http://{ip}  (보조 기능)")

    print("\n===== 센서 모니터링 시작 =====")

    while True:
        # ① 센서 읽기
        val   = gas_sensor.read_u16()
        state = get_state(val)
        r, g, b, desc = STATE_MAP[state]

        print(f"ADC:{val:6d} | 상태:{state:8s} | {desc}")

        # ② LED 업데이트 (★ 최우선)
        update_led(state)

        # ③ 웹 요청 처리 (있을 때만, 없으면 즉시 통과)
        if srv:
            handle_web(srv, val, state)

        # ④ 루프 간격 (LED 효과 속도에 따라 자동 조절됨)

main()
