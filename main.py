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

# =============================================
# 전역 변수
# =============================================
sensor_data = []
MAX_DATA    = 50

# =============================================
# LED 제어
# =============================================
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

# =============================================
# 센서값 변환
# =============================================
def get_gas_percentage(raw):
    return round((raw / 65535) * 100, 1)

def get_status(raw):
    if raw < 30000:
        return "safe"
    elif raw < 45000:
        return "caution"
    elif raw < 57000:
        return "danger"
    else:
        return "emergency"

def get_status_korean(raw):
    if raw < 30000:
        return "안전"
    elif raw < 45000:
        return "주의"
    elif raw < 57000:
        return "위험"
    else:
        return "긴급"

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
            print("\nWi-Fi 연결 실패!")
            return None

    ip = wlan.ifconfig()[0]
    print(f"\n연결 성공! IP: {ip}")
    return ip

# =============================================
# HTML (센서값 표시 + 실시간 그래프)
# =============================================
def get_html():
    return """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>약품 실험실 안전 모니터링</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', sans-serif;
            background: #0f0f1a;
            color: white;
            padding: 20px;
            min-height: 100vh;
        }

        h1 {
            text-align: center;
            font-size: 1.6em;
            margin-bottom: 25px;
            color: #00d4ff;
            letter-spacing: 1px;
        }

        /* 상태 박스 */
        .status-box {
            text-align: center;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            font-size: 2em;
            font-weight: bold;
            transition: all 0.3s;
            border: 2px solid transparent;
        }
        .status-safe      { background: #0d3b0d; border-color: #00ff00; color: #00ff00; }
        .status-caution   { background: #3b3b0d; border-color: #ffff00; color: #ffff00; }
        .status-danger    { background: #3b0d0d; border-color: #ff4444; color: #ff4444; }
        .status-emergency { background: #5c0000; border-color: #ff0000; color: #ff0000;
                            animation: blink 0.4s infinite; }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50%       { opacity: 0.4; }
        }

        /* 수치 카드 */
        .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }

        .info-card {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid #2a2a5a;
        }

        .info-card .label {
            font-size: 0.85em;
            color: #888;
            margin-bottom: 10px;
        }

        /* ✅ 수치 크게! */
        .info-card .value {
            font-size: 2.2em;
            font-weight: bold;
            color: #00d4ff;
            font-variant-numeric: tabular-nums;
            min-height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* 단계 범례 */
        .legend-box {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 8px;
            margin-bottom: 20px;
        }

        .legend-item {
            border-radius: 8px;
            padding: 10px 5px;
            text-align: center;
            font-size: 0.75em;
            font-weight: bold;
        }
        .leg-safe      { background: #0d3b0d; color: #00ff00; }
        .leg-caution   { background: #3b3b0d; color: #ffff00; }
        .leg-danger    { background: #3b0d0d; color: #ff4444; }
        .leg-emergency { background: #5c0000; color: #ff6666; }

        /* 그래프 */
        .chart-box {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            height: 480px;
            border: 1px solid #2a2a5a;
            margin-bottom: 20px;
        }

        .chart-box canvas {
            width:  100% !important;
            height: 100% !important;
        }

        /* 연결 상태 */
        .conn-status {
            text-align: center;
            font-size: 0.8em;
            color: #555;
            margin-top: 10px;
        }
        .conn-ok  { color: #00ff00; }
        .conn-err { color: #ff4444; }
    </style>
</head>
<body>

    <h1>💊🧪 약품 실험실 안전 모니터링</h1>

    <!-- 상태 박스 -->
    <div class="status-box status-safe" id="statusBox">
        🟢 안전
    </div>

    <!-- 수치 카드 -->
    <div class="info-grid">
        <div class="info-card">
            <div class="label">📡 센서 원시값</div>
            <div class="value" id="rawValue">---</div>
        </div>
        <div class="info-card">
            <div class="label">💨 가스 농도</div>
            <div class="value" id="gasPercent">--.-&nbsp;%</div>
        </div>
    </div>

    <!-- 단계 범례 -->
    <div class="legend-box">
        <div class="legend-item leg-safe">🟢 안전<br>0~46%</div>
        <div class="legend-item leg-caution">🟡 주의<br>46~69%</div>
        <div class="legend-item leg-danger">🔴 위험<br>69~87%</div>
        <div class="legend-item leg-emergency">🚨 긴급<br>87% 이상</div>
    </div>

    <!-- 실시간 그래프 -->
    <div class="chart-box">
        <canvas id="gasChart"></canvas>
    </div>

    <!-- 연결 상태 -->
    <div class="conn-status" id="connStatus">연결 중...</div>

<script>
// =============================================
// Chart.js 초기화
// =============================================
const ctx = document.getElementById('gasChart').getContext('2d');

const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: '가스 농도 (%)',
                data: [],
                borderColor: '#00d4ff',
                backgroundColor: 'rgba(0,212,255,0.08)',
                borderWidth: 2.5,
                pointRadius: 3,
                pointHoverRadius: 6,
                fill: true,
                tension: 0.35,
                yAxisID: 'y'
            },
            {
                label: '주의 기준 (46%)',
                data: [],
                borderColor: 'rgba(255,255,0,0.7)',
                borderWidth: 1.5,
                borderDash: [6, 4],
                pointRadius: 0,
                fill: false,
                yAxisID: 'y'
            },
            {
                label: '위험 기준 (69%)',
                data: [],
                borderColor: 'rgba(255,68,68,0.7)',
                borderWidth: 1.5,
                borderDash: [6, 4],
                pointRadius: 0,
                fill: false,
                yAxisID: 'y'
            },
            {
                label: '긴급 기준 (87%)',
                data: [],
                borderColor: 'rgba(255,0,0,0.9)',
                borderWidth: 2,
                borderDash: [8, 3],
                pointRadius: 0,
                fill: false,
                yAxisID: 'y'
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 150 },
        interaction: {
            mode: 'index',
            intersect: false
        },
        scales: {
            y: {
                min: 0,
                max: 100,
                ticks: {
                    color: '#aaa',
                    stepSize: 5,
                    callback: v => v + '%'
                },
                grid: { color: '#1e2a4a' },
                title: {
                    display: true,
                    text: '가스 농도 (%)',
                    color: '#aaa'
                }
            },
            x: {
                ticks: {
                    color: '#aaa',
                    maxTicksLimit: 8,
                    maxRotation: 0
                },
                grid: { color: '#1e2a4a' }
            }
        },
        plugins: {
            legend: {
                labels: {
                    color: 'white',
                    font: { size: 11 },
                    usePointStyle: true
                }
            },
            tooltip: {
                backgroundColor: '#1a1a3e',
                titleColor: '#00d4ff',
                bodyColor: 'white',
                borderColor: '#2a2a6a',
                borderWidth: 1,
                callbacks: {
                    label: c => ' ' + c.dataset.label + ': ' + c.parsed.y + '%'
                }
            }
        }
    }
});

// =============================================
// 상태 박스 업데이트
// =============================================
function updateStatusBox(status) {
    const box = document.getElementById('statusBox');

    const config = {
        safe      : { cls: 'status-safe',      text: '🟢 안전'    },
        caution   : { cls: 'status-caution',   text: '🟡 주의'    },
        danger    : { cls: 'status-danger',    text: '🔴 위험'    },
        emergency : { cls: 'status-emergency', text: '🚨 긴급 대피!' }
    };

    const c = config[status] || config['safe'];
    box.className = 'status-box ' + c.cls;
    box.textContent = c.text;
}

// =============================================
// ✅ 핵심 수정: 데이터 가져오기
// =============================================
let errorCount = 0;

function fetchData() {
    fetch('/data', { cache: 'no-store' })
        .then(res => {
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return res.text();           // ✅ text로 먼저 받기
        })
        .then(text => {
            console.log('받은 데이터:', text);   // 디버깅용
            const data = JSON.parse(text);        // ✅ 직접 파싱

            // ✅ 센서 원시값 업데이트
            const rawEl = document.getElementById('rawValue');
            rawEl.textContent = data.raw !== undefined ? data.raw : '---';

            // ✅ 가스 농도 업데이트
            const perEl = document.getElementById('gasPercent');
            perEl.textContent = data.percent !== undefined
                ? data.percent + ' %'
                : '--.- %';

            // 상태 박스 업데이트
            if (data.status) updateStatusBox(data.status);

            // 그래프 업데이트
            const now = new Date().toLocaleTimeString('ko-KR', {
                hour:   '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });

            chart.data.labels.push(now);
            chart.data.datasets[0].data.push(data.percent);
            chart.data.datasets[1].data.push(46);
            chart.data.datasets[2].data.push(69);
            chart.data.datasets[3].data.push(87);

            if (chart.data.labels.length > 50) {
                chart.data.labels.shift();
                chart.data.datasets.forEach(ds => ds.data.shift());
            }

            chart.update('none');

            // 연결 상태 표시
            errorCount = 0;
            document.getElementById('connStatus').className = 'conn-status conn-ok';
            document.getElementById('connStatus').textContent = '✅ 연결됨 · ' + now + ' 업데이트';
        })
        .catch(err => {
            errorCount++;
            console.error('오류:', err);

            document.getElementById('rawValue').textContent  = '오류';
            document.getElementById('gasPercent').textContent = '오류';
            document.getElementById('connStatus').className  = 'conn-status conn-err';
            document.getElementById('connStatus').textContent = '❌ 연결 오류 (' + errorCount + '번째)';
        });
}

// 페이지 로드 완료 후 시작
document.addEventListener('DOMContentLoaded', () => {
    fetchData();
    setInterval(fetchData, 500);
});
</script>
</body>
</html>"""

# =============================================
# HTTP 요청 처리
# =============================================
def handle_request(conn):
    try:
        request = conn.recv(2048).decode('utf-8', 'ignore')
        first_line = request.split('\n')[0]
        print("요청:", first_line.strip())

        if 'GET /data' in request:
            # 센서 읽기
            raw     = gas_sensor.read_u16()
            percent = get_gas_percentage(raw)
            status  = get_status(raw)
            korean  = get_status_korean(raw)

            update_led(raw)

            # Shell에 출력 (디버깅)
            print(f"  raw={raw} | {percent}% | {korean}")

            sensor_data.append(percent)
            if len(sensor_data) > MAX_DATA:
                sensor_data.pop(0)

            # ✅ JSON body 먼저 만들기
            body = json.dumps({
                "raw"    : raw,
                "percent": percent,
                "status" : status,
                "korean" : korean
            })

            # ✅ Content-Length 명시
            response = "\r\n".join([
                "HTTP/1.1 200 OK",
                "Content-Type: application/json; charset=utf-8",
                "Content-Length: " + str(len(body)),
                "Access-Control-Allow-Origin: *",
                "Connection: close",
                "",
                body
            ])

        else:
            html = get_html()
            response = "\r\n".join([
                "HTTP/1.1 200 OK",
                "Content-Type: text/html; charset=utf-8",
                "Content-Length: " + str(len(html)),
                "Connection: close",
                "",
                html
            ])

        conn.sendall(response.encode('utf-8'))

    except Exception as e:
        print(f"요청 처리 오류: {e}")

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
