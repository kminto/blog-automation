# 프로젝트 컨텍스트

## 프로젝트 개요
음식점 정보를 입력하면 네이버 키워드 분석 + Claude AI로 SEO 최적화된 맛집 블로그 글을 자동 생성하는 시스템.

## 기능 목록

### 완료
- (아직 없음)

### 진행중
- 프로젝트 초기 설정 및 디렉토리 구조 생성

### 예정
- 네이버 키워드도구 API 연동
- 네이버 데이터랩 검색어트렌드 API 연동
- 키워드 조합 로직 구현
- 키워드 점수 계산 로직 구현
- Claude API 본문 생성
- 프롬프트 빌더 구현
- 제목 자동 추천
- 해시태그 자동 생성
- Streamlit UI 구현
- 결과 복사 기능
- Streamlit Cloud 배포

## 현재 파일 구조

```
blog/
├── app.py                    # Streamlit 메인 앱
├── .env                      # 환경변수 (git 제외)
├── .env.example              # 환경변수 템플릿
├── requirements.txt          # 의존성
├── CLAUDE.md                 # Claude Code 설정
├── README.md                 # 프로젝트 설명
├── docs/
│   ├── SKILLS.md             # 기술 패턴
│   ├── CONTEXT.md            # 이 파일
│   ├── TOKEN.md              # 토큰 관리 규칙
│   └── API.md                # API 문서
├── .claude/
│   └── settings.json         # Claude 설정
├── modules/
│   ├── keyword_extractor.py  # 키워드 조합 생성
│   ├── naver_api.py          # 네이버 키워드도구 API
│   ├── datalab_api.py        # 네이버 데이터랩 API
│   ├── keyword_scorer.py     # 키워드 점수 계산
│   ├── title_generator.py    # 제목 생성
│   ├── hashtag_generator.py  # 해시태그 생성
│   ├── blog_writer.py        # 블로그 본문 생성
│   ├── prompt_builder.py     # Claude 프롬프트 구성
│   ├── validators.py         # 입력 검증
│   └── constants.py          # 상수 정의
└── utils/
    ├── text_utils.py         # 텍스트 유틸리티
    └── api_utils.py          # API 공통 유틸리티
```

## 주요 API 연동 현황

| API | 상태 | 비고 |
|-----|------|------|
| Anthropic Claude API | 예정 | 본문/제목/해시태그 생성 |
| 네이버 키워드도구 API | 예정 | 검색량/경쟁도 조회 |
| 네이버 데이터랩 API | 예정 | 검색어 트렌드 분석 |

## 최근 변경사항
- 2026-03-23: 프로젝트 초기 설정 파일 및 디렉토리 구조 생성
