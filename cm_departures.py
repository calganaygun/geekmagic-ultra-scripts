#!/usr/bin/env python3
"""
Bus Departures Display (Airport Board Style)
Fetches bus departure data from Citymapper API and generates a display image
High-contrast airport-style display board
"""

import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone
import os

# API Configuration
API_URL = "https://citymapper.com/api/1/departures"
STOP_ID = "WarsawStop_Centrum_01"
REGION_ID = "pl-warsaw"

# Display Configuration
IMAGE_WIDTH = 240
IMAGE_HEIGHT = 240
BG_COLOR = "#000000"  # Pure black background
HEADER_COLOR = "#1a1a1a"  # Dark gray header
TEXT_COLOR = "#FFFFFF"  # White text
ACCENT_COLOR = "#FFA500"  # Orange for live departures
GRID_COLOR = "#2a2a2a"  # Gray grid lines
MAX_BUSES = 4


def fetch_departures():
    """Fetch departure data from Citymapper API"""
    params = {
        'headways': '1',
        'ids': STOP_ID,
        'region_id': REGION_ID
    }

    try:
        response = requests.get(API_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None


def parse_departures(data):
    """Parse and organize departure data"""
    if not data or 'stops' not in data or not data['stops']:
        return []

    stop = data['stops'][0]
    services = stop.get('services', [])
    routes = {r['id']: r for r in stop.get('routes', [])}

    departures = []
    current_time = datetime.now(timezone.utc)

    for service in services:
        route_id = service['route_id']
        route = routes.get(route_id, {})

        departure_info = {
            'route_name': route.get('name', '???'),
            'headsign': service.get('headsign', ''),
            'color': route.get('color', '#888888'),
            'text_color': route.get('text_color', '#FFFFFF'),
        }

        # Check for live departures
        if 'live_departures_seconds' in service and service['live_departures_seconds']:
            seconds = service['live_departures_seconds'][0]
            minutes = seconds // 60
            departure_info['time_text'] = f"{minutes} min"
            departure_info['is_live'] = True
            departure_info['sort_key'] = seconds
        # Check for scheduled departures
        elif 'next_departures' in service and service['next_departures']:
            next_dep = datetime.fromisoformat(service['next_departures'][0])
            time_str = next_dep.strftime('%H:%M')

            # Add additional times if available
            additional_times = []
            for dep_str in service['next_departures'][1:3]:  # Get next 2 times
                dep_time = datetime.fromisoformat(dep_str)
                additional_times.append(dep_time.strftime('%H:%M'))

            departure_info['time_text'] = time_str
            if additional_times:
                departure_info['additional_times'] = ', '.join(
                    additional_times)

            departure_info['is_live'] = False
            departure_info['sort_key'] = (
                next_dep - current_time).total_seconds()
        else:
            continue

        departures.append(departure_info)

    # Sort by soonest departure
    departures.sort(key=lambda x: x['sort_key'])

    return departures[:MAX_BUSES]


def create_display_image(departures, output_path='departures.jpg'):
    """Generate a 240x240 display image"""
    # Create image with pure black background
    img = Image.new('RGB', (IMAGE_WIDTH, IMAGE_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Try to load fonts, use bold for better readability
    try:
        header_font = ImageFont.truetype(
            "/System/Library/Fonts/Helvetica.ttc", 16)
        route_font = ImageFont.truetype(
            "/System/Library/Fonts/Helvetica.ttc", 30)
        dest_font = ImageFont.truetype(
            "/System/Library/Fonts/Helvetica.ttc", 11)
        time_font = ImageFont.truetype(
            "/System/Library/Fonts/Helvetica.ttc", 24)
        small_font = ImageFont.truetype(
            "/System/Library/Fonts/Helvetica.ttc", 9)
        next_time_font = ImageFont.truetype(
            "/System/Library/Fonts/Helvetica.ttc", 11)
    except:
        header_font = ImageFont.load_default()
        route_font = ImageFont.load_default()
        dest_font = ImageFont.load_default()
        time_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        next_time_font = ImageFont.load_default()

    # Draw header background
    draw.rectangle([(0, 0), (IMAGE_WIDTH, 28)], fill=HEADER_COLOR)

    # Draw title
    title = "DEPARTURES"
    draw.text((8, 6), title, fill=TEXT_COLOR, font=header_font)

    # Draw current time in top right corner
    current_time = datetime.now().strftime('%H:%M')
    # Get text width to right-align
    bbox = draw.textbbox((0, 0), current_time, font=header_font)
    time_width = bbox[2] - bbox[0]
    draw.text((IMAGE_WIDTH - time_width - 8, 6),
              current_time, fill="#888888", font=header_font)

    # Draw header separator
    draw.line([(0, 28), (IMAGE_WIDTH, 28)], fill=GRID_COLOR, width=2)

    # Column headers
    col_y = 32
    draw.text((8, col_y), "LINE", fill="#888888", font=small_font)
    draw.text((65, col_y), "DESTINATION", fill="#888888", font=small_font)
    draw.text((185, col_y), "TIME", fill="#888888", font=small_font)

    # Draw column separator
    draw.line([(0, 45), (IMAGE_WIDTH, 45)], fill=GRID_COLOR, width=1)

    # Draw departures in table format
    y_offset = 50
    row_height = 47

    for i, dep in enumerate(departures):
        if i >= MAX_BUSES:
            break

        # Alternating row background for better readability
        if i % 2 == 1:
            draw.rectangle(
                [(0, y_offset - 2), (IMAGE_WIDTH, y_offset + row_height - 2)],
                fill="#0a0a0a"
            )

        # Column 1: Route number with color indicator
        route_x = 8
        route_y = y_offset + 8

        # Small colored bar indicator
        bar_width = 4
        bar_height = 30
        draw.rectangle(
            [(route_x, route_y - 2), (route_x + bar_width, route_y + bar_height)],
            fill=dep['color']
        )

        # Route number in large white text
        route_text = dep['route_name']
        draw.text((route_x + bar_width + 6, route_y), route_text,
                  fill=TEXT_COLOR, font=route_font)

        # Column 2: Destination (moved further right to avoid overlap)
        dest_x = 80
        dest_y = route_y + 1

        # Truncate destination if too long
        headsign = dep['headsign']
        max_chars = 11
        if len(headsign) > max_chars:
            headsign = headsign[:max_chars - 1] + "."

        draw.text((dest_x, dest_y), headsign, fill="#CCCCCC", font=dest_font)

        # Additional times on second line (more visible)
        if 'additional_times' in dep:
            add_y = dest_y + 15
            add_text = f"{dep['additional_times']}"
            draw.text((dest_x, add_y), add_text,
                      fill="#999999", font=next_time_font)

        # Column 3: Time (right-aligned, more prominent)
        time_text = dep['time_text']
        time_color = ACCENT_COLOR if dep['is_live'] else TEXT_COLOR

        # Right align the time
        bbox = draw.textbbox((0, 0), time_text, font=time_font)
        time_width = bbox[2] - bbox[0]
        time_x = IMAGE_WIDTH - time_width - 6
        time_y = route_y + 1

        draw.text((time_x, time_y), time_text, fill=time_color, font=time_font)

        # Live indicator dot
        if dep['is_live']:
            dot_x = time_x - 10
            dot_y = time_y + 10
            draw.ellipse(
                [(dot_x, dot_y), (dot_x + 6, dot_y + 6)],
                fill=ACCENT_COLOR
            )

        # Draw row separator
        if i < MAX_BUSES - 1:
            line_y = y_offset + row_height - 2
            draw.line([(8, line_y), (IMAGE_WIDTH - 8, line_y)],
                      fill=GRID_COLOR, width=1)

        y_offset += row_height

    # Save image
    img.save(output_path, 'JPEG', quality=95)
    print(f"Display image saved to: {output_path}")
    return output_path


def main():
    """Main execution function"""
    print("Fetching bus departures...")
    data = fetch_departures()

    if not data:
        print("Failed to fetch departure data")
        return

    print("Parsing departures...")
    departures = parse_departures(data)

    if not departures:
        print("No departures found")
        return

    print(f"Found {len(departures)} upcoming buses")
    for dep in departures:
        print(f"  {dep['route_name']}: {dep['headsign']} - {dep['time_text']}")

    print("\nGenerating display image...")
    create_display_image(departures)

    print("Done!")


if __name__ == "__main__":
    main()
