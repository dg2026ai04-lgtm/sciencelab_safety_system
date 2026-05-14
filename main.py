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
# LED 제어 함수
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
# 센서값 → 백분율 변환
# =============================================
def get_gas_percentage(raw):
    return round((raw / 65535) * 100, 1)

# =============================================
# 위험 단계 반환
# =============================================
def get_status(raw):
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
    print(f"\nWi-Fi 연결 성공! IP: {ip}")
    print(f"브라우저에서 http://{ip} 로 접속하세요!")
    return ip

# =============================================
# HTML 페이지
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
            background: #1a1a2e;
            color: white;
            padding: 20px;
        }

        h1 {
            text-align: center;
            font-size: 1.5em;
            margin-bottom: 20px;
            color: #00d4ff;
        }

        .status-box {
            text-align: center;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 1.8em;
            font-weight: bold;
            transition: background 0.3s;
        }

        .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 20px;
        }

        .info-card {
            background: #16213e;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }

        .info-card .label {
            font-size: 0.8em;
            color: #888;
            margin-bottom: 5px;
        }

        .info-card .value {
            font-size: 1.5em;
            font-weight: bold;
            color: #00d4ff;
        }

        .chart-box {
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            height: 500px;
        }

        .chart-box canvas {
            width: 100% !important;
            height: 100% !important;
        }

        .legend-box {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 8px;
            margin-bottom: 20px;
        }

        .legend-item {
            border-radius: 8px;
            padding: 8px;
            text-align: center;
            font-size: 0.75em;
            font-weight: bold;
        }

        .safe      { background: #1a5c1a; }
        .caution   { background: #5c5c1a; }
        .danger    { background: #5c1a1a; }
        .emergency { background: #8b0000; animation: blink 0.5s infinite; }

        @keyframes blink {
            0%   { opacity: 1; }
            50%  { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <h1>💊🧪 약품 실험실 안전 모니터링</h1>

    <div class="status-box safe" id="statusBox">
        🟢 안전
    </div>

    <div class="info-grid">
        <div class="info-card">
            <div class="label">센서 원시값</div>
            <div class="value" id="rawValue">불러오는 중...</div>
        </div>
        <div class="info-card">
            <div class="label">가스 농도</div>
            <div class="value" id="gasPercent">불러오는 중...</div>
        </div>
    </div>

    <div class="legend-box">
        <div class="legend-item safe">
            🟢 안전<br>0 ~ 46%
        </div>
        <div class="legend-item caution">
            🟡 주의<br>46 ~ 69%
        </div>
        <div class="legend-item danger">
            🔴 위험<br>69 ~ 87%
        </div>
        <div class="legend-item emergency">
            🚨 긴급<br>87% 이상
        </div>
    </div>

    <div class="chart-box">
        <canvas id="gasChart"></canvas>
    </div>

    <script>
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
                        backgroundColor: 'rgba(0, 212, 255, 0.1)',
                        borderWidth: 2,
                        pointRadius: 3,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: '주의 기준 (46%)',
                        data: [],
                        borderColor: '#ffff00',
                        borderWidth: 1,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: '위험 기준 (69%)',
                        data: [],
                        borderColor: '#ff4444',
                        borderWidth: 1,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: '긴급 기준 (87%)',
                        data: [],
                        borderColor: '#ff0000',
                        borderWidth: 2,
                        borderDash: [8, 4],
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 200 },
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        ticks: {
                            color: '#aaa',
                            stepSize: 5,
                            callback: val => val + '%'
                        },
                        grid: { color: '#2a2a4a' }
                    },
                    x: {
                        ticks: {
                            color: '#aaa',
                            maxTicksLimit: 10
                        },
                        grid: { color: '#2a2a4a' }
                    }
                },
                plugins: {
                    legend: {
                        labels: { color: 'white', font: { size: 11 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y + '%'
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
            box.className = 'status-box';

            if (status === '안전') {
                box.classList.add('safe');
                box.innerHTML = '🟢 안전';
            } else if (status === '주의') {
                box.classList.add('caution');
                box.innerHTML = '🟡 주의';
            } else if (status === '위험') {
                box.classList.add('danger');
                box.innerHTML = '🔴 위험';
            } else {
                box.classList.add('emergency');
                box.innerHTML = '🚨 긴급 대피!';
            }
        }

        // =============================================
        // 데이터 가져오기 (오류 처리 강화!)
        // =============================================
        function fetchData() {
            fetch('/data')
                .then(res => {
                    if (!res.ok) throw new Error('응답 오류');
                    return res.json();
                })
                .then(data => {
                    // ✅ null/undefined 체크 후 업데이트
                    if (data.raw !== undefined) {
                        document.getElementById('rawValue').textContent = data.raw;
                    }
                    if (data.percent !== undefined) {
                        document.getElementById('gasPercent').textContent = data.percent + '%';
                    }
                    if (data.status !== undefined) {
                        updateStatusBox(data.status);
                    }

                    const now = new Date().toLocaleTimeString();
                    chart.data.labels.push(now);
                    chart.data.datasets[0].data.push(data.percent);
                    chart.data.datasets[1].data.push(46);
                    chart.data.datasets[2].data.push(69);
                    chart.data.datasets[3].data.push(87);

                    if (chart.data.labels.length > 50) {
                        chart.data.labels.shift();
                        chart.data.datasets.forEach(ds => ds.data.shift());
                    }

                    chart.update();
                })
                .catch(err => {
                    // ✅ 오류 시 화면에 표시
                    document.getElementById('rawValue').textContent  = '연결 오류';
                    document.getElementById('gasPercent').textContent = '연결 오류';
                    console.log('데이터 오류:', err);
                });
        }

        setInterval(fetchData, 500);
        fetchData();
    </script>
</body>
</html>"""

# =============================================
# HTTP 요청 처리 (JSON 응답 수정!)
# =============================================
def handle_request(conn):
    try:
        request = conn.recv(1024).decode()
        print(f"요청 받음: {request[:50]}")  # 디버깅용

        if 'GET /data' in request:
            raw     = gas_sensor.read_u16()
            percent = get_gas_percentage(raw)
            status  = get_status(raw)

            update_led(raw)

            # 디버깅용 출력
            print(f"raw: {raw} | percent: {percent} | status: {status}")

            sensor_data.append(percent)
            if len(sensor_data) > MAX_DATA:
                sensor_data.pop(0)

            response_body = json.dumps({
                "raw"    : raw,
                "percent": percent,
                "status" : status
            })

            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "Access-Control-Allow-Origin: *\r\n"
                "Connection: close\r\n"    
                "\r\n" + response_body
            )

        else:
            html = get_html()
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html; charset=utf-8\r\n"
                "Connection: close\r\n"    
                "\r\n" + html
            )

        conn.send(response.encode())

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
    print("Wi-Fi 연결 실패 → 프로그램 종료")
    raise SystemExit

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', 80))
server.listen(5)

print(f"웹서버 시작! → http://{ip}")
print("=" * 40)

while True:
    try:
        conn, addr = server.accept()
        handle_request(conn)
    except Exception as e:
        print(f"서버 오류: {e}")
