# CGV 용아맥 예매봇

CGV 용산아이파크몰 IMAX 회차를 감시해서 **취소표**와 **새로 열리는 예매**를 자동으로 잡는다.
좌석까지 고르고 저장카드로 결제하며, 진행 상황은 디스코드로 알린다.

## 왜 Selenium인가

CGV는 2025년 7월 차세대 시스템으로 갈아엎으면서 `cgv.co.kr` 단일 도메인 SPA가 됐고,
전 도메인이 Cloudflare 뒤로 들어갔다. `curl`이나 `requests`로 찌르면 이렇게 나온다.

```
HTTP/2 403
비정상적으로 CGV에 접속한 것이 확인되어 이용이 제한되었어요.
```

그래서 진짜 Chrome 프로세스 안에서 움직이는 것 말고는 방법이 없다. 다만 ChromeDriver가
브라우저를 띄우면 `navigator.webdriver`가 켜져 탐지되므로, **평범한 Chrome을 우리가 직접
실행하고 Selenium은 CDP로 붙기만 한다.** 브라우저 입장에서는 사람이 켠 창과 구분되지 않는다.

## 구조

```
run.py           진입점
src/browser.py   전용 프로필 Chrome 실행 + CDP attach + 로그인 대기
src/cgv.py       API 클라이언트 (페이지 컨텍스트 fetch)
src/watcher.py   취소표 감시 + 오픈 대기 통합 루프
src/booker.py    회차 진입 -> 인원 -> 좌석 -> 결제
src/queue.py     오픈 대기열(넷퍼넬 등) 감지 후 통과까지 대기
src/notify.py    디스코드 웹후크
src/recorder.py  API 녹화기 (CGV가 바뀌었을 때 재조사용)
endpoints.yaml   확인된 API 목록
selectors.yaml   화면 조작에 쓰는 셀렉터
```

감시는 API로, 예매는 DOM 클릭으로 한다. 감시는 몇 초마다 반복되니 가벼워야 하고,
예매는 한 번뿐이라 몇백 ms보다 안정성이 중요하기 때문이다.

## 셋업

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp config.example.yaml config.yaml
cp .env.example .env
```

`.env`에 디스코드 웹후크 URL과 CGV 간편결제 비밀번호를 넣는다.
웹후크는 디스코드 채널 설정 → 연동 → 웹후크 → 새 웹후크에서 URL을 복사하면 된다.

`config.yaml`에서 영화, 날짜 범위, 매수, 선호 좌석을 지정한다.

**자동결제를 쓰려면 CGV 계정에 카드가 저장돼 있어야 한다.** CGV 로그인 → MY CGV →
결제수단 관리에서 카드를 등록하고 간편결제 비밀번호를 설정해 둘 것.

## 실행

```bash
.venv/bin/python run.py --test-notify   # 디스코드 웹후크 연결 확인
.venv/bin/python run.py --list          # 지금 조건에 맞는 회차 확인
.venv/bin/python run.py --dry-run       # 결제 직전까지만
caffeinate -dimsu .venv/bin/python run.py   # 실제 운용 (맥 절전 방지)
```

닫은 시점에
> pmset -g log | grep -i "Sleep\|Wake" | tail -20 

Entering Sleep 이 있으면 봇도 멈춘것

첫 실행에서 Chrome 창이 뜨면 CGV에 로그인한다. 로그인은 `.chrome-profile/`에 저장돼
다음부터는 자동으로 넘어간다.

## 주요 설정

| 항목 | 설명 |
| --- | --- |
| `theater.site_no` | 극장 코드. 용산아이파크몰은 `0013` |
| `theater.screen_keywords` | 상영관명·특별관등급·포맷 중 하나라도 포함해야 하는 단어 |
| `movie.title_contains` | 영화 제목 부분 일치 |
| `showtimes.after` / `before` | CGV 표기 그대로. 심야는 24시를 넘어간다 (`25:30` = 새벽 1시 반) |
| `showtimes.days` | 볼 요일. `fri, sat, sun` 이면 주말만 |
| `showtimes.friday_after` | 금요일은 이 시각 이후만 (예: `21:00`). 토·일에는 적용 안 됨 |
| `seats.prefer_rows` | 앞에 적은 행부터 우선 |
| `polling.interval_sec` | `[하한, 상한]` 사이 랜덤. 1초 미만은 설정 단계에서 막는다 |
| `polling.burst_at` | 예매 오픈 시각을 알 때 그 시점만 빠르게 |
| `booking.pay_method` | CGV 결제 화면의 결제수단 이름 그대로 (`카카오페이`, `toss`, `CJ PAY` 등) |
| `booking.max_price_krw` | 총액이 넘으면 결제하지 않고 알림 |
| `booking.queue_timeout_sec` | 오픈 대기열을 기다릴 상한(초). 좌석 선점 시간과 별개 |

## 결제는 토스로 한다

CGV 결제수단 중 자동화가 되는 건 사실상 토스뿐이다.

- **앱카드**는 카드사 앱(페이북/ISP) 인증을 거쳐야 해서 스크립트가 끝까지 못 간다.
- **CGV 간편결제**는 비밀번호 6자리로 결제되지만, 카드를 먼저 등록해야 하고 등록하려면
  카드번호를 직접 입력하는 결제를 한 번 해야 한다.
- **토스**는 `.env`에 번호와 생년월일만 넣어두면 봇이 결제 알림 발송까지 끝낸다.
  카드 정보를 이 저장소 어디에도 두지 않아도 된다.

토스를 고르면 봇이 여기까지 혼자 한다.

```
회차 진입 → 인원 선택 → 좌석 선점 → 결제수단 토스 → 약관 동의
        → 번호·생년월일 입력 → 폰으로 결제 알림 발송
```

그다음 디스코드로 `@here` 알림이 오고(QR코드 첨부), 폰의 토스 앱에서 승인만 누르면
예매가 끝난다. 밖에 있어도 된다. 승인될 때까지 봇이 기다리다가 완료 화면을 확인하면
성공 알림을 보내고, 좌석 선점 시간 안에 승인이 없으면 실패로 처리하고 감시로 돌아간다.

## 잔여석 숫자를 믿으면 안 되는 이유

상영시간표 API의 `frSeatCnt`에는 **장애인석이 포함된다.** 용아맥 IMAX관은 장애인석이
6석이라, 완전히 매진된 회차도 계속 "6석 남음"으로 보인다. 이 숫자만 보고 달려들면
30개 회차에 영원히 예매를 시도하며 디스코드를 도배하게 된다.

그래서 잔여석이 있어 보이는 회차만 좌석맵 API(`searchIfSeatData`)로 한 번 더 확인한다.
`seatSaleYn == "Y"`이면서 `seatSalfrmCd == "01"`(일반석)인 자리만 진짜 잡을 수 있는
좌석으로 센다. 판정 규칙은 `endpoints.yaml`의 `seat_rules`에 있다.

좌석맵 조회는 잔여석 숫자가 바뀐 회차만, 한 턴에 최대 8건까지만 한다.

## 폴링 간격을 왜 못 줄이나

Cloudflare가 요청 빈도를 보고 있어서 밀리초 폴링은 IP 차단으로 직행한다.
기본값은 4~9초 랜덤이고, 차단이 감지되면 자동으로 지수 백오프하며 디스코드로 알린다.
예매 오픈 시각을 아는 경우에만 `burst_at`으로 그 순간 몇 분간 1초 간격으로 돈다.

## 로그인 세션이 끊기면

상영시간표 조회는 **비로그인으로도 정상 응답한다.** 그래서 세션이 만료돼도 봇은 겉으로는
멀쩡히 도는 것처럼 보이다가, 정작 좌석을 잡는 순간에 실패한다. 그 사이에 표는 날아간다.

로그인 판정에는 `cgv.co.kr/api/v1/member/...` 를 쓴다. 비로그인이면 `statusCode`는 0인데
`data`만 null로 오기 때문에 상태코드가 아니라 `data` 유무를 봐야 한다. 참고로
`api.cgv.co.kr` 쪽은 브라우저 안에서 fetch 해도 401이 떨어지니 인증이 필요한 호출에는
쓸 수 없다.

그래서 로그인 상태를 따로 지켜본다.

- `session.check_every_sec`(기본 60초)마다 로그인 여부를 확인하고, 끊기면 디스코드로 `@here` 알림
- 끊긴 동안에는 예매를 시도하지 않고 감시만 계속한다 (시도해봐야 로그인 안내창만 뜬다)
- 알림을 놓쳤을 경우를 대비해 `renotify_every_sec`(기본 30분)마다 다시 알린다
- 다시 로그인하면 자동으로 감지해 "로그인 복구됨"을 알리고 예매 시도를 재개한다
- `keepalive_every_sec`(기본 10분)마다 인증 API를 한 번 건드려 유휴 만료를 늦춘다

재로그인은 사람만 할 수 있다. 알림을 받으면 Chrome 창에서 다시 로그인하면 되고,
봇을 재시작할 필요는 없다.

## 좌석 선점 10분 제한

좌석을 고르면 약 10분간 임시로 확보되고, 그 안에 결제하지 않으면 남에게 풀린다.
`booking.hold_timeout_sec`(기본 540초)을 넘기면 봇이 스스로 포기하고 감시로 돌아간다.

## CGV가 또 바뀌면

```bash
.venv/bin/python tools/record_api.py
```

Chrome이 뜨면 예매 흐름을 수동으로 한 번 걸어간다. 종료하면 `docs/cgv_api.md`에
관찰된 API가 정리되고, `discovery/endpoints.guess.yaml`에 추정값이 나온다.
그걸 보고 `endpoints.yaml`을 고치면 된다.

화면 셀렉터는 `tools/inspect_page.py`로 확인한다.

```bash
.venv/bin/python tools/inspect_page.py           # 버튼/링크 목록
.venv/bin/python tools/inspect_page.py --seats   # 좌석맵 요소 분석
```

## 알아둘 것

- 예매·결제는 로그인 세션에서 일어난다. 브라우저 창을 닫으면 봇도 멈춘다.
- 맥이 절전에 들어가면 감시가 끊긴다. `caffeinate -dimsu`로 감싸서 실행할 것.
- 새 주가 열릴 때 접속 대기열(넷퍼넬 등)이 뜨면 새로고침하지 않고 기다린다.
  처음 걸리면 `logs/queue/시각/` 에 화면·HTML·버튼·iframe을 남긴다. 대기 중
  UI가 바뀌면 `change-01` 같은 폴더가 추가로 생긴다. 다음 수정은 그 덤프 기준으로.
- `.env`, `config.yaml`, `.chrome-profile/`은 `.gitignore`에 들어 있다. 세션 쿠키와
  결제 비밀번호가 들어 있으니 실수로 커밋하지 말 것.
