from playwright.sync_api import sync_playwright

def run_cuj(page):
    page.goto("http://localhost:5173")
    page.wait_for_timeout(2000)

    inputs = page.locator('input').all()
    if len(inputs) == 2:
        inputs[0].fill("testuser")
        inputs[1].fill("password")
        page.get_by_text("Sign In").click()
        page.wait_for_timeout(3000)
    elif len(inputs) == 3:
        inputs[0].fill("testuser")
        inputs[1].fill("test@test.com")
        inputs[2].fill("password")
        page.get_by_text("Sign Up").click()
        page.wait_for_timeout(3000)

    page.screenshot(path="dashboard.png")

    # Check if we can find New Game button
    if page.get_by_text("New Game").is_visible():
        page.get_by_text("New Game").click()
        page.wait_for_timeout(2000)
    elif page.get_by_role("button", name="Create Game").is_visible():
        page.get_by_role("button", name="Create Game").click()
        page.wait_for_timeout(2000)

    # Click Prussian Rails Create Game
    if page.get_by_text("Create Prussian Rails Game").is_visible():
        page.get_by_text("Create Prussian Rails Game").click()
        page.wait_for_timeout(2000)
    elif page.locator('button:has-text("Create")').count() > 1:
        page.locator('button:has-text("Create")').nth(1).click()
        page.wait_for_timeout(2000)

    page.screenshot(path="dashboard_2.png")

    # Click Start Game
    if page.get_by_text("Start").is_visible():
        page.get_by_text("Start").click()
        page.wait_for_timeout(2000)
    elif page.locator('button:has-text("Start Game")').is_visible():
        page.locator('button:has-text("Start Game")').click()
        page.wait_for_timeout(2000)

    # We should be on the game board now
    page.screenshot(path="/home/jules/verification/screenshots/verification.png")
    page.wait_for_timeout(2000)

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="/home/jules/verification/videos",
            viewport={'width': 1200, 'height': 800}
        )
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
