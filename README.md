# 맛집 블로그 자동화 시스템

음식점 정보를 입력하면 네이버 키워드 분석 + Claude AI로 SEO 최적화된 맛집 블로그 글을 자동 생성하는 시스템입니다.

## 주요 기능

- 지역/메뉴/상황 기반 키워드 자동 조합
- 네이버 키워드도구 API로 검색량/경쟁도 분석
- 네이버 데이터랩으로 검색 트렌드 분석
- 경쟁력 있는 "숨은 강자 키워드" 자동 선별
- Claude API로 네이버 블로그 스타일 본문 생성
- 제목 후보 3~5개 + 해시태그 20~30개 자동 생성

## 기술 스택

- Python, Streamlit
- OpenAI ChatGPT API
- 네이버 키워드도구 API, 네이버 데이터랩 API

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열고 아래 값을 입력하세요:

| 키 | 설명 | 발급처 |
|----|------|--------|
| `OPENAI_API_KEY` | ChatGPT API 키 | [OpenAI Platform](https://platform.openai.com/) |
| `NAVER_CLIENT_ID` | 네이버 개발자 Client ID | [네이버 개발자센터](https://developers.naver.com/) |
| `NAVER_CLIENT_SECRET` | 네이버 개발자 Client Secret | 네이버 개발자센터 |
| `NAVER_AD_API_KEY` | 네이버 검색광고 API 키 | [네이버 검색광고](https://searchad.naver.com/) |
| `NAVER_AD_SECRET_KEY` | 네이버 검색광고 Secret 키 | 네이버 검색광고 |
| `NAVER_AD_CUSTOMER_ID` | 네이버 검색광고 고객 ID | 네이버 검색광고 |

### 3. 실행

```bash
streamlit run app.py
```
