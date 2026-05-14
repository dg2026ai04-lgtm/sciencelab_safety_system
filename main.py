from machine import Pin, ADC
import time

# =============================================
# 핀 설정
# =============================================
mq2 = ADC(Pin(34))          # MQ2 센서 (아날로그 입력)
mq2.atten(ADC.ATTN_11DB)    # 0 ~ 3.3V 범위 측정

led_green  = Pin(25, Pin.OUT)  # 초록 LED
led_yellow = Pin(26, Pin.OUT)  # 노랑 LED
led_red    = Pin(27, Pin.OUT)  # 빨강 LED

# =============================================
# 모든 LED 끄기
# =============================================
def all_led_off():
    led_green.value(0)
    led_yellow.value(0)
    led_red.value(0)

# =============================================
# 안전 단계 : 초록 LED ON
# =============================================
def safe_mode():
    all_led_off()
    led_green.value(1)
    print("[안전] 초록 LED 켜짐")

# =============================================
# 주의 단계 : 노랑 LED ON
# =============================================
def caution_mode():
    all_led_off()
    led_yellow.value(1)
    print("[주의] 노랑 LED 켜짐")

# =============================================
# 위험 단계 : 빨강 LED ON
# =============================================
def danger_mode():
    all_led_off()
    led_red.value(1)
    print("[위험] 빨강 LED 켜짐")

# =============================================
# 즉시 대피 단계 : 빨강 LED 빠르게 깜빡임
# =============================================
def emergency_mode():
    all_led_off()
    print("[긴급] 즉시 대피! 빨강 LED 점멸")
    for _ in range(5):          # 5회 빠르게 깜빡임
        led_red.value(1)
        time.sleep(0.1)
        led_red.value(0)
        time.sleep(0.1)

# =============================================
# 센서값 → 백분율로 변환 (0 ~ 100%)
# =============================================
def get_gas_percentage(raw_value):
    percentage = (raw_value / 4095) * 100
    return round(percentage, 1)

# =============================================
# 메인 루프
# =============================================
print("=" * 40)
print("  약품 실험실 스마트 안전 관리 시스템")
print("  MQ2 센서 + LED 경고 시스템 가동 중")
print("=" * 40)

while True:
    # 센서값 읽기
    raw = mq2.read()
    gas_level = get_gas_percentage(raw)

    print(f"센서 원시값: {raw} | 가스 농도: {gas_level}%")

    # 단계별 판단 및 LED 제어
    if raw < 300:
        safe_mode()

    elif raw < 600:
        caution_mode()

    elif raw < 800:
        danger_mode()

    else:
        emergency_mode()

    print("-" * 40)
    time.sleep(1)    # 1초마다 측정
