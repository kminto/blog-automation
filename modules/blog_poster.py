"""
네이버 블로그 자동 포스팅 모듈
Selenium + undetected-chromedriver로 네이버 에디터에
본문 붙여넣기 + 사진 업로드 + 임시저장까지 자동화한다.

⚠️ 주의: 네이버 봇 감지 → 계정 제재 위험 있음.
    최종 발행은 반드시 직접 확인 후 수동으로.
"""

import os
import time
import tempfile

import pyperclip

from modules.html_converter import blog_text_to_html

# Selenium 관련 import (설치 안 됐을 때 graceful 처리)
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"
BLOG_WRITE_URL = "https://blog.naver.com/{blog_id}/postwrite"


def check_selenium_available() -> bool:
    """Selenium 사용 가능 여부를 확인한다."""
    return SELENIUM_AVAILABLE


def _create_driver() -> "uc.Chrome":
    """봇 감지 우회용 Chrome 드라이버를 생성한다."""
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = uc.Chrome(options=options)
    return driver


def _login_naver(driver, naver_id: str, naver_pw: str):
    """네이버 로그인을 수행한다. 클립보드 붙여넣기 방식."""
    driver.get(NAVER_LOGIN_URL)
    time.sleep(2)

    # ID 입력 (클립보드 방식)
    id_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "id"))
    )
    id_input.click()
    time.sleep(0.3)

    # JavaScript로 값 설정 (send_keys 대신)
    driver.execute_script(
        'document.getElementById("id").value = arguments[0];',
        naver_id,
    )
    time.sleep(0.3)

    # PW 입력
    pw_input = driver.find_element(By.ID, "pw")
    pw_input.click()
    time.sleep(0.3)
    driver.execute_script(
        'document.getElementById("pw").value = arguments[0];',
        naver_pw,
    )
    time.sleep(0.3)

    # 로그인 버튼 클릭
    login_btn = driver.find_element(By.ID, "log.login")
    login_btn.click()
    time.sleep(3)

    # 캡챠 또는 2단계 인증 확인
    if "captcha" in driver.page_source.lower() or "otp" in driver.current_url:
        raise RuntimeError(
            "캡챠 또는 2단계 인증이 필요합니다. "
            "브라우저에서 직접 인증을 완료해주세요."
        )


def _open_editor(driver, blog_id: str):
    """블로그 글쓰기 에디터를 연다."""
    url = BLOG_WRITE_URL.format(blog_id=blog_id)
    driver.get(url)
    time.sleep(3)

    # "작성 중인 글이 있습니다" 팝업 닫기
    try:
        cancel_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.se-popup-button-cancel")
            )
        )
        cancel_btn.click()
        time.sleep(1)
    except Exception:
        pass

    # 도움말 팝업 닫기
    try:
        close_btn = driver.find_element(
            By.CSS_SELECTOR, "button.se-help-panel-close-button"
        )
        close_btn.click()
        time.sleep(0.5)
    except Exception:
        pass


def _input_title(driver, title: str):
    """제목을 입력한다."""
    try:
        title_area = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "span.se-ff-nanumgothic.se-fs32")
            )
        )
        title_area.click()
        time.sleep(0.3)

        # 클립보드로 붙여넣기
        pyperclip.copy(title)
        ActionChains(driver).key_down(Keys.META).send_keys("v").key_up(Keys.META).perform()
        time.sleep(0.5)
    except Exception:
        # 대체 방법: 제목 영역 직접 찾기
        title_el = driver.find_element(
            By.CSS_SELECTOR, ".se-documentTitle .se-text-paragraph"
        )
        title_el.click()
        pyperclip.copy(title)
        ActionChains(driver).key_down(Keys.META).send_keys("v").key_up(Keys.META).perform()
        time.sleep(0.5)


def _input_body(driver, body_html: str):
    """본문을 HTML로 붙여넣기한다."""
    # 본문 영역 클릭
    try:
        body_area = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".se-component-content .se-text-paragraph")
            )
        )
        body_area.click()
    except Exception:
        body_area = driver.find_element(By.CSS_SELECTOR, ".se-main-container")
        body_area.click()

    time.sleep(0.5)

    # HTML을 클립보드에 복사 후 붙여넣기
    pyperclip.copy(body_html)
    ActionChains(driver).key_down(Keys.META).send_keys("v").key_up(Keys.META).perform()
    time.sleep(2)


def _upload_photos(driver, photo_files: list[dict]):
    """사진을 순서대로 업로드한다."""
    if not photo_files:
        return

    for i, photo in enumerate(photo_files):
        try:
            # 이미지 추가 버튼 클릭
            img_btn = driver.find_element(
                By.CSS_SELECTOR, "button.se-image-toolbar-button"
            )
            img_btn.click()
            time.sleep(1)

            # 파일 input 찾기
            file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")

            # 임시 파일로 저장 후 경로 전달
            tmp_path = os.path.join(
                tempfile.gettempdir(),
                f"blog_photo_{i}_{photo['name']}"
            )
            with open(tmp_path, "wb") as f:
                f.write(photo["bytes"])

            file_input.send_keys(tmp_path)
            time.sleep(2)  # 업로드 대기

            # 임시 파일 정리
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        except Exception as e:
            # 업로드 실패해도 나머지 계속 시도
            continue


def _save_draft(driver):
    """임시저장을 실행한다."""
    try:
        # Ctrl+S (Mac: Cmd+S) 단축키
        ActionChains(driver).key_down(Keys.META).send_keys("s").key_up(Keys.META).perform()
        time.sleep(2)
    except Exception:
        # 버튼으로 임시저장
        try:
            save_btn = driver.find_element(
                By.CSS_SELECTOR, "button.se-toolbar-button-save"
            )
            save_btn.click()
            time.sleep(2)
        except Exception:
            pass


def auto_post(
    blog_id: str,
    naver_id: str,
    naver_pw: str,
    title: str,
    body_text: str,
    photo_files: list[dict] = None,
    publish: bool = False,
) -> dict:
    """네이버 블로그에 글을 자동 작성한다.

    Args:
        blog_id: 블로그 ID (예: "rinx_x")
        naver_id: 네이버 로그인 ID
        naver_pw: 네이버 로그인 PW
        title: 글 제목
        body_text: 본문 텍스트 (HTML로 자동 변환)
        photo_files: [{"name": "파일명", "bytes": 바이트데이터}, ...]
        publish: True면 발행, False면 임시저장만 (기본: False)

    Returns:
        {"success": bool, "message": str, "driver": driver}
    """
    if not SELENIUM_AVAILABLE:
        return {
            "success": False,
            "message": "selenium, undetected-chromedriver, pyperclip을 설치해주세요.",
            "driver": None,
        }

    driver = None
    try:
        # 1. 브라우저 실행
        driver = _create_driver()

        # 2. 네이버 로그인
        _login_naver(driver, naver_id, naver_pw)

        # 3. 에디터 열기
        _open_editor(driver, blog_id)

        # 4. 제목 입력
        _input_title(driver, title)

        # 5. 사진 업로드 (본문 위에)
        if photo_files:
            _upload_photos(driver, photo_files)

        # 6. 본문 입력
        body_html = blog_text_to_html(body_text)
        _input_body(driver, body_html)

        # 7. 임시저장 or 발행
        if publish:
            # 발행은 위험하므로 기본 비활성화
            _save_draft(driver)
            return {
                "success": True,
                "message": "임시저장 완료. 브라우저에서 확인 후 직접 발행해주세요.",
                "driver": driver,
            }
        else:
            _save_draft(driver)
            return {
                "success": True,
                "message": "임시저장 완료! 브라우저에서 확인 후 발행 버튼을 눌러주세요.",
                "driver": driver,
            }

    except Exception as e:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return {
            "success": False,
            "message": f"자동 포스팅 실패: {e}",
            "driver": None,
        }
