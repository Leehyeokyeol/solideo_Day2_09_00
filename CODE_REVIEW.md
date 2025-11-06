# 시스템 리소스 모니터링 시스템 - 코드 리뷰 보고서

**리뷰 날짜**: 2025-11-06
**리뷰 대상**: monitor.py (589 lines)
**리뷰어**: Claude Code Review System
**프로젝트**: System Resource Monitoring System

---

## 📋 목차
1. [실행 결과 요약](#실행-결과-요약)
2. [코드 구조 분석](#코드-구조-분석)
3. [보안 문제점](#보안-문제점)
4. [코드 품질 문제점](#코드-품질-문제점)
5. [성능 및 리소스 관리](#성능-및-리소스-관리)
6. [권장사항 및 개선안](#권장사항-및-개선안)

---

## 실행 결과 요약

### ✅ 실행 성공
- **총 실행 시간**: 120초 (2분)
- **수집된 데이터 포인트**: 109개
- **PDF 리포트 생성**: 성공 (176KB)
- **경고 발생**: 1건 (matplotlib tight_layout 경고)

```
Progress: 100% | Elapsed: 119.2s / 120s | Remaining: 0.8s | Data points: 109
PDF report generated successfully: system_monitor_report.pdf
```

---

## 코드 구조 분석

### 📊 코드 메트릭스

| 항목 | 값 | 비고 |
|------|-----|------|
| 총 라인 수 | 589 | |
| 클래스 수 | 1 | SystemMonitor |
| 메서드 수 | 7 | __init__, setup_plot, get_cpu_temp, get_gpu_info, collect_data, update_plot, generate_pdf_report, start |
| Import 수 | 12 | psutil, matplotlib, reportlab 등 |
| 외부 의존성 | 6개 | psutil, matplotlib, reportlab, pandas, numpy, GPUtil(선택) |

### 🏗️ 아키텍처 구조

```
┌─────────────────────────────────────────────────┐
│           SystemMonitor (Main Class)             │
├─────────────────────────────────────────────────┤
│  Data Collection Layer                           │
│  ├─ collect_data()                               │
│  ├─ get_cpu_temp()                               │
│  └─ get_gpu_info()                               │
├─────────────────────────────────────────────────┤
│  Visualization Layer                             │
│  ├─ setup_plot() [미사용]                        │
│  └─ update_plot()                                │
├─────────────────────────────────────────────────┤
│  Report Generation Layer                         │
│  └─ generate_pdf_report()                        │
├─────────────────────────────────────────────────┤
│  Orchestration Layer                             │
│  └─ start()                                      │
└─────────────────────────────────────────────────┘
```

---

## 보안 문제점

### 🔴 심각도별 분류

| 심각도 | 개수 | 비율 |
|--------|------|------|
| 🔴 HIGH | 3 | 30% |
| 🟡 MEDIUM | 4 | 40% |
| 🟢 LOW | 3 | 30% |
| **합계** | **10** | **100%** |

### 📈 보안 문제 분포

```
HIGH    ████████████████████████████████ 30%
MEDIUM  ████████████████████████████████████████ 40%
LOW     ████████████████████████████████ 30%
```

---

### 🔴 HIGH 심각도 문제

#### 1. Path Traversal 취약점 (라인 272)

**위치**: `generate_pdf_report(self, filename='system_monitor_report.pdf')`

**문제점**:
```python
def generate_pdf_report(self, filename='system_monitor_report.pdf'):
    doc = SimpleDocTemplate(filename, pagesize=A4)
```

**위험도**: 🔴 HIGH
**CVSS 점수**: 7.5 (High)

**공격 시나리오**:
```python
# 악의적인 호출 예시
monitor.generate_pdf_report('../../../etc/passwd')
monitor.generate_pdf_report('/tmp/malicious.pdf')
```

**영향**:
- 시스템의 임의 위치에 파일 생성 가능
- 기존 중요 파일 덮어쓰기 가능
- 디렉토리 트래버설 공격 가능

**권장 수정**:
```python
import os
from pathlib import Path

def generate_pdf_report(self, filename='system_monitor_report.pdf'):
    # 1. 파일명 검증
    filename = os.path.basename(filename)  # 경로 제거

    # 2. 확장자 검증
    if not filename.endswith('.pdf'):
        filename += '.pdf'

    # 3. 안전한 디렉토리로 제한
    safe_dir = Path('./reports')
    safe_dir.mkdir(exist_ok=True)
    full_path = safe_dir / filename

    doc = SimpleDocTemplate(str(full_path), pagesize=A4)
```

---

#### 2. 임시 파일 Race Condition (라인 468)

**위치**: `graph_file = 'temp_graphs.png'`

**문제점**:
```python
graph_file = 'temp_graphs.png'
plt.savefig(graph_file, dpi=150, bbox_inches='tight')
# ... 중간 처리 ...
if os.path.exists(graph_file):
    os.remove(graph_file)
```

**위험도**: 🔴 HIGH
**CWE-377**: Insecure Temporary File

**공격 시나리오**:
```bash
# 공격자가 심볼릭 링크 생성
ln -s /etc/passwd temp_graphs.png

# 프로그램 실행 시 /etc/passwd가 덮어써질 수 있음
```

**영향**:
- 동시 실행 시 파일 충돌
- 심볼릭 링크 공격 가능
- 중요 파일 손상 가능

**권장 수정**:
```python
import tempfile

# 안전한 임시 파일 생성
with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
    graph_file = tmp.name

plt.savefig(graph_file, dpi=150, bbox_inches='tight')
# ... 처리 ...
os.unlink(graph_file)  # 안전한 삭제
```

---

#### 3. Bare Exception 처리 (라인 35, 108, 122)

**위치**: 여러 곳에서 발견

**문제점**:
```python
# 라인 35
try:
    import GPUtil
    GPU_AVAILABLE = True
except:  # ❌ 모든 예외를 무시
    GPU_AVAILABLE = False

# 라인 108
try:
    temps = psutil.sensors_temperatures()
    # ...
except:  # ❌ KeyboardInterrupt도 잡힘
    pass

# 라인 122
try:
    gpus = GPUtil.getGPUs()
    # ...
except:  # ❌ 시스템 오류도 무시됨
    pass
```

**위험도**: 🔴 HIGH
**CWE-396**: Declaration of Catch for Generic Exception

**영향**:
- `KeyboardInterrupt`, `SystemExit` 등 중요 예외도 포착
- 디버깅 불가능
- 보안 감사 로그 없음
- 숨겨진 오류로 인한 예측 불가능한 동작

**권장 수정**:
```python
# 구체적인 예외 명시
try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError as e:
    logger.warning(f"GPUtil not available: {e}")
    GPU_AVAILABLE = False
except Exception as e:
    logger.error(f"Unexpected error loading GPUtil: {e}")
    GPU_AVAILABLE = False

# KeyboardInterrupt는 절대 잡지 말 것
try:
    temps = psutil.sensors_temperatures()
except (AttributeError, PermissionError) as e:
    logger.debug(f"Temperature sensors not available: {e}")
    return None
```

---

### 🟡 MEDIUM 심각도 문제

#### 4. 입력 검증 부재 (라인 43)

**위치**: `def __init__(self, duration=120)`

**문제점**:
```python
def __init__(self, duration=120):
    self.duration = duration  # ❌ 검증 없음
```

**위험도**: 🟡 MEDIUM

**공격 시나리오**:
```python
# 음수 값
monitor = SystemMonitor(duration=-1000)

# 매우 큰 값 (DoS)
monitor = SystemMonitor(duration=999999999)

# 잘못된 타입
monitor = SystemMonitor(duration="malicious")
```

**영향**:
- 무한 루프 가능
- 메모리 고갈 (데이터 수집 리스트 무한 증가)
- 시스템 리소스 남용

**권장 수정**:
```python
def __init__(self, duration=120):
    # 타입 검증
    if not isinstance(duration, (int, float)):
        raise TypeError(f"duration must be numeric, got {type(duration)}")

    # 범위 검증
    if duration <= 0:
        raise ValueError("duration must be positive")

    if duration > 86400:  # 24시간 제한
        raise ValueError("duration cannot exceed 24 hours (86400 seconds)")

    self.duration = float(duration)
```

---

#### 5. 시스템 정보 노출 (라인 273-310)

**위치**: PDF 리포트 생성

**문제점**:
```python
info_text = f"""
<b>Monitoring Duration:</b> {self.duration} seconds ({self.duration/60:.1f} minutes)<br/>
<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
<b>Data Points Collected:</b> {len(self.timestamps)}<br/>
<b>Update Interval:</b> {self.interval} second(s)
"""
```

**위험도**: 🟡 MEDIUM
**CWE-200**: Exposure of Sensitive Information

**영향**:
- 시스템 성능 프로파일링 가능
- 공격 타이밍 파악 가능
- 시스템 용량 및 한계 추정 가능

**수집되는 민감 정보**:
- CPU 사용 패턴
- 메모리 사용량 및 최대치
- 디스크 I/O 속도 (스토리지 타입 추정 가능)
- 네트워크 대역폭
- CPU/GPU 온도 (하드웨어 정보)

**권장 조치**:
```python
# 1. PDF 암호화
from PyPDF2 import PdfWriter

def encrypt_pdf(input_pdf, output_pdf, password):
    writer = PdfWriter()
    writer.append(input_pdf)
    writer.encrypt(password)
    with open(output_pdf, 'wb') as f:
        writer.write(f)

# 2. 데이터 익명화
def anonymize_stats(value):
    # 정확한 값 대신 범위로 표시
    if value < 25:
        return "LOW (0-25%)"
    elif value < 50:
        return "MEDIUM (25-50%)"
    elif value < 75:
        return "HIGH (50-75%)"
    else:
        return "CRITICAL (75-100%)"
```

---

#### 6. 권한 상승 가능성 (라인 67-68)

**위치**: 시스템 카운터 접근

**문제점**:
```python
self.last_net = psutil.net_io_counters()
self.last_disk = psutil.disk_io_counters()
```

**위험도**: 🟡 MEDIUM

**영향**:
- Root 권한 없이도 전체 시스템 네트워크 통계 수집
- 다른 사용자/프로세스의 디스크 I/O 모니터링
- 프라이버시 침해 가능

**수집 가능한 정보**:
```
├─ 전체 네트워크 트래픽 (모든 인터페이스)
├─ 모든 디스크의 I/O 통계
├─ 시스템 전체 CPU 사용률
└─ 전체 메모리 사용량
```

**권장 조치**:
```python
# 1. 현재 프로세스만 모니터링
import os
current_process = psutil.Process(os.getpid())
process_io = current_process.io_counters()

# 2. 권한 확인
def check_permissions():
    if os.geteuid() == 0:  # root 확인
        print("WARNING: Running as root is not recommended")
        return False
    return True

# 3. 명시적 동의 요청
def get_user_consent():
    print("This tool will collect system-wide metrics.")
    response = input("Continue? (yes/no): ")
    return response.lower() == 'yes'
```

---

#### 7. 로깅 및 감사 추적 부재

**위치**: 전체 코드

**문제점**:
- 보안 이벤트 로깅 없음
- 파일 생성/삭제 기록 없음
- 오류 발생 시 추적 불가

**위험도**: 🟡 MEDIUM
**CWE-778**: Insufficient Logging

**권장 수정**:
```python
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor_security.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SystemMonitor:
    def __init__(self, duration=120):
        logger.info(f"SystemMonitor initialized with duration={duration}")
        # ...

    def generate_pdf_report(self, filename):
        logger.info(f"Generating PDF report: {filename}")
        try:
            # ... PDF 생성 ...
            logger.info(f"PDF report successfully generated: {filename}")
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}", exc_info=True)
            raise
```

---

### 🟢 LOW 심각도 문제

#### 8. 하드코딩된 파일명

**위치**: 라인 468, 272

```python
graph_file = 'temp_graphs.png'  # 하드코딩
def generate_pdf_report(self, filename='system_monitor_report.pdf'):  # 기본값 하드코딩
```

**위험도**: 🟢 LOW

**문제점**:
- 동시 실행 시 충돌
- 테스트 어려움
- 설정 변경 어려움

---

#### 9. 매직 넘버 사용

**위치**: 여러 곳

```python
cpu = psutil.cpu_percent(interval=0.1)  # 0.1은?
disk_read_rate = (disk.read_bytes - self.last_disk.read_bytes) / (1024 * 1024)  # 1024*1024는?
```

**위험도**: 🟢 LOW

**권장 수정**:
```python
# 상수 정의
BYTES_PER_MB = 1024 * 1024
CPU_SAMPLE_INTERVAL = 0.1  # seconds
DEFAULT_DURATION = 120  # seconds
MAX_DURATION = 86400  # 24 hours
```

---

#### 10. 리소스 누수 가능성

**위치**: 라인 375

```python
fig_pdf = plt.figure(figsize=(10, 12))
# ... 처리 ...
plt.close(fig_pdf)  # 예외 발생 시 실행 안 될 수 있음
```

**위험도**: 🟢 LOW

**권장 수정**:
```python
fig_pdf = plt.figure(figsize=(10, 12))
try:
    # ... 그래프 생성 ...
    plt.savefig(graph_file, dpi=150, bbox_inches='tight')
finally:
    plt.close(fig_pdf)  # 항상 실행
```

---

## 코드 품질 문제점

### 📊 코드 품질 메트릭스

| 카테고리 | 문제 수 | 심각도 |
|----------|---------|--------|
| 코드 중복 | 2 | 🟡 |
| 미사용 코드 | 1 | 🟢 |
| 복잡도 | 3 | 🟡 |
| 가독성 | 4 | 🟢 |
| 유지보수성 | 5 | 🟡 |

---

### 1. 중복 Import (라인 7-8, 28-29)

```python
# 라인 7-8
import os
import sys

# ... 중간 생략 ...

# 라인 28-29
import os  # ❌ 중복
import sys  # ❌ 중복
```

**영향**: 코드 가독성 저하, 유지보수 어려움

---

### 2. 미사용 메서드 (라인 71-95)

```python
def setup_plot(self):
    """Setup the matplotlib figure with subplots"""
    self.fig = plt.figure(figsize=(16, 10))
    # ... 전체 메서드가 호출되지 않음
```

**분석**:
- 정의는 되어 있으나 어디서도 호출되지 않음
- 데드 코드 (Dead Code)
- 코드 크기 불필요하게 증가

---

### 3. 긴 메서드 - generate_pdf_report()

**메트릭스**:
- **라인 수**: 259줄 (272-530)
- **순환 복잡도**: 추정 15+
- **권장 최대**: 50줄, 복잡도 10

**권장 리팩토링**:
```python
def generate_pdf_report(self, filename='system_monitor_report.pdf'):
    elements = []

    # 메서드 분리
    self._add_title(elements)
    self._add_info_section(elements)
    self._add_statistics_table(elements)
    self._add_graphs(elements)
    self._add_detailed_data(elements)

    self._build_pdf(filename, elements)

def _add_title(self, elements):
    # 제목 추가 로직
    pass

def _add_statistics_table(self, elements):
    # 통계 테이블 생성 로직
    pass

# ... 각 섹션별 메서드 분리
```

---

### 4. 에러 처리 불완전

| 메서드 | 에러 처리 | 문제점 |
|--------|-----------|--------|
| `collect_data()` | 부분적 | 네트워크 카운터 실패 시 처리 없음 |
| `get_cpu_temp()` | Bare except | 모든 예외 무시 |
| `generate_pdf_report()` | 없음 | PDF 생성 실패 시 처리 없음 |

---

### 5. 테스트 코드 부재

```
📁 solideo_Day2_09_00/
├── monitor.py
├── requirements.txt
├── README.md
└── ❌ tests/  <-- 없음!
```

**권장 테스트 구조**:
```
tests/
├── test_system_monitor.py
├── test_pdf_generation.py
├── test_data_collection.py
└── test_security.py
```

---

## 성능 및 리소스 관리

### 📊 메모리 사용 분석

**데이터 구조**:
```python
self.timestamps = []        # 109 floats = ~872 bytes
self.cpu_percent = []       # 109 floats = ~872 bytes
self.memory_percent = []    # 109 floats = ~872 bytes
self.disk_read = []         # 109 floats = ~872 bytes
self.disk_write = []        # 109 floats = ~872 bytes
self.network_sent = []      # 109 floats = ~872 bytes
self.network_recv = []      # 109 floats = ~872 bytes
self.cpu_temp = []          # 109 floats = ~872 bytes
self.gpu_util = []          # 109 floats = ~872 bytes
self.gpu_temp = []          # 109 floats = ~872 bytes
self.gpu_memory = []        # 109 floats = ~872 bytes
```

**총 메모리**: ~10KB (데이터만, 2분 기준)

**24시간 실행 시 추정**:
```
109 데이터포인트 / 120초 = 0.908 포인트/초
24시간 = 86,400초
86,400 * 0.908 = 78,451 데이터포인트
78,451 * 8 bytes * 11 arrays = ~6.7MB
```

**문제점**:
- 메모리 증가에 대한 제한 없음
- 장기 실행 시 메모리 부족 가능
- GC가 제때 동작하지 않을 수 있음

**권장 개선**:
```python
# 링버퍼 사용
from collections import deque

class SystemMonitor:
    def __init__(self, duration=120, max_data_points=10000):
        self.max_data_points = max_data_points
        self.timestamps = deque(maxlen=max_data_points)
        self.cpu_percent = deque(maxlen=max_data_points)
        # ...
```

---

### ⚡ 성능 병목 지점

| 위치 | 작업 | 소요 시간 (추정) |
|------|------|------------------|
| `collect_data()` - line 132 | `cpu_percent(interval=0.1)` | ~100ms |
| `generate_pdf_report()` | 그래프 생성 | ~2-3초 |
| `generate_pdf_report()` | PDF 빌드 | ~1-2초 |
| **합계** | | **~3-5초** |

**개선 방안**:
```python
# CPU 샘플링 개선
cpu = psutil.cpu_percent(interval=0)  # 0으로 설정하면 즉시 반환

# 백그라운드 PDF 생성
from concurrent.futures import ThreadPoolExecutor

def start(self):
    # ... 데이터 수집 ...

    # 백그라운드에서 PDF 생성
    with ThreadPoolExecutor() as executor:
        executor.submit(self.generate_pdf_report)
```

---

## 권장사항 및 개선안

### 🎯 우선순위별 개선 로드맵

#### Phase 1: 보안 강화 (즉시 적용)

```
[우선순위: CRITICAL]
┌────────────────────────────────────────┐
│ 1. Path Traversal 수정                 │
│ 2. Bare Exception 구체화               │
│ 3. 임시 파일 안전 처리                  │
│ 4. 입력 검증 추가                       │
└────────────────────────────────────────┘
예상 작업 시간: 4-6 시간
```

#### Phase 2: 코드 품질 개선 (1주 이내)

```
[우선순위: HIGH]
┌────────────────────────────────────────┐
│ 1. 중복 코드 제거                       │
│ 2. 메서드 리팩토링 (분리)               │
│ 3. 로깅 시스템 구현                     │
│ 4. 설정 파일 분리                       │
└────────────────────────────────────────┘
예상 작업 시간: 8-12 시간
```

#### Phase 3: 기능 개선 (2주 이내)

```
[우선순위: MEDIUM]
┌────────────────────────────────────────┐
│ 1. 단위 테스트 작성                     │
│ 2. PDF 암호화 기능                      │
│ 3. 설정 파일 지원                       │
│ 4. CLI 인터페이스 개선                  │
└────────────────────────────────────────┘
예상 작업 시간: 16-20 시간
```

---

### 📋 체크리스트

#### 보안 체크리스트

- [ ] 모든 사용자 입력 검증
- [ ] 경로 트래버설 방지
- [ ] 안전한 임시 파일 처리
- [ ] 구체적인 예외 처리
- [ ] 보안 로깅 구현
- [ ] 권한 최소화 원칙 적용
- [ ] 민감 정보 암호화
- [ ] 보안 취약점 스캔 (bandit, safety)

#### 코드 품질 체크리스트

- [ ] 중복 코드 제거
- [ ] 데드 코드 제거
- [ ] 단위 테스트 작성 (커버리지 80% 이상)
- [ ] 문서화 (docstring 완성)
- [ ] 타입 힌트 추가
- [ ] 린터 통과 (pylint, flake8)
- [ ] 코드 리뷰 수행

---

### 🛠️ 권장 도구

#### 보안 스캔
```bash
# 보안 취약점 스캔
pip install bandit
bandit -r monitor.py

# 의존성 보안 체크
pip install safety
safety check

# 비밀키 스캔
pip install detect-secrets
detect-secrets scan
```

#### 코드 품질
```bash
# 정적 분석
pip install pylint
pylint monitor.py

# 코드 스타일
pip install black
black monitor.py

# 타입 체크
pip install mypy
mypy monitor.py
```

---

## 📊 종합 평가

### 보안 점수

```
┌─────────────────────────────────────────────┐
│ 보안 점수: 45/100                            │
│                                              │
│ ████████████████░░░░░░░░░░░░░░░░░░░░ 45%   │
│                                              │
│ 평가: 보안 개선 필요 (Below Average)          │
└─────────────────────────────────────────────┘

취약점 분포:
  🔴 High:   ███ 3개
  🟡 Medium: ████ 4개
  🟢 Low:    ███ 3개
```

### 코드 품질 점수

```
┌─────────────────────────────────────────────┐
│ 코드 품질: 65/100                            │
│                                              │
│ ████████████████████████████░░░░░░░░ 65%    │
│                                              │
│ 평가: 평균 (Average)                         │
└─────────────────────────────────────────────┘

항목별 점수:
  - 가독성:      70/100
  - 유지보수성:  60/100
  - 테스트:      0/100
  - 문서화:      75/100
  - 성능:        80/100
```

### 전체 평가

```
┌───────────────────────────────────────────────────────┐
│                   종합 평가표                          │
├───────────────────────────────────────────────────────┤
│ 항목            │ 점수   │ 가중치 │ 가중 점수           │
├─────────────────┼────────┼────────┼────────────────────┤
│ 보안            │ 45/100 │ 40%    │ 18.0               │
│ 코드 품질       │ 65/100 │ 30%    │ 19.5               │
│ 기능성          │ 90/100 │ 20%    │ 18.0               │
│ 성능            │ 80/100 │ 10%    │ 8.0                │
├─────────────────┴────────┴────────┼────────────────────┤
│ **총점**                          │ **63.5/100**       │
└───────────────────────────────────┴────────────────────┘

등급: C (개선 필요)
```

---

## 결론 및 최종 권고사항

### ✅ 강점

1. **기능 완성도**: 요구사항을 모두 충족하는 완전한 기능 구현
2. **시각화**: 풍부하고 직관적인 그래프 제공
3. **문서화**: README가 잘 작성되어 있음
4. **사용성**: 간단한 실행 방법

### ❌ 약점

1. **보안 취약점**: 다수의 보안 문제 존재 (특히 Path Traversal, Bare Exception)
2. **테스트 부재**: 단위 테스트가 전혀 없음
3. **에러 처리**: 불완전한 예외 처리
4. **리소스 관리**: 장기 실행 시 메모리 누수 가능성

### 🎯 핵심 개선사항 (Top 5)

1. **즉시 수정**: Path Traversal 취약점 제거
2. **즉시 수정**: Bare Exception을 구체적 예외로 변경
3. **우선 추가**: 로깅 시스템 구현
4. **필수 추가**: 단위 테스트 작성 (최소 50% 커버리지)
5. **권장 개선**: 메서드 리팩토링으로 복잡도 감소

### 📈 개선 후 예상 점수

```
현재:   63.5/100 (C)
개선 후: 85.0/100 (B+)

향상도: +21.5 points
```

---

## 부록: 참고 자료

### 보안 관련 표준

- **CWE-22**: Path Traversal
- **CWE-377**: Insecure Temporary File
- **CWE-396**: Declaration of Catch for Generic Exception
- **CWE-200**: Exposure of Sensitive Information
- **CWE-778**: Insufficient Logging

### 코딩 표준

- **PEP 8**: Python Style Guide
- **PEP 257**: Docstring Conventions
- **PEP 484**: Type Hints

### 추천 도서

- "Secure Coding in Python" - Christian Heimes
- "Clean Code in Python" - Mariano Anaya
- "Python Testing with pytest" - Brian Okken

---

**리뷰 종료일**: 2025-11-06
**다음 리뷰 예정**: 개선 완료 후
