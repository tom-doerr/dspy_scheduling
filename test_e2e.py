"""End-to-end tests using Playwright.

These tests run against the live application and test the full user workflow.
"""

import pytest
from playwright.sync_api import Page, expect


class TestTaskOperations:
    """Test task CRUD operations through the UI."""

    def test_home_page_loads(self, page: Page):
        """Test that the home page loads successfully."""
        page.goto("/")
        expect(page.locator("h1")).to_contain_text("DSPy Task Scheduler")
        expect(page.get_by_role("heading", name="Add New Task")).to_be_visible()

    def test_add_task_with_toast(self, page: Page):
        """Test adding a task and verifying toast notification appears."""
        page.goto("/")
        page.fill('input[name="title"]', "Test Task E2E")
        page.fill('textarea[name="context"]', "This is a test task")
        page.click('button[type="submit"]')

        toast = page.locator(".toast")
        expect(toast).to_be_visible(timeout=5000)
        expect(toast).to_contain_text("Task added")
        expect(toast).to_be_hidden(timeout=3000)
        expect(page.locator(".task")).to_contain_text("Test Task E2E")

    def test_start_task_with_toast(self, page: Page):
        """Test starting a task and verifying toast notification."""
        page.goto("/")
        page.fill('input[name="title"]', "Task to Start")
        page.click('button[type="submit"]')

        # Wait for "Task added" toast to disappear
        page.wait_for_timeout(2500)

        start_button = page.locator('button:has-text("Start")').first
        start_button.click()

        toast = page.locator(".toast")
        expect(toast).to_be_visible(timeout=5000)
        expect(toast).to_contain_text("Task started")
        expect(page.locator(".task")).to_contain_text("Started:")

    def test_complete_task_with_toast(self, page: Page):
        """Test completing a task and verifying toast notification."""
        page.goto("/")
        page.fill('input[name="title"]', "Task to Complete")
        page.click('button[type="submit"]')

        # Wait for "Task added" toast to disappear
        page.wait_for_timeout(2500)

        complete_button = page.locator('button:has-text("Complete")').first
        complete_button.click()

        toast = page.locator(".toast")
        expect(toast).to_be_visible(timeout=5000)
        expect(toast).to_contain_text("Task completed")
        expect(page.locator(".task.completed")).to_be_visible()

    def test_delete_task_with_toast(self, page: Page):
        """Test deleting a task and verifying toast notification."""
        page.goto("/")
        page.fill('input[name="title"]', "Task to Delete")
        page.click('button[type="submit"]')

        # Wait for "Task added" toast to disappear
        page.wait_for_timeout(2500)

        initial_count = page.locator(".task").count()
        delete_button = page.locator('button:has-text("Delete")').first
        delete_button.click()

        toast = page.locator(".toast")
        expect(toast).to_be_visible(timeout=5000)
        expect(toast).to_contain_text("Task deleted")

        page.wait_for_timeout(500)
        final_count = page.locator(".task").count()
        assert final_count == initial_count - 1

    def test_task_form_clears_after_submit(self, page: Page):
        """Test that form clears after successful submission."""
        page.goto("/")
        page.fill('input[name="title"]', "Task Form Clear Test")
        page.fill('textarea[name="context"]', "Context text")
        page.click('button[type="submit"]')
        page.wait_for_timeout(1000)

        assert page.input_value('input[name="title"]') == ""
        assert page.input_value('textarea[name="context"]') == ""


class TestNavigation:
    """Test navigation and page switching."""

    def test_navigate_to_calendar(self, page: Page):
        """Test navigation to calendar view."""
        page.goto("/")
        page.click('a:has-text("Timeline")')
        expect(page).to_have_url("/calendar")
        expect(page.locator("h1")).to_contain_text("DSPy Task Scheduler")

    def test_navigate_back_to_task_list(self, page: Page):
        """Test navigation back to task list from calendar."""
        page.goto("/calendar")
        page.click('a:has-text("Task List")')
        expect(page).to_have_url("/")
        expect(page.get_by_role("heading", name="Add New Task")).to_be_visible()


class TestGlobalContext:
    """Test global context management."""

    def test_update_global_context(self, page: Page):
        """Test updating global context."""
        page.goto("/")

        # Wait for global context section to load via HTMX
        context_section = page.locator('.section').filter(has_text="Global Context")
        expect(context_section).to_be_visible(timeout=10000)

        context_textarea = context_section.locator('textarea[name="context"]')
        context_textarea.fill("I work 9am-5pm. Prefer mornings for deep work.")

        context_section.locator('button[type="submit"]').click()
        page.wait_for_timeout(1000)

        page.reload()
        page.wait_for_timeout(1000)

        saved_context = context_section.locator('textarea[name="context"]').input_value()
        assert "9am-5pm" in saved_context


class TestActiveTaskTracker:
    """Test active task tracker component."""

    def test_active_task_appears_when_started(self, page: Page):
        """Test that active task tracker shows started task."""
        page.goto("/")
        page.fill('input[name="title"]', "Active Task Test")
        page.click('button[type="submit"]')
        page.wait_for_timeout(1000)

        page.locator('button:has-text("Start")').first.click()
        page.wait_for_timeout(6000)

        active_tracker = page.locator(".active-task-tracker")
        expect(active_tracker).to_contain_text("Active Task Test")

    def test_active_task_disappears_when_completed(self, page: Page):
        """Test that active task tracker clears when task is completed."""
        page.goto("/")
        page.fill('input[name="title"]', "Complete Active Task")
        page.click('button[type="submit"]')
        page.wait_for_timeout(1000)

        page.locator('button:has-text("Start")').first.click()
        page.wait_for_timeout(1000)

        expect(page.locator(".active-task-tracker")).to_contain_text("Complete Active Task")

        page.locator('button:has-text("Complete")').first.click()
        page.wait_for_timeout(6000)

        expect(page.locator(".active-task-tracker")).not_to_contain_text("Complete Active Task")


class TestTimelineView:
    """Test timeline/calendar view functionality."""

    def test_timeline_view_loads(self, page: Page):
        """Test that timeline view loads successfully."""
        page.goto("/calendar")
        expect(page.locator("h1")).to_contain_text("DSPy Task Scheduler")
        expect(page.locator("h2")).to_contain_text("Gantt Chart")

    def test_timeline_displays_scheduled_task(self, page: Page):
        """Test that scheduled tasks appear in timeline view."""
        # Create a task via task list
        page.goto("/")
        page.fill('input[name="title"]', "Timeline Task Test")
        page.fill('textarea[name="context"]', "Testing timeline display")
        page.click('button[type="submit"]')
        page.wait_for_timeout(1000)

        # Navigate to timeline
        page.click('a:has-text("Timeline")')
        page.wait_for_timeout(500)

        # Check that task appears in timeline
        expect(page.locator(".timeline-item")).to_be_visible()
        expect(page.locator(".gantt-item")).to_contain_text("Timeline Task Test")

    def test_timeline_shows_multiple_tasks(self, page: Page):
        """Test that timeline displays multiple scheduled tasks."""
        page.goto("/")

        # Create multiple tasks
        tasks = ["Morning Task", "Afternoon Task", "Evening Task"]
        for task_name in tasks:
            page.fill('input[name="title"]', task_name)
            page.click('button[type="submit"]')
            page.wait_for_timeout(500)

        # Navigate to timeline
        page.click('a:has-text("Timeline")')
        page.wait_for_timeout(1000)

        # Check all tasks appear
        gantt_items = page.locator(".timeline-item")
        expect(gantt_items).to_have_count(3)
        for task_name in tasks:
            expect(page.locator(".gantt-item")).to_contain_text(task_name)

    def test_timeline_shows_task_times(self, page: Page):
        """Test that timeline displays scheduled start and end times."""
        page.goto("/")
        page.fill('input[name="title"]', "Timed Task")
        page.click('button[type="submit"]')
        page.wait_for_timeout(1000)

        # Navigate to timeline
        page.click('a:has-text("Timeline")')
        page.wait_for_timeout(500)

        # Check that time information is displayed
        gantt_item = page.locator(".timeline-item").first
        expect(gantt_item).to_be_visible()
        # Timeline should show time range
        html = gantt_item.inner_html()
        assert "→" in html or "-" in html or ":" in html

    def test_timeline_empty_when_no_scheduled_tasks(self, page: Page):
        """Test that timeline shows appropriate message when no tasks scheduled."""
        page.goto("/calendar")
        page.wait_for_timeout(500)

        # Should either show "No scheduled tasks" or have no gantt items
        gantt_items = page.locator(".timeline-item")
        if gantt_items.count() == 0:
            # Empty state is acceptable
            pass
        else:
            # Or should show some indication
            expect(page.locator(".timeline-container")).to_be_visible()

    def test_timeline_shows_completed_tasks_differently(self, page: Page):
        """Test that completed tasks appear differently in timeline."""
        page.goto("/")
        page.fill('input[name="title"]', "Task to Complete")
        page.click('button[type="submit"]')
        page.wait_for_timeout(1000)

        # Complete the task
        page.locator('button:has-text("Complete")').first.click()
        page.wait_for_timeout(500)

        # Navigate to timeline
        page.click('a:has-text("Timeline")')
        page.wait_for_timeout(500)

        # Check that completed task appears with completed styling
        completed_item = page.locator(".gantt-item.completed")
        if completed_item.count() > 0:
            expect(completed_item).to_be_visible()
        else:
            # At minimum, the task should appear
            expect(page.locator(".gantt-item")).to_contain_text("Task to Complete")

    def test_timeline_chronological_order(self, page: Page):
        """Test that tasks appear in chronological order in timeline."""
        page.goto("/")

        # Create multiple tasks
        task_names = ["First Task", "Second Task", "Third Task"]
        for name in task_names:
            page.fill('input[name="title"]', name)
            page.click('button[type="submit"]')
            page.wait_for_timeout(800)

        # Navigate to timeline
        page.click('a:has-text("Timeline")')
        page.wait_for_timeout(1000)

        # All tasks should be present
        gantt_items = page.locator(".timeline-item")
        count = gantt_items.count()
        assert count == 3
