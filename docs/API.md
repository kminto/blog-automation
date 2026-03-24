# API 문서

## 1. OpenAI ChatGPT API

- **엔드포인트**: `https://api.openai.com/v1/chat/completions`
- **메서드**: POST
- **주요 파라미터**:
  - `model`: 사용할 모델 (예: `gpt-4o`)
  - `max_tokens`: 최대 생성 토큰 수
  - `messages`: 대화 메시지 배열 (`role` + `content`)
  - `temperature`: 생성 다양성 (0.0~2.0)
- **Python SDK**: `openai` 패키지 사용

## 2. 네이버 키워드도구 API (네이버 검색광고)

- **엔드포인트**: `https://api.naver.com/keywordstool`
- **메서드**: GET
- **인증 헤더**:
  - `X-Timestamp`: 밀리초 타임스탬프
  - `X-API-KEY`: 네이버 광고 API 키
  - `X-Customer`: 고객 ID
  - `X-Signature`: HMAC-SHA256 서명
- **주요 파라미터**:
  - `hintKeywords`: 검색할 키워드 (쉼표 구분)
  - `showDetail`: 상세 정보 포함 여부 (`1`)
- **응답 주요 필드**:
  - `relKeyword`: 연관 키워드
  - `monthlyPcQcCnt`: 월간 PC 검색량
  - `monthlyMobileQcCnt`: 월간 모바일 검색량
  - `compIdx`: 경쟁도 (낮음/중간/높음)

## 3. 네이버 데이터랩 검색어트렌드 API

- **엔드포인트**: `https://openapi.naver.com/v1/datalab/search`
- **메서드**: POST
- **인증 헤더**:
  - `X-Naver-Client-Id`: 네이버 개발자 Client ID
  - `X-Naver-Client-Secret`: 네이버 개발자 Client Secret
- **요청 본문**:
  - `startDate`: 시작 날짜 (yyyy-mm-dd)
  - `endDate`: 종료 날짜 (yyyy-mm-dd)
  - `timeUnit`: 시간 단위 (`date`, `week`, `month`)
  - `keywordGroups`: 키워드 그룹 배열
    - `groupName`: 그룹 이름
    - `keywords`: 키워드 배열
  - `device`: 디바이스 (선택: `pc`, `mo`)
  - `ages`: 연령대 (선택)
  - `gender`: 성별 (선택)
- **응답 주요 필드**:
  - `results[].data[].period`: 기간
  - `results[].data[].ratio`: 상대적 검색 비율 (0~100)

## .env 키 이름 목록

```
OPENAI_API_KEY=           # OpenAI ChatGPT API 키
NAVER_CLIENT_ID=          # 네이버 개발자센터 Client ID
NAVER_CLIENT_SECRET=      # 네이버 개발자센터 Client Secret
NAVER_AD_API_KEY=         # 네이버 검색광고 API 키
NAVER_AD_SECRET_KEY=      # 네이버 검색광고 Secret 키
NAVER_AD_CUSTOMER_ID=     # 네이버 검색광고 고객 ID
```
