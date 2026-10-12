import csv
import io
import os
import re
import time
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("BASE_URL", "").strip()
APP_KIND = os.environ.get("APP_KIND", "").strip().lower()
ARTIFACTS = Path("qa-artifacts")
ARTIFACTS.mkdir(exist_ok=True)

pytestmark = pytest.mark.skipif(
    not BASE_URL or APP_KIND not in {"expense", "todo"},
    reason="Set repository Actions variables BASE_URL and APP_KIND to run live tests.",
)


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    page.set_default_timeout(12_000)
    page.on("pageerror", lambda exc: print(f"BROWSER PAGE ERROR: {exc}"))
    response = page.goto(BASE_URL, wait_until="domcontentloaded", timeout=45_000)
    assert response is not None and response.status < 400, f"App returned HTTP {response.status if response else 'no response'}"
    # Wait for Streamlit's websocket-backed app to render.
    app = page.frame_locator('iframe[title="streamlitApp"]')
    expect(app.locator("body")).to_contain_text(re.compile(r".+"), timeout=30_000)
    yield app
    page.screenshot(path=str(ARTIFACTS / f"{APP_KIND}-final.png"), full_page=True)
    context.close()


def click_button(page, name):
    page.get_by_role("button", name=re.compile(name, re.I)).click()


def test_app_renders_without_streamlit_error(page):
    body = page.locator("body")
    if APP_KIND == "expense":
        expect(body).to_contain_text("Expense Tracker")
        expect(body).to_contain_text("Create New Workspace")
        expect(body).to_contain_text("Workspace name")
    else:
        expect(body).to_contain_text(re.compile("Task Management|Task Manager|Data Analyst Portfolio", re.I))
        expect(body).to_contain_text("Register")
        expect(body).to_contain_text("Login")
    assert "Traceback (most recent call last)" not in body.inner_text()


def test_primary_workflow(page):
    suffix = f"qa{int(time.time()) % 100000000:08d}"
    if APP_KIND == "expense":
        workspace = suffix[:24]
        page.locator('input[aria-label="Workspace name"]').fill(workspace)
        click_button(page, "Continue")
        expect(page.locator("body")).to_contain_text("Spending Summary")
        expect(page.locator("body")).to_contain_text("Transactions")
        # Add expense through the actual form.
        page.get_by_text("Add New Expense", exact=True).click()
        expect(page.locator("body")).to_contain_text("Add a New Expense")
        page.get_by_label("Amount").fill("123.45")
        page.get_by_label("Currency").click()
        page.get_by_text("INR", exact=True).last.click()
        page.get_by_label("Description (optional)").fill("Synthetic QA smoke-test expense")
        click_button(page, "Add Expense")
        expect(page.locator("body")).to_contain_text("Expense added successfully")
        # Check persistence after Streamlit rerun and navigate to the table.
        page.get_by_text("View Expenses", exact=True).click()
        expect(page.locator("body")).to_contain_text("Synthetic QA smoke-test expense")
        # Validate CSV download content, not just button visibility.
        with page.expect_download(timeout=15_000) as download_info:
            click_button(page, "Download filtered CSV")
        download = download_info.value
        dest = ARTIFACTS / "expense-filtered.csv"
        download.save_as(dest)
        rows = list(csv.DictReader(dest.open(newline="", encoding="utf-8")))
        assert any(r.get("Description") == "Synthetic QA smoke-test expense" for r in rows), rows
        # Verify currency converter basic math and same-currency handling.
        page.get_by_text("Currency Converter", exact=True).click()
        page.get_by_label("Amount").fill("100")
        page.get_by_label("From Currency").click()
        page.get_by_text("USD", exact=True).last.click()
        page.get_by_label("To Currency").click()
        page.get_by_text("INR", exact=True).last.click()
        click_button(page, "Convert")
        expect(page.locator("body")).to_contain_text(re.compile(r"100\.00 USD = [\d,]+(?:\.\d+)? INR"))
        expect(page.locator("body")).to_contain_text("Rate date:")
        # Close and reopen workspace to check persistence in the hosted filesystem.
        page.get_by_role("button", name=re.compile("Close Workspace", re.I)).click()
        page.get_by_text("Open Existing Workspace", exact=True).click()
        page.locator('input[aria-label="Workspace name"]').fill(workspace)
        click_button(page, "Continue")
        page.get_by_text("View Expenses", exact=True).click()
        expect(page.locator("body")).to_contain_text("Synthetic QA smoke-test expense")
    else:
        username = suffix
        password = "QA-only-" + suffix + "-pass!"
        page.get_by_text("Register", exact=True).click()
        page.get_by_label(re.compile("Username", re.I)).fill(username)
        page.get_by_label(re.compile("Password", re.I)).first.fill(password)
        page.get_by_label(re.compile("Confirm Password", re.I)).fill(password)
        click_button(page, "Register")
        expect(page.locator("body")).to_contain_text("Create New Task")
        # Create a task and check that it appears on the board.
        page.get_by_label(re.compile("Task Title", re.I)).fill("QA synthetic task " + suffix)
        click_button(page, "Add Task")
        expect(page.locator("body")).to_contain_text("QA synthetic task " + suffix)
        # Move it to Done and enter actual hours.
        status = page.get_by_label("Status").last
        status.click()
        page.get_by_text("Done", exact=True).last.click()
        expect(page.locator("body")).to_contain_text("Done")
        hours = page.get_by_label(re.compile("Actual hours", re.I)).last
        hours.fill("1.5")
        hours.press("Tab")
        # Verify analytics tab renders and contains the task metrics.
        page.get_by_role("tab", name=re.compile("Analytics Dashboard", re.I)).click()
        expect(page.locator("body")).to_contain_text("Total Tasks")
        expect(page.locator("body")).to_contain_text("Completion Rate")
        # Verify performance tab is reachable and does not show a fatal traceback.
        page.get_by_role("tab", name=re.compile("Performance Insights", re.I)).click()
        expect(page.locator("body")).to_contain_text("Performance")
        assert "Traceback (most recent call last)" not in page.locator("body").inner_text()
        # Return to board and delete the test task to limit test-data residue.
        page.get_by_role("tab", name=re.compile("Kanban Board", re.I)).click()
        page.get_by_role("button", name=re.compile("🗑️")).last.click()
        expect(page.locator("body")).not_to_contain_text("QA synthetic task " + suffix)
        # Log out and verify login screen returns.
        click_button(page, "Logout")
        expect(page.locator("body")).to_contain_text("Login")
