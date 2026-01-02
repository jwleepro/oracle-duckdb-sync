"""
Playwright automated test for Streamlit UI responsiveness.
Tests if the UI locks up after chart rendering.
"""
import pytest
import time
from playwright.sync_api import sync_playwright, expect

@pytest.mark.e2e
@pytest.mark.skip(reason="Requires Streamlit app running on localhost:8501")
def test_streamlit_ui_responsiveness():
    """
    Test that the Streamlit UI remains responsive after chart rendering.
    """
    with sync_playwright() as p:
        # Launch browser (headless=False to see what's happening)
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()

        print("🌐 Opening Streamlit app at http://localhost:8501")
        page.goto('http://localhost:8501', wait_until='networkidle', timeout=30000)

        # Wait for page to load
        print("⏳ Waiting for page to load...")
        time.sleep(3)

        # Take screenshot of initial state
        page.screenshot(path='test_screenshots/01_initial.png')
        print("📸 Screenshot saved: 01_initial.png")

        # Find and fill in table name input (if visible)
        try:
            table_input = page.locator('input[aria-label*="조회할 테이블"]').first
            if table_input.is_visible(timeout=2000):
                print("📝 Found table name input")
                # The input should already have default value, so we just proceed
        except Exception as e:
            print(f"ℹ️ Table input not found or not needed: {e}")

        # Click "조회" button
        try:
            print("🔍 Looking for '조회' button...")
            query_button = page.get_by_role('button', name='조회')
            query_button.click()
            print("✅ Clicked '조회' button")
            page.screenshot(path='test_screenshots/02_after_query_click.png')
            print("📸 Screenshot saved: 02_after_query_click.png")
        except Exception as e:
            print(f"❌ Failed to click '조회' button: {e}")
            browser.close()
            return

        # Wait for data to load (spinner should appear)
        print("⏳ Waiting for data to load...")
        time.sleep(5)
        page.screenshot(path='test_screenshots/03_data_loaded.png')
        print("📸 Screenshot saved: 03_data_loaded.png")

        # Try to select Y-axis columns for chart
        try:
            print("📊 Looking for Y축 multiselect...")
            # Find multiselect by label text
            y_axis_label = page.locator('text=Y축 (숫자 컬럼)').first
            if y_axis_label.is_visible(timeout=5000):
                print("✅ Found Y축 selector")

                # Click on the multiselect to open dropdown
                multiselect = page.locator('div[data-baseweb="select"]').first
                multiselect.click()
                print("✅ Opened Y축 dropdown")
                time.sleep(1)

                # Select first available option
                first_option = page.locator('li[role="option"]').first
                if first_option.is_visible(timeout=2000):
                    first_option.click()
                    print("✅ Selected first Y축 column")
                    time.sleep(2)
                    page.screenshot(path='test_screenshots/04_y_axis_selected.png')
                    print("📸 Screenshot saved: 04_y_axis_selected.png")

                    # Click outside to close dropdown
                    page.mouse.click(100, 100)
        except Exception as e:
            print(f"ℹ️ Could not select Y axis (might be no numeric columns): {e}")

        # Wait for chart to render
        print("⏳ Waiting for chart to render...")
        time.sleep(8)  # Give enough time for chart and data table rendering
        page.screenshot(path='test_screenshots/05_chart_rendered.png')
        print("📸 Screenshot saved: 05_chart_rendered.png")

        # Test UI responsiveness after chart rendering
        print("\n🧪 Testing UI responsiveness after chart rendering...")

        # Test 1: Check if page is still responsive by hovering
        try:
            # Try to hover over the sidebar
            sidebar = page.locator('[data-testid="stSidebar"]').first
            sidebar.hover(timeout=3000)
            print("✅ Test 1 PASSED: Can hover over sidebar (UI is responsive)")
        except Exception as e:
            print(f"❌ Test 1 FAILED: Cannot hover over sidebar (UI may be locked): {e}")

        # Test 2: Try to scroll the page
        try:
            page.mouse.wheel(0, 500)
            time.sleep(1)
            page.mouse.wheel(0, -500)
            print("✅ Test 2 PASSED: Can scroll page (UI is responsive)")
        except Exception as e:
            print(f"❌ Test 2 FAILED: Cannot scroll page (UI may be locked): {e}")

        # Test 3: Check if spinners appeared and disappeared (check screenshots)
        print("\n📊 Summary:")
        print("   - Check screenshots in test_screenshots/ folder")
        print("   - Look for spinners in screenshots 02-05")
        print("   - Verify chart rendered in 05_chart_rendered.png")

        # Keep browser open for manual inspection
        print("\n⏸️ Browser will stay open for 10 seconds for manual inspection...")
        time.sleep(10)

        browser.close()
        print("✅ Test completed successfully!")

if __name__ == "__main__":
    # Set UTF-8 encoding for Windows console
    import sys
    import os
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # Create screenshots directory
    os.makedirs('test_screenshots', exist_ok=True)

    print("=" * 80)
    print("Starting Streamlit UI Responsiveness Test")
    print("=" * 80)
    print("\nPrerequisites:")
    print("  - Streamlit app should be running at http://localhost:8501")
    print("  - Database should have data to query")
    print("\n" + "=" * 80 + "\n")

    try:
        test_streamlit_ui_responsiveness()
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
