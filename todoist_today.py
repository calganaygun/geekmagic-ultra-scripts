#!/usr/bin/env python3
"""
Todoist Today's Tasks Display
Fetches today's tasks from Todoist API and generates a display image
Similar design to BusBuzz with 240x240 dimensions
"""

import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_TOKEN = os.getenv('TODOIST_API_TOKEN')
if not API_TOKEN:
    raise ValueError(
        "TODOIST_API_TOKEN not found in environment variables. Copy .env.example to .env and add your token.")
API_URL = "https://api.todoist.com/rest/v2/tasks"

# Display Configuration
IMAGE_WIDTH = 240
IMAGE_HEIGHT = 240
BG_COLOR = "#1a1a1a"  # Black background
TEXT_COLOR = "#ffffff"  # White text
MAX_TASKS = 6  # Show more tasks including completed

# Todoist-style colors (actual Todoist design)
PRIORITY_COLORS = {
    4: "#d1453b",  # Urgent - Red
    3: "#eb8909",  # High - Orange
    2: "#4073ff",  # Medium - Blue
    1: "#808080",  # Low - Gray
}

ACCENT_COLOR = "#de4c4a"  # Todoist brand red
COMPLETED_COLOR = "#6b6b6b"  # Gray for completed tasks
BORDER_COLOR = "#2a2a2a"  # Dark gray borders


def fetch_today_tasks():
    """Fetch today's active and completed tasks from Todoist API"""
    headers = {
        'Authorization': f'Bearer {API_TOKEN}',
        'Content-Type': 'application/json'
    }

    # Fetch active tasks
    params = {'filter': 'today'}
    active_tasks = []
    completed_tasks = []

    try:
        response = requests.get(API_URL, headers=headers,
                                params=params, timeout=10)
        response.raise_for_status()
        active_tasks = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching active tasks: {e}")

    # Fetch completed tasks (from sync API)
    try:
        sync_url = "https://api.todoist.com/sync/v9/completed/get_all"
        today = datetime.now().strftime("%Y-%m-%d")
        sync_response = requests.get(
            sync_url,
            headers=headers,
            params={'since': f'{today}T00:00'},
            timeout=10
        )
        sync_response.raise_for_status()
        completed_data = sync_response.json()
        completed_tasks = completed_data.get('items', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching completed tasks: {e}")

    return {'active': active_tasks, 'completed': completed_tasks}


def parse_tasks(tasks_data):
    """Parse and organize task data"""
    if not tasks_data:
        return []

    active_tasks = tasks_data.get('active', [])
    completed_tasks = tasks_data.get('completed', [])
    parsed_tasks = []

    # Parse active tasks
    for task in active_tasks:
        task_info = {
            'content': task.get('content', 'Untitled Task'),
            'priority': task.get('priority', 1),
            'project_id': task.get('project_id', ''),
            'due': task.get('due', {}),
            'labels': task.get('labels', []),
            'completed': False,
        }

        # Parse due date/time if available
        if task_info['due']:
            due_string = task_info['due'].get('string', '')
            task_info['due_text'] = due_string if due_string else 'Today'
        else:
            task_info['due_text'] = 'Today'

        # Sort key: higher priority first (4->1), then alphabetically
        task_info['sort_key'] = (
            0, 5 - task_info['priority'], task_info['content'].lower())
        parsed_tasks.append(task_info)

    # Parse completed tasks
    for item in completed_tasks:
        task = item.get('task_id') if isinstance(item, dict) else None
        if isinstance(item, dict):
            task_info = {
                'content': item.get('content', 'Untitled Task'),
                'priority': 1,  # Completed tasks shown with low priority
                'project_id': item.get('project_id', ''),
                'due': {},
                'labels': [],
                'completed': True,
                'due_text': 'Completed',
                # Show after active tasks
                'sort_key': (1, 0, item.get('content', '').lower())
            }
            parsed_tasks.append(task_info)

    # Sort: active tasks first (by priority), then completed tasks
    parsed_tasks.sort(key=lambda x: x['sort_key'])

    return parsed_tasks[:MAX_TASKS]


def create_display_image(tasks, output_path='todoist_today.jpg'):
    """Generate a 240x240 display image"""
    # Create image
    img = Image.new('RGB', (IMAGE_WIDTH, IMAGE_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Try to load fonts, fallback to default if not available
    try:
        title_font = ImageFont.truetype(
            "/System/Library/Fonts/Helvetica.ttc", 16)
        task_font = ImageFont.truetype(
            "/System/Library/Fonts/Helvetica.ttc", 13)
        label_font = ImageFont.truetype(
            "/System/Library/Fonts/Helvetica.ttc", 10)
        time_font = ImageFont.truetype(
            "/System/Library/Fonts/Helvetica.ttc", 11)
    except:
        title_font = ImageFont.load_default()
        task_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        time_font = ImageFont.load_default()

    # Draw title with Todoist red
    title = "Today"
    draw.text((12, 10), title, fill=ACCENT_COLOR, font=title_font)

    # Draw task count
    active_count = sum(1 for t in tasks if not t['completed'])
    completed_count = sum(1 for t in tasks if t['completed'])
    if completed_count > 0:
        task_count = f"{active_count} active · {completed_count} completed"
    else:
        task_count = f"{active_count} tasks"
    draw.text((12, 30), task_count, fill="#888888", font=label_font)

    # Draw separator line
    draw.line([(0, 50), (IMAGE_WIDTH, 50)], fill=BORDER_COLOR, width=1)

    # Draw tasks
    y_offset = 58
    row_height = 36

    for i, task in enumerate(tasks):
        if i >= MAX_TASKS:
            break

        is_completed = task['completed']

        # Draw checkbox (filled if completed)
        checkbox_x = 12
        checkbox_y = y_offset + 2
        checkbox_size = 16

        if is_completed:
            # Filled checkbox with checkmark
            draw.ellipse(
                [(checkbox_x, checkbox_y), (checkbox_x +
                                            checkbox_size, checkbox_y + checkbox_size)],
                fill=COMPLETED_COLOR,
                outline=COMPLETED_COLOR
            )
            # Draw checkmark
            draw.line([(checkbox_x + 4, checkbox_y + 8), (checkbox_x +
                      7, checkbox_y + 11)], fill="#ffffff", width=2)
            draw.line([(checkbox_x + 7, checkbox_y + 11),
                      (checkbox_x + 12, checkbox_y + 5)], fill="#ffffff", width=2)
        else:
            # Empty circular checkbox with priority color
            priority_color = PRIORITY_COLORS.get(task['priority'], "#808080")
            draw.ellipse(
                [(checkbox_x, checkbox_y), (checkbox_x +
                                            checkbox_size, checkbox_y + checkbox_size)],
                outline=priority_color,
                width=2
            )

        # Draw task content
        content_x = checkbox_x + checkbox_size + 10
        content_y = checkbox_y

        # Truncate task if too long
        task_text = task['content']
        max_chars = 26
        if len(task_text) > max_chars:
            task_text = task_text[:max_chars-3] + "..."

        # Color based on completion status
        text_color = COMPLETED_COLOR if is_completed else TEXT_COLOR
        draw.text((content_x, content_y), task_text,
                  fill=text_color, font=task_font)

        # Draw strikethrough for completed tasks
        if is_completed:
            bbox = draw.textbbox((content_x, content_y),
                                 task_text, font=task_font)
            line_y = content_y + 8
            draw.line([(content_x, line_y), (bbox[2], line_y)],
                      fill=COMPLETED_COLOR, width=1)

        # Draw due time/labels below task
        info_y = content_y + 18

        # Due text (smaller, subtle)
        if not is_completed and task['due_text']:
            draw.text((content_x, info_y),
                      task['due_text'], fill="#666666", font=time_font)

        # Draw thin separator line
        if i < len(tasks) - 1:
            line_y = y_offset + row_height - 2
            draw.line([(12, line_y), (228, line_y)],
                      fill=BORDER_COLOR, width=1)

        y_offset += row_height

    # If no tasks, show a message
    if len(tasks) == 0:
        msg_y = IMAGE_HEIGHT // 2 - 10
        draw.text((IMAGE_WIDTH // 2 - 70, msg_y),
                  "All done for today! ✨", fill=ACCENT_COLOR, font=task_font)

    # Save image
    img.save(output_path, 'JPEG', quality=95)
    print(f"Display image saved to: {output_path}")
    return output_path


def main():
    """Main execution function"""
    print("Fetching today's tasks from Todoist...")
    tasks = fetch_today_tasks()

    if tasks is None:
        print("Failed to fetch tasks")
        return

    print("Parsing tasks...")
    parsed_tasks = parse_tasks(tasks)

    if not parsed_tasks:
        print("No tasks found for today")
        # Still create an image showing "no tasks"
        create_display_image([])
        return

    active_count = sum(1 for t in parsed_tasks if not t['completed'])
    completed_count = sum(1 for t in parsed_tasks if t['completed'])
    print(
        f"Found {active_count} active tasks and {completed_count} completed tasks")
    for task in parsed_tasks:
        status = "✓" if task['completed'] else " "
        if not task['completed']:
            priority_label = ["Low", "Low", "Medium",
                              "High", "Urgent"][task['priority']]
            print(
                f"  [{status}] [{priority_label}] {task['content']} - {task['due_text']}")
        else:
            print(f"  [{status}] {task['content']}")

    print("\nGenerating display image...")
    create_display_image(parsed_tasks)

    print("Done!")


if __name__ == "__main__":
    main()
