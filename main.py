import network
import socket
import time
import json
from machine import Pin, ADC
from wifi_config import WIFI_SSID, WIFI_PASSWORD

# =============================================
# 하드웨어 설정
# =============================================
gas_sensor = ADC(Pin(26))       # MQ2 센서 → GP26 (ADC0)

led_green  = Pin(13, Pin.OUT)   # 초록 LED → GP13
led_yellow = Pin(12, Pin.OUT)   # 노랑 LED → GP12
led_red    = Pin(11, Pin.OUT)   # 빨강 LED → GP11

# =============================================
# 전역 변수 (최근 50개 데이터 저장)
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
    if raw < 20000:
        all_led_off()
        led_green.value(1)

    elif raw < 40000:
        all_led_off()
        led_yellow.value(1)

    elif raw < 55000:
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
# 위험 단계 텍스트 반환
# =============================================
def get_status(raw):
    if raw < 20000:
        return "안전"
    elif raw < 40000:
        return "주의"
    elif raw < 55000:
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
# HTML 페이지 (Chart.js 사용)
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
            padding: 15px;
        }

        .safe     { background: #1a5c1a; }
        .caution  { background: #5c5c1a; }
        .danger   { background: #5c1a1a; }
        .emergency{ background: #8b0000; animation: blink 0.5s infinite; }

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
            <div class="value" id="rawValue">-</div>
        </div>
        <div class="info-card">
            <div class="label">가스 농도</div>
            <div class="value" id="gasPercent">- %</div>
        </div>
    </div>

    <div class="chart-box">
        <canvas id="gasChart"></canvas>
    </div>

    <script>
        // =============================================
        // Chart.js 설정
        // =============================================
        const ctx = document.getElementById('gasChart').getContext('2d');

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '가스 농도 (%)',
                    data: [],
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    borderWidth: 2,
                    pointRadius: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                animation: { duration: 300 },
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        ticks: { color: '#888' },
                        grid: { color: '#333' }
                    },
                    x: {
                        ticks: { color: '#888', maxTicksLimit: 10 },
                        grid: { color: '#333' }
                    }
                },
                plugins: {
                    legend: { labels: { color: 'white' } }
                }
            }
        });

        // =============================================
        // 상태에 따라 배경색 변경
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
        // 0.5초마다 /data 에서 데이터 가져오기
        // =============================================
        function fetchData() {
            fetch('/data')
                .then(res => res.json())
                .then(data => {
                    // 수치 업데이트
                    document.getElementById('rawValue').textContent   = data.raw;
                    document.getElementById('gasPercent').textContent = data.percent + '%';

                    // 상태 박스 업데이트
                    updateStatusBox(data.status);

                    // 차트 업데이트
                    const now = new Date().toLocaleTimeString();
                    chart.data.labels.push(now);
                    chart.data.datasets[0].data.push(data.percent);

                    // 최대 50개 유지
                    if (chart.data.labels.length > 50) {
                        chart.data.labels.shift();
                        chart.data.datasets[0].data.shift();
                    }

                    chart.update();
                })
                .catch(err => console.log('데이터 오류:', err));
        }

        // 0.5초마다 실행
        setInterval(fetchData, 500);
        fetchData();
    </script>
</body>
</html>"""

# =============================================
# HTTP 요청 처리
# =============================================
def handle_request(conn):
    try:
        request = conn.recv(1024).decode()
        
        # 경로 확인
        if 'GET /data' in request:
            # /data → JSON 응답
            raw     = gas_sensor.read_u16()
            percent = get_gas_percentage(raw)
            status  = get_status(raw)

            # LED 업데이트
            update_led(raw)

            # sensor_data 리스트에 저장
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
                "\r\n" + response_body
            )

        else:
            # 그 외 → HTML 페이지 응답
            html = get_html()
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html; charset=utf-8\r\n"
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

# Wi-Fi 연결
ip = connect_wifi()
if ip is None:
    print("Wi-Fi 연결 실패 → 프로그램 종료")
    raise SystemExit

# 소켓 서버 시작
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', 80))
server.listen(5)

print(f"웹서버 시작! → http://{ip}")
print("=" * 40)

# 요청 대기 루프
while True:
    try:
        conn, addr = server.accept()
        handle_request(conn)

    except Exception as e:
        print(f"서버 오류: {e}")
