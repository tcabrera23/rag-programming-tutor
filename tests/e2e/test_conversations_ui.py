"""
E2E: conversaciones Streamlit no se pisan al crear, cambiar o borrar hilos.
"""

import pytest

from tests.e2e.conftest import (
    chat_has,
    click_new_conversation,
    delete_history,
    history_buttons,
    open_history,
    select_tutor,
    send_chat,
)

pytestmark = pytest.mark.e2e


def test_selectors_and_buttons_work(app_page):
    page = app_page
    assert page.get_by_text("ChatPdeP", exact=False).first.is_visible()
    assert page.locator("[class*='st-key-nueva_conversacion']").is_visible()
    assert page.locator("[class*='st-key-selector_tutor']").is_visible()
    assert page.locator("[class*='st-key-selector_proveedor']").is_visible()
    assert page.locator("[class*='st-key-check_auto_clasificar']").is_visible()
    assert page.get_by_test_id("stChatInput").is_visible()

    select_tutor(page, "Prolog")
    page.get_by_text("Tutor:", exact=False).first.wait_for()
    assert page.get_by_text("Prolog", exact=False).first.is_visible()

    page.locator("[class*='st-key-nueva_conversacion']").locator("button").click()
    page.get_by_test_id("stChatInput").wait_for()
    assert page.locator("[class*='stException']").count() == 0


def test_two_conversations_keep_their_messages(app_page):
    page = app_page
    send_chat(page, "alpha-unique-1")
    click_new_conversation(page)
    send_chat(page, "beta-unique-2")

    assert history_buttons(page).count() == 2
    assert chat_has(page, "beta-unique-2")
    assert chat_has(page, "E2E: beta-unique-2")

    open_history(page, "alpha-unique-1")
    assert chat_has(page, "alpha-unique-1")
    assert chat_has(page, "E2E: alpha-unique-1")
    assert not chat_has(page, "E2E: beta-unique-2")

    open_history(page, "beta-unique-2")
    assert chat_has(page, "E2E: beta-unique-2")
    assert not chat_has(page, "E2E: alpha-unique-1")


def test_new_conversation_does_not_delete_others(app_page):
    page = app_page
    send_chat(page, "keep-me-aaa")
    click_new_conversation(page)
    send_chat(page, "keep-me-bbb")
    click_new_conversation(page)

    labels = history_buttons(page).all_inner_texts()
    joined = " ".join(labels)
    assert "keep-me-aaa" in joined
    assert "keep-me-bbb" in joined
    assert history_buttons(page).count() == 2


def test_changing_tutor_keeps_current_thread(app_page):
    page = app_page
    send_chat(page, "stay-visible-wollok")
    before = history_buttons(page).count()

    select_tutor(page, "Haskell")
    page.get_by_text("Tutor:", exact=False).first.wait_for()

    assert chat_has(page, "stay-visible-wollok")
    assert chat_has(page, "E2E: stay-visible-wollok")
    assert history_buttons(page).count() == before


def test_delete_one_conversation_keeps_the_other(app_page):
    page = app_page
    send_chat(page, "delete-target-zzz")
    click_new_conversation(page)
    send_chat(page, "keep-after-delete")

    delete_history(page, "delete-target-zzz")
    page.locator("[class*='st-key-load_']").filter(has_text="keep-after-delete").wait_for()

    labels = " ".join(history_buttons(page).all_inner_texts())
    assert "delete-target-zzz" not in labels
    assert "keep-after-delete" in labels
    assert chat_has(page, "E2E: keep-after-delete")
